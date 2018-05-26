#!/usr/bin/env python
# -*- encoding: utf-8

from elasticsearch import Elasticsearch
from flask import Flask

app = Flask(__name__)

client = Elasticsearch(hosts=['http://localhost:9200'])

from taggle.elastic import index_documents
from taggle.models import TaggedDocument


@app.route('/')
def index():
    documents = [
        TaggedDocument(id=1, tags=['a', 'b'], foo='bar'),
        TaggedDocument(id=2, tags=['b', 'c'], bar='baz'),
        TaggedDocument(id=3, tags=['c', 'd'], baz='foo'),
    ]

    return index_documents(client=client, name='taggle', documents=documents)


if __name__ == '__main__':
    app.run(debug=True)
