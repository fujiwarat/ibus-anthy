#!/usr/bin/python3
# -*- coding: utf-8 -*-

from __future__ import print_function

from gi import require_version as gi_require_version
gi_require_version('Gdk', '3.0')
from gi.repository import Gdk

import unittest

# Need to flush the output against Gtk.main()
def printflush(sentence):
    try:
        print(sentence, flush=True)
    except IOError:
        pass

def printerr(sentence):
    try:
        print(sentence, flush=True, file=sys.stderr)
    except IOError:
        pass

try:
    from tap import TAPTestRunner
    printflush('## Load tappy')
except ModuleNotFoundError:
    try:
        from pycotap import TAPTestRunner
        from pycotap import LogMode
        printflush('## Load pycotap')
    except ModuleNotFoundError as err:
        printflush('## Ignore tap module: %s' % str(err))

@unittest.skipIf(Gdk.Display.open('') == None, 'Display cannot be open.')
class foo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        pass

    def test_typing(self):
        print('Done')

def main():
    unittest.main()

if __name__ == '__main__':
    main()
