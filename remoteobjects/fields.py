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

Fields are class attributes for `RemoteObject` subclasses that provide data
coding functionality for your properties.

The `remoteobjects.fields` module also provides functionality for other
field-like properties through the `Property` class, and a `Property` subclass
that offers links between `RemoteObject` instances, `Link`.

"""

from datetime import datetime, tzinfo, timedelta
import logging
import time
import urlparse

import remoteobjects.dataobject


class Property(object):

    """An attribute that can be installed declaratively on a `DataObject` to
    provide data encoding or loading behavior.

    The primary kinds of `Property` objects are `Field` (and its subclasses)
    and `Link` objects.

    """

    def install(self, cls, attrname):
        """Signals to the `Property` that it has been installed on the given
        class as an attribute with the given name.

        This implementation does nothing. Override this method to customize
        the behavior to install an attribute on DataObject classes where your
        field is declared.

        """
        pass


class Field(Property):

    """A property for encoding object attributes as dictionary values and
    decoding dictionary values into object attributes.

    Declare a `Field` instance for each attribute of a `DataObject` that
    should be encoded to or decoded from a dictionary.

    Use a `Field` instance directly for simple `DataObject` attributes that
    can be the same type as their dictionary values. That is, use `Field`
    fields for strings, numbers, and boolean values. If your attribute data
    does need converted, use one of the `Field` subclasses from the
    `remoteobjects.fields` module to encode and decode your data as
    appropriate.

    If your attribute needs converted specially, override the `decode()` and
    `encode()` methods in a new subclass of `Field`. For example, the
    `fields.Datetime` subclass of `Field` encodes Python `datetime.datetime`
    instances in a dictionary as timestamp strings.

    """

    def __init__(self, api_name=None, default=None):
        """Sets the field's matching deserialization field and default value.

        Optional parameter `api_name` is the key of this field's matching
        value in a dictionary. If not given, the attribute name of the field
        when its class was defined is used. (The attribute of the object
        containing the decoded value will always be the attribute name of the
        field as declared.)

        Optional parameter `default` is the default value to use for this
        attribute when the dictionary to decode does not contain a value.
        `default` can be a value or callable function. If `default` is a
        callable function, it is called when a dictionary is decoded into an
        instance, is passed the object to decode into and the dictionary to
        decode from, and should return the default value of the attribute. As
        fields are processed in no particular order, a `default` function
        should not set the value itself, nor should it depend on values
        already decoded into the DataObject instance.

        Default values are *not* special when encoding an object, so those
        values will stick on `DataObject` instances that are saved and
        retrieved (such as `RemoteObject` instances).

        """
        self.api_name = api_name
        self.default  = default

    def install(self, attrname, cls):
        self.attrname = attrname
        if self.api_name is None:
            self.api_name = attrname
        # attrname has to be set before of_cls or Constant fields break.
        self.of_cls = cls

    def __get__(self, obj, cls):
        """Returns the field's value on the given object instance, or the
        field's default value if no value for the field is available.

        Note the field's value will be decoded from API data if necessary,
        raising any exceptions that the field's `decode()` method may raise.

        """
        if obj is None:
            # Yield the real field instance when gotten through the class.
            return self

        if self.attrname not in obj.__dict__:
            try:
                value = obj.api_data[self.api_name]
            except KeyError:
                if callable(self.default):
                    value = self.default(obj)
                else:
                    value = self.default
            else:
                value = self.decode(value)
            # Store the value so we need decode it only once.
            obj.__dict__[self.attrname] = value

        return obj.__dict__[self.attrname]

    def __set__(self, obj, value):
        obj.__dict__[self.attrname] = value

    def __delete__(self, obj):
        # Delete both the instance and API data, so we'll get a real
        # attribute miss next time and return the field's default.
        try:
            del obj.__dict__[self.attrname]
        except KeyError:
            pass

        try:
            del obj.api_data[self.api_name]
        except KeyError:
            pass

    def decode(self, value):
        """Decodes a dictionary value into a `DataObject` attribute value.

        This implementation returns the `value` parameter unchanged. This is
        generally only appropriate for strings, numbers, and boolean values.
        Use another `Field` class (or a custom `Field` implementation that
        overrides this method) if you need to convert objects.

        """
        return value

    def encode(self, value):
        """Encodes a `DataObject` attribute value into a dictionary value.

        This implementation returns the `value` parameter unchanged. This is
        generally only appropriate for strings, numbers, and boolean values.
        Use another `Field` class (or a custom `Field` implementation that
        overrides this method) if you need to convert objects.

        """
        return value


class Constant(Field):

    """A field for data that always has a certain value for all instances of
    the owning class.

    Use this field for an attribute of an object that is always the same for
    every instance of that class. For instance, if you define subclasses for a
    `DataObject` that represent different kinds of search results based on
    type, and there's a `type` field that says which class the result will be,
    use this field for the invariant `type` field with a different matching
    value for each subclass.

    """

    def __init__(self, value, **kwargs):
        """Sets the field's constant value to parameter `value`."""
        super(Constant, self).__init__(**kwargs)
        self.value = value

    def install(self, attrname, cls):
        """Records the class that owns this field.

        This implementation also registers the owning class by this constant
        field's value, so that `DataObject.subclass_with_constant_field()`
        will find this field's class.

        """
        super(Constant, self).install(attrname, cls)

        # Register class by this field.
        cf = remoteobjects.dataobject.classes_by_constant_field
        attrname, value = self.attrname, self.value
        if attrname not in cf:
            cf[attrname] = dict()
        cf[attrname][value] = cls.__name__

    def __get__(self, obj, cls):
        if obj is None:
            # Yield the real field instance when gotten through the class.
            return self
        # Since it's a constant, always return the same value.
        return self.value
    
    def __set__(self, obj, value):
        # If it's the correct value, do nothing. Else, raise an exception.
        if value != self.value:
            raise ValueError('Value %r is not expected value %r'
                % (value, self.value))

    def decode(self, value):
        if value != self.value:
            raise ValueError('Value %r is not expected value %r'
                % (value, self.value))
        return self.value

    def encode(self, value):
        # Don't even bother caring what we were given; it's our constant.
        return self.value


