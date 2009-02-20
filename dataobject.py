import logging
import remoteobjects.fields

all_classes = {}
def find_by_name(name):
    """Finds and returns the DataObject subclass with the given name.

    Parameter `name` should be a full dotted module and class name.

    """
    return all_classes[name]

class DataObjectMetaclass(type):
    def __new__(cls, name, bases, attrs):
        fields = {}
        new_fields = {}

        # Inherit all the parent DataObject classes' fields.
        for base in bases:
            if isinstance(base, DataObjectMetaclass):
                fields.update(base.fields)

        # Move all the class's attributes that are Fields to the fields set.
        for attrname, field in attrs.items():
            if isinstance(field, remoteobjects.fields.Field):
                new_fields[attrname] = field
                del attrs[attrname]
            elif attrname in fields:
                # Throw out any parent fields that the subclass defined as
                # something other than a Field.
                del fields[attrname]

        fields.update(new_fields)
        attrs['fields'] = fields
        obj_cls = super(DataObjectMetaclass, cls).__new__(cls, name, bases, attrs)

        # Register the new class so Object fields can have forward-referenced it.
        all_classes['.'.join((obj_cls.__module__, name))] = obj_cls
        # Tell this class's fields what this class is, so they can find their
        # forward references later.
        for field in new_fields.values():
            field.of_cls = obj_cls

        return obj_cls

class DataObject(object):

    """An object that can be decoded from or encoded as a dictionary, suitable
    for serializing to or deserializing from JSON.

    DataObject subclasses should be declared with their different data
    attributes defined as instances of fields from the `remoteobjects.fields`
    module. For example:

    >>> from remoteobjects import DataObject, fields
    >>> class Asset(DataObject):
    ...     name    = fields.Something()
    ...     updated = fields.Datetime()
    ...     author  = fields.Object('Author')
    ...

    A DataObject's fields then provide the coding between live DataObject
    instances and dictionaries.

    """

    __metaclass__ = DataObjectMetaclass

    def __init__(self, **kwargs):
        self._id = None
        self.__dict__.update(kwargs)

    def to_dict(self):
        """Encodes the DataObject to a dictionary."""
        data = {}
        for field_name, field in self.fields.iteritems():
            field.encode_into(self, data, field_name=field_name)
        return data

    @classmethod
    def from_dict(cls, data):
        """Decodes a dictionary into an instance of the DataObject class."""
        self = cls()
        self.update_from_dict(data)
        return self

    def update_from_dict(self, data):
        for field_name, field in self.fields.iteritems():
            field.decode_into(data, self, field_name=field_name)
