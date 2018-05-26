# -*- encoding: utf-8
"""
This file contains utilities for dealing with tagged documents.
"""

import attr


@attr.s(init=False)
class TaggedDocument:
    id = attr.ib()
    tags = attr.ib()
    metadata = attr.ib()

    def __init__(self, id, tags, **metadata):
        self.id = id
        self.tags = tags
        self.metadata = metadata
        super().__init__()
