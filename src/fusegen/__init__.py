# fusegen/__init__.py

import errno
import os
import re
import shutil
import subprocess
import sys

__all__ = ['__version__', '__version_date__',
           'BASH', 'SH',
           'DEPRECATED', 'NOT_IMPLEMENTED',
           # functions
           'check_date', 'check_pkg_name', 'check_pgm_names', 'check_version',
           'invoke_shell', 'make_fuse_pkg',
           'op_names', ]

# -- exported constants ---------------------------------------------
__version__ = '0.6.34'
__version_date__ = '2017-09-25'

BASH = '/bin/bash'
SH = '/bin/sh'

# path to text file of quasi-prototypes
PATH_TO_FIRST_LINES = 'fragments/prototypes'

# a table of FUSE function names
OP_NAMES = [
    'getattr', 'readlink', 'getdir', 'mknod', 'mkdir',
    'unlink', 'rmdir', 'symlink', 'rename', 'link',
    'chmod', 'chown', 'truncate', 'utime', 'open',
    'read', 'write', 'statfs', 'flush', 'release',
    'fsync', 'setxattr', 'getxattr', 'listxattr', 'removexattr',
    'opendir', 'readdir', 'releasedir', 'fsyncdir', 'init',
    'destroy', 'access', 'create', 'ftruncate', 'fgetattr',
    # fuse version 2.6
    'utimens', 'bmap', 'lock',
    # fusion 2.9
    'flock',
    # fusion 2.9.1
    'fallocate',
    # AS THESE ARE IMPLEMENTED, update the consistency check in fuseGen
    # NOT YET IMPLEMENTED
    # fusion 2.8
    # 'ioctl',        'poll',
    # fusion 2.9
    # 'write_buf','read_buf',
]


def op_names():
    """
    Return a copy of the list of op names, possibly including deprecated
    functions but excluding any which are not implemented.
    """
    in_file = []
    for name in OP_NAMES:
        in_file.append(name)
    return in_file


SET_STATUS = 0x01      # sets the status variable
SET_FD = 0x02      # sets an fd variable
OP_SPECIAL = 0x04      # messy handling
FH_PARAM = 0x08      # param is fi->fh instead of fpath
FLAGS_PARAM = 0x10      # param is fi->flags instead of fi

# Map FUSE op name to syscall name and attributes.  This is for use in
# generating syscalls.
OP_CALL_MAP = {
    'getattr': ('lstat', SET_STATUS),
    'readlink': ('readlink', SET_STATUS | OP_SPECIAL),  # size - 1
    'mknod': ('mknod', SET_STATUS | OP_SPECIAL),  # v messy
    'mkdir': ('mkdir', SET_STATUS),
    'unlink': ('unlink', SET_STATUS),
    'rmdir': ('rmdir', SET_STATUS),
    'symlink': ('symlink', SET_STATUS),
    'rename': ('rename', SET_STATUS),
    'link': ('link', SET_STATUS),
    'chmod': ('chmod', SET_STATUS),
    'chown': ('chown', SET_STATUS),
    'truncate': ('truncate', SET_STATUS),
    'utime': ('utime', SET_STATUS),
    'open': ('open', SET_FD | FLAGS_PARAM),
    'read': ('pread', SET_STATUS | FH_PARAM),
    'write': ('pwrite', SET_STATUS | FH_PARAM),
    'statfs': ('statvfs', SET_STATUS),
    'flush': ('', SET_STATUS),     # a no-op ??
    'release': ('close', SET_STATUS | FH_PARAM),
    'fsync': ('fsync', SET_STATUS | OP_SPECIAL),  # may be fdatasync
    'setxattr': ('lsetxattr', SET_STATUS),
    'getxattr': ('lgetxattr', SET_STATUS),
    'listxattr': ('llistxattr', SET_STATUS),
    'removexattr': ('lremovexattr', SET_STATUS),
    'opendir': ('opendir', SET_STATUS),
    'readdir': ('lreaddir', OP_SPECIAL),  # loops
    'releasedir': ('closedir', OP_SPECIAL),  # must cast fi->fh
    'fsyncdir': ('', SET_STATUS),  # a no-op ??
    'init': ('', OP_SPECIAL),  # kukemal
    'destroy': ('', SET_STATUS),
    'access': ('access', SET_STATUS),
    'create': ('creat', SET_FD),       # call returns fd
    'ftruncate': ('ftruncate', SET_STATUS | FH_PARAM),
    'fgetattr': ('fstat', SET_STATUS | FH_PARAM),

    'utimens': ('utimensat', SET_STATUS),
    'bmap': ('_bmap', SET_STATUS),
    'lock': ('ulockmgr_op', SET_STATUS),
    'flock': ('flock', SET_STATUS),
    'fallocate': ('posix_fallocate', SET_STATUS),
}
LOG_ENTRY_PAT_MAP = {
    'blocksize': '0x%08x',
    'buf': '0x%08x',
    'cmd': '%d',
    'datasync': '%d',
    'dev': '%lld',
    'fi': '0x%08x',
    'filler': '0x%08x',
    'flags': '0x%08x',
    'fpath': '\\"%s\\"',
    'gid': '%d',
    'idx': '0x016x',
    'len': '%lld',
    'link': '\\"%s\\"',
    'list': '0x%08x',
    'lock': '0x%08x',
    'mask': '0%o',
    'mode': '0%03o',
    'name': '\\"%s\\"',
    'newpath': '\\"%s\\"',
    'newsize': '%lld',
    'offset': '%lld',
    'op': '%d',
    'path': '\\"%s\\"',
    'rootdir': '\\"%s\\"',
    'size': '%d',             # or should this be lld ?
    'statbuf': '0x%08x',
    'statv': '0x%08x',
    'tv[2]': '0x%08x',
    'ubuf': '0x%08x',
    'uid': '%d',
    'userdata': '0x%08x',
    'value': '\\"%s\\"',
}
PAT_MAP = {
    'buf': '0x%08x',  # XXX ?
    'fi': '0x%08x',
    'statbuf': '0x%08x',
    'ubuf': '%s',
}

