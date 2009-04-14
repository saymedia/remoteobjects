import remoteobjects.dataobject
import remoteobjects.fields as fields
import remoteobjects.http
import remoteobjects.promise
from remoteobjects.promise import ListObject

__all__ = ('RemoteObject', 'fields', 'ListObject')

class RemoteObject(remoteobjects.promise.PromiseObject):
    pass
