#!/usr/bin/env python

"""
This will benchmark remoteobjects decoding speed. It will decode the JSON data
you specify as the first argument into the remoteobject subclass you specify as
the second argument. The decode process is run as many times as you specify (via
the -n flag). The raw times to decode the JSON data will be dumped to stdout.
"""

import optparse
import time
import remoteobjects
import mox

from tests import utils


def test_decoding(object_class, json, count):
    request = {
        'uri': 'http://example.com/ohhai',
        'headers': {'accept': 'application/json'},
    }
    h = utils.mock_http(request, json)

    # warm up remoteobjects
    o = object_class.get('http://example.com/ohhai', http=h)
    o.deliver()

    for _ in xrange(count):
        h = utils.mock_http(request, json)

        t = time.time()
        o = object_class.get('http://example.com/ohhai', http=h)
        o.deliver()
        yield (time.time() - t)


if __name__ == '__main__':
    parser = optparse.OptionParser(
        usage="%prog [options] json_file remoteobject_class",
        description=("Test the performance of decoding JSON into remoteobjects."))
    parser.add_option("-n", action="store", type="int", default=100,
                      dest="num_runs", help="Number of times to run the test.")
    options, args = parser.parse_args()

    if len(args) != 2:
        parser.error("Incorrect number of arguments")

    try:
        fd = open(args[0])
        json = fd.read()
    except:
        parser.error("Unable to read file: '%s'" % args[1])
    finally:
        fd.close()

    module_name, _, class_name = args[1].rpartition('.')
    try:
        module = __import__(module_name)
    except ImportError, e:
        parser.error(e.message)

    try:
        RemoteObject = getattr(module, class_name)
    except AttributeError, e:
        parser.error(e.message)

    for t in test_decoding(RemoteObject, json, options.num_runs):
        print t
