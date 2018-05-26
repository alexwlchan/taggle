# -*- encoding: utf-8

import time

from elasticsearch.exceptions import RequestError as ElasticsearchRequestError
from elasticsearch.helpers import bulk as bulk_helper


def create_index(client, name):
    """Creates an index with the appropriate mapping for the tags field."""
    try:
        client.indices.create(
            index=name,
            body={
                'mappings': {
                    name: {
                        'properties': {
                            'tags': {
                                'type': 'text',
                                'fields': {
                                    'raw': {'type': 'keyword'}
                                }
                            }
                        }
                    }
                }
            }
        )
    except ElasticsearchRequestError as err:
        if err.info['error']['type'] == 'resource_already_exists_exception':
            pass
        else:
            raise


def index_documents(client, name, documents):
    """Index a series of documents into an Elasticsearch index."""
    index_name = f'{name}-{time.time()}'

    create_index(client=client, name=index_name)

    def _actions():
        for doc in documents:
            act = {
                '_op_type': 'index',
                '_index': index_name,
                '_type': index_name,
                '_id': doc.id,
                'tags': doc.tags,
            }
            act.update(**doc.metadata)
            yield act

    actions = list(_actions())
    for _ in range(3):
        _, actions = bulk_helper(client=client, actions=actions)
        if not actions:
            break

    return index_name
