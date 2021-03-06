# -*- encoding: utf-8

import math
import shlex
import time

import attr
from elasticsearch.exceptions import RequestError as ElasticsearchRequestError
from elasticsearch.helpers import bulk as bulk_helper

from taggle.models import TaggedDocument


DATE_FORMAT = '%Y%m%dT%H%M%SZ'


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


def create_index(client, name):
    """Creates an index with the appropriate mapping for the tags field."""
    try:
        client.indices.create(
            index=name,
            body={
                'mappings': {
                    name: {
                        'properties': {
                            'date_added': {
                                'type': 'date',
                                'format': 'basic_date_time_no_millis',
                            },
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


def index_documents(client, index_name, documents):
    """Index a series of documents into an Elasticsearch index."""
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

    print('Cleaning up deleted bookmarks...')
    indexed = client.search(index=index_name, _source=False, size=10000)
    hits = indexed['hits']['hits']
    indexed_ids = [h['_id'] for h in hits]

    delete_actions = []
    document_ids = [doc.id for doc in documents]
    for i in indexed_ids:
        if i not in document_ids:
            delete_actions.append({
                '_op_type': 'delete',
                '_index': index_name,
                '_type': index_name,
                '_id': i,
            })

    if delete_actions:
        resp = bulk_helper(client=client, actions=delete_actions)


def _join_dicts(x, y):
    x.update(y)
    return x


def search_documents(client,
                     index_name,
                     query_string,
                     query_params=None,
                     page=1,
                     page_size=96):
    body = _build_query(
        query_string=query_string,
        page=page,
        page_size=page_size
    )

    if query_params is not None:
        body.update(query_params)

    resp = client.search(index=index_name, body=body)

    total_size = resp['hits']['total']
    documents = [
        TaggedDocument(**_join_dicts(doc['_source'], {'id': doc['_id']}))
        for doc in resp['hits']['hits']
    ]

    aggregations = resp['aggregations']
    tags = {
        bucket['key']: bucket['doc_count']
        for bucket in aggregations['tags']['buckets']
    }

    return ResultList(
        total_size=total_size,
        documents=documents,
        page=page,
        page_size=page_size,
        tags=tags
    )


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
                'size': 200
            }
        }
    }

    return query


def add_tag_to_query(query_string, new_tag):
    """Given a query in Elasticsearch's query string syntax, add another tag
    to further filter the query.

    https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html

    """
    tag_marker = f'tags:{new_tag}'

    # Look for the tag in the existing query; remember if might be at the end!
    if (
        (tag_marker + ' ') in query_string or
        query_string.endswith(tag_marker)
    ):
        return query_string

    return ' '.join([query_string, tag_marker]).strip()
