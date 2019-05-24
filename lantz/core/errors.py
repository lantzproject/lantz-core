# -*- coding: utf-8 -*-
"""
    lantz.core.errors
    ~~~~~~~~~~~~~~~~~

    Implements base classes for instrumentation related exceptions. They are
    useful to mix with specific exceptions from libraries or modules and
    therefore allowing code to catch them via lantz excepts without
    breaking specific ones.

    :copyright: 2018 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""

class InvalidCommand(Exception):
    """ """
    pass

class LantzTimeoutError(Exception):
    """ """
    pass

class InstrumentError(Exception):
    """ """
    pass

class NotSupportedError(Exception):
    """ """
    pass

class NotInitializedError(Exception):

    def __str__(self):
        return "The resource is not ready yet. Call the initialize() method of the driver instance."
