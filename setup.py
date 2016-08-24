#!/usr/bin/python3

# ~/dev/py/fusegen/setup.py

import re
from distutils.core import setup
__version__ = re.search("__version__\s*=\s*'(.*)'",
                        open('fusegen/__init__.py').read()).group(1)

# see http://docs.python.org/distutils/setupscript.html

setup(name='fusegen',
      version=__version__,
      author='Jim Dixon',
      author_email='jddixon@gmail.com',
      #
      # wherever we have a .py file that will be
      # imported, we list it here, without the
      # extension but SQuoted
      py_modules=[],
      #
      # a package has its own directory with an
      #  __init__.py in it
      packages=['fusegen', ],
      #
      # scripts should have a globally unique name;
      #   they might be in a scripts/ subdir; SQuote
      #   the script name
      scripts=['fuseDecode', 'fuseGen', ],
      description='generator for fusegen projects',
      ulr='https://jddixon.github.io/fusegen',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Natural Language :: English',
          'Programming Language :: Python 3',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],
      )
