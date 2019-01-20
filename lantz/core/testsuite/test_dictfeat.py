# -*- coding: utf-8 -*-


import logging
import unittest

from lantz.core import Driver, DictFeat, Q_, DimensionalityWarning

from lantz.core.log import get_logger
from lantz.core.helpers import UNSET
from lantz.core.testsuite import MemHandler, must_warn

from pimpmyclass import helpers



class DictFeatTest(unittest.TestCase):

    # Modified from python quantities test suite
    def assertQuantityEqual(self, q1, q2, msg=None, delta=None):
        """
        Make sure q1 and q2 are the same quantities to within the given
        precision.
        """

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

    def test_readonly(self):

        class Spam(Driver):

            _eggs = {'answer': 42}

            @DictFeat()
            def eggs(self_, key):
                return self_._eggs[key]

        obj = Spam()
        self.assertEqual(obj.eggs['answer'], 42)
        self.assertRaises(AttributeError, setattr, obj, "eggs", 3)
        self.assertRaises(AttributeError, delattr, obj, "eggs")

    def test_writeonly(self):

        # noinspection PyPropertyDefinition
        class Spam(Driver):

            _eggs = {'answer': 42}

            eggs = DictFeat()

            @eggs.setter
            def eggs(self_, key, value):
                self_._eggs[key] = value

        obj = Spam()

        obj.eggs['answer'] = 46
        self.assertEqual(obj._eggs['answer'], 46)

        with self.assertRaises(AttributeError):
            obj.eggs['answer']

        with self.assertRaises(AttributeError):
            del obj.eggs

        with self.assertRaises(AttributeError):
            del obj.eggs['answer']

    def test_readwrite(self):

        # noinspection PyPropertyDefinition
        class Spam(Driver):

            _eggs = {'answer': 42}

            @DictFeat()
            def eggs(self_, key):
                return self_._eggs[key]

            @eggs.setter
            def eggs(self_, key, value):
                self_._eggs[key] = value

        obj = Spam()
        self.assertEqual(obj.eggs['answer'], 42)
        obj.eggs['answer'] = 46
        self.assertEqual(obj._eggs['answer'], 46)
        self.assertEqual(obj.eggs['answer'], 46)
        self.assertRaises(AttributeError, delattr, obj, "eggs")

    def test_cache(self):

        class Spam(Driver):

            _eggs = {'answer': 42}

            @DictFeat()
            def eggs(self_, key):
                return self_._eggs[key]

            @eggs.setter
            def eggs(self_, key, value):
                self_._eggs[key] = value

        obj = Spam()
        out = obj.recall("eggs")
        self.assertEqual(out, {})
        self.assertIsInstance(out, helpers.missingdict)
        # Any non present value
        self.assertEqual(out[1234], Spam._cache_unset_value)


        self.assertEqual(obj.eggs['answer'], 42)
        self.assertEqual(obj._eggs['answer'], 42)
        # After reading 1 element, it is stored in the cache
        self.assertEqual(obj.recall("eggs"), {'answer': 42})

        obj.eggs['answer'] = 46
        self.assertEqual(obj._eggs['answer'], 46)
        self.assertEqual(obj.eggs['answer'], 46)

        ##self.assertEqual(obj.recall("eggs"), {'answer': 46})
        obj._eggs['answer'] = 0
        ##self.assertEqual(obj.recall("eggs"), {'answer': 46})
        self.assertEqual(obj.eggs['answer'], 0)
        ##self.assertEqual(obj.recall("eggs"), {'answer': 0})

    def test_logger(self):

        hdl = MemHandler()

        logger = get_logger('lantz.driver')
        logger.addHandler(hdl)
        logger.setLevel(logging.DEBUG)

        class Spam(Driver):

            _eggs = {'answer': 42}

            @DictFeat()
            def eggs(self_, key):
                return self_._eggs[key]

            @eggs.setter
            def eggs(self_, key, value):
                self_._eggs[key] = value

        obj = Spam(name='myspam')
        x = obj.eggs['answer']
        obj.eggs['answer'] = x
        obj.eggs['answer'] = x + 1
        self.assertEqual(hdl.history, ['Created myspam',
                                       "Getting eggs['answer']",
                                       "Got 42 for eggs['answer']",
                                       "No need to set eggs['answer'] = 42 (current=42)",
                                       "Setting eggs['answer'] to 43",
                                       "eggs['answer'] was set to 43"])

    def test_units(self):

        hdl = MemHandler()

        class Spam(Driver):
            _logger = get_logger('test.feat')
            _logger.addHandler(hdl)
            _logger.setLevel(logging.DEBUG)

            _eggs = {'answer': 42}

            @DictFeat(units='s')
            def eggs(self_, key):
                return self_._eggs[key]

            @eggs.setter
            def eggs(self_, key, value):
                self_._eggs[key] = value

        obj = Spam()
        self.assertQuantityEqual(obj.eggs['answer'], Q_(42, 's'))
        obj.eggs['answer'] = Q_(46, 'ms')
        self.assertQuantityEqual(obj.eggs['answer'], Q_(46 / 1000, 's'))

        with must_warn(DimensionalityWarning, 1) as msg:
            obj.eggs['answer'] = 42

        self.assertFalse(msg, msg=msg)


    def test_keys(self):

        class Spam(Driver):
            _eggs = {'answer': 42}

            @DictFeat(keys=('answer', ))
            def eggs(self_, key):
                return self_._eggs[key]

            @eggs.setter
            def eggs(self_, key, value):
                self_._eggs[key] = value

        obj = Spam()
        self.assertEqual(obj.eggs['answer'], 42)
        obj.eggs['answer'] = 46
        self.assertEqual(obj.eggs['answer'], 46)
        self.assertRaises(KeyError, lambda x: obj.eggs['spam'], None)

        with self.assertRaises(KeyError):
            obj.eggs['spam'] = 1

    def test_keys_mapping(self):

        class Spam(Driver):
            _eggs = {'answer': 42}

            @DictFeat(keys={28: 'answer'})
            def eggs(self_, key):
                return self_._eggs[key]

            @eggs.setter
            def eggs(self_, key, value):
                self_._eggs[key] = value

        obj = Spam()
        self.assertEqual(obj.eggs[28], 42)
        obj.eggs[28] = 46
        self.assertEqual(obj.eggs[28], 46)
        self.assertRaises(KeyError, lambda x: obj.eggs['spam'], None)
        self.assertRaises(KeyError, lambda x: obj.eggs['answer'], None)

    def test_of_instance(self):

        class Spam(Driver):

            def __init__(self_):
                super().__init__()
                self_._eggs = {1: 9}

            @DictFeat()
            def eggs(self_, key):
                return self_._eggs[key]

            @eggs.setter
            def eggs(self_, key, value):
                self_._eggs[key] = value

        obj = Spam()
        obj2 = Spam()

        self.assertEqual(obj.eggs.instance, obj)
        self.assertEqual(obj2.eggs.instance, obj2)

        #self.assertEqual(obj.recall("eggs"), {})
        self.assertEqual(obj.eggs[1], 9)

        self.assertEqual(obj.recall("eggs")[1], 9)
        obj.eggs[1] = 10
        self.assertEqual(obj._eggs[1], 10)
        self.assertEqual(obj.eggs[1], 10)
        self.assertEqual(obj.recall("eggs")[1], 10)
        obj._eggs = {1: 0}

        self.assertEqual(obj.recall("eggs")[1], 10)
        self.assertEqual(obj.eggs[1], 0)
        self.assertEqual(obj.recall("eggs")[1], 0)

        self.assertEqual(obj2.recall("eggs")[1], UNSET)


    def test_in_instance(self):

        class Spam(Driver):

            @DictFeat(keys=(1, 2, 3), units='ms')
            def eggs(self_, key):
                return 9

        x = Spam()
        y = Spam()
        self.assertEqual(str(x.eggs[1].units), 'millisecond')
        self.assertEqual(x.dictfeats.eggs[1].units, y.dictfeats.eggs[1].units)
        self.assertEqual(x.eggs[1], y.eggs[1])
        x.dictfeats.eggs[1].units = 's'
        self.assertNotEqual(x.dictfeats.eggs[1].units, y.dictfeats.eggs[1].units)
        self.assertNotEqual(x.eggs[1], y.eggs[1])
        self.assertEqual(str(x.eggs[1].units), 'second')
        self.assertEqual(str(x.eggs[2].units), 'millisecond')

if __name__ == '__main__':
    unittest.main()