class List(Field):

    """A field representing a homogeneous list of data.

    The elements of the list are decoded through another field specified when
    the `List` is declared.

    """

    def __init__(self, fld, **kwargs):
        """Sets the type of field representing the content of the list.

        Parameter `fld` is another field instance representing the list's
        content. For instance, if the field were to represent a list of
        timestamps, `fld` would be a `Datetime` instance.

        """
        super(List, self).__init__(**kwargs)
        self.fld = fld

    def install(self, attrname, cls):
        super(List, self).install(attrname, cls)

        # Make sure our content field knows its owner too.
        self.fld.install(attrname, cls)

    def decode(self, value):
        """Decodes the dictionary value (a list of dictionary values) into a
        `DataObject` attribute (a list of `DataObject` attribute values)."""
        return [self.fld.decode(v) for v in value]

    def encode(self, value):
        """Encodes a `DataObject` attribute (a list of `DataObject` attribute
        values) into a dictionary value (a list of dictionary values)."""
        return [self.fld.encode(v) for v in value]


class Dict(List):

    """A field representing a homogeneous mapping of data.

    The elements of the mapping are decoded through another field specified
    when the `Dict` is declared.

    """

    def decode(self, value):
        """Decodes the dictionary value (a dictionary with dictionary values
        for values) into a `DataObject` attribute (a dictionary with
        `DataObject` attributes for values)."""
        return dict((k, self.fld.decode(v)) for k, v in value.iteritems())

    def encode(self, value):
        """Encodes a `DataObject` attribute (a dictionary with decoded
        `DataObject` attribute values for values) into a dictionary value (a
        dictionary with encoded dictionary values for values)."""
        return dict((k, self.fld.encode(v)) for k, v in value.iteritems())


class AcceptsStringCls(object):
    """Mixin for fields with a ``cls`` attribute that can either be a
    ``DataObject`` subclass or a string name of a ``DataObject`` subclass (to
    allow forward references)."""

    def get_cls(self):
        cls = self.__dict__['cls']
        if not callable(cls):
            cls = remoteobjects.dataobject.find_by_name(cls)
        return cls

    def set_cls(self, cls):
        self.__dict__['cls'] = cls

    cls = property(get_cls, set_cls)

