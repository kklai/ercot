#! /usr/bin/env python
from __future__ import print_function

from glob import glob
import datetime
import json
import logging
import os
import sys
import time

import dataset

from ercot.utils import normalize_html

URL = 'http://www.ercot.com/content/cdr/html/real_time_system_conditions.html'
DATA_DIR = "../download"


def process(store, files):
    """Process all the files."""
    for f in files:
        try:
            with open(f, 'r') as fh:
                data = normalize_html(fh)
            ctime = int(time.mktime(data['timestamp'].timetuple()))
            # TODO delete file after parsing
        except AssertionError as e:
            # malformed HTML
            logger.error("{} {}".format(f, e))
            continue
        logger.info("{} {}".format(ctime, data))
        store.upsert(data, ['timestamp'])


def batch_process(store, files, batch=False):
    """Process all the files in batches."""
    # TODO abstract common stuff with `process()`
    for f in files:
        try:
            with open(f, 'r') as fh:
                data = normalize_html(fh)
        except AssertionError as e:
            # malformed HTML
            logger.error("{} {}".format(f, e))
            continue
        yield data


def get_db_store():
    """Get the dataset table object that stores our data."""
    # TODO abstract db settings out of here
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///test.db')
    db = dataset.connect(database_url)
    table = db['ercot_realtime']
    table.create_index(['timestamp'])  # WISHLIST make this UNIQUE
    return table


def get_from_website():
    """Get the current data directly from the website."""
    # `parse` will also take a url (http only, no https)
    data = normalize_html(URL)
    table = get_db_store()
    table.upsert(data, ['timestamp'])
    return data


def main(batch):
    """Get the data from downloaded files."""
    table = get_db_store()
    files = glob(os.path.join(DATA_DIR, '*.html'))
    if batch:
        table.insert_many(batch_process(table, files, batch))
    else:
        process(table, files)


def dumps(data):
    """JSON encode junk"""
    # http://stackoverflow.com/questions/455580/json-datetime-between-python-and-javascript
    dthandler = (lambda obj: obj.isoformat(sep=' ')
            if isinstance(obj, datetime.datetime) else None)
    return json.dumps(data, default=dthandler),


logger = logging.getLogger(__name__)
if __name__ == "__main__":
    batch = '--initial' in sys.argv
    if '--now' in sys.argv:
        print(dumps(get_from_website()))
    else:
        main(batch)
