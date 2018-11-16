# -*- coding: utf-8 -*-

import time
import logging
import unittest

from lantz.core import Driver, Feat, Q_, ureg, DimensionalityWarning, MessageBasedDriver
from lantz.core.log import get_logger
from lantz.core.helpers import UNSET, MISSING
from lantz.core.testsuite import must_warn, MemHandler
from lantz.core import mfeats


class FakeMBDriver(Driver):

    def __init__(self):
        super().__init__()
        self.internal = dict(eggs=0)

    def query(self, msg):
        if msg == 'eggs?':
            return self.internal['eggs']
        elif msg == 'eggs 0':
            self.internal['eggs'] = 0
        elif msg == 'eggs 1':
            self.internal['eggs'] = 1
        else:
            raise ValueError

    get_query = query
    set_query = query


class FeatTest(unittest.TestCase):

    # Modified from python quantities test suite
    def assertQuantityEqual(self, q1, q2, msg=None, delta=None):
        """
        Make sure q1 and q2 are the same quantities to within the given
        precision.
        """

        if isinstance(q1, (list, tuple)):
            for first, second in zip(q1, q2):
                self.assertQuantityEqual(first, second)
            return

        delta = 1e-5 if delta is None else delta
        msg = '' if msg is None else ' (%s)' % msg

        q1 = Q_(q1)
        q2 = Q_(q2)

        d1 = getattr(q1, '_dimensionality', None)
        d2 = getattr(q2, '_dimensionality', None)
        if (d1 or d2) and not (d1 == d2):
            raise self.failureException(
                "Dimensionalities are not equal (%s vs %s)%s" % (d1, d2, msg)
                )

    def test_boolfeat(self):

        class Spam(FakeMBDriver):

            eggs = mfeats.BoolFeat('eggs?', 'eggs {:d}', 1, 0)

        obj = Spam()
        self.assertEqual(obj.eggs, False)
        self.assertEqual(setattr(obj, 'eggs', True), None)
        self.assertEqual(obj.eggs, True)


    def test_boolfeat_instrvalues(self):

        class Spam(FakeMBDriver):

            DRIVER_TRUE = 1
            DRIVER_FALSE = 0

            eggs = mfeats.BoolFeat('eggs?', 'eggs {:d}')

        obj = Spam()
        self.assertEqual(obj.eggs, False)
        self.assertEqual(setattr(obj, 'eggs', True), None)
        self.assertEqual(obj.eggs, True)

if __name__ == '__main__':
    unittest.main()
