# -*- encoding: utf-8

import datetime as dt

import attr


@attr.s(init=False)
class TaggedDocument:
    id = attr.ib()
    tags = attr.ib()
    date_added = attr.ib()
    metadata = attr.ib()

    def __init__(self, id, tags, date_added=None, **metadata):
        self.id = id
        self.tags = tags
        self.date_added = date_added or dt.datetime.now()
        self.metadata = metadata.get('metadata') or metadata
        super().__init__()

    def __getattr__(self, name):
        try:
            return self.metadata[name]
        except KeyError:
            raise AttributeError(name)