class Object(AcceptsStringCls, Field):

    """A field representing a nested `DataObject`."""

    def __init__(self, cls, **kwargs):
        """Sets the the `DataObject` class the field represents.

        Parameter `cls` is the `DataObject` class representing the nested
        objects.

        `cls` may also be the name of a class, in which case the referenced
        class is the leafmost `DataObject` subclass declared with that name.
        This means you can not only forward-reference a class by specifying
        its name, but subclassing a `DataObject` class with the same name in
        another module will make all name-based `Object` fields reference the
        new subclass.

        """
        super(Object, self).__init__(**kwargs)
        self.cls = cls

    def decode(self, value):
        """Decodes the dictionary value into an instance of the `DataObject`
        class the field references."""
        if value is None:
            if callable(self.default):
                return self.default()
            return self.default
        return self.cls.from_dict(value)

    def encode(self, value):
        """Encodes an instance of the field's DataObject class into its
        representative dictionary value."""
        return value.to_dict()


class UTC(tzinfo):
    """UTC"""
    ZERO = timedelta(0)

    def utcoffset(self, dt):
        return UTC.ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return UTC.ZERO


class Datetime(Field):

    """A field representing a timestamp."""

    dateformat = "%Y-%m-%dT%H:%M:%SZ"
    utc = UTC()

    def __init__(self, dateformat=None, **kwargs):
        super(Datetime, self).__init__(**kwargs)
        if dateformat is not None:
            self.dateformat = dateformat

    def decode(self, value):
        """Decodes a timestamp string into a `DataObject` attribute (a Python
        `datetime` instance).

        Timestamp strings should be of the format ``YYYY-MM-DDTHH:MM:SSZ``.
        The resulting `datetime` will have UTC tzinfo.
        """
        if value is None:
            if callable(self.default):
                return self.default()
            return self.default
        try:
            return datetime(*(time.strptime(value, self.dateformat))[0:6],
                    tzinfo=Datetime.utc)
        except (TypeError, ValueError):
            raise TypeError('Value to decode %r is not a valid date time stamp' % (value,))

    def encode(self, value):
        """Encodes a `DataObject` attribute (a Python `datetime` instance)
        into a timestamp string.

        The `datetime` instance should have no time zone set. Timestamp
        strings will be of the format ``YYYY-MM-DDTHH:MM:SSZ``.

        """
        if not isinstance(value, datetime):
            raise TypeError('Value to encode %r is not a datetime' % (value,))
        if value.tzinfo is not None:
            value = value.astimezone(Datetime.utc)
        return value.replace(microsecond=0).strftime(self.dateformat)


class Link(AcceptsStringCls, Property):

    """A `RemoteObject` property representing a link from one `RemoteObject`
    instance to another.

    Use this property when related content is not *part* of a RemoteObject,
    but is instead available at a URL relative to it. By default the target
    object's URL should be available at the property name relative to the
    owning instance's URL.

    For example:

    >>> class Item(RemoteObject):
    ...     feed = Link(Event)
    ...
    >>> i = Item.get('http://example.com/item/')
    >>> f = i.feed  # f's URL: http://example.com/item/feed

    Override the `__get__` method of a `Link` subclass to customize how the
    URLs to linked objects are constructed.

    """

    def __init__(self, cls, api_name=None, **kwargs):
        """Sets the `RemoteObject` class of the target resource and,
        optionally, the real relative URL of the resource.

        Optional parameter `api_name` is used as the link's relative URL. If
        not given, the name of the attribute to which the Link is assigned
        will be used.

        """
        self.cls = cls
        self.api_name = api_name
        super(Link, self).__init__(**kwargs)

    def install(self, attrname, cls):
        """Installs the `Link` instance as an attribute of the `RemoteObject`
        class in which it was declared."""
        self.of_cls = cls
        self.attrname = attrname
        if self.api_name is None:
            self.api_name = attrname

    def __get__(self, instance, owner):
        """Generates the RemoteObject for the target resource of this Link.

        By default, target resources are at a URL relative to the "parent"
        object's URL, named by the `api_name` attribute of the `Link`
        instance. Override this method to define some other strategy for
        building links for your target API.

        """
        if instance._location is None:
            raise AttributeError('Cannot find URL of %s relative to URL-less %s' % (self.cls.__name__, owner.__name__))
        newurl = urlparse.urljoin(instance._location, self.api_name)
        return self.cls.get(newurl)