# -- functions ------------------------------------------------------
PKG_DATE_RE = re.compile(r'^[\d]{4}-\d\d-\d\d$')


def check_date(str_):
    if not str_:
        print("date must not be empty")
        sys.exit(1)
    else:
        str_ = str_.strip()
        match_ = PKG_DATE_RE.match(str_)
        if match_ is None:
            print(("'%s' is not a valid YYYY-MM-DD date" % str_))
            sys.exit(1)


PKG_NAME_RE = re.compile(r'^[a-z_][a-z0-9_\-]*$', re.IGNORECASE)


def check_pkg_name(str_):
    if not str_:
        print("you must provide a package name")
        sys.exit(1)
    else:
        str_ = str_.strip()
        match_ = PKG_NAME_RE.match(str_)
        if match_ is None:
            print("'%s' is not a valid package name" % str_)
            sys.exit(1)


PGM_NAME_RE = re.compile(r'^[a-z_][a-z0-9_\-]*$', re.IGNORECASE)


def check_pgm_names(strings):
    if not strings or len(strings) == 0:
        print("you must supply at least one program name")
        sys.exit(1)
    else:
        for str_ in strings:
            if not PGM_NAME_RE.match(str_):
                print("'%s' is not a valid program name" % str_)
                sys.exit(1)


PKG_VERSION_RE = re.compile(r'^\d+\.\d+.\d+$')


def check_version(str_):
    if not str_:
        print("version must not be empty")
        sys.exit(1)
    else:
        str_ = str_.strip()
        match_ = PKG_VERSION_RE.match(str_)
        if match_ is None:
            print(("'%s' is not a valid X.Y.Z version" % str_))
            sys.exit(1)


def invoke_shell(cmd_list):
    try:
        output = subprocess.check_output(cmd_list, stderr=subprocess.STDOUT)
        output = str(output, 'utf-8')
    except subprocess.CalledProcessError as exc:
        output = str(exc)
    return output


class FuseFunc(object):

    def __init__(self, f_name, f_type, params, p2t_map):
        self._name = f_name      # string, trimmed
        self._type = f_type      # string, left-trimmed,
        self._params = params   # a list of 2-tuples
        self._p2p_map = p2t_map   # map, parameter name to type (as string)

    @property
    def name(self):
        return self._name

    @property
    def f_type(self):
        return self._type

    @property
    def params(self):
        return self._params

    @property
    def p2t_map(self):
        return self._p2p_map

    def first_line(self):
        """ return the first line of the function """
        line = self.f_type + self.name + '('
        p_count = len(self.params)
        for ndx, param in enumerate(self.params):
            line += param[0]
            line += param[1]
            if ndx < p_count - 1:
                line += ', '
        line += ')'
        return line

    def other_args(self):
        """ return comma-separated list of arguments other than the first """

        # p_count = len(self.params)
        str_ = ''
        for ndx, param in enumerate(self.params):
            p_name = param[1]
            if p_name != 'fi' and ndx > 0:
                str_ += ', ' + param[1]
        return str_

    @classmethod
    def parse_proto(cls, line, prefix=''):

        line = line.strip()
        params = []     # of 2-tuples
        p2t_map = {}

        parts = line.split(' ', 1)
        p_count = len(parts)
        if p_count != 2:
            print("error parsing prototype: splits into %d parts!" % p_count)
            sys.exit(1)
        f_type = parts[0].strip()
        f_type += ' '
        rest = parts[1].lstrip()
        if rest[0] == '*':
            rest = rest[1:]
            f_type += '*'

        l_ndx = rest.index('(')
        r_ndx = rest.index(')')
        if l_ndx == -1 or r_ndx == -1:
            print("can't locate parens is '%s'; aborting" % rest)
            sys.exit(1)
        base_name = rest[:l_ndx]
        if prefix == '' or base_name == 'main':
            f_name = base_name
        else:
            f_name = prefix + base_name

        arg_list = rest[l_ndx + 1:r_ndx]

        # DEBUG
        # print("type '%s', fName '%s', args '%s'" % (fType, fName, argList))
        # END

        parts = arg_list.split(',')
        for part in parts:
            # DEBUG
            # print("  part: '%s'" % part)
            # END
            if part == '':
                continue
            chunks = part.rsplit(' ', 1)
            chunk_count = len(chunks)
            if chunk_count != 2:
                print("can't split '%s': aborting" % part)
                sys.exit(1)
            arg_type = chunks[0].strip()
            arg_type += ' '
            art_name = chunks[1]
            if art_name[0] == '*':
                art_name = art_name[1:]
                arg_type += '*'
            # DEBUG
            # print("    argType: '%s', argName '%s'" % (argType, argName))
            # END
            params.append((arg_type, art_name))     # that's a 2-tuple
            p2t_map[art_name] = arg_type

        return base_name, FuseFunc(f_name, f_type, params, p2t_map)

    @classmethod
    def get_func_map(cls, prefix=''):

        lines = []
        with open(PATH_TO_FIRST_LINES, 'r') as file:
            line = file.readline()
            while line and line != '':
                # simplified comments
                if line[0] != '#':
                    line = line[:-1]
                    lines.append(line)
                    line = file.readline()

        func_map = {}  # this maps prefixed names to FuseFunc objects
        op_code_map = {}  # maps names to integer opCodes

        for ndx, line in enumerate(lines):
            name, f_map = FuseFunc.parse_proto(line, prefix)
            func_map[name] = f_map
            op_code_map[name] = ndx
            # DEBUG
            print("FuseFunc.getFuncMap: %-13s => %2d" % (name, ndx))
            # END

        # DEBUG
        if 'lock' in func_map:
            print("lock is in the map")
        else:
            print("lock is NOT in the map")
        # END
        return func_map, op_code_map

