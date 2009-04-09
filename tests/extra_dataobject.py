from remoteobjects import fields, dataobject

class Referencive(dataobject.DataObject):
    related = fields.Object('Related')
    other   = fields.Object('OtherRelated')

class Related(dataobject.DataObject):
    pass

class OtherRelated(dataobject.DataObject):
    pass
