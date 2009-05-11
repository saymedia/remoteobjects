#!/usr/bin/env python
from distutils.core import setup
setup(
    name='remoteobjects',
    version='1.0',
    description='an Object RESTational Model',
    author='Six Apart',
    author_email='python@sixapart.com',
    url='http://code.sixapart.com/svn/remoteobjects/',

    packages=['remoteobjects'],
    provides=['remoteobjects'],
    requires=['simplejson(>=2.0.0)', 'httplib2(>=0.4.0)'],
)
