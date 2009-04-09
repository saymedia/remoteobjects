import logging
from datetime import datetime
import time

import remoteobjects.dataobject

__all__ = ('Property', 'Field', 'Something', 'List', 'Object', 'Datetime')

class Property(object):

    """An attribute that can be installed declaratively on a `DataObject` to
    provide data encoding or loading behavior.

    The primary kinds of `Property` objects are `Field` (and its subclasses)
    and `Link` objects.

    """

    def install(self, attrname):
        """Produces the replacement object to be installed as a class
        attribute where this field is declared.

        Override this method to install an attribute on DataObject classes
        where your field is declared. This implementation installs no
        attribute (by raising a `NotImplementedError`).

        """
        raise NotImplementedError()


class Field(Property):

    """A property for encoding object attributes as dictionary values and
    decoding dictionary values into object attributes.

    Declare a `Field` instance for each attribute of a `DataObject` that
    should be encoded to or decoded from a dictionary.

    If your attribute needs converted specially, override the `decode` and
    `encode` methods in a subclass. For example, the `fields.Datetime`
    subclass of `Field` encodes Python `datetime` instances in a dictionary as
    timestamp strings.

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

    def decode(self, value):
        """Decodes a dictionary value into a `DataObject` attribute value."""
        raise NotImplementedError, 'Decoding for this field is not implemented'

    def encode(self, value):
        """Encodes a `DataObject` attribute value into a dictionary value."""
        raise NotImplementedError, 'Encoding for this field is not implemented'

    def encode_into(self, obj, data, field_name=None):
        """Encodes the attribute the field represents out of `DataObject`
        instance `obj` into a dictionary `data`.

        Parameter `field_name` specifies the name of the `DataObject` attribute
        to encode from.

        """
        # value = getattr(obj, field_name)
        value = obj.__dict__.get(field_name)
        if value is not None:
            value = self.encode(value)
            # only put in data if defined
            data[self.api_name or field_name] = value

    def decode_into(self, data, obj, field_name=None):
        """Decodes the attribute the field represents out of dictionary `data`
        into a DataObject instance `obj`.

        Parameter `field_name` specifies the name of the DataObject attribute
        to encode into.

        """
        value = data.get(self.api_name or field_name)
        if value is not None:
            value = self.decode(value)
        if value is None and self.default is not None:
            if callable(self.default):
                value = self.default(obj, data)
            else:
                value = self.default
        # always set the attribute, even if it's still None
        setattr(obj, field_name, value)

class Something(Field):

    """A generic field for data that doesn't need converted between dictionary
    content and DataObject values.

    Use this generic field for simple `DataObject` parameters that can be the
    same type as their dictionary values. That is, use this `Field` for
    strings, numbers, and boolean values.

    """

    def decode(self, value):
        """Decodes a dictionary value into a DataObject attribute value."""
        return value

    def encode(self, value):
        """Encodes a DataObject attribute value into a dictionary value."""
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

    def decode(self, value):
        if value != self.value:
            raise ValueError, 'Value %r is not expected value %r' % (value, self.value)
        return self.value

    def encode(self, value):
        # Don't even bother caring what we were given; it's our constant.
        return self.value

    def encode_into(self, obj, data, field_name=None):
        data[self.api_name or field_name] = self.value

    def decode_into(self, data, obj, field_name=None):
        setattr(obj, field_name, self.value)

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

    def get_of_cls(self):
        return self.__dict__['of_cls']

    def set_of_cls(self, of_cls):
        self.__dict__['of_cls'] = of_cls
        # Make sure our content field knows its owner too.
        self.fld.of_cls = of_cls

    of_cls = property(get_of_cls, set_of_cls)

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
        return dict([(k, self.fld.decode(v)) for k, v in value.iteritems()])

    def encode(self, value):
        """Encodes a `DataObject` attribute (a dictionary with decoded
        `DataObject` attribute values for values) into a dictionary value (a
        dictionary with encoded dictionary values for values)."""
        return dict([(k, self.fld.encode(v)) for k, v in value.iteritems()])

class Object(Field):
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

    def get_cls(self):
        cls = self.__dict__['cls']
        if not callable(cls):
            cls = remoteobjects.dataobject.find_by_name(cls)
        return cls

    def set_cls(self, cls):
        self.__dict__['cls'] = cls

    cls = property(get_cls, set_cls)

    def decode(self, value):
        """Decodes the dictionary value into an instance of the `DataObject`
        class the field references."""
        return self.cls.from_dict(value)

    def encode(self, value):
        """Encodes an instance of the field's DataObject class into its
        representative dictionary value."""
        return value.to_dict()

class Datetime(Field):

    """A field representing a timestamp."""

    def decode(self, value):
        """Decodes a timestamp string into a `DataObject` attribute (a Python
        `datetime` instance).

        Timestamp strings should be of the format `YYYY-MM-DDTHH:MM:SSZ`. The
        resulting `datetime` will have no time zone.

        """
        try:
            return datetime(*(time.strptime(value, '%Y-%m-%dT%H:%M:%SZ'))[0:6])
        except ValueError:
            raise TypeError('Value to decode %r is not a valid date time stamp' % (value,))

    def encode(self, value):
        """Encodes a `DataObject` attribute (a Python `datetime` instance)
        into a timestamp string.

        The `datetime` instance should have no time zone set. Timestamp
        strings will be of the format `YYYY-MM-DDTHH:MM:SSZ`.

        """
        if not isinstance(value, datetime):
            raise TypeError('Value to encode %r is not a datetime' % (value,))
        if value.tzinfo is not None:
            raise TypeError("Value to encode %r is a datetime, but it has timezone information and we don't want to deal with timezone information" % (value,))
        return '%sZ' % (value.replace(microsecond=0).isoformat(),)
