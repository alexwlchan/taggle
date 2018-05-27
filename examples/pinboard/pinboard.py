# -*- encoding: utf-8

import datetime as dt

import requests


class PinboardManager:

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.last_fetched = None

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

    def update(self):
        last_updated_resp = self._api_get('/posts/update')['update_time']
        last_updated_date = dt.datetime.strptime(
            last_updated_resp, '%Y-%m-%dT%H:%M:%SZ')

        if (
            (self.last_fetched is None) or
            (last_updated_date - self.last_fetched).seconds > 60
        ):
            print('We need to do an update!')
        else:
            print("We're already up-to-date!")

        self.last_fetched = last_updated_date
