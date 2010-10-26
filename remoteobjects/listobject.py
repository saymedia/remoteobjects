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

from urlparse import urljoin, urlparse, urlunparse
import cgi
import inspect
import sys
import urllib

import remoteobjects.fields as fields
from remoteobjects.dataobject import find_by_name
from remoteobjects.promise import PromiseObject, PromiseError


class SequenceProxy(object):

    """An abstract class implementing the sequence protocol by proxying it to
    an instance attribute.

    `SequenceProxy` instances act like sequences by forwarding all sequence
    method calls to their `entries` attributes. The `entries` attribute should
    be a list or some other that implements the sequence protocol.

    """

    def make_sequence_method(methodname):
        """Makes a new function that proxies calls to `methodname` to the
        `entries` attribute of the instance on which the function is called as
        an instance method."""
        def seqmethod(self, *args, **kwargs):
            # Proxy these methods to self.entries.
            return getattr(self.entries, methodname)(*args, **kwargs)
        seqmethod.__name__ = methodname
        return seqmethod

    __len__      = make_sequence_method('__len__')
    __getitem__  = make_sequence_method('__getitem__')
    __setitem__  = make_sequence_method('__setitem__')
    __delitem__  = make_sequence_method('__delitem__')
    __iter__     = make_sequence_method('__iter__')
    __reversed__ = make_sequence_method('__reversed__')
    __contains__ = make_sequence_method('__contains__')


class OfOf(type):

    class _Module(object):
        pass

    def __new__(cls, name, bases, attr):
        modulename = attr['_modulename']
        sys.modules[modulename] = cls._Module()

        attr['_subclasses'] = {}
        attr['_basemodule'] = None

        return type.__new__(cls, name, bases, attr)


class PageOf(PromiseObject.__metaclass__):

    """Metaclass defining a `PageObject` containing a set of some other
    class's instances.

    Unlike most metaclasses, this metaclass can be called directly to define
    new `PageObject` classes that contain objects of a specified other class,
    like so:

    >>> PageOfEntry = PageOf(Entry)

    This is equivalent to defining ``PageOfEntry`` yourself:

    >>> class PageOfEntry(PageObject):
    ...     entryclass = Entry

    which is a `PageObject` of ``Entry`` instances.

    """

    __metaclass__ = OfOf

    _modulename = 'remoteobjects.listobject._pages'

    def __new__(cls, name, bases=None, attr=None):
        """Creates a new `PageObject` subclass.

        If `bases` and `attr` are specified, as in a regular subclass
        declaration, a new class is created as per the specified settings.

        If only `name` is specified, that value is used as a reference to a
        `RemoteObject` class to which the new `PageObject` class is bound.
        The `name` parameter can be either a name or a `RemoteObject` class,
        as when declaring a `remoteobjects.fields.Object` field.

        """
        direct = attr is None
        if direct:
            # Don't bother making a new subclass if we already made one for
            # this target.
            if name in cls._subclasses:
                return cls._subclasses[name]

            entryclass = name
            if callable(entryclass):
                name = cls.__name__ + entryclass.__name__
            else:
                name = cls.__name__ + entryclass

            bases = (cls._basemodule,)

            attr = {
                'entries': fields.List(fields.Object(entryclass)),
            }

        newcls = super(PageOf, cls).__new__(cls, name, bases, attr)

        # Save the result for later direct invocations.
        if direct:
            cls._subclasses[entryclass] = newcls
            newcls.__module__ = cls._modulename
            setattr(sys.modules[cls._modulename], name, newcls)
        elif cls._basemodule is None:
            cls._basemodule = newcls

        return newcls


class PageObject(SequenceProxy, PromiseObject):

    """A `RemoteObject` representing a set of other `RemoteObject` instances.

    Endpoints in APIs are often not objects themselves but lists of objects.

    As with regular `PromiseObject` instances, `PageObject` instances can be
    filtered by parameters that are then passed to your target API, such as a
    list of recent objects or a search. Filtering a `PageObject` instance by a
    parameter returns a new copy of that `PageObject` instance that includes
    the new parameter.

    The contents of regular `PageObject` instances will be decoded as with
    `Field` fields; that is, not decoded at all. To customize decoding of API
    contents, subclass `PageObject` and redefine the ``entries`` member with a
    `Field` instance that decodes the list content as necessary.

    As many API endpoints are sets of objects, to create a `PageObject`
    subclass for those endpoints, you can directly call its metaclass,
    `PageOf`, with the class reference you would use to construct an `Object`
    field. That is, these declarations are equivalent:

    >>> PageOfEntry = PageOf(Entry)

    >>> class PageOfEntry(PageObject):
    ...     entries = fields.List(fields.Object(Entry))

    For an ``Entry`` list you then fetch with the `PageOfEntry` class's
    `get()` method, all the entities in the list resource's `entries` member
    will be decoded into ``Entry`` instances.

    """

    __metaclass__ = PageOf

    entries = fields.List(fields.Field())

    def __getitem__(self, key):
        """Translates slice notation on a `ListObject` instance into ``limit``
        and ``offset`` filter parameters."""
        if isinstance(key, slice):
            args = dict()
            if key.start is not None:
                args['offset'] = key.start
                if key.stop is not None:
                    args['limit'] = key.stop - key.start
            elif key.stop is not None:
                args['limit'] = key.stop
            return self.filter(**args)

        try:
            getitem = super(PageObject, self).__getitem__
        except AttributeError:
            raise TypeError("'%s' object is unsubscriptable except by slices"
                % (type(self).__name__,))
        else:
            return getitem(key)


class ListOf(PageOf):

    _modulename = 'remoteobjects.listobject._lists'


class ListObject(PageObject):

    __metaclass__ = ListOf

    def update_from_dict(self, data):
        super(ListObject, self).update_from_dict({ 'entries': data })

    def to_dict(self):
        return super(ListObject, self).to_dict()['entries']
