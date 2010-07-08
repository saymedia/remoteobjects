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

remoteobjects are real subclassable Python objects on which you can build a
rich API library.

remoteobjects provides easy coding and transfer between Python objects and a
JSON REST API. You can define the resources in a RESTful API as `RemoteObject`
classes and their properties. These objects then support using the basic HTTP
verbs to request and submit data to the API.

remoteobjects have:

* programmable conversion between Python objects and your API's JSON resource
  format

* full and correct HTTP support through the `httplib2` library, including
  caching and authentication

* delayed evaluation of objects to avoid unnecessary requests


Example
=======

For example, you can build a simplified Twitter API library in the shell::

    >>> from remoteobjects import RemoteObject, fields, ListObject
    >>> class Tweeter(RemoteObject):
    ...     name        = fields.Field()
    ...     screen_name = fields.Field()
    ...     location    = fields.Field()
    ...
    >>> class Tweet(RemoteObject):
    ...     text    = fields.Field()
    ...     source  = fields.Field()
    ...     tweeter = fields.Object(Tweeter, api_name='user')
    ...
    >>> class Timeline(ListObject):
    ...     entries = fields.List(fields.Object(Tweet))
    ...
    >>> tweets = Timeline.get('http://twitter.com/statuses/public_timeline.json')
    >>> [t.tweeter.screen_name for t in tweets.entries[0:3]]
    ['eddeaux', 'CurtisLilly', '8email8']


For web APIs
============

`remoteobjects` is your Object RESTational Model for web APIs. You can define
each type of resource as a `RemoteObject` subclass, with all the resource's
member data specified as `remoteobjects.field.Field` instances for lightweight
typing.

As provided, `remoteobjects` works with JSON REST APIs. Such an API should be
arranged as a series of resources available at URLs as JSON entities
(generally objects). The API server should support editing through ``POST``
and ``PUT`` requests, and return appropriate HTTP status codes for errors.

The remoteobjects module is not *limited* to a particular kind of API. The
`RemoteObject` interface is provided in `DataObject`, `HttpObject`, and
`PromiseObject` layers you can reuse, extend, and override to tailor objects
to your target API.


Dictionaries with methods
=========================

While you can use an HTTP module and plain JSON coding to convert API
resources into dictionaries, `remoteobjects` gives you real objects with
encapsulated behavior instead of processing with external functions. A
`RemoteObject` instance's behavior is clearly packaged in your `RemoteObject`
subclass, where it is not only enforced through use of the object interface
but extensible and replaceable through plain old subclassing.

"""

__version__ = '1.1.1'
__date__ = '8 July 2010'
__author__ = 'Six Apart Ltd.'
__credits__ = """Brad Choate
Leah Culver
Mike Malone
Mark Paschal"""

import remoteobjects.dataobject
import remoteobjects.fields as fields
import remoteobjects.http
import remoteobjects.promise
from remoteobjects.listobject import ListObject, PageObject

__all__ = ('RemoteObject', 'fields', 'ListObject', 'PageObject', 'json')


class RemoteObject(remoteobjects.promise.PromiseObject):
    pass
