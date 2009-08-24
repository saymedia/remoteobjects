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
