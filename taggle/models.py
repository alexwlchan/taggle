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


@attr.s
class ResultList:
    """Represents a set of results from Elasticsearch.

    This stores some information about the results from the query, and
    some convenience methods about records on the query.

    """
    total_size = attr.ib()
    page = attr.ib()
    page_size = attr.ib()
    documents = attr.ib()
    tags = attr.ib()

    @property
    def start_idx(self):
        return 1 + self.page_size * (self.page - 1)

    @property
    def end_idx(self):
        return min(self.total_size, self.page_size * self.page)

    @property
    def total_pages(self):
        return math.ceil(self.total_size / self.page_size)
