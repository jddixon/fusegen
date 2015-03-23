#!/usr/bin/python3

# fusegen/testFuseGeneration.py

import base64, hashlib, os, time, unittest
from argparse import Namespace
from rnglib         import SimpleRNG
from fusegen        import invokeShell, makeFusePkg, SH

class TestPKCS7Padding (unittest.TestCase):
    def setUp(self):
        self.rng = SimpleRNG( time.time() )
    def tearDown(self):
        pass

    def fiddleWithFiles(self, pkgName, pathToPkg):
        workDir     = os.path.join(pathToPkg, 'workdir')
        mountPoint  = os.path.join(workDir,     'mountPoint')
        rootDir     = os.path.join(workDir,     'rootDir')
       
        # Devise a directory structure, say M files wide, N directories deep.
        # The files are of random-ish length, populated with random-ish data.
        # XXX STUB XXX

        # Run the file system executable, which mounts the file system.
        # XXX STUB XXX

        # If this succeeds, write the directory structure on the 
        # mount point, reporting any non-fatal problems.
        # XXX STUB XXX

        # Unmount the file system
        # XXX STUB XXX

        # Verify that the expected directory structure appears below
        # the root directory.
        # XXX STUB XXX

    def exerciseFileSystem(self, pkgName, pathToPkg):
        dirNow  = os.getcwd()
        os.chdir(pathToPkg)
        cmd     = [SH, os.path.join(pathToPkg, 'build'),]
        chatter = ''
        try:
            self.fiddleWithfiles(pkgName, pathToPkg)
        except Exception as e:
            print(e)
        if chatter and chatter != '':
            print(chatter)
        os.chdir(dirNow)

        # DEBUG
        print("after fiddling with files we are back in %s" % dirNow)
        # END


    def doBaseTest(self, logging=False, instrumenting=False):
        """
        Build the selected type of file system under devDir and
        then run exerciseFileSystem() on it.
        """
        devDir      = '/home/jdd/dev/c'
        pkgName     = 'xxxfs'
        if instrumenting:   pkgName += 'I'
        if logging:         pkgName += 'L'
        pathToPkg   = os.path.join(devDir, pkgName)
        
        ns = Namespace()
        setattr(ns,'acPrereq',      '2.6.9')
        setattr(ns,'devDir',        devDir)
        setattr(ns, 'emailAddr',    'jddixon at gmail dot com')
        setattr(ns,'force',         True)
        setattr(ns,'instrumenting', instrumenting)
        setattr(ns,'logging',       logging)
        setattr(ns,'myDate',        "%04d-%02d-%02d" % time.gmtime()[:3])
        setattr(ns,'myVersion',    '1.2.3')
        setattr(ns,'pathToPkg',     pathToPkg)
        setattr(ns,'pkgName',       pkgName)
        setattr(ns,'lcName',        pkgName.lower())
        setattr(ns,'ucName',        pkgName.upper())
        setattr(ns,'testing',       False)
        setattr(ns,'verbose',       False)

        # DEBUG
        print(ns);
        # END

        # create the target file system
        makeFusePkg(ns)

        # invoke the build command
        dirNow  = os.getcwd()
        os.chdir(pathToPkg)
        cmd     = [SH, os.path.join(pathToPkg, 'build'),]
        chatter = ''
        try:
            chatter = invokeShell(cmd)
        except Exception as e:
            print(e)
        if chatter and chatter != '':
            print(chatter)
        os.chdir(dirNow)

        # DEBUG
        print("we are back in %s" % dirNow)
        # END
        
        # run test verifying that the file system works as expected
        # XXX STUB XXX

    def doInstrumentedTest(self):
        self.doBaseTest(instrumenting=True)

    def doLoggingTest(self):
        self.doBaseTest(logging=True)

    def doTestLoggingAndInstrumented(self):
        self.doBaseTest(logging=True, instrumenting=True)

    def testPadding (self):
        self.doBaseTest()
        #self.doInstrumentedTest()
        #self.doLoggingTest()
        #self.doTestLoggingAndInstrumented()

if __name__ == '__main__':
    unittest.main()
