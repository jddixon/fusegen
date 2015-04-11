# fusegen/__init__.py

import errno, os, re, shutil, subprocess, sys

__all__ = [ '__version__', '__version_date__',
            'BIN', 'SH',
            'DEPRECATED',   'NOT_IMPLEMENTED', 
            # functions
            'checkDate', 'checkPkgName', 'checkPgmNames', 'checkVersion',
            'invokeShell', 'makeFusePkg',
            'opNames',
       ]

# -- exported constants ---------------------------------------------
__version__      = '0.6.15'
__version_date__ = '2015-04-11'

BASH    = '/bin/bash'
SH      = '/bin/sh'

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
    # fuse version 2.6
    'utimens',  'bmap',     'lock',
    # fusion 2.9
    'flock', 
    # fusion 2.9.1
    'fallocate',
    # AS THESE ARE IMPLEMENTED, update the consistency check in fuseGen
    # NOT YET IMPLEMENTED 
    # fusion 2.8
    #'ioctl',        'poll',
    # fusion 2.9
    #'write_buf','read_buf', 
    ]

def opNames():
    """ 
    Return a copy of the list of op names, possibly including deprecated
    functions but excluding any which are not implemented.
    """
    x = []
    for name in opNames:
        x.append(name)
    return x

SET_STATUS  = 0x01      # sets the status variable
SET_FD      = 0x02      # sets an fd variable
OP_SPECIAL  = 0x04      # messy handling
FH_PARAM    = 0x08      # param is fi->fh instead of fpath
FLAGS_PARAM = 0x10      # param is fi->flags instead of fi

