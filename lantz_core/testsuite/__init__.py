# -*- coding: utf-8 -*-

import contextlib
import logging
import os
import unittest
import warnings


class Msg:

    def __init__(self):
        self.s = ''

    def __bool__(self):
        return bool(self.s)

    def set(self, value):
        self.s = value

    def __str__(self):
        return self.s

    __repr__ = __str__


@contextlib.contextmanager
def must_warn(warning, count):
    msg = Msg()
    with warnings.catch_warnings(record=True) as ws:
        # Catch all warnings of this type
        warnings.simplefilter('always', warning)

        # Execute the function
        yield msg

    # If we are looking for a specific amount of
    # warnings, re-send all warnings if not the same
    if count is not None and count != len(ws):
        for w in ws:
            warnings.showwarning(
                message=w.message,
                category=w.category,
                filename=w.filename,
                lineno=w.lineno,
                file=w.file,
                line=w.line,
            )

    if count > len(ws):
        msg.set('More %s than expected (%d > %d)' % (warning, count, len(ws)))
    elif count < len(ws):
        msg.set('Less %s than expected (%d < %d)' % (warning, count, len(ws)))


class MemHandler(logging.Handler):

    def __init__(self):
        super().__init__()
        self.setFormatter(logging.Formatter(style='{'))
        self.history = list()

    def emit(self, record):
        self.history.append(self.format(record))



def testsuite():
    """A testsuite that has all the lantz tests.
    """
    return unittest.TestLoader().discover(os.path.dirname(__file__))


def main():
    """Runs the testsuite as command line application.
    """
    try:
        unittest.main()
    except Exception as e:
        print('Error: %s' % e)


def run():
    """Run all tests.

    :return: a :class:`unittest.TestResult` object
    """
    test_runner = unittest.TextTestRunner()
    return test_runner.run(testsuite())
