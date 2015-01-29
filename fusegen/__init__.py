# fusegen/__init__.py

import os, re, sys

__all__ = [ '__version__', '__version_date__',
            'LOG_ENTRY_PAT_MAP', 'OP_NAMES', 'PATH_TO_FIRST_LINES',
            'SET_STATUS', 'SET_FD', 'OP_SPECIAL', 'FH_PARAM', 'FLAGS_PARAM',
            'OP_CALL_MAP',
            # functions
            'checkDate', 'checkPkgName', 'checkPgmNames', 'checkVersion',
            # classes
            'FuseFunc',
       ]

# -- exported constants ---------------------------------------------
__version__      = '0.3.2'
__version_date__ = '2015-01-28'

# path to text file of quasi-prototypes
PATH_TO_FIRST_LINES = 'fragments/prototypes'

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


SET_STATUS  = 0x01      # sets the status variable
SET_FD      = 0x02      # sets an fd variable
OP_SPECIAL  = 0x04      # messy handling
FH_PARAM    = 0x08      # param is fi->fh instead of fpath
FLAGS_PARAM = 0x10      # param is fi->flags instead of fi

# Map FUSE op to syscall name and attributes.  This is for use in
# generating syscalls.
OP_CALL_MAP = {
    'getattr'    : ('lstat',         SET_STATUS),
    'readlink'   : ('readlink',      SET_STATUS | OP_SPECIAL),  # size - 1
    'mknod'      : ('mknod',         SET_STATUS | OP_SPECIAL),  # v messy
    'mkdir'      : ('mkdir',         SET_STATUS),
    'unlink'     : ('unlink',        SET_STATUS),
    'rmdir'      : ('rmdir',         SET_STATUS),
    'symlink'    : ('symlink',       SET_STATUS),
    'rename'     : ('rename',        SET_STATUS),
    'link'       : ('link',          SET_STATUS),
    'chmod'      : ('chmod',         SET_STATUS),
    'chown'      : ('chown',         SET_STATUS),
    'truncate'   : ('truncate',      SET_STATUS),
    'utime'      : ('utime',         SET_STATUS),
    'open'       : ('open',          SET_FD | FLAGS_PARAM),
    'read'       : ('pread',         SET_STATUS | FH_PARAM),
    'write'      : ('pwrite',        SET_STATUS | FH_PARAM),
    'statfs'     : ('statvfs',       SET_STATUS),
    'flush'      : ('',              SET_STATUS),     # a no-op ??
    'release'    : ('close',         SET_STATUS | FH_PARAM),
    'fsync'      : ('fsync',         SET_STATUS | OP_SPECIAL), # may be fdatasync
    'setxattr'   : ('lsetxattr',     SET_STATUS),
    'getxattr'   : ('lgetxattr',     SET_STATUS),
    'listxattr'  : ('llistxattr',    SET_STATUS),
    'removexattr': ('lremovexattr',  SET_STATUS),
    'opendir'    : ('opendir',       SET_STATUS),
    'readdir'    : ('lreaddir',      OP_SPECIAL),  # loops
    'releasedir' : ('closedir',      OP_SPECIAL),  # must cast fi->fh
    'fsyncdir'   : ('',              SET_STATUS),  # a no-op ??
    'init'       : ('',              OP_SPECIAL),  # kukemal
    'destroy'    : ('',              SET_STATUS),
    'access'     : ('access',        SET_STATUS),
    'create'     : ('creat',         SET_FD),       # call returns fd
    'ftruncate'  : ('ftruncate',     SET_STATUS | FH_PARAM),
    'fgetattr'   : ('fstat',         SET_STATUS | FH_PARAM),
}
LOG_ENTRY_PAT_MAP = {
        'buf'       : '0x%08x',
        'datasync'  : '%d',
        'dev'       : '%lld',
        'fi'        : '0x%08x',
        'filler'    : '0x%08x',
        'flags'     : '0x%08x',
        'fpath'     : '\\"%s\\"',
        'gid'       : '%d',
        'mode'      : '0%3o',           # XXX check me!
        'link'      : '\\"%s\\"',
        'list'      : '0x%08x',
        'mask'      : '0%o',
        'name'      : '\\"%s\\"',
        'newpath'   : '\\"%s\\"',
        'newsize'   : '%lld',
        'offset'    : '%lld',
        'path'      : '\\"%s\\"',
        'rootdir'   : '\\"%s\\"',
        'size'      : '%d',             # or should this be lld ?
        'statbuf'   : '0x%08x',
        'statv'     : '0x%08x',
        'ubuf'      : '0x%08x',
        'uid'       : '%d',
        'userdata'  : '0x%08x',
        'value'     : '\\"%s\\"',
        }
PAT_MAP = {
        'buf'       : '0x%08x',         #  XXX ?
        'fi'        : '0x%08x',
        'statbuf'   : '0x%08x',
        'ubuf'      : '%s',
        }

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

    def __init__(self, fName, fType, params, p2tMap):
        self._name = fName      # string, trimmed
        self._type = fType      # string, left-trimmed,
        self._params = params   # a list of 2-tuples
        self._p2tMap = p2tMap   # map, parameter name to type (as string)

    @property
    def name(self):
        return self._name
    @property
    def fType(self):
        return self._type
    @property
    def params(self):
        return self._params
    @property
    def p2tMap(self):
        return self._p2tMap

    def firstLine(self):
        """ return the first line of the function """
        line = self.fType  + self.name + '('
        pCount = len(self.params)
        for ndx, param in enumerate(self.params):
            line += param[0]
            line += param[1]
            if ndx < pCount - 1:
                line += ', '
        line += ')'
        return line

    def otherArgs(self):
        """ return comma-separated list of arguments other than the first """

        pCount = len(self.params)
        s = ''
        for ndx, param in enumerate(self.params):
            if ndx > 0:
                s += ', ' +param[1]
        return s

    @classmethod
    def parseProto(clz, line, prefix=''):

        line   = line.strip()
        params = []     # of 2-tuples
        p2tMap = {}

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
            fName = prefix + baseName

        argList = rest[lNdx+1:rNdx]

        # DEBUG
        #print("type '%s', fName '%s', args '%s'" % (fType, fName, argList))
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
            #print("    argType: '%s', argName '%s'" % (argType, argName))
            # END
            params.append( (argType, argName) )     # that's a 2-tuple
            p2tMap[argName] = argType

        return baseName, FuseFunc(fName, fType, params, p2tMap)

    @classmethod
    def getFuncMap(clz, prefix=''):

        lines = []
        with open(PATH_TO_FIRST_LINES, 'r') as f:
            line = f.readline()
            while line and line != '':
                line = line[:-1]
                lines.append(line)
                # DEBUG
                #print(line)
                #
                line = f.readline()

        funcMap = {}    # this maps prefixed names to FuseFunc objects
        for line in lines:
            name, ff = FuseFunc.parseProto(line, prefix)
            funcMap[name] = ff

        return funcMap
