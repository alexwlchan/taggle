# -*- encoding: utf-8

import datetime as dt
import os

from flask import Flask
from flask_scss import Scss
from jinja2 import StrictUndefined
import maya

from taggle.elastic import add_tag_to_query


def TaggleApp(name, instance_path):
    app = Flask(__name__,
        static_folder=os.path.join(instance_path, 'static'),
        template_folder=os.path.join(instance_path, 'templates')
    )

    scss = Scss(app,
        asset_dir=os.path.join(instance_path, 'assets'),
        static_dir=os.path.join(instance_path, 'static')
    )
    scss.update_scss()

    app.jinja_env.filters['add_tag_to_query'] = add_tag_to_query
    app.jinja_env.filters['generation_time'] = generation_time
    app.jinja_env.filters['next_page_url'] = next_page_url
    app.jinja_env.filters['prev_page_url'] = prev_page_url
    app.jinja_env.filters['slang_time'] = lambda d: maya.parse(d).slang_time()

    app.jinja_env.undefined = StrictUndefined

    return app



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


def generation_time(start_time):
    diff = dt.datetime.now() - start_time
    time = (diff.seconds * 1e6 + diff.microseconds) / 1e6
    return '%.3f' % time
