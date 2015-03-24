#!/usr/bin/python3

# fusegen/testFuseGeneration.py

import base64, hashlib, os, time, unittest
from argparse import Namespace
from rnglib         import SimpleRNG
from fusegen        import invokeShell, makeFusePkg, SH
from merkletree     import *

class TestFuseGeneration (unittest.TestCase):
    def setUp(self):
        self.rng = SimpleRNG( time.time() )
    def tearDown(self):
        pass

    # FUNCTIONS TO MODIFY IN-MEMORY DATA STRUCTURE AND DISK IMAGE
    # XXX STUB XXX

    # FUNCTIONS TO DETERMINE EQUALITY OF IN-MEMORY DATA STRUCTURE 
    # AND DISK IMAGE (either under mountPoint or rootDir)
    # XXX STUB XXX
    
    def fiddleWithFiles(self, pkgName, pathToPkg, umountCmd):
        """ Enter with the file system mounted """
        workDir     = os.path.join(pathToPkg, 'workdir')
        mountPoint  = os.path.join(workDir,     'mountPoint')
        rootDir     = os.path.join(workDir,     'rootDir')
      
        # Devise a directory structure, say M files wide, N directories deep.
        # The files are of random-ish length, populated with random-ish data.
        sampleName      = self.rng.nextFileName(16)
        pathToSample    = os.path.join(mountPoint, sampleName)
        # builds a directory tree with a depth of 4, 5 files (including
        # directories) at each level, and 16 <= file length <= 128
        self.rng.nextDataDir(pathToDir=pathToSample,
                depth=4, width=5,maxLen=128,minLen=16)
        tree1 = MerkleTree.createFromSerialization(pathToSample)

        # If this succeeds, we have written the directory structure on the 
        # mount point.

        # Delete some files, modifying in-memory data structure accordingly
        # Shorten some files, modifying in-memory data structure accordingly
        # Lengthen some files, modifying in-memory data structure accordingly
        
        # Unmount the file system
        chatter = invokeSHell(SH, umountCmd)

        # Verify that the expected directory structure appears below
        # the root directory.
        pathViaRoot = os.path.join(rootDir, sampleName) 
        tree2 = MerkleTree.createFromSerialization(pathViaRoot)
        self.assertEqual(tree1.equal(tree2), True)

    def exerciseFileSystem(self, pkgName, pathToPkg):
        dirNow  = os.getcwd()
        os.chdir(pathToPkg)
        pathToBin = os.path.join(pathToPkg, 'bin')

        mountCmd  = [SH, os.path.join(pathToBin, 'mount%s' % pkgName.upper()),]
        umountCmd = [SH, os.path.join(pathToBin, 'umount%s' % pkgName.upper()),]
        
        chatter = ''
        try:
            chatter = invokeShell(mountCmd)
            chatter += self.fiddleWithFiles(pkgName, pathToPkg, umountCmd)
        except Exception as e:
            print(e)

        try:
            invokeShell(umountCmd)
        except:
            pass

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
        
        cmds = Namespace()
        setattr(cmds,'acPrereq',      '2.6.9')
        setattr(cmds,'devDir',        devDir)
        setattr(cmds, 'emailAddr',    'jddixon at gmail dot com')
        setattr(cmds,'force',         True)
        setattr(cmds,'instrumenting', instrumenting)
        setattr(cmds,'logging',       logging)
        setattr(cmds,'myDate',        "%04d-%02d-%02d" % time.gmtime()[:3])
        setattr(cmds,'myVersion',    '1.2.3')
        setattr(cmds,'pathToPkg',     pathToPkg)
        setattr(cmds,'pkgName',       pkgName)
        setattr(cmds,'lcName',        pkgName.lower())
        setattr(cmds,'ucName',        pkgName.upper())
        setattr(cmds,'testing',       False)
        setattr(cmds,'verbose',       False)

        # DEBUG
        print(cmds);
        # END

        # create the target file system
        makeFusePkg(cmds)

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
        self.exerciseFileSystem(pkgName, pathToPkg)

    def doInstrumentedTest(self):
        self.doBaseTest(instrumenting=True)

    def doLoggingTest(self):
        self.doBaseTest(logging=True)

    def doTestLoggingAndInstrumented(self):
        self.doBaseTest(logging=True, instrumenting=True)

    def testFuseGeneration (self):
        self.doBaseTest()
        #self.doInstrumentedTest()
        #self.doLoggingTest()
        #self.doTestLoggingAndInstrumented()

if __name__ == '__main__':
    unittest.main()
