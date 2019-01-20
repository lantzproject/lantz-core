# -*- coding: utf-8 -*-
"""
    lantz.core.processors
    ~~~~~~~~~~~~~~~~~~~~~

    A processor is an object that takes value

    :copyright: 2018 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""

import enum
import functools
import warnings

from . import Q_
from .log import LOGGER as _LOG
from stringparser import Parser


class DimensionalityWarning(Warning):
    """ """
    pass


def noop(value):
    """Returns the input value. (No operation)
    """
    return value


def convert_to(units, on_dimensionless='warn', on_incompatible='raise',
               return_float=False, logger=_LOG):
    """Convert a Quantity to other units.

    Parameters
    ----------
    units : str or Quantity
        Specifies the target units

    on_dimensionless : string, optional
        Indicates how to proceed when a dimensionless number is given.
        - 'raise' to raise an exception.
        - 'warn' to log a warning and proceed.
        - 'ignore' to silently proceed.

        (the default value is 'warn')

    on_incompatible : string, optional
        Indicates how to proceed when source and target units are incompatible.
        Same options as `on_dimensionless`

        (the default value is 'raise')

    return_float : bool, optional
        If True, only the magnitude of the converted Quantity will be returned.
        (Default value is False)

    Returns
    -------
    Quantity or float

    Examples
    --------
    >>> convert_to('mV')(Q_(1, 'V'))
    <Quantity(1000.0, 'millivolt')>
    >>> convert_to('mV', return_float=True)(Q_(1, 'V'))
    1000.0
    """
    if on_dimensionless not in ('ignore', 'warn', 'raise'):
        raise ValueError("{} is not a valid value for 'on_dimensionless'. "
                         "It should be either 'ignore', 'warn' or 'raise'".format(on_dimensionless))
    if on_incompatible not in ('ignore', 'warn', 'raise'):
        raise ValueError("{} is not a valid value for 'on_incompatible'. "
                         "It should be either 'ignore', 'warn' or 'raise'".format(on_dimensionless))

    if isinstance(units, str):
        units = Q_(1, units)
    elif not isinstance(units, Q_):
        raise ValueError("{} is not a valid value for 'units'. "
                         "It should be either str or Quantity".format(units))

    if return_float:
        def _inner(value):
            if isinstance(value, Q_):
                try:
                    return value.to(units).magnitude
                except ValueError as e:
                    if on_incompatible == 'raise':
                        raise ValueError(e)
                    elif on_incompatible == 'warn':
                        msg = 'Unable to convert {} to {}. Ignoring source units.'.format(value, units)
                        warnings.warn(msg, DimensionalityWarning)
                        logger.warning(msg)

                # on_incompatible == 'ignore'
                return value.magnitude
            else:
                if not units.dimensionless:
                    if on_dimensionless == 'raise':
                        raise ValueError('Unable to convert {} to {}'.format(value, units))
                    elif on_dimensionless == 'warn':
                        msg = 'Assuming units `{1.units}` for {0}'.format(value, units)
                        warnings.warn(msg, DimensionalityWarning)
                        logger.warning(msg)

                # on_incompatible == 'ignore'
                return float(value)
        return _inner
    else:
        def _inner(value):
            if isinstance(value, Q_):
                try:
                    return value.to(units)
                except ValueError as e:
                    if on_incompatible == 'raise':
                        raise ValueError(e)
                    elif on_incompatible == 'warn':
                        msg = 'Assuming units `{1.units}` for {0}'.format(value, units)
                        warnings.warn(msg, DimensionalityWarning)
                        logger.warning(msg)

                # on_incompatible == 'ignore'
                return Q_(float(value.magnitude), units)
            else:
                if not units.dimensionless:
                    if on_dimensionless == 'raise':
                        raise ValueError('Unable to convert {} to {}'.format(value, units))
                    elif on_dimensionless == 'warn':
                        msg = 'Assuming units `{1.units}` for {0}'.format(value, units)
                        warnings.warn(msg, DimensionalityWarning)
                        logger.warning(msg)

                # on_incompatible == 'ignore'
                return Q_(float(value), units)
        return _inner


def range_checker_coercer(low, high, step=None):
    """Callable that returns the same value if within range,
    optionally coercing the value to a grid.

    The callable raises a ValueError if value not in range.

    Parameters
    ----------
    low : int or float
        Lower value in the range (included)
    high : int or float
        Higher value in the range (included)
    step : int or float

    Returns
    -------
    callable (value) -> (value) might raise ValueError

    Examples
    --------
    >>> checker = range_checker_coercer(1, 10)
    >>> checker(1), checker(5), checker(10)
    (1, 5, 10)
    >>> checker(11)
    Traceback (most recent call last):
    ...
    ValueError: 11 not in range (1, 10)
    >>> checker = range_checker_coercer(1, 10, 1)
    >>> checker(1), checker(5.4), checker(10)
    (1, 5, 10)
    """

    def _inner(value):

        if not (low <= value <= high):
            raise ValueError('{} not in range ({}, {})'.format(value, low, high))
        if step:
            value = round((value - low) / step) * step + low
        return value

    return _inner


def membership_checker(container):
    """Callable that returns the same value if present in a container.

    The callable raises a ValueError if value not in the container.

    Parameters
    ----------
    container : tuple or list or set-like object

    Returns
    -------
    callable (value) -> (value) might raise ValueError

    Examples
    -------
    >>> checker = membership_checker((1, 2, 3))
    >>> checker(1)
    1
    >>> checker(0)
    Traceback (most recent call last):
    ...
    ValueError: 0 not in (1, 2, 3)
    """

    def _inner(value):

        if value not in container:
            raise ValueError('{!r} not in {}'.format(value, container))
        return value

    return _inner


def mapper(container):
    """Callable that returns the value for a given key
    in a dict-like container.

    The callable raises a ValueError if value not in the container.

    Parameters
    ----------
    container : dict-like object

    Returns
    -------
    callable (value) -> (value) might raise ValueError

    Examples
    -------
    >>> getter = mapper({'A': 42, 'B': 43})
    >>> getter('A')
    42
    >>> getter(0)
    Traceback (most recent call last):
    ...
    ValueError: 0 not in ('A', 'B')
    """

    def _inner(key):

        if key not in container:
            raise ValueError("{!r} not in {}".format(key, tuple(container.keys())))
        return container[key]

    return _inner


def enum_mapper(container):
    """Callable that returns the value for a given key
    in a Enum class.

    The callable raises a ValueError if value not in the container.

    Parameters
    ----------
    container : Enum class

    Returns
    -------
    callable (value) -> (value) might raise ValueError

    Examples
    -------
    >>> getter = mapper(MyEnum)
    >>> getter(MyEnum.A)
    42
    >>> getter('A')
    42
    >>> getter('B')
    Traceback (most recent call last):
    ...
    ValueError: 'B' not in MyEnum
    """

    def _inner(key):

        if isinstance(key, enum.Enum):
            return key.value

        elif isinstance(key, str):
            try:
                key = container[key]
            except KeyError:
                raise ValueError("{!r} not in {!r}".format(key, container))

            return key.value

        else:
            raise ValueError("{!r} not in {!r}".format(key, container))

    return _inner


def to_converter(func):
    """Wraps a function taking a single value to

    - If spec is None, return noop
    - If spec is callable, returns the same spec
    - If spec is list/tuple, returns a callable that

    Examples
    --------
    >>> @to_converter
    ... def multiplier(mult):
    ...     def _inner(value):
    ...         return value * mult
    ...     return _inner
    >>> doubler = multiplier(2)
    >>> doubler(3)
    6
    >>> tuple_mult = multiplier((2, 3))
    >>> tuple_mult((3, 5))
    (6, 15)
    """

    def conv(f, s):
        if callable(s):
            return s

        if f is None or s is None:
            return noop

        return f(s)

    @functools.wraps(func)
    def _inner(specs):

        if isinstance(specs, (list, tuple)):

            fs = tuple(conv(func, spec) for spec in specs)

            def _most_inner(values):
                return tuple(f(val) for f, val in zip(fs, values))

            _most_inner.accepts_tuples = True
            return _most_inner

        else:
            return conv(func, specs)

    return _inner


@to_converter
def to_magnitude_converter(units):
    """Callable that extracts the magnitude of a quantity in the destination units

    The callable emits a warning if the quantity is dimensionless.
    The callable raises a ValueError if the source and destination units are incompatible.

    Parameters
    ----------
    units : str or Quantity
        Destination units

    Raises
    ------
    TypeError
        If the unit argument cannot be interpreted.

    Example
    -------
    >>> conv = to_magnitude_converter('ms')
    >>> conv(Q_(1, 's'))
    1000.0
    """

    if isinstance(units, (str, Q_)):
        return convert_to(units, return_float=True)

    raise TypeError('to_magnitude_converter argument must be a string, '
                    'not {}'.format(units))


@to_converter
def to_quantity_converter(units):
    """Callable that extracts the magnitude of a quantity in the destination units

    The callable does not emit a warning if the quantity is dimensionless.
    The callable raises a ValueError if the source and destination units are incompatible.

    Parameters
    ----------
    units : str or Quantity

    Raises
    ------
    TypeError
        If the unit argument cannot be interpreted.

    Example
    -------
    >>> conv = to_quantity_converter('ms')
    >>> conv(Q_(1, 's'))
    <Quantity(1000.0, 'millisecond')>
    >>> conv(1)
    <Quantity(1.0, 'millisecond')>
    """

    if isinstance(units, (str, Q_)):
        return convert_to(units, on_dimensionless='ignore')

    raise TypeError('to_quantity_converter argument must be a string, '
                    'not {}'.format(units))


@to_converter
def parser(spec):
    """Callable to convert/parse the function parameters.

    Parameters
    ----------
    unit : str
        This is interpreted as a stringparser_ PEP 3101.

    Raises
    ------
    TypeError
        If the unit argument cannot be interpreted.

    Example
    -------
    >>> conv = parser('spam {:s} eggs')
    >>> conv('spam ham eggs')
    'ham'

    >>> conv = parser(('hi {:d}', 'bye {:s}'))
    >>> conv(('hi 42', 'bye Brian'))
    (42, 'Brian')

    .. _stringparser:
        https://github.com/hgrecco/stringparser
    """

    if isinstance(spec, str):
        return Parser(spec)
    raise TypeError('parser argument must be a string, '
                    'not {}'.format(spec))


@to_converter
def mapper_or_checker(container):
    """Callable to map the function parameter values.

    Parameters
    ----------
    container : dict-like object

    Raises
    ------
    TypeError
        If the unit argument cannot be interpreted.

    Example
    -------
    >>> conv = mapper_or_checker({True: 42})
    >>> conv(True)
    42
    """

    if isinstance(container, dict):
        return mapper(container)
    if isinstance(container, enum.EnumMeta):
        return enum_mapper(container)
    if isinstance(container, set):
        return membership_checker(container)
    raise TypeError('to_mapper argument must be a dict, '
                    'not {}'.format(container))


@to_converter
def reverse_mapper_or_checker(container):
    """Callable to REVERSE map the function parameter values.

    Parameters
    ----------
    container : dict-like object

    Raises
    ------
    TypeError
        If the unit argument cannot be interpreted.

    Example
    -------
    >>> conv = reverse_mapper_or_checker({True: 42})
    >>> conv(42)
    True
    """

    #: Shared cache of reversed dictionaries indexed by the id()
    __reversed_cache = {}

    if isinstance(container, dict):
        return mapper({value: key for key, value in container.items()})
    if isinstance(container, set):
        return membership_checker(container)
    raise TypeError('reverse_mapper argument must be a dict or set, '
                    'not {}'.format(container))


class MyRange:

    def __init__(self, *args):
        if len(args) == 1:
            start, stop, step = 0, args[0], None
        elif len(args) == 2:
            start, stop, step = args[0], args[1], None
        elif len(args) == 3:
            start, stop, step = args
        else:
            raise TypeError('1-3 arguments expected')

        self.start = start
        self.stop = stop
        self.step = step


@to_converter
def range_checker(spec):
    """Callable that returns the same value if within range,
    optionally coercing the value to a grid.

    The callable raises a ValueError if value not in range.

    It is just a thin wrapper around range_checker_coercer that uses range objects
    
    Parameters
    ----------
    spec : MyRange
        (low, high, step) or (low, high) with step = 1 or (high, ) with step=1 and low=0

    Raises
    ------
    TypeError
        If the unit argument cannot be interpreted.

    Example
    -------
    >>> conv = range_checker(MyRange(1, 2, .5))
    >>> conv(1.7)
    1.5
    """

    if not isinstance(spec, MyRange):
        raise TypeError('range_checker argument must be a MyRange object, '
                        'not {}'.format(spec))

    return range_checker_coercer(spec.start, spec.stop, spec.step)


class Processor:

    def __init__(self, *funcs):
        self._funcs = tuple(funcs)

    def __call__(self, value):
        if isinstance(value, tuple):
            return self._call_tuple(value)

        for func in self._funcs:
            value = func(value)

        return value

    def __bool__(self):
        return bool(self._funcs)

    def _call_tuple(self, values):
        for func in self._funcs:
            if getattr(func, 'accepts_tuples', False):
                values = func(values)
            else:
                values = tuple(func(v) for v in values)

        return values

    def prepend(self, func):
        assert callable(func) or isinstance(func, tuple)
        self._funcs = (func, ) + self._funcs

    def append(self, func):
        assert callable(func) or isinstance(func, tuple)
        self._funcs = self._funcs + (func, )

    def __reversed__(self):
        return self.__class__(*reversed(self._funcs))

