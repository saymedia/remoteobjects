import logging
from datetime import datetime
import time

import remoteobjects.dataobject

__all__ = ('Property', 'Field', 'Something', 'List', 'Object', 'Datetime')

class Property(object):

    def install(self, attrname):
        """Produces the replacement object to be installed as a class
        attribute where this field is declared.

        Override this method to install an attribute on DataObject classes
        where your field is declared. This implementation installs no
        attribute (by raising a `NotImplementedError`).

        """
        raise NotImplementedError()


class Field(Property):

    """A field for encoding object attributes as JSON values and decoding JSON
    values into object attributes.

    Each attribute of a DataObject has a field that dictates how a dictionary
    deserialized from a JSON resource is turned into an instance of that
    DataObject.

    """

    def __init__(self, api_name=None, default=None):
        """Sets the field's matching deserialization field and default value.

        Optional parameter `api_name` is the name of the matching field in the
        JSON resource to decode into this object attribute. If not given, the
        name given to the field when its class was defined is used.

        Optional parameter `default` is the default value to use for this
        attribute when the dictionary to decode does not contain a value.

        `default` can be a callable function that is passed the object to
        decode into and the dictionary to decode from, and should return the
        default value of the attribute. As fields are processed in no
        particular order, a `default` function should not set the value
        itself, nor should it depend on values already decoded into the
        DataObject instance.

        Default values are *not* special when encoding an object, so those
        values will stick on DataObjects that are saved and retrieved (such as
        RemoteObjects).

        """
        self.api_name = api_name
        self.default  = default

    def decode(self, value):
        """Decodes a dictionary value into a DataObject attribute value."""
        raise NotImplementedError, 'Decoding for this field is not implemented'

    def encode(self, value):
        """Encodes a DataObject attribute value into a dictionary value."""
        raise NotImplementedError, 'Encoding for this field is not implemented'

    def encode_into(self, obj, data, field_name=None):
        """Encodes the attribute the field represents out of DataObject
        instance `obj` into a dictionary `data`.

        Parameter `field_name` specifies the name of the DataObject attribute
        to encode from.

        """
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

    Use this generic field for DataObject parameters that should be equivalent
    to their JSON deserializations: strings, numbers, and boolean values.

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

    Use this field when a class is designed to represent only some resources
    in a set, such as those of a certain subtype, and one of the object's
    fields indicates that unchanging type.

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

    """A field representing a homogeneous list of data."""

    def __init__(self, fld, **kwargs):
        """Sets the field's deserialization field and default value (as in
        `Field.__init__()`) and the type of field representing the content
        of the list.

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
        DataObject attribute (a list of DataObject attribute values)."""
        return [self.fld.decode(v) for v in value]

    def encode(self, value):
        """Encodes a DataObject attribute (a list of DataObject attribute
        values) into a dictionary value (a list of dictionary values)."""
        return [self.fld.encode(v) for v in value]

class Dict(List):
    """A field representing a homogeneous mapping of data."""

    def decode(self, value):
        return dict([(k, self.fld.decode(v)) for k, v in value.iteritems()])

    def encode(self, value):
        return dict([(k, self.fld.encode(v)) for k, v in value.iteritems()])

class Object(Field):
    """A field representing another DataObject."""

    def __init__(self, cls, **kwargs):
        """Sets the field's deserialization field and default value (as in
        `Field.__init__()`) and the DataObject class the field
        represents.

        Parameter `cls` is the DataObject class to decode dictionary values
        into. If the class has not yet been defined, `cls` may be the name of
        a DataObject class defined in the same module as the class that owns
        the `Object` field.

        """
        super(Object, self).__init__(**kwargs)
        self.cls = cls

    def get_cls(self):
        cls = self.__dict__['cls']
        if not callable(cls):
            # Assume the name is sibling to our owner class.
            clsname = '.'.join((self.of_cls.__module__, cls))
            cls = remoteobjects.dataobject.find_by_name(clsname)
        return cls

    def set_cls(self, cls):
        self.__dict__['cls'] = cls

    cls = property(get_cls, set_cls)

    def decode(self, value):
        """Decodes the dictionary value into an instance of the field's
        DataObject class."""
        if not isinstance(value, dict):
            raise TypeError('Value to decode into a %s %r is not a dict' % (self.cls.__name__, value))
        return self.cls.from_dict(value)

    def encode(self, value):
        """Encodes an instance of the field's DataObject class into its
        representative dictionary value."""
        if not isinstance(value, self.cls):
            raise TypeError('Value to encode %r is not a %s' % (value, self.cls.__name__))
        return value.to_dict()

class Datetime(Field):

    """A field representing a timestamp."""

    def decode(self, value):
        """Decodes a dictionary timestamp string into a DataObject attribute
        (a `datetime`).

        Dictionary timestamps should be of the format `YYYY-MM-DDTHH:MM:SSZ`.

        """
        try:
            return datetime(*(time.strptime(value, '%Y-%m-%dT%H:%M:%SZ'))[0:6])
        except ValueError:
            raise TypeError('Value to decode %r is not a valid date time stamp' % (value,))

    def encode(self, value):
        """Encodes a DataObject attribute (a `datetime`) into a dictionary
        timestamp string.

        Dictionary timestamps will be of the format `YYYY-MM-DDTHH:MM:SSZ`.

        """
        if not isinstance(value, datetime):
            raise TypeError('Value to encode %r is not a datetime' % (value,))
        if value.tzinfo is not None:
            raise TypeError("Value to encode %r is a datetime, but it has timezone information and we don't want to deal with timezone information" % (value,))
        return '%sZ' % (value.isoformat(),)
