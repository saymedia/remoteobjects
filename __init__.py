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

    >>> from remoteobjects import RemoteObject, fields
    >>> class Tweeter(remoteobjects.RemoteObject):
    ...     name        = fields.Field()
    ...     screen_name = fields.Field()
    ...     location    = fields.Field()
    ...
    >>> class Tweet(remoteobjects.RemoteObject):
    ...     text    = fields.Field()
    ...     source  = fields.Field()
    ...     tweeter = fields.Object(Tweeter, api_name='user')
    ...
    >>> class Timeline(remoteobjects.ListObject):
    ...     entries = fields.List(fields.Object(Tweet))
    ...     def update_from_dict(self, data):
    ...         super(Timeline, self).update_from_dict({ 'entries': data })
    ...
    >>> t = Timeline.get('http://twitter.com/statuses/public_timeline.json')
    >>> [tweet.tweeter.screen_name for tweet in t.entries[0:3]]
    ['eddeaux', 'CurtisLilly', '8email8']


"""

import remoteobjects.dataobject
import remoteobjects.fields as fields
import remoteobjects.http
import remoteobjects.promise
from remoteobjects.promise import ListObject

__all__ = ('RemoteObject', 'fields', 'ListObject')


class RemoteObject(remoteobjects.promise.PromiseObject):
    pass
