# fusegen

Tools for generating and monitoring a Linux FUSE user-space file system.

## fuseGen

FuseGen is a Python 3 script which generates a FUSE file system.  These
are a mix of Autotools configuration files and ANSI C source code.  The
C files constitute a pass-through FUSE file system.  This means that FUSE
operations are logged and statistics gathered, and then the commands are
passed through to the local file system for execution.  

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

This is the command line at the time of writing; when you unpack 
fusegen you should type `fuseGen -h` to see the current set of 
supported arguments.

### Typical FuseGen Command Line: genEm

When fusegen is unpacked, the distribution directory contains a file
`genEm`.  As it stands this creates the `xxxfs` file system.  That is,
it writes a number of files to a subdirectory of your development 
directory.  

	cd ~/dev/py/fusegen
	./fuseGen -fIvP xxxfs

In this case, the package name is **xxxfs** (because the follows the **-P**), 
and that will be the name
of the development directory.  If the directory already exists, it is
overwritten (**-f**).  Instrumentation code will be generated (**-I**)

### File System Created

`genEm` creates a number of files and directories.   What you see below
is a snapshot taken shortly after initialization (in fact, after running
the **build** command but without the object files and executables
generated my `make`).

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

For easy customization there is a `.inc` file for each FUSE command.

### The build Command

The `build` command completes the creation of the file system.  It runs
`autogen.sh`, which installs many of the standard Autotools files, and 
then creates the `configure` script from the instructions in `configure.ac`.
Finaly it runs make, which compiles the object files and then links the 
file system, the `xxxfs` executable.
 
	./autogen.sh
	./configure
	make

It may be desirable to change the generated system to some degree.  
Usually limited changes are accomplished by editing `configure.ac`
and/or `Makefile.ac` and then rerunning build.  This will have no 
effect on `src/*.inc` and in that sense is safe.

### bin/ Commands

The `bin/` subdirectory contains scripts for

* mounting the file system (`mountXXXFS` in this case)
* running a simple FIO benchmark (`blk-31-4k`)
* and dismounting the file system (`umountXXXFS`)

## Putting It All Together: Running an Application

The script `blk-31-4k`, found in the default `bin/` directory, is used
to collect statistics on a short **fio** run.  FIO is an open source tool
for measuring the performance of a file system.  

	echo "blk-31-4k: test size is being set to $1 MB"
	#
	cd ~/dev/c/xxxfs
	bin/mountXXXFS
	cd workdir/mountPoint
	fio --name=global --bs=4k --size=$1m 	--rw=randrw --rwmixread=75 	--name=job1 --name=job2 --name=job3 --name=job4
	cd ../..
	bin/umountXXXFS

This particular script runs four jobs simultaneously.  Each job reads 
and/or writes the same amount of data to the disk.  On the command line
the script has a single argument, the number of megabytes to be read from
and/or written to the disk.  For this test the mount point and the root
directory are both subdirecties of `workdir`.  The script changes to the
directory above that, then mounts the FUSE file system (`bin/mountXXXFS`).
It then runs the FIO jobs in the `mountPoint` subdirectory.  When the FIO
jobs terminate, the script changes back to the distribution directory and
unmounts the file system.

Running this script has two major effects:

* it writes its log to the file `xxxfs.log`
* it writes run statistics to a file under `tmp/`

If full logging is turned on, the log file can be very large.

## FuseGen Statistics File

The statistics file has a name like `bucket-20150316-150838`.  The first
set of numbers in the file name represents the date in `CCYYMMDD` format; the 
second set is the start time of the run, local time, as `HHMMSS`.  We use
a 24-hour clock, so in this case the run started at 15:08:38, just 
after 3 pm local time.

	typedef struct o_ {
	    uint32_t    opSec;
	    uint32_t    opNsec;             // may not exceed BILLION
	    uint32_t    lateNsec;           // ns of latency; may not exceed BILLION
	    unsigned    lateSec     :  7;   // sec of latency
	    unsigned    count       : 17;   // bytes read or written; 128K max
	    unsigned    opCode      :  8;
	} __attribute__((aligned(16), packed)) opData_t;

Each call on the FUSE file system is recorded to the statistics file as
a 16-byte object laid out as specified above.  

The time of the call is recorded as a 128-bit pair, `opSec` and 
`opNsec`.  This is a Linux CLOCK_MONOTONIC time representing an absolute
elapsed time; it is generally **not** the same as the system's (guess at)
the local time.

When the system call is complete, the latency is calculated.  This has the
same 32-bit nanosecond part, but only 7 bits are reserved for the seconds
of latency.  That is, latencies greater than 128 seconds will not be recorded
correctly.

Finally 8 bits are reserved for the FUSE opcode.  There are currently 
fewer than four dozen opcodes so this number of bits is likely to be 
sufficient for some time.

## FuseDecode

FuseDecode is a utility for converting FuseGen statistics files to a 
human-readable format.

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
