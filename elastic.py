# -*- encoding: utf-8

from elasticsearch.exceptions import RequestError as ElasticsearchRequestError


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
