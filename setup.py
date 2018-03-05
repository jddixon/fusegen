#!/usr/bin/python3
# fusegen/setup.py

""" Setuptools project configuration for fusegen. """

from os.path import exists
from setuptools import setup

LONG_DESC = None
if exists('README.md'):
    with open('README.md', 'r') as file:
        LONG_DESC = file.read()

setup(name='fusegen',
      version='0.6.37',
      author='Jim Dixon',
      author_email='jddixon@gmail.com',
      long_description=LONG_DESC,
      packages=['fusegen'],
      package_dir={'': 'src'},
      py_modules=[],
      include_package_data=False,
      zip_safe=False,
      scripts=['src/fuse_decode', 'src/run_fusegen'],
      description='generator for fusegen projects',
      url='https://jddixon.github.io/fusegen',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Natural Language :: English',
          'Programming Language :: Python 2.7',
          'Programming Language :: Python 3.5',
          'Programming Language :: Python 3.6',
          'Programming Language :: Python 3.7',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],)
