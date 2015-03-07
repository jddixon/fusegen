#!/usr/bin/python3

# testFuseFunc.py

import os, sys, unittest

#from rnglib        import SimpleRNG
from fusegen        import FuseFunc, OP_NAMES, PATH_TO_FIRST_LINES

class TestFuseFunc (unittest.TestCase):

    def setUp(self):
        pass
    def tearDown(self):
        pass

    # utility functions #############################################
    
    # actual unit tests #############################################
   
    def testNameToFuncMap(self):
        m,o = FuseFunc.getFuncMap('xxx_')   # funcMap, opCodeMap
        # for testing, build a new p2tMap from the data in funcMap
        for name in m:
            func   = m[name]
            params = func.params        # a list of 2-tuples
            myP2T  = {}    # maps parameter names to type as a string
            p2tMap = func.p2tMap
            for p in params:
                pType = p[0]
                pName = p[1]
                myP2T[pName] = pType

            # now check the maps for equality
            self.assertEqual(len(myP2T), len(p2tMap))
            for p in p2tMap:
                t = p2tMap[p]   # param type from param name
                T = myP2T[p]
                self.assertEqual(t, T)

    def testFirstLine(self):
        m, o = FuseFunc.getFuncMap('xxx_')  # funcMap, opCodeMap
        for name in m:
            func = m[name]
            line = func.firstLine()
            # DEBUG
            print(line)
            # END

            # TODO: compare generated line with corresponding line
            # in the file PATH_TO_FIRST_LINES

if __name__ == '__main__':
    unittest.main()