# == MAIN FUNCTION ==================================================

# attributes of fuse operations


DEPRECATED = 0x00000001
RETURNS_STATUS = 0x00000002
CHECK_ERR_AND_FLIP = 0x00000004
FULL_PATH = 0x00000008
DOUBLE_FULL_PATH = 0x00000010
#
LOGGING_STAT = 0x00000040
LOGGING_STATVFS = 0x00000080
HAS_LINK_FILE = 0x00000100
LOGGING_FI = 0x00000200
SYSCALL_RET_FD = 0x00000400
SET_FH_FROM_FD = 0x00000800
SYSCALL_FI_PARAM1 = 0x00001000

CHK_DEF_XATTR = 0x10000000
NOT_IMPLEMENTED = 0x80000000


def set_op_attrs():
    """
    Return a map from fuse op names to attributes
    """
    op_attrs = {}
    for name in OP_NAMES:
        attrs = 0
        if name in ['getdir', 'utime', ]:
            attrs |= DEPRECATED
        elif name in ['ioctl', 'poll', 'write_buf', 'read_buf', ]:
            attrs |= NOT_IMPLEMENTED
        else:
            if name in ['symlink', ]:
                attrs |= HAS_LINK_FILE

            if name != 'init' and name != 'destroy':
                attrs |= RETURNS_STATUS

            if name in ['rename', 'link', ]:
                attrs |= DOUBLE_FULL_PATH

            # this is a NEGATIVE check: list those ops which do NOT use
            if name not in ['flock', 'lock',
                            'symlink',
                            'read', 'write', 'flush', 'release', 'fsync',
                            'readdir', 'releasedir', 'fsyncdir', 'init',
                            'destroy', 'ftruncate', 'fgetattr']:
                attrs |= FULL_PATH

            if name not in ['destroy', 'flush', 'fsyncdir',
                            'init', 'mknod', 'readdir', ]:
                attrs |= CHECK_ERR_AND_FLIP

            if name in ['setxattr', 'getxattr', 'listxattr', 'removexattr', ]:
                attrs |= CHK_DEF_XATTR

            if name in ['create', 'fallocate', 'fgetattr', 'flush',
                        'fsync', 'fsyncdir', 'ftruncate',
                        'lock',
                        'opendir', 'open', 'readdir', 'read', 'releasedir',
                        'release', 'write', ]:
                attrs |= LOGGING_FI

            if name in ['create', 'open', ]:
                attrs |= SET_FH_FROM_FD

            if name in ['fgetattr', 'flock', 'fsync', 'opendir',
                        'read', 'releasedir', 'release', 'ftruncate', 'write']:
                attrs |= SYSCALL_FI_PARAM1

            if name in ['getattr', 'fgetattr', ]:
                attrs |= LOGGING_STAT
            elif name == 'statfs':
                attrs |= LOGGING_STATVFS
            if name in ['create', 'open', ]:
                attrs |= SYSCALL_RET_FD

        op_attrs[name] = attrs
    return op_attrs


def makedir_p(path, mode):
    # XXX SLOPPY: doesn't handle case where mode is wrong
    # XXX MISLEADING: the name suggests it creates missing subdirs
    try:
        os.mkdir(path, mode)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise exc
        pass


