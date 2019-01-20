# -*- coding: utf-8 -*-
"""
    lantz.core.action
    ~~~~~~~~~~~~~~~~~

    Implements the Action class to wrap driver bound methods with Lantz's
    data handling, logging, timing.

    :copyright: 2018 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""

from collections import defaultdict
import inspect

from pimpmyclass import InstanceConfig
from pimpmyclass.methods import LockMethod, TransformMethod, StatsMethod, LogMethod, NamedMethod

from .helpers import keep_if_not, MISSING, Self
from .processors import (Processor,
                         reverse_mapper_or_checker, mapper_or_checker,
                         to_quantity_converter, to_magnitude_converter,
                         range_checker, MyRange)

_NoneType = type(None)

class SimMethod(NamedMethod):

    _simulator = None

    def call(self, instance, *args, **kwargs):
        if self._simulator:
            return self._simulator(instance, *args, **kwargs)

        return super().call(instance, *args, **kwargs)


class Action(LockMethod, TransformMethod, LogMethod, StatsMethod, SimMethod):
    """Wraps a Driver method with Lantz. Can be used as a decorator.

    Processors can registered for each arguments to modify their values before
    they are passed to the body of the method. Three standard processors are
    defined: `values`, `units`, `limits` and others can be given as callables
    in the `funcs` parameter.

    Action has the following nested behaviors:

    1. Feat: lantz specific modifiers: values, units, limits, funcs, read_once)
    2. LockMethod: locks the parent drive (for multi-threading apps)
    3. TransformMethod: transform values according to predefined rules.
    4. StatsMethod: record number of calls and timing stats for get/set/failed operations.
    5. Finally the actual method is called.

    If a method contains multiple arguments, use the param syntax:

    Examples
    --------

    class MyClass:

        @Action(units='s')
        def test(self, x):
            print('%.2f is the magnitude in seconds' % x)

        @Action()
        @Action.param('x', units='s')
        @Action.param('y', values={'a', 'b', 'c'})
        def another(self, x, y):
            print('%.2f is the magnitude in seconds' % x)
            print('%s is one of a, b or c. Others are rejected.' % y)

        @Action()
        @Action.ret(units='s')
        def another(self):
            return 3 # Even if the value is given as float, the output with be a Quantity in seconds


        @Action()
        @Action.param('x', units='s')
        @Action.param('y', values={'a', 'b', 'c'})
        def another(self, x, y):
            print('%.2f is the magnitude in seconds' % x)
            print('%s is one of a, b or c. Others are rejected.' % y)

    Parameters
    ----------
    func : callable
        driver method to be wrapped.
    values :
        A dictionary to values key to values.
        If a list/tuple instead of a dict is given, the value is not
        changed but only tested to belong to the container.
    units : Quantity or string
        Quantity` or string that can be interpreted as units.
    limits :

    funcs :
        Other callables to be applied to input arguments.
    """

    __original_doc__ = ''

    _storage_ns = 'action'
    _storage_ns_init = lambda instance: defaultdict(dict)


    modifiers = InstanceConfig(default=None)

    def __init__(self, *, values=None, units=None, limits=None, funcs=None):
        super().__init__()
        self.modifiers = {None: keep_if_not(values=values, units=units, limits=limits, funcs=funcs)}

    def check_signature(self, func):
        super().check_signature(func)

        names = tuple(inspect.signature(func).parameters.keys())

        p = self.modifiers.pop(None, None)

        if not p:
            return

        d = dict()
        for name in names[1:]:
            if name not in self.modifiers:
                d[name] = p

        self.modifiers = dict(d, **self.modifiers)

    @classmethod
    def build_converter(cls, values=None, units=None, limits=None, funcs=None):

        p = Processor()

        if values:
            p.append(mapper_or_checker(values))

        if units:
            p.append(to_magnitude_converter(units))

        if limits:
            if isinstance(limits[0], (list, tuple)):
                proc = range_checker(tuple(MyRange(*l) for l in limits))
            else:
                proc = range_checker(MyRange(*limits))

            p.append(proc)

        if funcs:
            if isinstance(funcs, (list, tuple)):
                for proc in funcs:
                    p.append(proc)
            else:
                p.append(funcs)

        return p

    @classmethod
    def param(cls, names, *, values=None, units=None, limits=None, funcs=None):
        """Add modifiers to a specific parameter.

        See Action for more information.
        """
        return super().param(names,
                             cls.build_converter(values=values, units=units,
                                                 limits=limits, funcs=funcs))

    @classmethod
    def ret(cls, *, values=None, units=None, limits=None, funcs=None):
        """Add modifiers to the return value.

        See Action for more information.
        """
        return super().param('<ret>',
                             cls.build_converter(values=values, units=units,
                                                 limits=limits, funcs=funcs))

    def __set_name__(self, owner, name):

        # See Feat.__set_name__ for a description of this part

        d = owner._lantz_actions

        if getattr(d, '__lantz_driver_cls__', None) != owner.__qualname__:
            d = d.__class__(**d)
            setattr(d, '__lantz_driver_cls__', owner.__qualname__)
            owner._lantz_actions = d

        owner._lantz_actions[name] = self

        if not name.endswith('_async') and not hasattr(owner, name + '_async'):
            owner._lantz_actions[name + '_async'] = owner.attach_async(self)

        super().__set_name__(owner, name)

    def on_config_set(self, instance, key, value):
        """Rebuild processors based on modifiers and
        store the resulting processors in the Class.Action or instance.

        Parameters
        ----------
        instance : object
            (Default value = None)

        """
        super().on_config_set(instance, key, value)

        if key not in ('modifiers', ):
            return

        if len(value) == 1 and tuple(value.keys())[0] is None:
            self.params_iset(instance, {})
        else:
            self.params_iset(instance, {k: self.build_converter(**v)
                                        for k, v in value.items()})


class ActionProxy(object):
    """Proxy object for Actions that allows to
    store instance specific modifiers.
    """

    def __init__(self, instance, action):
        super().__setattr__('instance', instance)
        super().__setattr__('action', action)

    def __getattr__(self, item):

        if item in self.action._modifiers:
            return self.action.modifiers_get(self.instance, item)

        elif hasattr(self.action, item):
            return getattr(self.action, item)

        raise AttributeError('Cannot get %s in %s. '
                             'Invalid Action method, property or modifier', item, self.action.name)

    def __setattr__(self, item, value):

        if item not in self.action._modifiers:
            raise AttributeError('Cannot set %s in %s. '
                                 'Invalid Action modifier', item, self.feat.name)

        self.action.modifiers_set(self.instance, item, value)

    def param(self, name, *, values=MISSING, units=MISSING, limits=MISSING, funcs=MISSING):
        current = self.action.modifiers_iget(self.instance)

        if not (values or units or limits or funcs):
            return current[name]

        else:
            current[name].update(keep_if_not(MISSING, values=values, units=units, limits=limits, funcs=funcs))
            self.action.modifiers_iset(self.instance, current)
            return current[name]

