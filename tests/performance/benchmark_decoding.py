#!/usr/bin/env python

# Copyright (c) 2009-2010 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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
