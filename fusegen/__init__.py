# fusegen/__init__.py

import os, re, sys

__all__ = [ '__version__', '__version_date__',
            'checkDate', 'checkPkgName', 'checkPgmNames', 'checkVersion',
       ]

# -- exported constants ---------------------------------------------
__version__      = '0.0.0'
__version_date__ = '2015-01-17'

# -- functions ------------------------------------------------------
PKG_DATE_RE = re.compile(r'^[\d]{4}-\d\d-\d\d$')
def checkDate(s):
    if not s:
        print("date must not be empty")
        sys.exit(1)
    else:
        s = s.strip()
        m = PKG_DATE_RE.match(s)
        if m == None:
            print(("'%s' is not a valid YYYY-MM-DD date" % s))
            sys.exit(1)

PKG_NAME_RE = re.compile(r'^[a-z_][a-z0-9_\-]*$', re.IGNORECASE)
def checkPkgName(s):
    if not s:
        print("you must provide a package name")
        sys.exit(1)
    else:
        s = s.strip()
        m = PKG_NAME_RE.match(s)
        if m == None:
            print("'%s' is not a valid package name" % s)
            sys.exit(1)

PGM_NAME_RE = re.compile(r'^[a-z_][a-z0-9_\-]*$', re.IGNORECASE)
def checkPgmNames(ss):
    if not ss or len(ss) == 0:
        print("you must supply at least one program name")
        sys.exit(1)
    else:
        for s in ss:
            if not PGM_NAME_RE.match(s):
                print("'%s' is not a valid program name" % s)
                sys.exit(1)

PKG_VERSION_RE = re.compile(r'^\d+\.\d+.\d+$')
def checkVersion(s):
    if not s:
        print("version must not be empty")
        sys.exit(1)
    else:
        s = s.strip()
        m = PKG_VERSION_RE.match(s)
        if m == None:
            print(("'%s' is not a valid X.Y.Z version" % s))
            sys.exit(1)
