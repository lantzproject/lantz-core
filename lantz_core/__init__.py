# -*- coding: utf-8 -*-
"""
    lantz.core
    ~~~~~~~~~~

    An automation and instrumentation toolkit with a clean, well-designed and
    consistent interface.

    The lantz.core package provides basic definitions to build drivers, including
    a Driver class and the Feat and Action decorators.

    :copyright: 2018 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""

import pkg_resources

try:
    __version__ = pkg_resources.get_distribution('lantz-core').version
except:
    __version__ = "unknown"

from pint import UnitRegistry
ureg = UnitRegistry()
Q_ = ureg.Quantity

from serialize import register_class
register_class(ureg.Quantity, ureg.Quantity.to_tuple, ureg.Quantity.from_tuple)

from .log import LOGGER
from .driver import Driver
from .feat import Feat, DictFeat
from .action import Action
from .flock import initialize_many, finalize_many
from .messagebased import MessageBasedDriver
from .processors import DimensionalityWarning

__all__ = ['Driver', 'Action', 'Feat', 'DictFeat', 'Q_', 'MessageBasedDriver']


def test():
    """Run all tests.

    Parameters
    ----------

    Returns
    -------
    unittest.TestResult

    """
    from .testsuite import run
    return run()
