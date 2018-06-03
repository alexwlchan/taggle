#!/usr/bin/env python
# -*- encoding: utf-8
"""
Usage: viewer.py --metadata=<METADATA> --app_password=<APPPASSWORD> --es_host=<HOST> --loris_host=<LORIS_HOST> [--debug]
"""

import datetime as dt
import os
import subprocess
import sys
import time

import docopt
from elasticsearch import Elasticsearch
from flask import render_template, request, url_for, Flask
from flask_apscheduler import APScheduler
from flask_login import login_required
from flask_scss import Scss
from jinja2 import StrictUndefined
import maya

sys.path.append(subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel']).strip().decode('utf8'))

from taggle.elastic import add_tag_to_query, index_documents, search_documents
from taggle.flask_utils import generation_time, next_page_url, prev_page_url
from taggle.login import configure_login
from taggle.tagcloud import build_tag_cloud, TagcloudOptions

from filters import description_markdown, title_markdown
from pinboard import PinboardManager
from tagsort import custom_tag_sort


app = Flask(__name__)


app.jinja_env.filters['add_tag_to_query'] = add_tag_to_query
app.jinja_env.filters['custom_tag_sort'] = custom_tag_sort
app.jinja_env.filters['description_markdown'] = description_markdown
app.jinja_env.filters['generation_time'] = generation_time
app.jinja_env.filters['next_page_url'] = next_page_url
app.jinja_env.filters['prev_page_url'] = prev_page_url
app.jinja_env.filters['slang_time'] = lambda d: maya.parse(d).slang_time()
app.jinja_env.filters['title_markdown'] = title_markdown

options = TagcloudOptions(
    size_start=9, size_end=24, colr_start='#999999', colr_end='#ca3b0c'
)

app.jinja_env.filters['build_tag_cloud'] = lambda t: build_tag_cloud(
    t, options
)

# The query is exposed in the <input> search box with the ``safe`` filter,
# so HTML entities aren't escaped --- but we need to avoid closing the
# value attribute early.
app.jinja_env.filters['display_query'] = lambda q: q.replace('"', '&quot;')


def update_index():
    manager.get_bookmark_metadata()

    try:
        mtime = os.stat(manager.cache_path('write_marker')).st_mtime
        if time.time() - mtime > 45:
            print('Index already up-to-date...')
            return
    except FileNotFoundError:
        pass

    index_documents(
        client=client,
        index_name='pinboard',
        documents=list(manager.get_data_for_indexing())
    )


@app.route('/')
@login_required
def index():
    start_time = dt.datetime.now()
    query_string = request.args.get('query', '')

    results = search_documents(
        client=client,
        index_name='pinboard',
        query_string=query_string,
        page=int(request.args.get('page', '1')),
        query_params={
            '_source': {
                'excludes': ['full_text']
            }
        }
    )

    return render_template(
        'index.html',
        results=results,
        query_string=query_string,
        start_time=start_time
    )


@app.errorhandler(404)
def page_not_found(error):
    message = (
        'The requested URL was not found on the server. If you entered the '
        'URL manually please check your spelling and try again.'
    )
    return render_template(
        'error.html',
        title='404 Not Found',
        message=message), 404


class Config(object):
    index_name = None

    def __init__(self, manager):
        self.JOBS = [
            {
                'id': 'update_index',
                'func': update_index,
                'trigger': 'interval',
                'seconds': 30,
                'timezone': 'utc',
            },
            {
                'id': 'download_assets',
                'func': manager.download_assets,
                'trigger': 'interval',
                'seconds': 600,
                'timezone': 'utc',
            }
        ]


if __name__ == '__main__':
    args = docopt.docopt(__doc__)

    client = Elasticsearch(hosts=[f'http://{args["--es_host"]}'])

    manager = PinboardManager(
        username=args['--pin_username'],
        password=args['--pin_password']
    )

    app.config.from_object(Config(manager))
    app.jinja_env.undefined = StrictUndefined

    scss = Scss(app)
    scss.update_scss()

    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    configure_login(app, password=args['--app_password'])

    app.run(host='0.0.0.0', debug=args['--debug'])
