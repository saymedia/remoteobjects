from remoteobjects import RemoteObject, fields

class Frob(RemoteObject):
    kind = fields.Constant("tag:api.example.com,2009;Frobnitz")
    name = fields.Field()
    size = fields.Field()
    attr = fields.Dict(fields.Field())

class Zot(RemoteObject):
    kind = fields.Constant("tag:api.example.com,2009;Zot")
    size = fields.Field()
    born = fields.Datetime()

class Twiddle(RemoteObject):
    kind = fields.Constant("tag:api.example.com,2009;Twiddle")
    name = fields.Field()
    frob = fields.Object(Frob, api_name="frobnitz")
    zotz = fields.List(fields.Object(Zot))
