#!/usr/bin/env python
from distutils.core import setup
setup(
    name='remoteobjects',
    version='1.1',
    description='an Object RESTational Model',
    author='Six Apart Ltd.',
    author_email='python@sixapart.com',
    url='http://sixapart.github.com/remoteobjects/',

    packages=['remoteobjects'],
    provides=['remoteobjects'],
    requires=['simplejson(>=2.0.0)', 'httplib2(>=0.4.0)'],
)
