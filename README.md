# fusegen

Tools for generating and monitoring a skeletal Linux FUSE user-space file system.

## fuseGen

### FuseGen Command Line

	usage: fuseGen [-h] [-A ACPREREQ] [-D MYDATE] [-E EMAILADDR] [-I] [-f] [-j]
	               [-P PKGNAME] [-T] [-v] [-V MYVERSION]
	
	generate a minimal FUSE (file system in user space) package
	
	optional arguments:
	  -h, --help            show this help message and exit
	  -A ACPREREQ, --acPrereq ACPREREQ
	                        prerequisite autoconfig version number
	  -D MYDATE, --myDate MYDATE
	                        date in YYYY-MM-DD format
	  -E EMAILADDR, --emailAddr EMAILADDR
	                        contact email address
	  -I, --instrumenting   generate instrumentation code
	  -f, --force           if utility already exists, overwrite it
	  -j, --justShow        show options and exit
	  -P PKGNAME, --pkgName PKGNAME
	                        utility package name
	  -T, --testing         this is a test run
	  -v, --verbose         be chatty
	  -V MYVERSION, --myVersion MYVERSION
	                        version in X.Y.Z format

### Typical FuseGen Command Line: genEm


	cd ~/dev/py/fusegen
	./fuseGen -fIvP xxxfs

### File System Created

	/home/jdd/dev/c/xxxfs
	├── aclocal.m4
	├── AUTHORS
	├── autogen.sh
	├── autom4te.cache
	├── bin
	│   ├── blk-31-4k
	│   ├── mountXXXFS
	│   └── umountXXXFS
	├── build
	├── ChangeLog
	├── CHANGES
	├── config
	├── config.guess
	├── config.log
	├── config.status
	├── config.sub
	├── configure
	├── configure.ac
	├── COPYING
	├── COPYING.AUTOCONF.EXCEPTION
	├── COPYING.GNUBL
	├── COPYING.LIB
	├── doc
	├── examples
	├── INSTALL
	├── libtool
	├── m4
	├── Makefile
	├── Makefile.am
	├── Makefile.in
	├── man
	├── NEWS
	├── README
	├── README.licenses
	├── scripts
	├── src
	│   ├── access.inc
	│   ├── bmap.inc
	│   ├── chmod.inc
	│   ├── chown.inc
	│   ├── config.h
	│   ├── config.h.in
	│   ├── create.inc
	│   ├── destroy.inc
	│   ├── fallocate.inc
	│   ├── fgetattr.inc
	│   ├── flock.inc
	│   ├── flush.inc
	│   ├── fsyncdir.inc
	│   ├── fsync.inc
	│   ├── ftruncate.inc
	│   ├── fuse_common.h
	│   ├── fuse.h
	│   ├── fuse_opt.h
	│   ├── fuse_version.h
	│   ├── getattr.inc
	│   ├── getxattr.inc
	│   ├── init.inc
	│   ├── link.inc
	│   ├── listxattr.inc
	│   ├── lock.inc
	│   ├── main.inc
	│   ├── Makefile
	│   ├── Makefile.am
	│   ├── Makefile.in
	│   ├── mkdir.inc
	│   ├── mknod.inc
	│   ├── opcodes.h
	│   ├── opendir.inc
	│   ├── open.inc
	│   ├── optable.inc
	│   ├── readdir.inc
	│   ├── read.inc
	│   ├── readlink.inc
	│   ├── releasedir.inc
	│   ├── release.inc
	│   ├── removexattr.inc
	│   ├── rename.inc
	│   ├── rmdir.inc
	│   ├── setxattr.inc
	│   ├── stamp-h1
	│   ├── statfs.inc
	│   ├── symlink.inc
	│   ├── truncate.inc
	│   ├── unlink.inc
	│   ├── util.c
	│   ├── utimens.inc
	│   ├── write.inc
	│   ├── xxxfs
	│   ├── xxxfs.c
	│   ├── xxxfs.h
	├── tmp
	│   └── bucket-20150316-150838
	├── workdir
	│   ├── mountPoint
	│   └── rootdir
	│       ├── foo
	│       ├── job1.1.0
	│       ├── job2.2.0
	│       ├── job3.3.0
	│       └── job4.4.0
	└── xxxfs.log

### The build Command

	./autogen.sh
	./configure
	make

### bin/ Commands

## FuseDecode

### FuseDecode Command Line

	usage: fuseDecode [-h] [-D PATHTODATA] [-j] [-n HOWMANY] [-v]
	
	parse a fuseGenned data file
	
	optional arguments:
	  -h, --help            show this help message and exit
	  -D PATHTODATA, --pathToData PATHTODATA
	                        path to data file
	  -j, --justShow        show options and exit
	  -n HOWMANY, --howMany HOWMANY
	                        how many data points to decode
	  -v, --verbose         be chatty

### Typical FuseDecode Output

	==== op time === == latency == = byte = == opcode ==     = flags =
	  sec   nanosec  sec  nanosec   count   op   name
	369886 170431079  0     74955       0   29 init             
	369886 170592946  0     91116       0    0 getattr          
	369886 170601627  0     58834       0   25 opendir          P
	369886 170728424  0     68768       0   26 readdir          
	369886 170849263  0     60370       0    0 getattr          
	369886 170851394  0     80361       0    0 getattr          P
	369886 170937891  0     22188       0   31 access           
	369886 170972000  0     52993       0    0 getattr          
	369886 171057175  0     28741       0    0 getattr          
	369886 171112174  0     21897       0    0 getattr          
	369886 171181270  0     26367       0    0 getattr          
	369886 171243684  0     22415       0    0 getattr          
	369886 171301507  0     41395       0    0 getattr          
	369886 171378102  0     24336       0    0 getattr          
	369886 171483916  0     21530       0   27 releasedir       
	369886 171505940  0     30953       0   25 opendir          
	369886 171587944  0     47520       0   26 readdir          
	369886 171748142  0     16430       0   27 releasedir       
	369886 171768149  0     25347       0   25 opendir          
	369886 171832503  0     46673       0   26 readdir          
	369886 171986430  0     70618       0   27 releasedir       
	369886 172007454  0     53362       0   25 opendir          P
	369886 172099167  0     49953       0   26 readdir          
