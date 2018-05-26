#!/usr/bin/env python
# -*- encoding: utf-8

from elasticsearch import Elasticsearch
from flask import Flask

app = Flask(__name__)

client = Elasticsearch(hosts=['http://localhost:9200'])

from taggle.elastic import create_index


@app.route('/')
def index():
    create_index(client=client, name='taggle-test-index')
    return 'Hello world!'


if __name__ == '__main__':
    app.run(debug=True)
