# -*- encoding: utf-8

import shlex
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
                'date_added': doc.date_added,
            }
            act.update(**doc.metadata)
            yield act

    actions = list(_actions())
    for _ in range(3):
        _, actions = bulk_helper(client=client, actions=actions)
        if not actions:
            break

    return index_name


def search_documents(client, index_name, query_string, page=1, page_size=96):
    body = _build_query(
        query_string=query_string,
        page=page,
        page_size=page_size
    )

    return client.search(index=index_name, body=body)


def _build_query(query_string, page, page_size):
    """Search an Elasticsearch index."""
    # These parameters can be set irrespective of the query string.
    # Note: 'from' is an offset parameter, and is 0-indexed.
    query = {
        'from': (page - 1) * page_size,
        'size': page_size,
    }

    def _is_filter(token):
        return _is_tag(token)

    def _is_tag(token):
        return token.startswith('tags:')

    query_string = query_string.strip()

    # Attempt to split the query string into tokens, but don't try too hard.
    # If it fails, we shouldn't error here --- better for it to error when it
    # hits Elasticsearch, if at all.
    try:
        tokens = shlex.split(query_string)
    except ValueError:
        tokens = [query_string]

    if not query_string or all(_is_filter(t) for t in tokens):
        query['sort'] = [{'date_added': 'desc'}]

    query['query'] = {'bool': {'filter': []}}
    bool_conditions = query['query']['bool']

    # If there are any fields which don't get replaced as tag filters,
    # add them with the simple_query_string syntax.
    simple_qs = ' '.join(t for t in tokens if not _is_filter(t))
    if simple_qs:
        bool_conditions['must'] = {
            'query_string': {'query': simple_qs}
        }

    # Any tags get added as explicit "this must match" fields.
    tag_tokens = [t for t in tokens if _is_tag(t)]
    tags = [t.split(':', 1)[-1] for t in tag_tokens]
    if tags:
        bool_conditions['filter'].append({
            'terms_set': {
                'tags.raw': {
                    'terms': tags,

                    # This tells Elasticsearch: every term should match!
                    'minimum_should_match_script': {
                        'source': 'params.num_terms'
                    }
                }
            }
        })

    if not bool_conditions['filter']:
        del bool_conditions['filter']

    # We always ask for an aggregation on tags.raw (which is a keyword field,
    # unlike the free-text field we can't aggregate), which is used to display
    # the contextual tag cloud.
    query['aggregations'] = {
        'tags': {
            'terms': {
                'field': 'tags.raw',
                'size': 120
            }
        }
    }

    return query
