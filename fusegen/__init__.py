# fusegen/__init__.py

import os, re, sys

__all__ = [ '__version__', '__version_date__',
            'FIRST_LINES', 'OP_NAMES',
            # functions
            'checkDate', 'checkPkgName', 'checkPgmNames', 'checkVersion',
            # classes
            'FuseFunc',
       ]

# -- exported constants ---------------------------------------------
__version__      = '0.2.0'
__version_date__ = '2015-01-24'

# path to text file of quasi-prototypes
FIRST_LINES = 'fragments/prototypes'

# a table of FUSE function names
OP_NAMES = [
    'getattr',  'readlink', 'getdir',       'mknod',        'mkdir',
    'unlink',   'rmdir',    'symlink',      'rename',       'link',
    'chmod',    'chown',    'truncate',     'utime',        'open',
    'read',     'write',    'statfs',       'flush',        'release',
    'fsync',    'setxattr', 'getxattr',     'listxattr',    'removexattr',
    'opendir',  'readdir',  'releasedir',   'fsyncdir',     'init',
    'destroy',  'access',   'create',       'ftruncate',    'fgetattr',
    ]

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

class FuseFunc(object):
    def __init__(self, fName, fType, params):
        self._name = fName      # string, trimmed
        self._type = fType      # string, left-trimmed,
        self._params = params   # a list of 2-tuples

    @property
    def name(self):
        return self._name
    @property
    def fType(self):
        return self._fType
    @property
    def params(self):
        return self._params

    @classmethod
    def parseProto(clz, line, prefix=''):
        
        line   = line.strip()
        params = []     # of 2-tuples
       
        parts = line.split(' ', 1)
        pCount = len(parts)
        if pCount != 2:
            print("error parsing prototype: splits into %d parts!" % pCount)
            sys.exit(1)
        fType = parts[0].strip()
        fType += ' '
        rest  = parts[1].lstrip()
        if rest[0] == '*':
            rest = rest[1:]
            fType += '*'

        lNdx = rest.index('(')
        rNdx = rest.index(')')
        if lNdx == -1 or rNdx == -1:
            print("can't locate parens is '%s'; aborting" % rest)
            sys.exit(1)
        baseName = rest[:lNdx]
        if prefix == '' or baseName == 'main':
            fName = baseName
        else:
            fName = prefix + '_' + baseName

        argList = rest[lNdx+1:rNdx]

        # DEBUG
        print("type '%s', fName '%s', args '%s'" % (fType, fName, argList))
        # END 
      
        parts = argList.split(',')
        for part in parts:
            # DEBUG
            #print("  part: '%s'" % part)
            # END
            if part == '':
                continue
            chunks = part.rsplit(' ', 1)
            chunkCount = len(chunks)
            if chunkCount != 2:
                print("can't split '%s': aborting" % part)
                sys.exit(1)
            argType = chunks[0].strip()
            argType += ' '
            argName = chunks[1]
            if argName[0] == '*':
                argName = argName[1:]
                argType += '*'
            # DEBUG
            print("    argType: '%s', argName '%s'" % (argType, argName))
            # END
            params.append( (argType, argName) )     # that's a 2-tuple
        return baseName, FuseFunc(fName, fType, params)
