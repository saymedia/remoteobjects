from remoteobjects import fields, DataObject

class Referencive(DataObject):
    related = fields.Object('Related')
    other   = fields.Object('OtherRelated')

class Related(DataObject):
    pass

class OtherRelated(DataObject):
    pass
