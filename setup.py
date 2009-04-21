#!/usr/bin/env python
from setuptools import setup
setup(
    name='remoteobjects',
    version='1.0',
    description='an Object RESTational Model',
    packages=['remoteobjects'],
    package_dir={'remoteobjects': '.'},

    install_requires=['simplejson>=2.0.0', 'httplib2>=0.4.0'],
    provides=['remoteobjects'],

    author='Six Apart',
    author_email='python@sixapart.com',
    url='http://code.sixapart.com/svn/remoteobjects/',
)
