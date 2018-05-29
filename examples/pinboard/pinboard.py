# -*- encoding: utf-8

import datetime as dt
import json
import os
import re
import tempfile

from bs4 import BeautifulSoup
import maya
import readability
import requests
from requests.exceptions import RequestException

from taggle.elastic import DATE_FORMAT
from taggle.models import TaggedDocument


def updates_cache(fn):
    def wrapper(self, *args, **kwargs):
        res = fn(self, *args, **kwargs)
        open(self.cache_path('write_marker'), 'wb').write(b'')
        return res

    return wrapper


class PinboardManager:

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.last_fetched = None

        self.cache_dir = '/tmp/pinboard'
        os.makedirs(self.cache_dir, exist_ok=True)

    def __repr__(self):
        return '<%s username=%r>' % (type(self).__name__, self.username)

    def _api_get(self, path, params=None):
        if params is None:
            params = {}
        params['format'] = 'json'

        resp = requests.get(
            f'https://api.pinboard.in/v1{path}',
            auth=(self.username, self.password),
            params=params
        )
        resp.raise_for_status()
        return resp.json()

    def cache_path(self, path):
        return os.path.join(self.cache_dir, path)

    def get_bookmark_metadata(self):
        last_updated_resp = self._api_get('/posts/update')['update_time']
        last_updated_date = dt.datetime.strptime(
            last_updated_resp, '%Y-%m-%dT%H:%M:%SZ')

        if (
            (self.last_fetched is None) or
            (last_updated_date - self.last_fetched).seconds > 60
        ):
            print('We need to do an update!')
            self.last_fetched = last_updated_date
            return self._get_enriched_data()
        else:
            print("We're already up-to-date!")
            return json.load(open(self.cache_path('enriched_metadata.json')))

    def _login_pinboard_sess(self):
        sess = requests.Session()
        sess.hooks['response'].append(
            lambda r, *args, **kwargs: r.raise_for_status()
        )

        # Yes, Pinboard sends you into a redirect loop if you're not in a
        # browser.  It's very silly.
        resp = sess.post(
            'https://pinboard.in/auth/',
            data={'username': self.username, 'password': self.password},
            allow_redirects=False
        )
        assert resp.headers['Location'] != '?error=bad+login'

        return sess

    @updates_cache
    def _get_enriched_data(self):
        # Page through my Pinboard account, and attach the Pinboard IDs.
        sess = self._login_pinboard_sess()

        pinboard_metadata = []
        starred = []
        archive_links = {}
        url = f'https://pinboard.in/u:{self.username}'

        while True:
            print(f'Processing {url}...')
            resp = sess.get(url)

            # Starred data is in a <script> tag:
            #
            #     var starred = ["123","124"];
            #
            starredjs = resp.text.split('var starred = ')[1].split(';')[0].strip('[]')
            stars = [s.strip('"') for s in starredjs.split(',')]
            starred.extend(stars)

            # Turns out all the bookmark data is declared in a massive <script>
            # tag in the form:
            #
            #   var bmarks={};
            #   bmarks[1234] = {...};
            #   bmarks[1235] = {...};
            #
            # so let's just read that!
            bookmarkjs = resp.text.split('var bmarks={};')[1].split('</script>')[0]

            # I should use a proper JS parser here, but for now simply looking
            # for the start of variables should be enough.
            bookmarks_list = re.split(r';bmarks\[[0-9]+\] = ', bookmarkjs.strip(';'))

            # The first entry is something like '\nbmarks[1234] = {...}',
            # which we can discard.
            bookmarks_list[0] = re.sub(r'^\s*bmarks\[[0-9]+\] = ', '', bookmarks_list[0])
            pinboard_metadata.extend(json.loads(b) for b in bookmarks_list)

            # And now get all the archive links
            soup = BeautifulSoup(resp.text, 'html.parser')
            bookmarks = soup.find('div', attrs={'id': 'bookmarks'})
            for book in bookmarks.findAll('div', attrs={'class': 'bookmark'}):
                cache = book.find('a', attrs={'class': 'cached'})
                if cache is not None:
                    archive_links[book.attrs['id']] = cache.attrs['href']

            # Now look for the thing with the link to the next page:
            #
            #   <div id="bottom_next_prev">
            #       <a class="next_prev" href="...">earlier</a>
            #
            bottom_next_prev = resp.text.split('<div id="bottom_next_prev">')[1].split('</div>')[0]
            earlier, _ = bottom_next_prev.split('</a>', 1)
            if 'earlier' in earlier:
                url = 'https://pinboard.in' + earlier.split('href="')[1].split('"')[0]
            else:
                break

        enriched_metadata = {
            'archive_links': archive_links,
            'starred': sorted(set(starred)),
            'metadata': pinboard_metadata,
        }

        json_str = json.dumps(enriched_metadata)
        with open(self.cache_path('enriched_metadata.json'), 'w') as f:
            f.write(json_str)

        return enriched_metadata

    @updates_cache
    def download_assets(self):
        txt_dir = os.path.join(self.cache_dir, 'txt')
        os.makedirs(txt_dir, exist_ok=True)
        try:
            data = json.load(open(self.cache_path('enriched_metadata.json')))
        except FileNotFoundError:
            return

        print('Downloading archive...')
        sess = self._login_pinboard_sess()

        for bookmark in data['metadata']:
            try:
                archive_id = data['archive_links'][bookmark['id']]
            except KeyError:
                continue

            local_archive_id = archive_id.replace('/cached', '').replace('/', '')

            out_path = os.path.join(txt_dir, f'{local_archive_id}.txt')
            if os.path.exists(out_path):
                continue

            print(f'Downloading archive for {bookmark["id"]}...')
            resp = sess.get(f'https://pinboard.in/{archive_id}')
            archive_soup = BeautifulSoup(resp.text, 'html.parser')
            frames = archive_soup.findAll('iframe')
            if len(frames) != 2:
                print(frames)
                continue

            try:
                resp = sess.get(
                    frames[1].attrs['src'],
                    headers={
                        'Referer': f'https://pinboard.in/{archive_id}'
                    }
                )
            except RequestException as exc:
                print(exc)
                continue
            doc = readability.Document(resp.text)
            with open(out_path, 'w') as f:
                f.write(doc.summary())

    def get_data_for_indexing(self):
        try:
            data = json.load(open(self.cache_path('enriched_metadata.json')))
        except FileNotFoundError:
            return

        for bookmark in data['metadata']:
            id = bookmark['id']
            is_starred = id in data['starred']
            archive_id = data['archive_links'].get(id)
            if archive_id is not None:
                archive_id = archive_id.replace('/cached', '').replace('/', '')

                try:
                    full_text = open(
                        self.cache_path(f'txt/{archive_id}.txt')).read()
                except FileNotFoundError:
                    full_text = None
            else:
                full_text = None

            yield TaggedDocument(
                id=id,
                tags=bookmark['tags'],
                date_added=maya.parse(bookmark['created']).datetime().strftime(DATE_FORMAT),
                title=bookmark['title'],
                url=bookmark['url'],
                description=bookmark['description'],
                starred=is_starred,
                archive_id=archive_id,
                full_text=full_text,
                toread=(bookmark['toread'] != '0'),
            )