def make_fuse_pkg(args):
    ac_prereq = args.ac_prereq
    email_addr = args.email_addr
    instrumenting = args.instrumenting
    force = args.force
    logging = args.logging
    my_date = args.my_date
    my_version = args.my_version
    path_to_pkg = args.path_to_pkg    # target package directory
    pkg_name = args.pkg_name
    prefix = pkg_name + '_'     # XXX FORCES UNDERSCORE
    uc_name = args.uc_name

    # make sure opCode <-> opName maps are consistent ---------------
    func_map, op_code_map = FuseFunc.get_func_map(prefix)
    # DEBUG
    if 'lock' in func_map:
        print("lock is in the main map")
    else:
        print("lock is NOT in the main map")
    # END
    inconsistent = False
    for ndx in range(len(OP_NAMES)):
        name = OP_NAMES[ndx]
        if name not in op_code_map:
            break
        ndx_from_name = op_code_map[name]
        if ndx != ndx_from_name:
            print("INCONSISTENCY: %s is OP_NAME %d, but opCodeMap has %d" % (
                name, ndx, ndx_from_name))
            inconsistent = True
    if inconsistent:
        print("aborting")
        sys.exit(1)

    # ===============================================================
    # CREATE DIRECTORIES
    # ===============================================================

    # if -force and pathToPkg exists, delete it -- unless there is a .git/
    if force and os.path.exists(path_to_pkg):
        path_to_dot_git = os.path.join(path_to_pkg, ".git")
        if os.path.exists(path_to_dot_git):
            print("'%s' exists; cannot proceed" % path_to_dot_git)
            sys.exit(0)
        else:
            shutil.rmtree(path_to_pkg)

    makedir_p(path_to_pkg, 0o755)

    mount_point = os.path.join('workdir', 'mount_point')
    root_dir = os.path.join('workdir', 'rootdir')
    make_file_sub_dirs = [
        'doc',
        'examples',
        'man',
        'scripts',
        'src',
        'tests',
    ]
    other_sub_dirs = ['bin', 'config', 'ghpDoc', 'm4', 'workdir',
                      mount_point, root_dir, 'tmp', ]
    sub_dir = make_file_sub_dirs + other_sub_dirs
    for dir in sub_dir:
        path_to_sub_dir = os.path.join(path_to_pkg, dir)
        makedir_p(path_to_sub_dir, 0o755)

    # ===============================================================
    # TOP LEVEL FILES
    # ===============================================================

    # copy over fusgegen/src files  ---------------------------------
    def copy_from_csrc(name, executable=False, top_file=True):
        """ copy a file from py/fusegen/src/ to the top level package dir """
        src = os.path.join('src', 'c_src', name)
        if top_file:
            dest = os.path.join(path_to_pkg, name)
        else:
            dest = os.path.join(path_to_pkg, os.path.join('src', name))
        with open(src, 'r') as file_a:
            text = file_a.read()
            with open(dest, 'w') as file_b:
                file_b.write(text)
            if executable:
                os.chmod(dest, 0o744)
            else:
                os.chmod(dest, 0o644)

    # install-sh removed from both lists 2015-02-22
    for in_file in ['autogen.sh', 'build', 'config.guess', 'config.sub',
                    'COPYING', 'COPYING.LIB', 'COPYING.AUTOCONF.EXCEPTION',
                    'COPYING.GNUBL', 'README.licenses', ]:
        copy_from_csrc(in_file, in_file in ['autogen.sh', 'build', ])
    for in_file in ['fuse.h', 'fuse_common.h', 'fuse_opt.h', ]:
        copy_from_csrc(in_file, False, False)

    # write CHANGES -------------------------------------------------
    chg_file = os.path.join(path_to_pkg, 'CHANGES')
    with open(chg_file, 'w', 0o644) as file:
        file.write("~/dev/c/%s/CHANGES\n\n" % pkg_name)
        file.write("v%s\n" % my_version)
        file.write("    %s\n" % my_date)
        file.write("        *\n")

    # write configure.ac --------------------------------------------
    config_file = os.path.join(path_to_pkg, 'configure.ac')
    config_test = """#                                               -*- Autoconf -*-
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
AC_CHECK_HEADERS([fcntl.h limits.h stdlib.h string.h sys/statvfs.h\\
    unistd.h utime.h sys/xattr.h])

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

AC_CHECK_FUNCS([fdatasync ftruncate mkdir mkfifo realpath rmdir strerror \\
    utimensat])
AC_CHECK_FUNCS([posix_fallocate])

AC_CONFIG_FILES([Makefile src/Makefile])
AC_OUTPUT
""".format(ac_prereq, pkg_name, my_date, email_addr)
    with open(config_file, 'w', 0o644) as file:
        file.write(config_test)

    # write Makefile.am  --------------------------------------------
    # XXX The EXTRA_DIST line seems senseless, as we copy it in.
    make_am_file = os.path.join(path_to_pkg, 'Makefile.am')
    content = """
ACLOCAL_AMFLAGS = -I m4
EXTRA_DIST = autogen.sh
SUBDIRS = src

# <ATTRIBUTION>
#
# Make it impossible to install the fuse file system. It must never be run
# as root, because that causes critical security risks.
install install-data install-exec uninstall installdirs check installcheck:
\	echo This package must never be installed.

install-dvi install-info install-ps install-pdf dvi pdf ps info :
\	echo This package must never be installed.
"""
    with open(make_am_file, 'w', 0o644) as file:
        file.write(content)

    # write Makefile.in  --------------------------------------------
    # XXX This bit of silliness handles aclocal's requirement that
    # the file exist before we create it
    make_in_file = os.path.join(
        path_to_pkg, os.path.join(
            'src', 'Makefile.in'))
    content = """
"""
    with open(make_in_file, 'w', 0o644) as file:
        file.write(content)

    # write TODO ----------------------------------------------------
    todo_file = os.path.join(path_to_pkg, 'TODO')
    with open(todo_file, 'w', 0o644) as file:
        file.write("~/dev/c/%s/TODO\n\n" % pkg_name)
        file.write("%s\n" % my_date)
        file.write("    *\n")

    # ===============================================================
    # bin/ FILE GENERATION
    # ===============================================================

    # write bin/mountNAME
    path_to_bin = os.path.join(path_to_pkg, 'bin')
    path_to_cmd = os.path.join(path_to_bin, 'mount' + uc_name)
    with open(path_to_cmd, 'w') as file:
        file.write("cd %s\n" % path_to_pkg)
        file.write("src/%s workdir/rootdir workdir/mountPoint\n" % pkg_name)
    os.chmod(path_to_cmd, 0o744)

    # write bin/umountNAME
    path_to_cmd = os.path.join(path_to_bin, 'umount' + uc_name)
    with open(path_to_cmd, 'w') as file:
        file.write("cd %s\n" % path_to_pkg)
        file.write("fusermount -uz workdir/mountPoint\n")
    os.chmod(path_to_cmd, 0o744)

    # write bin/blk-31-4k
    path_to_cmd = os.path.join(path_to_bin, 'blk-31-4k')
    content = """echo "blk-31-4k: test size is being set to $1 MB"
#
cd ~/dev/c/{0:s}
bin/mount{1:s}
cd workdir/mountPoint
fio --name=global --bs=4k --size=$1m \
\	--rw=randrw --rwmixread=75 \
\	--name=job1 --name=job2 --name=job3 --name=job4
cd ../..
bin/umount{1:s}
""".format(pkg_name, uc_name)
    with open(path_to_cmd, 'w') as file:
        file.write(content)
    os.chmod(path_to_cmd, 0o744)

    # ===============================================================
    # src/ FILE GENERATION
    # ===============================================================

    path_to_src = os.path.join(path_to_pkg, 'src')

    # src/fuse_version.h --------------------------------------------

    fuse_version_file = os.path.join(path_to_src, 'fuse_version.h')
    content = """/** fuse_version.h */

#ifndef _FUSE_VERSION_H_
#define _FUSE_VERSION_H_

#define FUSE_USE_VERSION 26

#endif
"""

    with open(fuse_version_file, 'w') as file:
        file.write(content)

    # src/Makefile.am -----------------------------------------------
    make_am_file = os.path.join(path_to_src, 'Makefile.am')
    content = """
bin_PROGRAMS = {0:s}
{1:s}SOURCES = {0:s}.c fuse.h fuse_version.h opcodes.h {0:s}.h util.c\\
    $(wildcard *.inc)
AM_CFLAGS = @FUSE_CFLAGS@
LDADD = @FUSE_LIBS@
""".format(pkg_name, prefix)

    with open(make_am_file, 'w', 0o644) as file:
        file.write(content)

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
""".format(pkg_name)                                # BAZ

    if logging:
        content += """\
    // Set up logging
    myData->logfile = {0:s}OpenLog();
