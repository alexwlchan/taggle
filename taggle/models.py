# -*- encoding: utf-8
"""
This file contains utilities for dealing with tagged documents.
"""

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
        self.metadata = metadata
        super().__init__()
