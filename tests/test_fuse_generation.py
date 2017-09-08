#!/usr/bin/env python3

# fusegen/testFuseGeneration.py

import os
import sys
import time
import unittest
from argparse import Namespace
from rnglib import SimpleRNG
from fusegen import invoke_shell, make_fuse_pkg, SH
from merkletree import MerkleTree


class TestFuseGeneration(unittest.TestCase):

    def setUp(self):
        self.rng = SimpleRNG(time.time())

    def tearDown(self):
        pass

    # FUNCTIONS TO MODIFY IN-MEMORY DATA STRUCTURE AND DISK IMAGE
    # XXX STUB XXX

    # FUNCTIONS TO DETERMINE EQUALITY OF IN-MEMORY DATA STRUCTURE
    # AND DISK IMAGE (either under mountPoint or rootDir)
    # XXX STUB XXX

    def fiddle_with_files(self, pkg_name, path_to_pkg, umount_cmd):
        """ Enter with the file system mounted """
        work_dir = os.path.join(path_to_pkg, 'workdir')
        mount_point = os.path.join(work_dir, 'mount_point')
        root_dir = os.path.join(work_dir, 'rootdir')

        # Devise a directory structure, say M files wide, N directories deep.
        # The files are of random-ish length, populated with random-ish data.
        sample_name = self.rng.next_file_name(16)
        path_to_sample = os.path.join(mount_point, sample_name)
        # builds a directory tree with a depth of 4, 5 files (including
        # directories) at each level, and 16 <= file length <= 128
        self.rng.next_data_dir(path_to_dir=path_to_sample,
                               depth=4, width=5, max_len=128, min_len=16)
        # DEBUG
        print("creating tree1")
        sys.stdout.flush()
        # END
        tree1 = MerkleTree.create_from_file_system(path_to_sample)
        self.assertTrue(tree1 is not None)

        # If this succeeds, we have written the directory structure on the
        # mount point.

        # Delete some files, modifying in-memory data structure accordingly
        # Shorten some files, modifying in-memory data structure accordingly
        # Lengthen some files, modifying in-memory data structure accordingly

        # Unmount the file system
        chatter = invoke_shell(umount_cmd)

        # Verify that the expected directory structure appears below
        # the root directory.
        path_via_root = os.path.join(root_dir, sample_name)
        # DEBUG
        print("creating tree2")
        sys.stdout.flush()
        # END
        tree2 = MerkleTree.create_from_file_system(path_via_root)
        self.assertTrue(tree2 is not None)
        self.assertEqual(tree1.equal(tree2), True)
        # DEBUG
        print("directory trees are equal")
        sys.stdout.flush()
        # END
        return chatter

    def exercise_file_system(self, pkg_name, path_to_pkg):
        dir_now = os.getcwd()
        os.chdir(path_to_pkg)
        path_to_bin = os.path.join(path_to_pkg, 'bin')

        mount_cmd = [
            SH,
            os.path.join(
                path_to_bin,
                'mount%s' %
                pkg_name.upper()),
        ]
        umount_cmd = [
            SH,
            os.path.join(
                path_to_bin,
                'umount%s' %
                pkg_name.upper()),
        ]

        chatter = ''
        try:
            chatter = invoke_shell(mount_cmd)
            chatter += self.fiddle_with_files(pkg_name,
                                              path_to_pkg, umount_cmd)
        except Exception as exc:
            print(exc)

        else:
            # XXX STUB XXX
            pass

        finally:
            """ unmount the file system, ignoring any exceptions """
            # DEBUG
            print("enter finally block")
            sys.stdout.flush()
            # END
            try:
                invoke_shell(umount_cmd)
            except BaseException:
                pass

            if chatter and chatter != '':
                print(chatter)
            os.chdir(dir_now)

            # DEBUG
            print("after fiddling with files we are back in %s" % dir_now)
            sys.stdout.flush()
            # END

    def do_bae_test(self, logging=False, instrumenting=False):
        """
        Build the selected type of file system under devDir and
        then run exerciseFileSystem() on it.
        """
        dev_dir = '/home/jdd/dev/c'
        pkg_name = 'xxxfs'
        if instrumenting:
            pkg_name += 'I'
        if logging:
            pkg_name += 'L'
        path_to_pkg = os.path.join(dev_dir, pkg_name)

        cmds = Namespace()
        setattr(cmds, 'ac_prereq', '2.6.9')
        setattr(cmds, 'dev_dir', dev_dir)
        setattr(cmds, 'email_addr', 'jddixon at gmail dot com')
        setattr(cmds, 'force', True)
        setattr(cmds, 'instrumenting', instrumenting)
        setattr(cmds, 'logging', logging)
        setattr(cmds, 'my_date', "%04d-%02d-%02d" % time.gmtime()[:3])
        setattr(cmds, 'my_version', '1.2.3')
        setattr(cmds, 'path_to_pkg', path_to_pkg)
        setattr(cmds, 'pkg_name', pkg_name)
        setattr(cmds, 'lc_name', pkg_name.lower())
        setattr(cmds, 'uc_name', pkg_name.upper())
        setattr(cmds, 'testing', False)
        setattr(cmds, 'verbose', False)

        # DEBUG
        print(cmds)
        # END

        # create the target file system
        make_fuse_pkg(cmds)

        # invoke the build command
        dir_now = os.getcwd()
        os.chdir(path_to_pkg)
        cmd = [SH, os.path.join(path_to_pkg, 'build'), ]
        chatter = ''
        try:
            chatter = invoke_shell(cmd)
        except Exception as exc:
            print(exc)
        if chatter and chatter != '':
            print(chatter)
        os.chdir(dir_now)

        # DEBUG
        print("we are back in %s" % dir_now)
        # END

        # run test verifying that the file system works as expected
        self.exercise_file_system(pkg_name, path_to_pkg)

    def do_instruments_test(self):
        self.do_bae_test(instrumenting=True)

    def do_logging_test(self):
        self.do_bae_test(logging=True)

    def do_test_logging_and_instrumented(self):
        self.do_bae_test(logging=True, instrumenting=True)

    def test_fuse_generation(self):
        self.do_bae_test()
        self.do_instruments_test()
        self.do_logging_test()
        self.do_test_logging_and_instrumented()


if __name__ == '__main__':
    unittest.main()
