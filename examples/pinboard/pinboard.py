# -*- encoding: utf-8

import datetime as dt
import json
import os
import tempfile

import requests


class PinboardManager:

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.last_fetched = None

        self.cache_dir = tempfile.mkdtemp()

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

            posts = self._api_get('/posts/all')
            json_str = json.dumps(posts)
            with open(self.cache_path('bookmarks.json'), 'w') as f:
                f.write(json_str)
            return posts
        else:
            print("We're already up-to-date!")
            return json.load(open(self.cache_path('bookmarks.json')))
