#!/usr/bin/env python
# -*- encoding: utf-8

from elasticsearch import Elasticsearch
from flask import Flask

app = Flask(__name__)

client = Elasticsearch(hosts=['http://localhost:9200'])

from taggle.elastic import index_documents, search_documents
from taggle.models import TaggedDocument


@app.route('/')
def index():
    documents = [
        TaggedDocument(id=1, tags=['ab', 'ba'], foo='bar'),
        TaggedDocument(id=2, tags=['ba', 'cd'], bar='baz'),
        TaggedDocument(id=3, tags=['cd', 'de'], baz='foo'),
    ]

    print(documents)
    index_name = index_documents(client=client, name='taggle', documents=documents)
    print(index_name)

    import time
    time.sleep(1)

    return str(search_documents(client=client, index_name=index_name, query_string='tags:ba'))


if __name__ == '__main__':
    app.run(debug=True)
