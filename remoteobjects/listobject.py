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


class _ListsModule(object):
    pass

lists_module_name = 'remoteobjects.listobject._lists'
lists_module = _ListsModule()
sys.modules[lists_module_name] = lists_module


class ListOf(PromiseObject.__metaclass__):

    """Metaclass defining a `ListObject` containing a list of some other
    class's instances.

    Unlike most metaclasses, this metaclass can be called directly to define
    new `ListObject` classes that contain objects of a specified other class,
    like so:

    >>> ListOfEntry = ListOf(Entry)

    This is equivalent to defining ``ListOfEntry`` yourself:

    >>> class ListOfEntry(ListObject):
    ...     entryclass = Entry

    which is a `ListObject` of ``Entry`` instances.

    """

    _subclasses = {}

    def __new__(cls, name, bases=None, attr=None):
        """Creates a new `ListObject` subclass.

        If `bases` and `attr` are specified, as in a regular subclass
        declaration, a new `ListObject` subclass bound to no particular
        `RemoteObject` class is created. `name` is the declared name of the
        new class, as usual.

        If only `name` is specified, that value is used as a reference to a
        `RemoteObject` class to which the new `ListObject` class is bound.
        The `name` parameter can be either a name or a `RemoteObject` class,
        as when declaring a `fields.Object` on a class.

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
            bases = (ListObject,)
            attr = {
                'entryclass': entryclass,
                'entries': fields.List(fields.Object(entryclass)),
            }
        else:
            # Make sure classes we create conventionally are SequenceProxies.
            # As that includes ListObject, classes that are created directly
            # inherit SequenceProxy behavior through ListObject.
            bases = bases + (SequenceProxy,)

        newcls = super(ListOf, cls).__new__(cls, name, bases, attr)

        # Save the result for later direct invocations.
        if direct:
            orig_name = attr['entryclass']
            cls._subclasses[orig_name] = newcls
            newcls.__module__ = lists_module_name
            setattr(lists_module, name, newcls)
        return newcls


class ListObject(PromiseObject):

    """A `RemoteObject` representing a list of other `RemoteObject` instances.

    Endpoints in APIs are often not objects themselves but lists of objects.

    As with regular `PromiseObject` instances, `ListObject` instances can be
    filtered by parameters that are then passed to your target API, such as a
    list of recent objects or a search. Filtering a `ListObject` instance by a
    parameter returns a new copy of that `ListObject` instance that includes
    the new parameter.

    The contents of regular `ListObject` instances will be decoded as with
    `Field` fields; that is, not decoded at all. To customize decoding, of API
    contents, subclass `ListObject` and redefine the ``entries`` member with a
    `Field` instance that decodes the list content as necessary.

    As many API endpoints are lists of objects, to create a `ListObject`
    subclass for those endpoints you can directly call its metaclass,
    `ListOf`, with the class reference you would use to construct an `Object`
    field. That is, these declarations are equivalent:

    >>> ListOfEntry = ListOf(Entry)

    >>> class ListOfEntry(ListObject):
    ...     entries = fields.List(fields.Object(Entry))

    For an ``Entry`` list you then fetch with the `ListOfEntry` class's
    `get()` method, all the entities in the list resource's `entries` member
    will be decoded into ``Entry`` instances.

    """

    __metaclass__ = ListOf

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
            getitem = super(ListObject, self).__getitem__
        except AttributeError:
            raise TypeError("'%s' object is unsubscriptable except by slices"
                % (type(self).__name__,))
        else:
            print "getitem is %r" % getitem
            return getitem(key)
