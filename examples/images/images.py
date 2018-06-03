# -*- encoding: utf-8

import json
import os

import maya

from taggle.elastic import DATE_FORMAT
from taggle.models import TaggedDocument


class ImageManager:

    def __init__(self):
        self.last_indexed = None

        self.cache_dir = '/tmp/images'
        os.makedirs(self.cache_dir, exist_ok=True)

    def __repr__(self):
        return '<%s>' % (type(self).__name__)

    def cache_path(self, path):
        return os.path.join(self.cache_dir, path)

    def get_image_metadata(self):
        return json.load(open(self.cache_path('metadata.json')))

    def download_assets(self):
        print('Calling download_assets...')
        metadata = self.get_image_metadata()

    def get_data_for_indexing(self):
        for doc in self.get_image_metadata():
            print(doc['date_added'])
            print(maya.parse(
                doc['date_added']).datetime().strftime(DATE_FORMAT))
            doc['date_added'] = maya.parse(
                doc['date_added']).datetime().strftime(DATE_FORMAT)
            print(doc['date_added'])
            yield TaggedDocument(**doc)
