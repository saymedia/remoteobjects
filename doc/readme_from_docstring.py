#!/usr/bin/env python

import remoteobjects

readme = file('README.rst', 'w')
readme.write(remoteobjects.__doc__.strip())
readme.write("\n")
readme.close()
