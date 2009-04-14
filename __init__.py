"""
remoteobjects provides easy coding and transfer between Python objects and a
JSON REST API.



"""

import remoteobjects.dataobject
import remoteobjects.fields as fields
import remoteobjects.http
import remoteobjects.promise
from remoteobjects.promise import ListObject

__all__ = ('RemoteObject', 'fields', 'ListObject')

class RemoteObject(remoteobjects.promise.PromiseObject):
    pass