""".format(prefix)                                  # BAZ

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
        {{"fgBlockSize", 1, NULL, 0}},    // default = 4, times 1024 bytes
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

""".format(pkg_name)        # , prefix, uc_name)     # FOO

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
"""                 # .format(pkg_name, prefix, uc_name)     # FOO

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
""".format(pkg_name, prefix)                         # BAZ

    path_to_main = os.path.join(path_to_src, 'main.inc')
    with open(path_to_main, 'w') as file:
        file.write(content)

    # src/opcodes.h -------------------------------------------------
    path_to_op_codes = os.path.join(path_to_src, 'opcodes.h')
    with open(path_to_op_codes, 'w') as file:
        file.write("/* opcodes.h */\n\n")
        file.write("#ifndef _OPCODES_H_\n")
        for ndx, name in enumerate(OP_NAMES):
            file.write("#define FG_%-14s (%d)\n" % (name.upper(), ndx))
        file.write("#endif\n")

    # package header file -------------------------------------------
    content = """/** {0:s}.h */

#ifndef _{1:s}_H_
#define _{1:s}_H_

#ifdef linux
#ifndef _XOPEN_SOURCE
#define _XOPEN_SOURCE (700)
#endif
#endif

""".format(pkg_name, uc_name)     # FOO

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

""".format(pkg_name, prefix, uc_name)     # FOO

    if logging:
        content += """\

void {0:s}LogConn   (struct fuse_conn_info *conn);
void {0:s}LogEntry  (const char *fmt, ...);
void {0:s}LogFI     (struct fuse_file_info *fi);
void {0:s}LogMsg    (const char *fmt, ...);
void {0:s}LogStat   (struct stat *si);
void {0:s}LogstatVFS(struct statvfs *sv);
FILE *{0:s}OpenLog  (void);
int  {0:s}FlushLog  (void);
""".format(prefix)          # pkg_name, prefix, uc_name)     # FOO

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
    unsigned    count       : 17;   // number bytes read or written; 128K max
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

opData_t *{0:s}ClockMeIn(struct timespec *tEntry, unsigned opCode);
void {0:s}ClockMeOut(struct timespec *tEntry, opData_t *mySlot, size_t count);
int {0:s}WriteBucket();

// END INSTRUMENTATION ----------------------------------------------
""".format(prefix)          # pkg_name, prefix, uc_name)     # FOO

    content += """\
#endif
"""
    header_file = os.path.join(path_to_src, "%s.h" % pkg_name)
    with open(header_file, 'w') as file:
        file.write(content)

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
""".format(pkg_name)

    pkg_c_file = os.path.join(path_to_src, "%s.c" % pkg_name)
    with open(pkg_c_file, 'w') as file:
        file.write(content)

    # generate util.c -----------------------------------------------

    content = """/** util.c */

#include "fuse_version.h"   // make me first
#include <stdarg.h>
#include <sys/stat.h>
#include "{0:s}.h"          // this header file should be last

// Return -errno to caller, conditionally after logging -------------

int {0:s}Error(char *msg)
{{
    int errCode = -errno;
""".format(prefix)      # pkg_name, prefix, uc_name)

    if logging:
        content += """\
    {0:s}LogMsg("    ERROR %s: %s\\n", msg, strerror(errno));
""".format(prefix)          # pkg_name, prefix, uc_name)

    content += """\
    return errCode;
}}