# Map FUSE op name to syscall name and attributes.  This is for use in
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

    'utimens'    : ('utimensat',        SET_STATUS),
    'bmap'       : ('_bmap',            SET_STATUS),
    'lock'       : ('ulockmgr_op',      SET_STATUS),
    'flock'      : ('flock',            SET_STATUS),
    'fallocate'  : ('posix_fallocate',  SET_STATUS),
}
LOG_ENTRY_PAT_MAP = {
        'blocksize' : '0x%08x',
        'buf'       : '0x%08x',
        'cmd'       : '%d',
        'datasync'  : '%d',
        'dev'       : '%lld',
        'fi'        : '0x%08x',
        'filler'    : '0x%08x',
        'flags'     : '0x%08x',
        'fpath'     : '\\"%s\\"',
        'gid'       : '%d',
        'idx'       : '0x016x',
        'len'       : '%lld',
        'link'      : '\\"%s\\"',
        'list'      : '0x%08x',
        'lock'      : '0x%08x',
        'mask'      : '0%o',
        'mode'      : '0%03o',
        'name'      : '\\"%s\\"',
        'newpath'   : '\\"%s\\"',
        'newsize'   : '%lld',
        'offset'    : '%lld',
        'op'        : '%d',
        'path'      : '\\"%s\\"',
        'rootdir'   : '\\"%s\\"',
        'size'      : '%d',             # or should this be lld ?
        'statbuf'   : '0x%08x',
        'statv'     : '0x%08x',
        'tv[2]'     : '0x%08x',
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

def invokeShell(cmdList):
    try:
        output = subprocess.check_output(cmdList, stderr=subprocess.STDOUT)
        output = str(output, 'utf-8')
    except subprocess.CalledProcessError as e:
        output = str(e)
    return output

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
            pName = param[1]
            if pName != 'fi' and ndx > 0:
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
                # simplified comments
                if line[0] != '#':
                    line = line[:-1]
                    lines.append(line)
                    line = f.readline()

        funcMap   = {}  # this maps prefixed names to FuseFunc objects
        opCodeMap = {}  # maps names to integer opCodes

        for ndx, line in enumerate(lines):
            name, ff = FuseFunc.parseProto(line, prefix)
            funcMap[name]   = ff
            opCodeMap[name] = ndx
            # DEBUG
            print("FuseFunc.getFuncMap: %-13s => %2d" % (name, ndx))
            # END

        # DEBUG
        if 'lock' in funcMap:       print("lock is in the map")
        else:                       print("lock is NOT in the map")
        # END
        return funcMap, opCodeMap

# == MAIN FUNCTION ==================================================

# attributes of fuse operations

DEPRECATED          = 0x00000001
RETURNS_STATUS      = 0x00000002
CHECK_ERR_AND_FLIP  = 0x00000004
FULL_PATH           = 0x00000008
DOUBLE_FULL_PATH    = 0x00000010
#
LOGGING_STAT        = 0x00000040
LOGGING_STATVFS     = 0x00000080
HAS_LINK_FILE       = 0x00000100
LOGGING_FI          = 0x00000200
SYSCALL_RET_FD      = 0x00000400
SET_FH_FROM_FD      = 0x00000800
SYSCALL_FI_PARAM1   = 0x00001000

CHK_DEF_XATTR       = 0x10000000
NOT_IMPLEMENTED     = 0x80000000

def setOpAttrs():
    """
    Return a map from fuse op names to attributes
    """
    opAttrs = {}
    for name in OP_NAMES:
        attrs = 0
        if name in ['getdir', 'utime',]:
            attrs |= DEPRECATED
        elif name in ['ioctl','poll','write_buf','read_buf',]:
            attrs |= NOT_IMPLEMENTED
        else:
            if name in ['symlink',]:
                attrs |= HAS_LINK_FILE
    
            if name != 'init' and name != 'destroy':
                attrs |= RETURNS_STATUS
    
            if name in ['rename','link',]:
                attrs |= DOUBLE_FULL_PATH
    
            # this is a NEGATIVE check: list those ops which do NOT use
            if name not in ['flock', 'lock', 
                            'symlink',
                            'read', 'write', 'flush', 'release', 'fsync',
                            'readdir', 'releasedir','fsyncdir', 'init',
                            'destroy', 'ftruncate', 'fgetattr']:
                attrs |= FULL_PATH
    
            if name not in [ 'destroy', 'flush', 'fsyncdir',
                    'init', 'mknod', 'readdir', ]:
                attrs |= CHECK_ERR_AND_FLIP
    
            if name in ['setxattr', 'getxattr', 'listxattr', 'removexattr',]:
                attrs |= CHK_DEF_XATTR
    
            if name in ['create', 'fallocate', 'fgetattr', 'flush',
                    'fsync', 'fsyncdir', 'ftruncate',
                    'lock',
                    'opendir', 'open', 'readdir', 'read', 'releasedir',
                    'release', 'write',]:
                attrs |= LOGGING_FI
    
            if name in ['create', 'open',  ]:
                attrs |= SET_FH_FROM_FD
    
            if name in ['fgetattr', 'flock', 'fsync', 'opendir', 
                    'read', 'releasedir', 'release', 'ftruncate', 'write']:
                attrs |= SYSCALL_FI_PARAM1
    
            if name in ['getattr', 'fgetattr',]:
                attrs |= LOGGING_STAT
            elif name == 'statfs':
                attrs |= LOGGING_STATVFS
            if name in ['create', 'open',]:
                attrs |= SYSCALL_RET_FD

        opAttrs[name] = attrs
    return opAttrs

def makedir_p(path, mode):
    # XXX SLOPPY: doesn't handle case where mode is wrong
    # XXX MISLEADING: the name suggests it creates missing subdirs
    try:
        os.mkdir(path, mode)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e
        pass

def makeFusePkg(args):
    acPrereq        = args.acPrereq
    emailAddr       = args.emailAddr
    instrumenting   = args.instrumenting
    force           = args.force
    lcName          = args.lcName
    logging         = args.logging
    myDate          = args.myDate
    myVersion       = args.myVersion
    pathToPkg       = args.pathToPkg    # target package directory
    pkgName         = args.pkgName
    prefix          = pkgName + '_'     # XXX FORCES UNDERSCORE
    testing         = args.testing
    ucName          = args.ucName
    verbose         = args.verbose

    # make sure opCode <-> opName maps are consistent ---------------
    funcMap, opCodeMap = FuseFunc.getFuncMap(prefix)
    # DEBUG
    if 'lock' in funcMap:       print("lock is in the main map")
    else:                       print("lock is NOT in the main map")
    # END
    inconsistent = False
    for ndx in range(len(OP_NAMES)):
        name = OP_NAMES[ndx]
        if not name in opCodeMap:
            break
        ndxFromName = opCodeMap[name]
        if ndx != ndxFromName:
            print("INCONSISTENCY: %s is OP_NAME %d, but opCodeMap has %d" % (
                name, ndx, ndxFromName))
            inconsistent = True
    if inconsistent:
        print("aborting")
        sys.exit(1)

    # ===============================================================
    # CREATE DIRECTORIES 
    # ===============================================================
    
    # if -force and pathToPkg exists, delete it -- unless there is a .git/
    if force and os.path.exists(pathToPkg):
        pathToDotGit = os.path.join(pathToPkg, ".git")
        if os.path.exists(pathToDotGit):
            print("'%s' exists; cannot proceed" % pathToDotGit)
            sys.exit(0)
        else:
            shutil.rmtree(pathToPkg)

    makedir_p(pathToPkg, 0o755)

    mountPoint      = os.path.join('workdir', 'mountPoint')
    rootDir         = os.path.join('workdir', 'rootdir')
    makeFileSubDirs = ['doc', 'examples', 'man', 'scripts', 'src', 'tests',]
    otherSubDirs    = ['bin', 'config', 'ghpDoc', 'm4', 'workdir',
                        mountPoint, rootDir, 'tmp',]
    subDirs         = makeFileSubDirs + otherSubDirs
    for dir in subDirs:
        pathToSubDir = os.path.join(pathToPkg, dir)
        makedir_p(pathToSubDir, 0o755)

    # ===============================================================
    # TOP LEVEL FILES
    # ===============================================================

    # copy over fusgegen/src files  ---------------------------------
    def copyFromSrc(name, executable=False, topLevel=True):
        """ copy a file from py/fusegen/src/ to the top level package dir """
        src  = os.path.join('src', name)
        if topLevel:
            dest = os.path.join(pathToPkg, name)
        else:
            dest = os.path.join(pathToPkg, os.path.join('src', name))
        with open(src, 'r') as a:
            text = a.read()
            with open(dest,'w') as b:
                b.write(text)
            if executable:
                os.chmod(dest, 0o744)
            else:
                os.chmod(dest, 0o644)

    # install-sh removed from both lists 2015-02-22
    for x in ['autogen.sh', 'build', 'config.guess', 'config.sub', 'COPYING',
            'COPYING.LIB', 'COPYING.AUTOCONF.EXCEPTION', 'COPYING.GNUBL',
            'README.licenses',]:
        copyFromSrc(x, x in ['autogen.sh', 'build', ])
    for x in ['fuse.h', 'fuse_common.h', 'fuse_opt.h', ]:
        copyFromSrc(x, False, False)

    # write CHANGES -------------------------------------------------
    chgFile = os.path.join(pathToPkg, 'CHANGES')
    with open(chgFile, 'w', 0o644) as f:
        f.write("~/dev/c/%s/CHANGES\n\n" % pkgName)
        f.write("v%s\n" % myVersion)
        f.write("    %s\n" % myDate)
        f.write("        *\n")

    # write configure.ac --------------------------------------------
    configFile = os.path.join(pathToPkg, 'configure.ac')
    configText = """#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([{0:s}])
AC_INIT([{1:s}], [{2:s}], [{3:s}])
AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_AUX_DIR([config])
LT_INIT
AM_INIT_AUTOMAKE
AC_CONFIG_SRCDIR([src/{1:s}.c])
AC_CONFIG_HEADERS([src/config.h])

# Programs
AC_PROG_CC

# Header files.
AC_CHECK_HEADERS([fcntl.h limits.h stdlib.h string.h sys/statvfs.h unistd.h utime.h sys/xattr.h])

# FUSE development environment
PKG_CHECK_MODULES(FUSE, fuse)
FUSE_LIBS="$FUSE_LIBS -lulockmgr"

# Necessary typedefs and structures
AC_TYPE_MODE_T
AC_TYPE_OFF_T
AC_TYPE_PID_T
AC_TYPE_SIZE_T
AC_TYPE_UID_T
AC_TYPE_UINT64_T
AC_STRUCT_ST_BLOCKS
AC_CHECK_MEMBERS([struct stat.st_blksize])
AC_CHECK_MEMBERS([struct stat.st_rdev])

# Necessary library functions.
AC_FUNC_CHOWN
AC_FUNC_LSTAT_FOLLOWS_SLASHED_SYMLINK
AC_FUNC_MALLOC

AC_CHECK_FUNCS([fdatasync ftruncate mkdir mkfifo realpath rmdir strerror utimensat])
AC_CHECK_FUNCS([posix_fallocate])

AC_CONFIG_FILES([Makefile src/Makefile])
AC_OUTPUT
""".format(acPrereq, pkgName, myDate, emailAddr)
    with open(configFile, 'w', 0o644) as f:
        f.write(configText)

    # write Makefile.am  --------------------------------------------
    # XXX The EXTRA_DIST line seems senseless, as we copy it in.
    makeAMFile = os.path.join(pathToPkg, 'Makefile.am')
    content = """
ACLOCAL_AMFLAGS = -I m4
EXTRA_DIST = autogen.sh
SUBDIRS = src

# <ATTRIBUTION>
#
# Make it impossible to install the fuse file system. It must never be run
# as root, because that causes critical security risks.
install install-data install-exec uninstall installdirs check installcheck:
	echo This package must never be installed.

install-dvi install-info install-ps install-pdf dvi pdf ps info :
	echo This package must never be installed.
"""
    with open(makeAMFile, 'w', 0o644) as f:
        f.write(content)

    # write Makefile.in  --------------------------------------------
    # XXX This bit of silliness handles aclocal's requirement that
    # the file exist before we create it
    makeInFile = os.path.join(pathToPkg, os.path.join('src','Makefile.in'))
    content = """
"""
    with open(makeInFile, 'w', 0o644) as f:
        f.write(content)

    # write TODO ----------------------------------------------------
    todoFile = os.path.join(pathToPkg, 'TODO')
    with open(todoFile, 'w', 0o644) as f:
        f.write("~/dev/c/%s/TODO\n\n" % pkgName)
        f.write("%s\n" % myDate)
        f.write("    *\n")

    # ===============================================================
    # bin/ FILE GENERATION
    # ===============================================================

    # write bin/mountNAME
    pathToBin = os.path.join(pathToPkg, 'bin')
    pathToCmd = os.path.join(pathToBin, 'mount' + ucName)
    with open(pathToCmd, 'w') as f:
        f.write("cd %s\n" % pathToPkg)
        f.write("src/%s workdir/rootdir workdir/mountPoint\n" % pkgName)
    os.chmod(pathToCmd, 0o744)

    # write bin/umountNAME
    pathToCmd = os.path.join(pathToBin, 'umount' + ucName)
    with open(pathToCmd, 'w') as f:
        f.write("cd %s\n" % pathToPkg)
        f.write("fusermount -uz workdir/mountPoint\n")
    os.chmod(pathToCmd, 0o744)

    # write bin/blk-31-4k
    pathToCmd = os.path.join(pathToBin, 'blk-31-4k')
    content = """echo "blk-31-4k: test size is being set to $1 MB"
#
cd ~/dev/c/{0:s}
bin/mount{1:s}
cd workdir/mountPoint
fio --name=global --bs=4k --size=$1m \
	--rw=randrw --rwmixread=75 \
	--name=job1 --name=job2 --name=job3 --name=job4
cd ../..
bin/umount{1:s}
""".format(pkgName, ucName)
    with open(pathToCmd, 'w') as f:
        f.write(content)
    os.chmod(pathToCmd, 0o744)

    # ===============================================================
    # src/ FILE GENERATION
    # ===============================================================

    pathToSrc = os.path.join(pathToPkg, 'src')

    # src/fuse_version.h --------------------------------------------

    fuseVersionFile = os.path.join(pathToSrc, 'fuse_version.h')
    content = """/** fuse_version.h */

#ifndef _FUSE_VERSION_H_
#define _FUSE_VERSION_H_

#define FUSE_USE_VERSION 26

#endif
"""

    with open(fuseVersionFile, 'w') as f:
        f.write(content)

    # src/Makefile.am -----------------------------------------------
    makeAMFile = os.path.join(pathToSrc, 'Makefile.am')
    content = """
bin_PROGRAMS = {0:s}
{1:s}SOURCES = {0:s}.c fuse.h fuse_version.h opcodes.h {0:s}.h util.c $(wildcard *.inc)
AM_CFLAGS = @FUSE_CFLAGS@
LDADD = @FUSE_LIBS@
""".format(pkgName, prefix)

    with open(makeAMFile, 'w', 0o644) as f:
        f.write(content)

    # src/main.inc --------------------------------------------------
    content = """/** main.inc */

void {0:s}Usage()
{{
    fprintf(stderr,
        "usage:  {0:s} [FUSE, mount, and fg* options] rootDir mountPoint\\n");
    exit(0);
}}
void {0:s}PerrorAndUsage(const char* where)
{{
    if (where && (strlen(where) > 0))
        fprintf(stderr, "%s: ", where);
    fprintf(stderr, "%s\\n", strerror(errno));
    {0:s}Usage();
}}
// Return 0 if OK
void {0:s}ChkDir(char *dirName)
{{
    struct stat sb;
    int status = 0;
    char *name = "";
    if (dirName == NULL) {{
        fprintf(stderr, "null directory name\\n");
        status = -1;
        errno  = ENOENT;
    }} else {{
        name = dirName;
        if (dirName[0] == '-') {{
            fprintf(stderr, "directory name may not begin with '-'\\n");
            status = -1;
            errno  = EPERM;
        }} else {{
            status = stat(dirName, &sb);
            if ((!status) && (!S_ISDIR(sb.st_mode))) {{
                fprintf(stderr, "'%s' is not a directory\\n", dirName);
                status = -1;
                errno  = ENOTDIR;
            }}
        }}
    }}
    if (status)
        {0:s}PerrorAndUsage(name);
}}

int32_t {0:s}GetULongArg(const char *name, const char *s)
{{
    char *end = NULL;
    int32_t val = strtol(s, &end, 0);
    if (*end != 0) {{
        fprintf(stderr, "%s must be numeric but is '%s'\\n", name, s);
        {0:s}Usage();
    }}
    if (val <= 0) {{
        fprintf(stderr, "%s must be a positive integer but is '%s'\\n",
                name, s);
        {0:s}Usage();
    }}
    return val;
}}
int main(int argc, char *argv[])
{{
    int status = 0;
    struct {0:s}Data *myData;
    int fuseArgc;
    char **fuseArgv;

    int  localArgs   = 0;   // count of command line args consumed here

    // Prevent this script from being run by root, because such use is
    // an unacceptable security risk.
    if ((getuid() == 0) || (geteuid() == 0)) {{
        fprintf(stderr, "{0:s} must not be run as root\\n");
        exit(EPERM);
    }}

    // Try to allocate memory for file system's private data.
    myData = calloc(1, sizeof(struct {0:s}Data));
    if (myData == NULL) {{
        perror("main calloc failed");
        abort();
    }}
""".format(pkgName, prefix)                         # BAZ

    if logging:
        content += """\
    // Set up logging
    myData->logfile = {1:s}OpenLog();
""".format(pkgName, prefix)                         # BAZ

    content += """\
    // Strange warning here "initialization makes pointer from integer
    // without a cast"
    char *whereNow = get_current_dir_name();    // mallocs
    if (whereNow == NULL) {{
        fprintf(stderr, "get_current_dir_name failed\\n");
        perror("can't get working directory");
        abort();
    }} else {{
        myData->cwd = whereNow;
    }}

    // Handle the argument list.  Any arguments whose names begin with "fg"
    // are assumed to be local and are not passed on to fuse.  The last two
    // arguments are the paths to the root directory and the mount point
    // respectively.  The first of these is removed.  Other arguments
    // (excluding the fg* but including the path to mount point) are
    // passed on to fuse_main.

    static struct option longOptions[] = {{
        {{"fgBlockSize", 1, NULL, 0}},    // default = 4, multiple of 1024 bytes
        {{"fgHelp",      0, NULL, 0}},
        {{"fgJobCount",  1, NULL, 0}},    // default = 4
        {{"fgMBPerJob",  1, NULL, 0}},
        {{"fgVerbose",   0, NULL, 0}},
        {{NULL,          1, NULL, 0 }}    // marks end of list
    }};

    // process the argument list, permuting it so that local fg* arguments
    // are moved towards the front
    while (1) {{
        int optNdx;
        int c = getopt_long(argc, argv, "", longOptions, &optNdx);
        if (c == -1)
            break;
        switch (optNdx) {{
        case 0:
            fgBlockSize = {0:s}GetULongArg(longOptions[optNdx].name, optarg);
            localArgs += 2;
            break;
        case 1:
            {0:s}Usage();
            localArgs += 1;
            break;
        case 2:
            fgJobCount = {0:s}GetULongArg(longOptions[optNdx].name, optarg);
            localArgs += 2;
            break;
        case 3:
            fgMBPerJob = {0:s}GetULongArg(longOptions[optNdx].name, optarg);
            localArgs += 2;
            break;
        case 4:
            fgVerbose = 1;
            localArgs += 1;
            break;
        }}
    }}
    int i;

""".format(pkgName, prefix, ucName)     # FOO

    if instrumenting:
        content += """\
    // number of slots in a bucket
    slotsPerBucket = 1024 * fgMBPerJob * fgJobCount / fgBlockSize;

    buckets         = (bucket_t*)calloc(BUCKET_COUNT, sizeof(bucket_t));
    buckets[0].ops  = (opData_t*)calloc(slotsPerBucket, sizeof(opData_t));
    status = pthread_mutex_init(&buckets[0].lock, NULL);
    if (status)
        perror("initializing bucket lock");
    assert(status == 0);

    if (fgVerbose) {{
        fprintf(stderr, "fgBlockSize := %ld\\n", fgBlockSize);
        fprintf(stderr, "fgJobCount  := %ld\\n", fgJobCount);
        fprintf(stderr, "fgMBPerJob  := %ld\\n", fgMBPerJob);
        fprintf(stderr, "opData_ per bucket: %ld\\n", slotsPerBucket);
        fprintf(stderr, "  sizeof(opData_t)  %ld\\n",  sizeof(opData_t));
        fprintf(stderr, "  so size of buffer %ld bytes\\n",
            slotsPerBucket * sizeof(opData_t));

        fprintf(stderr, "\\nafter processing the %d local arguments\\n",
            localArgs);
        for (i = 0; i < argc; i++)
            fprintf(stderr, "  %d: %s\\n", i, argv[i]);
    }}
""".format(pkgName, prefix, ucName)     # FOO

    content += """\


    int n = argc - localArgs;
    if (n > 0)
        for (i = 1; i < n; i++)
            argv[i] = argv[i + localArgs];
    argc -= localArgs;

    // The last two arguments are the paths to the root directory and the
    // mount point respectively.  They must represent valid names for
    // existing directories that the user may access.
    if (argc < 3) {{
        fprintf(stderr, "not enough arguments\\n");
        {0:s}Usage();
    }}
    {0:s}ChkDir(argv[argc-2]);
    {0:s}ChkDir(argv[argc-1]);

    // The next to the last argument is the root directory.  Save it to
    // private data and then remove it from the argument list passed to fuse,
    // which doesn't expect to see it.
    //
    myData->rootdir = realpath(argv[argc-2], NULL);
    argv[argc-2] = argv[argc-1];
    argv[argc-1] = NULL;
    argc--;

    if (fgVerbose) {{
        fprintf(stderr, "\\nafter editing argument list\\n");
        for (i = 0; i < argc; i++)
            printf("  %d: %s\\n", i, argv[i]);
    }}

    status = fuse_main(argc, argv, &{1:s}OpTable, myData);
    return status;
}}
""".format(pkgName, prefix)                         # BAZ

    pathToMain = os.path.join(pathToSrc, 'main.inc')
    with open(pathToMain, 'w') as f:
        f.write(content)

    # src/opcodes.h -------------------------------------------------
    pathToOpcodes = os.path.join(pathToSrc, 'opcodes.h')
    with open(pathToOpcodes, 'w') as f:
        f.write("/* opcodes.h */\n\n");
        f.write("#ifndef _OPCODES_H_\n");
        for ndx, name in enumerate(OP_NAMES):
            f.write("#define FG_%-14s (%d)\n" % (name.upper(), ndx))
        f.write("#endif\n");

    # package header file -------------------------------------------
    content = """/** {0:s}.h */

#ifndef _{2:s}_H_
#define _{2:s}_H_

#ifdef linux
#ifndef _XOPEN_SOURCE
#define _XOPEN_SOURCE (700)
#endif
#endif

""".format(pkgName, prefix, ucName)     # FOO

    if instrumenting:
        content += """\
#include <pthread.h>        // should be first
"""

    content += """\
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <fuse.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>       // for flock()
#include <sys/types.h>
#include <time.h>
#include <ulockmgr.h>
#include <unistd.h>

#include "config.h"
#include "opcodes.h"

// prototypes
int  {1:s}Error(char *);
void {1:s}FullPath(char fpath[PATH_MAX], const char *path);

struct {0:s}Data {{
    // XXX next line should be generated only if logging capability
    FILE *logfile;
    char *rootdir;
    char *cwd;      // at the beginning of the run
}};

#define {2:s}_DATA ((struct {0:s}Data *) fuse_get_context()->private_data)

""".format(pkgName, prefix, ucName)     # FOO

    if logging:
        content += """\

void {1:s}LogConn   (struct fuse_conn_info *conn);
void {1:s}LogEntry  (const char *fmt, ...);
void {1:s}LogFI     (struct fuse_file_info *fi);
void {1:s}LogMsg    (const char *fmt, ...);
void {1:s}LogStat   (struct stat *si);
void {1:s}LogstatVFS(struct statvfs *sv);
FILE *{1:s}OpenLog  (void);
int  {1:s}FlushLog  (void);
""".format(pkgName, prefix, ucName)     # FOO

    if instrumenting:
        content += """
// BEGIN INSTRUMENTATION --------------------------------------------

// from the command line
extern long fgBlockSize;            // in kilobytes, so 1 means 1024
extern long fgJobCount;
extern long fgMBPerJob;             // in megabytes
extern int  fgVerbose;

#define BILLION     (1000000000UL)
#define BUCKET_COUNT (2)

// Beware: the standard does not guarantee the order of fields!
typedef struct o_ {{
    uint32_t    opSec;
    uint32_t    opNsec;             // may not exceed BILLION
    uint32_t    lateNsec;           // ns of latency; may not exceed BILLION
    unsigned    lateSec     :  7;   // sec of latency
    unsigned    count       : 17;   // number of bytes read or written; 128K max
    unsigned    opCode      :  8;
}} __attribute__((aligned(16), packed)) opData_t;

typedef struct b_ {{
    uint32_t        count;          // number of slots in use
    pthread_mutex_t lock;
    pthread_cond_t  cond;
    opData_t        *ops;           // [BUCKET_SIZE];
}} bucket_t;

extern long     slotsPerBucket;     // number of opData_t
extern long     maxBucketSize;
extern bucket_t *buckets;           // [BUCKET_COUNT];

opData_t *{1:s}ClockMeIn(struct timespec *tEntry, unsigned opCode);
void {1:s}ClockMeOut(struct timespec *tEntry, opData_t *mySlot, size_t count);
int {1:s}WriteBucket();

// END INSTRUMENTATION ----------------------------------------------
""".format(pkgName, prefix, ucName)     # FOO

    content += """\
#endif
"""
    headerFile = os.path.join(pathToSrc, "%s.h" % pkgName)
    with open(headerFile, 'w') as f:
        f.write(content)

    # package .c file -----------------------------------------------

    content = """/* {0:s}.c */

#include "fuse_version.h"   // this should be the first header file

#include <ctype.h>
#include <dirent.h>
#include <fcntl.h>
#include <libgen.h>
#include <string.h>

#ifdef HAVE_SYS_XATTR_H
#include <sys/xattr.h>
#endif

#include <getopt.h>             // for getopt_long
#include <linux/fs.h>           // for bmap
#include <linux/fiemap.h>       // for bmap
#include "{0:s}.h"              // this should be the last header file

// defaults for local (=fuseGen) command line arguments
long fgBlockSize = 4L;
long fgJobCount  = 4L;
long fgMBPerJob  = 512L;
int  fgVerbose   = 0;

long slotsPerBucket;

///////////////////////////////////////////////////////////
//
// Prototypes for all these functions, and the C-style comments,
// come indirectly from /usr/include/fuse.h

#include "getattr.inc"
#include "readlink.inc"
#include "mknod.inc"
#include "mkdir.inc"
#include "unlink.inc"
#include "rmdir.inc"
#include "symlink.inc"
#include "rename.inc"
#include "link.inc"
#include "chmod.inc"
#include "chown.inc"
#include "truncate.inc"

#ifndef HAVE_UTIMENSAT
#include "utime.inc"
#endif

#include "open.inc"
#include "read.inc"
#include "write.inc"
#include "statfs.inc"
#include "flush.inc"
#include "release.inc"
#include "fsync.inc"

#ifdef HAVE_SYS_XATTR_H
/** Set extended attributes */
#include "setxattr.inc"
#include "getxattr.inc"
#include "listxattr.inc"
#include "removexattr.inc"
#endif

#include "opendir.inc"
#include "readdir.inc"
#include "releasedir.inc"
#include "fsyncdir.inc"
#include "init.inc"
#include "destroy.inc"
#include "access.inc"
#include "create.inc"
#include "ftruncate.inc"
#include "fgetattr.inc"

#ifdef HAVE_UTIMENSAT
#include "utimens.inc"
#endif
#include "lock.inc"
#include "fallocate.inc"

#include "optable.inc"
#include "main.inc"
""".format(pkgName)

    pkgCFile = os.path.join(pathToSrc, "%s.c" % pkgName)
    with open(pkgCFile, 'w') as f:
        f.write(content)

    # generate util.c -----------------------------------------------

    content = """/** util.c */

#include "fuse_version.h"   // make me first
#include <stdarg.h>
#include <sys/stat.h>
#include "{0:s}.h"          // this header file should be last

// Return -errno to caller, conditionally after logging -------------

int {1:s}Error(char *msg)
{{
    int errCode = -errno;
""".format(pkgName, prefix, ucName)     # GEEP

    if logging:
        content += """\
    {1:s}LogMsg("    ERROR %s: %s\\n", msg, strerror(errno));
""".format(pkgName, prefix, ucName)     # GEEP
   
    content += """\
    return errCode;
}}

// Given a path relative to the mount point, return an absolute -----
// path including the root directory
void {1:s}FullPath(char fpath[PATH_MAX], const char *path)
{{
    strcpy(fpath, {2:s}_DATA->rootdir);
    strncat(fpath, path, PATH_MAX);
""".format(pkgName, prefix, ucName)     # GEEP

    if logging:
        content += """\
    {1:s}LogMsg("  FullPath:  rootdir = \\"%s\\", path = \\"%s\\", fpath = \\"%s\\"\\n",
           {2:s}_DATA->rootdir, path, fpath);
""".format(pkgName, prefix, ucName)     # GEEP

    content += """\
}
"""

    if logging:
        content2 = """\
// == LOGGING =======================================================

FILE *{1:s}OpenLog()
{{
    FILE *logfile;

    // Linux appends are guaranteed to be atomic
    logfile = fopen("{0:s}.log", "a");
    if (logfile == NULL) {{
        perror("logfile");
        exit(EXIT_FAILURE);
    }}
    setvbuf(logfile, NULL, _IOLBF, 0);
    return logfile;
}}

int  {1:s}FlushLog  (void)
{{
    return fflush({2:s}_DATA->logfile);
}}

void {1:s}LogEntry(const char *format, ...)
{{
    va_list ap;
    va_start(ap, format);

    vfprintf({2:s}_DATA->logfile, format, ap);
}}
void {1:s}LogMsg(const char *format, ...)
{{
    va_list ap;
    va_start(ap, format);

    vfprintf({2:s}_DATA->logfile, format, ap);
}}

static char *msgHeader(char *p, int *maxChar, char *name)
{{
    int n =  snprintf(p, *maxChar, "  %s:\\n", name);
    *maxChar -= n;
    return p + n;
}}

#define MAX_BUFFER (1024 - 1)

// log the name and value of a particular field of the structure s
#define ADD_FIELD(s, field, fmt) \\
  n = snprintf(p, bytesLeft, \\
          "   %-20s = " #fmt "\\n", " " #field "  ", s->field); \\
  bytesLeft -= n;   \\
  p += n;

#define ADD_INT_FIELD(s, field) \\
  n = snprintf(p, bytesLeft, "  %-20s  = %d\\n", "  " #field "  ", (int) s->field); \\
  bytesLeft -= n;   \\
  p += n;

#define ADD_ULONG_FIELD(s, field) \\
  n = snprintf(p, bytesLeft, "  %-20s  = 0x%08lx\\n", "  " #field "  ", (uintptr_t) s->field); \\
  bytesLeft -= n;   \\
  p += n;

#define ADD_LL_FIELD(s, field) \\
  n = snprintf(p, bytesLeft, "  %-20s  = %lld\\n", "  " #field "  ", (long long) s->field); \\
  bytesLeft -= n;   \\
  p += n;

#define ADD_ULL_FIELD(s, field) \\
  n = snprintf(p, bytesLeft, "  %-20s  = 0x%016llx\\n", "  " #field "  ", (unsigned long long) s->field); \\
  bytesLeft -= n;   \\
  p += n;

// struct is from fuse.h
void {1:s}LogContext(struct fuse_context *ctx)
{{
    char buffer[MAX_BUFFER+1];  // allow for null byte
    char *p = buffer;
    int  bytesLeft = MAX_BUFFER;
    int  n;

    p = msgHeader(p, &bytesLeft, "ctx");
    ADD_ULONG_FIELD(ctx, fuse);
    ADD_INT_FIELD(ctx, uid);
    ADD_INT_FIELD(ctx, gid);
    ADD_INT_FIELD(ctx, pid);
    ADD_FIELD(ctx, umask,                   %05o);

    ADD_ULONG_FIELD(ctx, private_data);
    // two fields defined locally
    ADD_ULONG_FIELD(((struct {0:s}Data *)ctx->private_data), logfile);
    ADD_FIELD(((struct {0:s}Data *)ctx->private_data), rootdir, %s);

    {1:s}LogMsg(buffer);
}}

// struct is from fuse_common.h
void {1:s}LogConn(struct fuse_conn_info *conn)
{{
    char buffer[MAX_BUFFER+1];  // allow for null byte
    char *p = buffer;
    int  bytesLeft = MAX_BUFFER;
    int  n;

    p = msgHeader(p, &bytesLeft, "conn");
    ADD_INT_FIELD(conn, proto_major);
    ADD_INT_FIELD(conn, proto_minor);
    ADD_INT_FIELD(conn, async_read);
    ADD_INT_FIELD(conn, max_write);
    ADD_INT_FIELD(conn, max_readahead);
    ADD_ULONG_FIELD(conn, capable);
    ADD_ULONG_FIELD(conn, want);
    ADD_INT_FIELD(conn, max_background);
    ADD_INT_FIELD(conn, congestion_threshold);

    {1:s}LogMsg(buffer);
}}

// struct is from fuse_common.h
void {1:s}LogFI (struct fuse_file_info *fi)
{{
    char buffer[MAX_BUFFER+1];  // allow for null byte
    char *p = buffer;
    int  bytesLeft = MAX_BUFFER;
    int  n;

    p = msgHeader(p, &bytesLeft, "fi");
    ADD_ULONG_FIELD(fi, flags);
    ADD_ULL_FIELD(fi, fh_old);
    ADD_INT_FIELD(fi, writepage);
    ADD_INT_FIELD(fi, direct_io);
    ADD_INT_FIELD(fi, keep_cache);
    ADD_INT_FIELD(fi, flush);
    ADD_INT_FIELD(fi, nonseekable);
    ADD_INT_FIELD(fi, flock_release);
    ADD_ULL_FIELD(fi, fh);
    ADD_ULL_FIELD(fi, lock_owner);

    {1:s}LogMsg(buffer);
}};

// for struct see man struct stat
void {1:s}LogStat(struct stat *ss)
{{
    char buffer[MAX_BUFFER+1];  // allow for null byte
    char *p = buffer;
    int  bytesLeft = MAX_BUFFER;
    int  n;

    p = msgHeader(p, &bytesLeft, "ss");
    ADD_ULL_FIELD(ss, st_dev);
    ADD_ULL_FIELD(ss, st_ino);
    ADD_FIELD(ss, st_mode,      0%o);
    ADD_INT_FIELD(ss, st_nlink);
    ADD_INT_FIELD(ss, st_uid);
    ADD_INT_FIELD(ss, st_gid);
    ADD_ULL_FIELD(ss, st_rdev);
    ADD_ULL_FIELD(ss, st_size);
    ADD_FIELD(ss, st_blksize,   %ld);
    ADD_ULL_FIELD(ss, st_blocks);
    ADD_ULONG_FIELD(ss, st_atime);
    ADD_ULONG_FIELD(ss, st_mtime);
    ADD_ULONG_FIELD(ss, st_ctime);

    {1:s}LogMsg(buffer);
}}

// for struct see man struct statvfs
void {1:s}LogStatVFS(struct statvfs *sv)
{{
    char buffer[MAX_BUFFER+1];  // allow for null byte
    char *p = buffer;
    int  bytesLeft = MAX_BUFFER;
    int  n;

    p = msgHeader(p, &bytesLeft, "sv");
    ADD_FIELD(sv, f_bsize,      %ld);
    ADD_FIELD(sv, f_frsize,     %ld);
    ADD_LL_FIELD(sv, f_blocks);
    ADD_LL_FIELD(sv, f_bfree);
    ADD_LL_FIELD(sv, f_bavail);
    ADD_LL_FIELD(sv, f_files);
    ADD_LL_FIELD(sv, f_ffree);
    ADD_LL_FIELD(sv, f_favail);
    ADD_FIELD(sv, f_fsid,       %ld);
    ADD_ULL_FIELD(sv, f_flag);
    ADD_FIELD(sv, f_namemax,    %ld);

    {1:s}LogMsg(buffer);
}}
""".format(pkgName, prefix, ucName)     # GEEP
        content += content2

    content3 = ''
    if instrumenting:
        content3 = """\

// == INSTRUMENTATION ===============================================

// calloc BUCKET_COUNT of these
bucket_t *buckets;

opData_t *{1:s}ClockMeIn(struct timespec *tEntry, unsigned opcode)
{{
    int status = clock_gettime(CLOCK_MONOTONIC, tEntry);
    assert(status == 0);
    bucket_t *myBucket = &buckets[0];   // should be bktNdx
    int doubled = 0; 
    
    status = pthread_mutex_lock(&myBucket->lock);
    assert(status == 0);
    int myCount = myBucket->count++;
    if(myCount >= slotsPerBucket) {{
        opData_t *p;
        slotsPerBucket *= 2;
        doubled++;
        p = realloc(buckets[0].ops, 
                slotsPerBucket*sizeof(opData_t));
        assert(p != NULL);
        buckets[0].ops = p;
    }}
    status = pthread_mutex_unlock(&myBucket->lock);

""".format(pkgName, prefix, ucName)     # GEEP

        if logging:
            content3 += """\
    // DEBUG
    if (doubled) {{
        {1:s}LogMsg("slotsPerBucket doubled to %d\\n", slotsPerBucket);
        {1:s}FlushLog(); 
    }}
    // END
""".format(pkgName, prefix, ucName)     # GEEP

        content3 += """\
    assert(status == 0);
    opData_t *mySlot = &myBucket->ops[myCount];
    mySlot->opCode = opcode;
    return mySlot;
}}

void {1:s}ClockMeOut(struct timespec *tEntry, opData_t *mySlot, size_t count)
{{
    struct timespec tExit;
    long inSec  = tEntry->tv_sec;
    long inNsec = tEntry->tv_nsec;
    int status = clock_gettime(CLOCK_MONOTONIC, &tExit);
    assert(status == 0);
    long lateSec  = tExit.tv_sec - inSec;
    long outNsec = tExit.tv_nsec;
    if (inNsec > outNsec) {{
        outNsec += BILLION;
        lateSec  --;
    }}
    long lateNsec    = outNsec - inNsec;
    assert(lateSec   >= 0);
    assert(lateNsec  < BILLION);
    mySlot->opSec    = inSec;
    mySlot->opNsec   = inNsec;
    mySlot->lateNsec = lateNsec;
    mySlot->lateSec  = lateSec;
    mySlot->count    = count;
}}

int {1:s}WriteBucket()
{{
    time_t now         = time(NULL);
    struct tm *when    = localtime(&now);
    char fullPath[PATH_MAX];
    strcpy(fullPath, {2:s}_DATA->cwd);
    strncat(fullPath, "/tmp/", PATH_MAX);
    char *p = fullPath + strlen(fullPath);
    snprintf(p, PATH_MAX, "/bucket-%04d%02d%02d-%02d%02d%02d",
        when->tm_year + 1900, when->tm_mon + 1, when->tm_mday,
        when->tm_hour, when->tm_min, when->tm_sec);

""".format(pkgName, prefix, ucName)     # GEEP

        if logging:
            content3 += """\
    // DEBUG
    {1:s}LogMsg("data file is %s\\n", fullPath);
    // END

""".format(pkgName, prefix, ucName)     # GEEP

        content3 += """\
    // any 'b' has no effect in Linux
    FILE *f = fopen(fullPath, "w+");
    if (f != NULL) {{
        size_t written = fwrite(
                buckets[0].ops, sizeof(opData_t), buckets[0].count, f);
""".format(pkgName, prefix, ucName)     # GEEP

        if logging:
            content3 += """\
        {1:s}LogMsg("wrote %lu bytes, %lu items, to %s\\n",
                written, buckets[0].count, fullPath);
""".format(pkgName, prefix, ucName)     # GEEP

        content3 += """\
        fflush(f);
        fclose(f);
    }} else {{
        int myErr = errno;
""".format(pkgName, prefix, ucName)     # GEEP

        if logging:
            content3 += """\
        {1:s}LogMsg("errno is %d (%s); failed to open %s\\n", myErr, strerror(myErr), p);
""".format(pkgName, prefix, ucName)     # GEEP

        content3 += """\
    }}
}}
""".format(pkgName, prefix, ucName)     # GEEP
    content += content3

    utilCFile = os.path.join(pathToSrc, "util.c")
    with open(utilCFile, 'w') as f:
        f.write(content)

    # generate .inc files -------------------------------------------

    # optable.inc -----------------------------------------
    content = """/** optable.inc */

struct fuse_operations {0:s}OpTable = {{
    .getattr      = {0:s}getattr,
    .readlink     = {0:s}readlink,
    .getdir       = NULL,
    .mknod        = {0:s}mknod,
    .mkdir        = {0:s}mkdir,
    .unlink       = {0:s}unlink,
    .rmdir        = {0:s}rmdir,
    .symlink      = {0:s}symlink,
    .rename       = {0:s}rename,
    .link         = {0:s}link,
    .chmod        = {0:s}chmod,
    .chown        = {0:s}chown,
    .truncate     = {0:s}truncate,
#ifndef HAVE_UTIMENSAT
    .utime        = {0:s}utime,
#endif
    .open         = {0:s}open,
    .read         = {0:s}read,
    .write        = {0:s}write,
    .statfs       = {0:s}statfs,
    .flush        = {0:s}flush,
    .release      = {0:s}release,
    .fsync        = {0:s}fsync,

#ifdef HAVE_SYS_XATTR_H
    .setxattr     = {0:s}setxattr,
    .getxattr     = {0:s}getxattr,
    .listxattr    = {0:s}listxattr,
    .removexattr  = {0:s}removexattr,
#endif

    .opendir      = {0:s}opendir,
    .readdir      = {0:s}readdir,
    .releasedir   = {0:s}releasedir,
    .fsyncdir     = {0:s}fsyncdir,
    .init         = {0:s}init,
    .destroy      = {0:s}destroy,
    .access       = {0:s}access,
    .create       = {0:s}create,
    .ftruncate    = {0:s}ftruncate,
    .fgetattr     = {0:s}fgetattr

#ifdef HAVE_UTIMENSAT
    , .utimens      = {0:s}utimens
#endif

    , .lock         = {0:s}lock

#ifdef HAVE_POSIX_FALLOCATE
    , .fallocate    = {0:s}fallocate
#endif
}};
""".format(prefix)
    opTableFile = os.path.join(pathToPkg, os.path.join('src', 'optable.inc'))
    with open(opTableFile, 'w') as f:
        f.write(content)

    # generate op .inc files ------------------------------
    opAttrs = setOpAttrs()
    # mkSrcDir(args, opAttrs)

    srcDir = os.path.join(pathToPkg, 'src')
    makedir_p(srcDir, 0o755)

    # XXX does not catch 'main'
    for name in OP_NAMES:
        attrs = opAttrs[name]
        if (attrs & DEPRECATED) or (attrs & NOT_IMPLEMENTED):
            continue
        if not name in funcMap:   # names at end are not yet implemented
            # DEBUG
            print("%s is NOT IN funcMap" % name)
            # END
            break
        ff = funcMap[name]    # FuseFunc for this name
        opCode = "FG_%s" % name.upper()
        pathToInc = os.path.join(srcDir, "%s.inc" % name)
        ss = []
        ss.append("/** %s.inc */\n" % (name))
        if attrs & CHK_DEF_XATTR:
            ss.append("#ifdef HAVE_SYS_XATTR_H")
        elif name == 'utimens':
            ss.append("#ifdef HAVE_UTIMENSAT")
        elif name == 'fallocate':
            ss.append("#ifdef HAVE_POSIX_FALLOCATE")

        # -- first line, LBRACE -----------------------
        ss.append("static %s\n{" % ff.firstLine())

        # -- instrumenation ---------------------------
        if instrumenting:
            content = """    struct timespec tEntry;
    opData_t *myData = {1:s}ClockMeIn(&tEntry, {2:s});
""".format(name, prefix, opCode)
            ss.append(content)
        # -- variable declarations --------------------
        if attrs & RETURNS_STATUS:
            ss.append('    int status = 0;')
        if (attrs & SYSCALL_RET_FD) or name == 'fallocate':
            ss.append('    int fd;')
        if attrs & (FULL_PATH | DOUBLE_FULL_PATH) :
            ss.append('    char fpath[PATH_MAX];')
        if attrs & DOUBLE_FULL_PATH:
            ss.append('    char fnewpath[PATH_MAX];')
        if attrs & HAS_LINK_FILE:
            ss.append('    char flink[PATH_MAX];')

        if name in ['opendir', 'readdir']:
            ss.append('    DIR *dp;')
            if name=='readdir':
                ss.append('    struct dirent *entry;')
        elif name == 'listxattr':
            ss.append('    char *ptr;')

        ss.append("")

        # -- log on entry -----------------------------
        if logging:
            if name == 'init':
                ss.append("    %sLogEntry(\"\\n%sinit()\\n\");" % (prefix, prefix))
                ss.append('    %sLogConn(conn);' % prefix)
                ss.append('    %sLogContext(fuse_get_context());' % prefix)
            else:
                if attrs & DOUBLE_FULL_PATH:
                    part0 = "\"\\n%s%s" % (prefix, name)
                    part1 = '(path=\\"%s\\", newpath=\\"%s\\")\\n",'
                    s = ("    %sLogEntry(" % prefix) + part0 + part1
                    ss.append(s)
                    ss.append("            path, newpath);")
                else:
                    logE = ['    %sLogEntry(\"\\n%s%s(' % (prefix, prefix, name) ]
                    for ndx, param in enumerate(ff.params):
                        if ndx > 0:
                            logE.append(', ')
                        pName = param[1]
                        if pName == 'size':
                            if name in ['read', 'write', ]:
                                pat = '%lld'
                            else:
                                pat = '%d'
                        elif pName == 'value':
                            if name in ['getxattr',]:
                                pat = '0x%08x'
                            else:
                                pat = '\\"%s\\"'
                        elif pName in LOG_ENTRY_PAT_MAP:
                            pat  = LOG_ENTRY_PAT_MAP[pName]
                        else:
                            pat = 'UNKNOWN PAT FOR \'%s\'' % pName
                        logE.append( '%s=%s' % (pName, pat))
                    logE.append(")\\n\",")
                    ss.append( ''.join(logE))
    
                    # now add a parameter list on the next line
                    logEP = ['             ']
                    for ndx, param in enumerate(ff.params):
                        if ndx > 0:
                            logEP.append(', ')
                        pName = param[1]
                        logEP.append(pName)
                    logEP.append(');')
                    ss.append(''.join(logEP))

        if name == 'readdir':
            ss.append('    dp = (DIR *) (uintptr_t) fi->fh;')

        if logging and name != 'opendir' and name != 'readdir' and attrs & LOGGING_FI and not attrs & SET_FH_FROM_FD:
            ss.append('    %sLogFI(fi);' % prefix)

        # -- set up absolute paths ------------------------
        if attrs & FULL_PATH:
            ss.append("    %sFullPath(fpath, path);" % prefix)
        if attrs & DOUBLE_FULL_PATH:
            ss.append("    %sFullPath(fnewpath, newpath);" % prefix)
        if attrs & HAS_LINK_FILE:
            ss.append("    %sFullPath(flink, link);" % prefix)
        ss.append("")

        # -- SYS CALL -------------------------------------

        sysCall = OP_CALL_MAP[name][0]
        if sysCall == '':
            if name != 'init':
                ss.append("    // CURRENTLY A NO-OP\n")
        else:
            if name == 'fallocate':
                ss.append("""
    if (mode) {
        status = -1;
        errno  = EOPNOTSUPP;
    } else {
        fd = open(fpath, O_WRONLY);
        if (fd == -1) {
            status = -1;
        } else {
            status = posix_fallocate(fd, offset, len);
            close(fd);
        }
    }
""")
            elif name == 'flock':
                ss.append('    status = flock(fi->fh, op);')
            elif name == 'fsync':
                ss.append(
"""    // freebsd
#ifdef HAVE_FDATASYNC
    if (datasync)
        status = fdatasync(fi->fh);
    else
#endif
        status = fsync(fi->fh);""")

            elif name == 'lock':
                ss.append('    status = ulockmgr_op(fi->fh, cmd, lock, &fi->lock_owner, sizeof(fi->lock_owner));')

            elif name == 'mknod':
                # in python format specs {} must be doubled :-(
                ss.append(

"""    // ATTRIBUTION
    if (S_ISREG(mode)) {{
        status = open(fpath, O_CREAT | O_EXCL | O_WRONLY, mode);
        if (status < 0)
            status = {1:s}Error(\"{1:s}mknod open\");
        else {{
            status = close(status);
            if (status < 0)
                status = {1:s}Error(\"{1:s}mknod close\");
        }}
    }} else if (S_ISFIFO(mode)) {{
        status = mkfifo(fpath, mode);
        if (status < 0)
            status = {1:s}Error(\"{1:s}mknod mkfifo\");
    }} else {{
        status = mknod(fpath, mode, dev);
        if (status < 0)
            status = {1:s}Error(\"{1:s}mknod mknod\");
    }}""".format(name, prefix) )

            elif name == 'open':
                ss.append("    fd = %s(fpath, fi->flags);" % sysCall)
            elif name == 'readdir':
                content = """
    entry = readdir(dp);
    if (entry == 0) {{
        status = {1:s}Error("{1:s}readdir readdir");
        return status;
    }}
    do {{
""".format(name,prefix)                         # BLIP
                if logging:
                    content += """\
        {1:s}LogMsg("calling filler(%s)\\n", entry->d_name);
""".format(name,prefix)                         # BLIP

                content += """\
        if (filler(buf, entry->d_name, NULL, 0) != 0) {{
""".format(name,prefix)                         # BLIP
                if logging:
                    content += """\
            {1:s}LogMsg("    ERROR {1:s}readdir filler:  buffer full");
""".format(name,prefix)                         # BLIP

                content += """\
            return -ENOMEM;
        }
    } while ((entry = readdir(dp)) != NULL);
"""
                ss.append(content)

            elif name == 'readlink':
                ss.append("    status = readlink(fpath, link, size - 1);")
            elif name == 'releasedir':
                ss.append("    status = closedir((DIR *) (uintptr_t) fi->fh);")
            elif name == 'utimens':
                ss.append(
                "    status = utimensat(0, fpath, tv, AT_SYMLINK_NOFOLLOW);")
            elif attrs & HAS_LINK_FILE:
                ss.append("    status = %s(path, flink);" % sysCall)
            elif attrs & DOUBLE_FULL_PATH:
                ss.append("    status = %s(fpath, fnewpath);" % sysCall)
            elif attrs & (FULL_PATH | LOGGING_FI):
                if attrs & SYSCALL_RET_FD:
                    ss.append("    fd = %s(fpath%s);" % (
                        sysCall, ff.otherArgs()))
                else:
                    if attrs & SYSCALL_FI_PARAM1:
                        if name == 'fgetattr':
                            ss.append('    // FreeBSD special case; ATTRIBUTION')
                            ss.append('    if (!strcmp(path, "/")) {')
                            ss.append('        char fpath[PATH_MAX];')
                            ss.append("        %sFullPath(fpath, path);" % (
                                prefix))
                            ss.append("        status = lstat(fpath%s);" % (
                                ff.otherArgs()))
                            ss.append('        if (status < 0)')
                            ss.append("            status = %sError(\"%sfgetattr lstat\");" % (prefix, prefix))
                            ss.append('    } else {')
                            ss.append("        status = %s(fi->fh%s);" % (
                                sysCall, ff.otherArgs()))
                            ss.append('        if (status < 0)')
                            ss.append("            status = %sError(\"%sfgetattr fstat\");" % (prefix, prefix))
                            ss.append('    }')
                        elif name == 'opendir':
                            ss.append('    dp = opendir(fpath);')
                        else:
                            ss.append("    status = %s(fi->fh%s);" % (
                                sysCall, ff.otherArgs()))
                    else:
                        ss.append("    status = %s(fpath%s);" % (
                            (sysCall, ff.otherArgs())))

        # -- check for error status -----------------------
        if name == 'opendir':
            ss.append('    if (dp == NULL)')
            ss.append("        status = %sError(\"%s%s %s\");" % (
                prefix, prefix, name, sysCall))
        elif name != 'fgetattr' and attrs & CHECK_ERR_AND_FLIP:
            if attrs & SYSCALL_RET_FD:
                ss.append("    if (fd < 0)")
            else:
                ss.append("    if (status < 0)")
            ss.append("        status = %sError(\"%s %s\");\n" % (
                prefix, prefix + name, sysCall))
            if name == 'readlink':
                ss.append('    else {')
                ss.append('        link[status] = \'\\0\';')
                ss.append('        status = 0;')
                ss.append('    }')
        if logging and name in ['getxattr',]:
            ss.append('    else')
            start = '        %sLogMsg(' % prefix
            ss.append(start + '"    value=\\"%s\\"\\n", value);' )

        if logging and name == 'listxattr':
            start = '    %sLogMsg("    ' % prefix
            ss.append(
                  start + 'returned attributes (length %d):\\n", status);')
            ss.append(
              '    for (ptr = list; ptr < list + status; ptr += strlen(ptr)+1)')
            start = '        %sLogMsg' % prefix
            ss.append( start + '("    \\"%s\\"\\n", ptr);')

        # -- logging stat -----------------------------
        if logging:
            if (attrs & LOGGING_STAT):
                ss.append("    %sLogStat(%s);\n"    % (prefix, ff.params[1][1]))
            elif attrs & LOGGING_STATVFS:
                ss.append("    %sLogStatVFS(%s);\n" % (prefix, ff.params[1][1]))

        if attrs & SET_FH_FROM_FD:
            ss.append('    fi->fh = fd;')
            if logging:
                ss.append('    %sLogFI(fi);' % prefix)
        elif name=='opendir':
            ss.append('    fi->fh = (intptr_t) dp;')
            if logging:
                ss.append('    %sLogFI(fi);' % prefix)
        elif logging and name=='readdir':
            ss.append('    %sLogFI(fi);' % prefix)

        # -- instrumentation at exit ------------------
        if instrumenting:
            if name in ['readlink', 'read', 'write',
                    'setxattr', 'getxattr', 'listxattr',]:
                ss.append('    %sClockMeOut(&tEntry, myData, size);' % prefix)
            else:
                ss.append('    %sClockMeOut(&tEntry, myData, %s);' % (prefix,0))
            if name == 'destroy':
                ss.append('\n    %sWriteBucket();' % prefix)

        # -- return -----------------------------------
        if attrs & RETURNS_STATUS:
            ss.append("    return status;")
        elif name == 'init':
            ss.append("    return %s_DATA;" % ucName)
        ss.append("}")
        if (attrs & CHK_DEF_XATTR) or (name == 'fallocate') or (name=='utimens'):
            ss.append("#endif")

        out = "\n".join(ss) + "\n"
        with open(pathToInc, 'w') as f:
            f.write(out)
