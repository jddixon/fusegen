#!/usr/bin/env python3

# testFuseFunc.py

""" Test various fuse-related functions. """

import unittest

# from rnglib        import SimpleRNG
from fusegen import FuseFunc


class TestFuseFunc(unittest.TestCase):
    """ Test various fuse-related functions. """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    # utility functions #############################################

    # actual unit tests #############################################

    def test_name_to_func_map(self):
        """ Verify map from function names to opcodes is correct. """

        match_, o_map = FuseFunc.get_func_map('xxx_')   # funcMap, opCodeMap
        _ = o_map               # suppress warning
        # for testing, build a new p2tMap from the data in funcMap
        for name in match_:
            func = match_[name]
            params = func.params        # a list of 2-tuples
            my_p2t = {}    # maps parameter names to type as a string
            p2t_map = func.p2t_map
            for param_ in params:
                p_type = param_[0]
                p_name = param_[1]
                my_p2t[p_name] = p_type

            # now check the maps for equality
            self.assertEqual(len(my_p2t), len(p2t_map))
            for param_ in p2t_map:
                p_type_name = p2t_map[param_]   # param type from param name
                p_type = my_p2t[param_]
                self.assertEqual(p_type_name, p_type)

    def test_first_line(self):
        """ UNFINISHED: test handling of first line. """

        match_, o_map = FuseFunc.get_func_map('xxx_')  # funcMap, opCodeMap
        _ = o_map               # suppress warning
        _ = self                # suppress warning
        for name in match_:
            func = match_[name]
            line = func.first_line()
            # DEBUG
            print(line)
            # END

            # TODO: compare generated line with corresponding line
            # in the file PATH_TO_FIRST_LINES


if __name__ == '__main__':
    unittest.main()