// Given a path relative to the mount point, return an absolute -----
// path including the root directory
void {0:s}FullPath(char fpath[PATH_MAX], const char *path)
{{
    strcpy(fpath, {1:s}_DATA->rootdir);
    strncat(fpath, path, PATH_MAX);
""".format(prefix, uc_name)              # pkg_name, prefix, uc_name)

    if logging:
        content += """\
    {0:s}LogMsg("  FullPath:  rootdir = \\"%s\\", path = \\"%s\\",\\
        fpath = \\"%s\\"\\n",
           {1:s}_DATA->rootdir, path, fpath);
""".format(prefix, uc_name)              # pkg_name, prefix, uc_name)

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
  n = snprintf(p, bytesLeft, "  %-20s  = %d\\n", "  " #field "  ", \\
  (int) s->field); \\
  bytesLeft -= n;   \\
  p += n;

#define ADD_ULONG_FIELD(s, field) \\
  n = snprintf(p, bytesLeft, "  %-20s  = 0x%08lx\\n", "  " #field "  ", \\
  (uintptr_t) s->field); \\
  bytesLeft -= n;   \\
  p += n;

#define ADD_LL_FIELD(s, field) \\
  n = snprintf(p, bytesLeft, "  %-20s  = %lld\\n", "  " #field "  ", \\
  (long long) s->field); \\
  bytesLeft -= n;   \\
  p += n;

#define ADD_ULL_FIELD(s, field) \\
  n = snprintf(p, bytesLeft, "  %-20s  = 0x%016llx\\n", "  " #field "  ", \\
  (unsigned long long) s->field); \\
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
""".format(pkg_name, prefix, uc_name)
        content += content2

    content3 = ''
    if instrumenting:
        content3 = """\

// == INSTRUMENTATION ===============================================

// calloc BUCKET_COUNT of these
bucket_t *buckets;

opData_t *{0:s}ClockMeIn(struct timespec *tEntry, unsigned opcode)
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

""".format(prefix)      # pkg_name, prefix, uc_name)

        if logging:
            content3 += """\
    // DEBUG
    if (doubled) {{
        {0:s}LogMsg("slotsPerBucket doubled to %d\\n", slotsPerBucket);
        {0:s}FlushLog();
    }}
    // END
""".format(prefix)          # pkg_name, prefix, uc_name)

        content3 += """\
    assert(status == 0);
    opData_t *mySlot = &myBucket->ops[myCount];
    mySlot->opCode = opcode;
    return mySlot;
}}

void {0:s}ClockMeOut(struct timespec *tEntry, opData_t *mySlot, size_t count)
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

int {0:s}WriteBucket()
{{
    time_t now         = time(NULL);
    struct tm *when    = localtime(&now);
    char fullPath[PATH_MAX];
    strcpy(fullPath, {1:s}_DATA->cwd);
    strncat(fullPath, "/tmp/", PATH_MAX);
    char *p = fullPath + strlen(fullPath);
    snprintf(p, PATH_MAX, "/bucket-%04d%02d%02d-%02d%02d%02d",
        when->tm_year + 1900, when->tm_mon + 1, when->tm_mday,
        when->tm_hour, when->tm_min, when->tm_sec);

""".format(prefix, uc_name)          # pkg_name, prefix, uc_name)

        if logging:
            content3 += """\
    // DEBUG
    {0:s}LogMsg("data file is %s\\n", fullPath);
    // END

""".format(prefix)              # pkg_name, prefix, uc_name)

        content3 += """\
    // any 'b' has no effect in Linux
    FILE *f = fopen(fullPath, "w+");
    if (f != NULL) {{
        size_t written = fwrite(
                buckets[0].ops, sizeof(opData_t), buckets[0].count, f);
"""         # .format(pkg_name, prefix, uc_name)

        if logging:
            content3 += """\
        {0:s}LogMsg("wrote %lu bytes, %lu items, to %s\\n",
                written, buckets[0].count, fullPath);
""".format(prefix)  # pkg_name, prefix, uc_name)

        content3 += """\
        fflush(f);
        fclose(f);
    }} else {{
        int myErr = errno;
"""             # .format(pkg_name, prefix, uc_name)

        if logging:
            content3 += """\
        {0:s}LogMsg("errno %d (%s); failed to open %s\\n", " +\
myErr, strerror(myErr), p);
""".format(prefix)  # pkg_name, prefix, uc_name)

        content3 += """\
    }}
}}
"""             # .format(pkg_name, prefix, uc_name)
    content += content3

    util_c_file = os.path.join(path_to_src, "util.c")
    with open(util_c_file, 'w') as file:
        file.write(content)

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
    op_table_file = os.path.join(
        path_to_pkg, os.path.join(
            'src', 'optable.inc'))
    with open(op_table_file, 'w') as file:
        file.write(content)

    # generate op .inc files ------------------------------
    op_attrs = set_op_attrs()
    # mkSrcDir(args, opAttrs)

    src_dir = os.path.join(path_to_pkg, 'src')
    makedir_p(src_dir, 0o755)

    # XXX does not catch 'main'
    for name in OP_NAMES:
        attrs = op_attrs[name]
        if (attrs & DEPRECATED) or (attrs & NOT_IMPLEMENTED):
            continue
        if name not in func_map:   # names at end are not yet implemented
            # DEBUG
            print("%s is NOT IN funcMap" % name)
            # END
            break
        f_map = func_map[name]    # FuseFunc for this name
        op_code = "FG_%s" % name.upper()
        path_to_inc = os.path.join(src_dir, "%s.inc" % name)
        strings = []
        strings.append("/** %s.inc */\n" % (name))
        if attrs & CHK_DEF_XATTR:
            strings.append("#ifdef HAVE_SYS_XATTR_H")
        elif name == 'utimens':
            strings.append("#ifdef HAVE_UTIMENSAT")
        elif name == 'fallocate':
            strings.append("#ifdef HAVE_POSIX_FALLOCATE")

        # -- first line, LBRACE -----------------------
        strings.append("static %s\n{" % f_map.first_line())

        # -- instrumenation ---------------------------
        if instrumenting:
            content = """    struct timespec tEntry;
    opData_t *myData = {0:s}ClockMeIn(&tEntry, {1:s});
""".format(prefix, op_code)  # name, prefix, op_code)
            strings.append(content)
        # -- variable declarations --------------------
        if attrs & RETURNS_STATUS:
            strings.append('    int status = 0;')
        if (attrs & SYSCALL_RET_FD) or name == 'fallocate':
            strings.append('    int fd;')
        if attrs & (FULL_PATH | DOUBLE_FULL_PATH):
            strings.append('    char fpath[PATH_MAX];')
        if attrs & DOUBLE_FULL_PATH:
            strings.append('    char fnewpath[PATH_MAX];')
        if attrs & HAS_LINK_FILE:
            strings.append('    char flink[PATH_MAX];')

        if name in ['opendir', 'readdir']:
            strings.append('    DIR *dp;')
            if name == 'readdir':
                strings.append('    struct dirent *entry;')
        elif name == 'listxattr':
            strings.append('    char *ptr;')

        strings.append("")

        # -- log on entry -----------------------------
        if logging:
            if name == 'init':
                strings.append(
                    "    %sLogEntry(\"\\n%sinit()\\n\");" %
                    (prefix, prefix))
                strings.append('    %sLogConn(conn);' % prefix)
                strings.append(
                    '    %sLogContext(fuse_get_context());' %
                    prefix)
            else:
                if attrs & DOUBLE_FULL_PATH:
                    part0 = "\"\\n%s%s" % (prefix, name)
                    part1 = '(path=\\"%s\\", newpath=\\"%s\\")\\n",'
                    str_ = ("    %sLogEntry(" % prefix) + part0 + part1
                    strings.append(str_)
                    strings.append("            path, newpath);")
                else:
                    log_e = [
                        '    %sLogEntry(\"\\n%s%s(' %
                        (prefix, prefix, name)]
                    for ndx, param in enumerate(f_map.params):
                        if ndx > 0:
                            log_e.append(', ')
                        p_name = param[1]
                        if p_name == 'size':
                            if name in ['read', 'write', ]:
                                pat = '%lld'
                            else:
                                pat = '%d'
                        elif p_name == 'value':
                            if name in ['getxattr', ]:
                                pat = '0x%08x'
                            else:
                                pat = '\\"%s\\"'
                        elif p_name in LOG_ENTRY_PAT_MAP:
                            pat = LOG_ENTRY_PAT_MAP[p_name]
                        else:
                            pat = 'UNKNOWN PAT FOR \'%s\'' % p_name
                        log_e.append('%s=%s' % (p_name, pat))
                    log_e.append(")\\n\",")
                    strings.append(''.join(log_e))

                    # now add a parameter list on the next line
                    log_ep = ['             ']
                    for ndx, param in enumerate(f_map.params):
                        if ndx > 0:
                            log_ep.append(', ')
                        p_name = param[1]
                        log_ep.append(p_name)
                    log_ep.append(');')
                    strings.append(''.join(log_ep))

        if name == 'readdir':
            strings.append('    dp = (DIR *) (uintptr_t) fi->fh;')

        if logging and name != 'opendir' and name != 'readdir' and \
                attrs & LOGGING_FI and not attrs & SET_FH_FROM_FD:
            strings.append('    %sLogFI(fi);' % prefix)

        # -- set up absolute paths ------------------------
        if attrs & FULL_PATH:
            strings.append("    %sFullPath(fpath, path);" % prefix)
        if attrs & DOUBLE_FULL_PATH:
            strings.append("    %sFullPath(fnewpath, newpath);" % prefix)
        if attrs & HAS_LINK_FILE:
            strings.append("    %sFullPath(flink, link);" % prefix)
        strings.append("")

        # -- SYS CALL -------------------------------------

        sys_call = OP_CALL_MAP[name][0]
        if sys_call == '':
            if name != 'init':
                strings.append("    // CURRENTLY A NO-OP\n")
        else:
            if name == 'fallocate':
                strings.append("""
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
                strings.append('    status = flock(fi->fh, op);')
            elif name == 'fsync':
                strings.append(
                    """    // freebsd
#ifdef HAVE_FDATASYNC
    if (datasync)
        status = fdatasync(fi->fh);
    else
#endif
        status = fsync(fi->fh);""")

            elif name == 'lock':
                strings.append(
                    '    status = ulockmgr_op(fi->fh, cmd, lock, '
                    '&fi->lock_owner, sizeof(fi->lock_owner));')

            elif name == 'mknod':
                # in python format specs {} must be doubled :-(
                strings.append(

                    """    // ATTRIBUTION
    if (S_ISREG(mode)) {{
        status = open(fpath, O_CREAT | O_EXCL | O_WRONLY, mode);
        if (status < 0)
            status = {0:s}Error(\"{0:s}mknod open\");
        else {{
            status = close(status);
            if (status < 0)
                status = {0:s}Error(\"{0:s}mknod close\");
        }}
    }} else if (S_ISFIFO(mode)) {{
        status = mkfifo(fpath, mode);
        if (status < 0)
            status = {0:s}Error(\"{0:s}mknod mkfifo\");
    }} else {{
        status = mknod(fpath, mode, dev);
        if (status < 0)
            status = {0:s}Error(\"{0:s}mknod mknod\");
    }}""".format(prefix))  # name, prefix) )

            elif name == 'open':
                strings.append("    fd = %s(fpath, fi->flags);" % sys_call)
            elif name == 'readdir':
                content = """
    entry = readdir(dp);
    if (entry == 0) {{
        status = {0:s}Error("{0:s}readdir readdir");
        return status;
    }}
    do {{
""".format(prefix)  # name, prefix)                     # BLIP
                if logging:
                    content += """\
        {0:s}LogMsg("calling filler(%s)\\n", entry->d_name);
""".format(prefix)          # name, prefix)                         # BLIP

                content += """\
        if (filler(buf, entry->d_name, NULL, 0) != 0) {{
"""                         # .format(name, prefix)                     # BLIP
                if logging:
                    content += """\
            {0:s}LogMsg("    ERROR {0:s}readdir filler:  buffer full");
""".format(prefix)              # name, prefix)

                content += """\
            return -ENOMEM;
        }
    } while ((entry = readdir(dp)) != NULL);
"""
                strings.append(content)

            elif name == 'readlink':
                strings.append("    status=readlink(fpath, link, size - 1);")
            elif name == 'releasedir':
                strings.append(
                    "    status = closedir((DIR *) (uintptr_t) fi->fh);")
            elif name == 'utimens':
                strings.append(
                    "    status=utimensat(0, fpath, tv, AT_SYMLINK_NOFOLLOW);")
            elif attrs & HAS_LINK_FILE:
                strings.append("    status = %s(path, flink);" % sys_call)
            elif attrs & DOUBLE_FULL_PATH:
                strings.append("    status = %s(fpath, fnewpath);" % sys_call)
            elif attrs & (FULL_PATH | LOGGING_FI):
                if attrs & SYSCALL_RET_FD:
                    strings.append("    fd = %s(fpath%s);" % (
                        sys_call, f_map.other_args()))
                else:
                    if attrs & SYSCALL_FI_PARAM1:
                        if name == 'fgetattr':
                            strings.append(
                                '    // FreeBSD special case; ATTRIBUTION')
                            strings.append('    if (!strcmp(path, "/")) {')
                            strings.append('        char fpath[PATH_MAX];')
                            strings.append("        " +
                                           " %sFullPath(fpath, path);" %
                                           prefix)
                            strings.append("        status=lstat(fpath%s);" % (
                                f_map.other_args()))
                            strings.append('        if (status < 0)')
                            strings.append(
                                "            status" +
                                " = %sError(\"%sfgetattr lstat\");" % (
                                    prefix, prefix))
                            strings.append('    } else {')
                            strings.append("        status = %s(fi->fh%s);" % (
                                sys_call, f_map.other_args()))
                            strings.append('        if (status < 0)')
                            strings.append(
                                "            status = " +
                                " %sError(\"%sfgetattr fstat\");" %
                                (prefix, prefix))
                            strings.append('    }')
                        elif name == 'opendir':
                            strings.append('    dp = opendir(fpath);')
                        else:
                            strings.append("    status = %s(fi->fh%s);" % (
                                sys_call, f_map.other_args()))
                    else:
                        strings.append("    status = %s(fpath%s);" % (
                            (sys_call, f_map.other_args())))

        # -- check for error status -----------------------
        if name == 'opendir':
            strings.append('    if (dp == NULL)')
            strings.append("        status = %sError(\"%s%s %s\");" % (
                prefix, prefix, name, sys_call))
        elif name != 'fgetattr' and attrs & CHECK_ERR_AND_FLIP:
            if attrs & SYSCALL_RET_FD:
                strings.append("    if (fd < 0)")
            else:
                strings.append("    if (status < 0)")
            strings.append("        status = %sError(\"%s %s\");\n" % (
                prefix, prefix + name, sys_call))
            if name == 'readlink':
                strings.append('    else {')
                strings.append('        link[status] = \'\\0\';')
                strings.append('        status = 0;')
                strings.append('    }')
        if logging and name in ['getxattr', ]:
            strings.append('    else')
            start = '        %sLogMsg(' % prefix
            strings.append(start + '"    value=\\"%s\\"\\n", value);')

        if logging and name == 'listxattr':
            start = '    %sLogMsg("    ' % prefix
            strings.append(
                start + 'returned attributes (length %d):\\n", status);')
            strings.append(
                '    for (ptr=list; ptr<list + status; ptr += strlen(ptr)+1)')
            start = '        %sLogMsg' % prefix
            strings.append(start + '("    \\"%s\\"\\n", ptr);')

        # -- logging stat -----------------------------
        if logging:
            if (attrs & LOGGING_STAT):
                strings.append(
                    "    %sLogStat(%s);\n" %
                    (prefix, f_map.params[1][1]))
            elif attrs & LOGGING_STATVFS:
                strings.append(
                    "    %sLogStatVFS(%s);\n" %
                    (prefix, f_map.params[1][1]))

        if attrs & SET_FH_FROM_FD:
            strings.append('    fi->fh = fd;')
            if logging:
                strings.append('    %sLogFI(fi);' % prefix)
        elif name == 'opendir':
            strings.append('    fi->fh = (intptr_t) dp;')
            if logging:
                strings.append('    %sLogFI(fi);' % prefix)
        elif logging and name == 'readdir':
            strings.append('    %sLogFI(fi);' % prefix)

        # -- instrumentation at exit ------------------
        if instrumenting:
            if name in ['readlink', 'read', 'write',
                        'setxattr', 'getxattr', 'listxattr', ]:
                strings.append(
                    '    %sClockMeOut(&tEntry, myData, size);' %
                    prefix)
            else:
                strings.append(
                    '    %sClockMeOut(&tEntry, myData, %s);' %
                    (prefix, 0))
            if name == 'destroy':
                strings.append('\n    %sWriteBucket();' % prefix)

        # -- return -----------------------------------
        if attrs & RETURNS_STATUS:
            strings.append("    return status;")
        elif name == 'init':
            strings.append("    return %s_DATA;" % uc_name)
        strings.append("}")
        if (attrs & CHK_DEF_XATTR) or (
                name == 'fallocate') or (name == 'utimens'):
            strings.append("#endif")

        out = "\n".join(strings) + "\n"
        with open(path_to_inc, 'w') as file:
            file.write(out)
