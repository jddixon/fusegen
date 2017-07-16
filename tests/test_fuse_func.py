#!/usr/bin/env python3

# testFuseFunc.py

import os
import sys
import unittest

#from rnglib        import SimpleRNG
from fusegen import FuseFunc, OP_NAMES, PATH_TO_FIRST_LINES


class TestFuseFunc (unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    # utility functions #############################################

    # actual unit tests #############################################

    def test_name_to_func_map(self):
        match_, o_map = FuseFunc.get_func_map('xxx_')   # funcMap, opCodeMap
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
        match_, o_map = FuseFunc.get_func_map('xxx_')  # funcMap, opCodeMap
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
