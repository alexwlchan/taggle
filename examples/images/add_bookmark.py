#!/usr/bin/env python
# -*- encoding: utf-8
"""
Usage: add_bookmark.py --img_url=<URL> [--url=<URL>] [--title=<TITLE>] --tags=<TAGS>
"""

import json
import os
import re
import subprocess
import sys
from urllib.parse import urlparse
from urllib.request import urlretrieve
import uuid

import attr
import docopt

ROOT = subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel']).strip().decode('utf8')
sys.path.append(ROOT)

from taggle.models import TaggedDocument


if __name__ == '__main__':
    args = docopt.docopt(__doc__)

    tags = re.split('[ ,]', args['--tags'])

    data = {
        'id': str(uuid.uuid4()),
        'tags': tags,
    }

    name = os.path.basename(urlparse(args['--img_url']).path)

    if name.startswith('tumblr_'):
        shard = name.replace('tumblr_', '')[:2]
    else:
        shard = name[:2]

    outdir = os.path.join(os.environ['HOME'], 'scrapbook', 'images', shard)
    os.makedirs(outdir, exist_ok=True)

    outpath = os.path.join(outdir, name)
    assert not os.path.exists(outpath)
    urlretrieve(args['--img_url'], outpath)

    data['file'] = name
    data['image_id'] = os.path.join(shard, name)

    if args['--url']:
        data['url'] = args['--url']

    if args['--title']:
        data['title'] = args['--title']

    doc = TaggedDocument(**data)

    metadata = os.path.join(os.environ['HOME'], 'scrapbook', 'metadata.json')
    existing = json.load(open(metadata))
    assert isinstance(existing, list)

    d = attr.asdict(doc)
    d['date_added'] = d['date_added'].isoformat()

    existing.append(d)
    new_json = json.dumps(existing)
    open(metadata, 'w').write(new_json)
