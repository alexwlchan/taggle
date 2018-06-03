# -*- encoding: utf-8

import datetime as dt


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
