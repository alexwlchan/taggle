#!/usr/bin/env python
# -*- encoding: utf-8

import os
import subprocess
import sys

from elasticsearch import Elasticsearch
from flask import render_template, request, url_for, Flask
from flask_login import login_required
from flask_scss import Scss
from jinja2 import StrictUndefined
import maya

sys.path.append(subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel']).strip().decode('utf8'))

from taggle.elastic import add_tag_to_query, index_documents, search_documents
from taggle.login import configure_login
from taggle.tagcloud import build_tag_cloud, TagcloudOptions

from filters import description_markdown, title_markdown
from pinboard import PinboardManager
from tagsort import custom_tag_sort


app = Flask(__name__)
app.jinja_env.undefined = StrictUndefined

scss = Scss(app)
scss.update_scss()

configure_login(app, password='password')


def _build_pagination_url(desired_page):
    if desired_page < 1:
        return None
    args = request.args.copy()
    args['page'] = desired_page
    return url_for(request.endpoint, **args)


def next_page_url(request):
    page = int(request.args.get('page', '1'))
    return _build_pagination_url(page + 1)


def prev_page_url(request):
    page = int(request.args.get('page', '1'))
    return _build_pagination_url(page - 1)


app.jinja_env.filters['add_tag_to_query'] = add_tag_to_query
app.jinja_env.filters['custom_tag_sort'] = custom_tag_sort
app.jinja_env.filters['description_markdown'] = description_markdown
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


client = Elasticsearch(hosts=['http://localhost:9200'])


manager = PinboardManager(
    username=open('username.txt').read().strip(),
    password=open('password.txt').read().strip(),
)


@app.route('/')
# @login_required
def index():
    manager.get_bookmark_metadata()

    index_name = index_documents(
        client=client,
        name='taggle',
        documents=list(manager.get_data_for_indexing())
    )

    import time
    time.sleep(1)

    query_string = request.args.get('query', '')

    results = search_documents(
        client=client,
        index_name=index_name,
        query_string=query_string,
        page=int(request.args.get('page', '1'))
    )

    return render_template(
        'index.html',
        results=results,
        query_string=query_string
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


if __name__ == '__main__':
    app.run(debug=True)
