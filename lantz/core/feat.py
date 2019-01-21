# -*- coding: utf-8 -*-
"""
    lantz.core.feat
    ~~~~~~~~~~~~~~~

    Implements Feat and DictFeat property-like classes with data handling,
    logging, timing, cache and notification.

    :copyright: 2018 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""

import functools

from collections import defaultdict

from pimpmyclass import InstanceConfig
from pimpmyclass.props import (LockProperty, ReadOnceProperty, PreventUnnecessarySetProperty, TransformProperty,
                               StatsProperty, LogProperty, ObservableProperty, NamedProperty, InstanceConfigurableProperty)
from pimpmyclass.dictprops import DictObservableProperty


from .helpers import Self, MetaSelf, Proxy
from .processors import (Processor, to_quantity_converter, to_magnitude_converter,
                         mapper_or_checker, reverse_mapper_or_checker, range_checker, MyRange)


_NoneType = type(None)


class SimProperty(NamedProperty):
    """A property that with a set or get Lock.

    Requires that the owner class inherits LogMixin.
    """

    _simulator = None

    def get(self, instance, objtype):

        # checking for fget allows dispatching checking for existence
        if self._simulator and self.fget:
            return self._simulator.get(instance)

        return super().get(instance, objtype)

    def set(self, instance, value):
        if self._simulator and self.fset:
            return self._simulator.set(instance, value)

        return super().set(instance, value)


class Feat(LockProperty, ObservableProperty, PreventUnnecessarySetProperty, ReadOnceProperty,
           TransformProperty, LogProperty, StatsProperty, SimProperty):
    """Pimped Python property for interfacing with instruments. Can be used as
    a decorator.

    Processors can registered for each arguments to modify their values before
    they are passed to the body of the method. Two standard processors are
    defined: `values` and `units` and others can be given as callables in the
    `get_funcs` parameter.

    If a method contains multiple arguments, use the `item` method.

    Feat has the following nested behaviors:

    1. Feat: lantz specific modifiers: values, units, limits, procs, read_once)
    2. LockProperty: locks the parent drive (for multi-threading apps)
    3. ObservableProperty: emits a signal when the cached value has changed (via set/get)
    4. SetCacheProperty: prevents unnecessary set operations by comparing the value in the cache
    5. TransformProperty: transform values according to predefined rules.
    6. LogProperty: log get and set operations
    7. StatsProperty: record number of calls and timing stats for get/set/failed operations.
    8. Finally the actual getter or setter is called.
    """

    __original_doc__ = ''

    _storage_ns = 'feat'
    _storage_ns_init = lambda instance: defaultdict(dict)

    # These are feat modifiers.
    values = InstanceConfig(valid_types=(set, dict, _NoneType, Self), default=None,
                            doc='A dictionary to map key to values or a set to restrict the values.')
    units = InstanceConfig(valid_types=(str, tuple, _NoneType, Self), default=None,
                           doc='Units used by this feat.')
    limits = InstanceConfig(valid_types=(tuple, _NoneType, Self), default=None,
                            doc='Specify a range (start, stop, step) for numerical values')
    get_funcs = InstanceConfig(default=None,
                               doc='Other callables to be applied to get output.')
    set_funcs = InstanceConfig(default=None,
                               doc='Other callables to be applied to set input argument.')

    def __set_name__(self, owner, name):
        super().__set_name__(owner, name)

        # Each feat is registered in the Driver class under the _lantz_feats attribute.
        # This attribute hold the qualname of the Driver subclass in __lantz_driver_cls__

        # To allow Driver subclassing, _lantz_feats is duplicated
        # if the owner class of the property does not match the __lantz_driver_cls__ value.
        # In this way, each DriverSubclass._lantz_feats contains only the Feats of DriverSubclass
        # and parent classes but not childs.

        d = owner._lantz_feats

        if getattr(d, '__lantz_driver_cls__', None) != owner.__qualname__:
            d = d.__class__(**d)
            setattr(d, '__lantz_driver_cls__', owner.__qualname__)
            owner._lantz_feats = d

        owner._lantz_feats[name] = self

        self.rebuild()

    # Modifiers Accesors
    # Get/set from instance.Feat or Class.Feat

    def on_config_set(self, instance, key, value):
        """Rebuild get and set funcs based on modifiers and
        store the resulting funcs in the Class.Feat or instance.

        Parameters
        ----------
        instance : object
            (Default value = None)

        """
        super().on_config_set(instance, key, value)

        if key not in ('values', 'units', 'limits', 'get_funcs', 'set_funcs'):
            return

        self.rebuild(instance)

    def rebuild(self, instance=None):

        # Get order
        # instrument value
        #  -> user funcs (get_funcs)
        #  -> reverse_mapper_or_checker (values)
        #  -> to quantity (units)
        #  -> user value

        # Set order
        # user value
        #  -> to magnitude (unit converter)
        #  -> check limit (limits)
        #  -> user func (set_funcs)
        #  -> instrument value

        values = self.values_iget(instance)
        units = self.units_iget(instance)
        limits = self.limits_iget(instance)
        get_funcs = self.get_funcs_iget(instance)
        set_funcs = self.set_funcs_iget(instance)

        get_processors = Processor()
        set_processors = Processor()

        if units:
            get_processors.append(to_quantity_converter(units))
            set_processors.append(to_magnitude_converter(units))
        if values:
            get_processors.append(reverse_mapper_or_checker(values))
            set_processors.append(mapper_or_checker(values))
        if limits:
            if isinstance(limits[0], (list, tuple)):
                set_processors.append(range_checker(tuple(MyRange(*l) for l in limits)))
            else:
                set_processors.append(range_checker(MyRange(*limits)))

        if get_funcs:
            for func in get_funcs:
                if func is not None:
                    get_processors.append(Processor(func))

        if set_funcs:
            for func in set_funcs:
                if func is not None:
                    set_processors.append(Processor(func))

        self.post_get_iset(instance, reversed(get_processors))
        self.pre_set_iset(instance, set_processors)


class DictFeat(InstanceConfigurableProperty, DictObservableProperty):
    """Pimped Python key, value property for interfacing with instruments.

    Parameters
    ----------
    keys : set
        Restricts the valid keys.

    See Feat for other parameters.

    """

    _storage_ns = 'dictfeat'
    _storage_ns_init = lambda instance: defaultdict(dict)

    # These are feat modifiers.
    values = InstanceConfig(valid_types=(set, dict, _NoneType, Self), default=None,
                            doc='A dictionary to map key to values or a set to restrict the values.')
    units = InstanceConfig(valid_types=(str, tuple, _NoneType), default=None,
                           doc='Units used by this feat.')
    limits = InstanceConfig(valid_types=(tuple, _NoneType), default=None,
                            doc='Specify a range (start, stop, step) for numerical values')
    get_funcs = InstanceConfig(default=None,
                               doc='Other callables to be applied to get output.')
    set_funcs = InstanceConfig(default=None,
                               doc='Other callables to be applied to set input argument.')

    _simulator = None

    def __set_name__(self, owner, name):
        super().__set_name__(owner, name)

        # See Feat.__set_name__ for a description of this part

        d = owner._lantz_dictfeats

        if getattr(d, '__lantz_driver_cls__', None) != owner.__qualname__:
            d = d.__class__(**d)
            setattr(d, '__lantz_driver_cls__', owner.__qualname__)
            owner._lantz_dictfeats = d

        owner._lantz_dictfeats[name] = self

    def build_subproperty(self, key, fget, fset, instance=None):
        p = Feat(
            fget=fget,
            fset=fset,
            **dict(self.config_iter(instance))
        )
        if self._simulator is not None:
            p._simulator = self._simulator(key)
        return p

    def on_config_set(self, instance, key, value):
        """Rebuild get and set funcs based on modifiers and
        store the resulting funcs in the Class.Feat or instance.

        Parameters
        ----------
        instance : object
            (Default value = None)

        """
        super().on_config_set(instance, key, value)

        if key not in ('values', 'units', 'limits', 'get_funcs', 'set_funcs'):
            return

        for _, subprop in self._subproperties.items():
            setattr(subprop, key, value)


class FeatProxy:
    """Proxy object for Feat that allows to
    store instance specific modifiers.
    """

    def __init__(self, instance, feat):
        super().__setattr__('instance', instance)
        super().__setattr__('proxied', feat)

    @property
    def __doc__(self):
        return self.feat.__doc__

    def __getattr__(self, item):

        if item in self.proxied._config.keys():
            return self.proxied.config_get(self.instance, item)

        elif hasattr(self.proxied, item):
            out = getattr(self.proxied, item)
            if callable(out):
                return functools.partial(getattr(self.proxied, item), self.instance)
            return out

        raise AttributeError('Cannot get %s in %s. '
                             'Invalid Feat method, property or modifier', item, self.proxied.name)

    def __setattr__(self, item, value):

        if item not in self.proxied._config.keys():
            raise AttributeError('Cannot set %s in %s. '
                                 'Invalid Feat modifier', item, self.proxied.name)

        self.proxied.config_set(self.instance, item, value)


class DictFeatProxy:
    """Proxy object for DictFeat that allows to
    store instance specific modifiers.
    """

    def __init__(self, instance, dictfeat):
        super().__setattr__('instance', instance)
        super().__setattr__('proxied', dictfeat)

    @property
    def __doc__(self):
        return self.proxied.__doc__

    def __getattr__(self, item):

        if item in self.proxied._config.keys():
            return self.proxied.config_get(self.instance, item)

        elif hasattr(self.proxied, item):
            out = getattr(self.proxied, item)
            if callable(out):
                return functools.partial(getattr(self.proxied, item), self.instance)
            return out

        raise AttributeError('Cannot get %s in %s. '
                             'Invalid DictFeat method, property or modifier', item, self.proxied.name)

    def __setattr__(self, item, value):

        if item not in self.proxied._config.keys():
            raise AttributeError('Cannot set %s in %s. '
                                 'Invalid DictFeat modifier', item, self.proxied.name)

        self.proxied.config_set(self.instance, item, value)

    def __getitem__(self, item):
        return FeatProxy(self.instance, self.proxied.subproperty(self.instance, item))


class TypedFeat(Feat):

    def __init__(self, valid_types, *args, **kwargs):
        self.valid_types = valid_types
        super().__init__(fget=self.local_get, fset=self.local_set, *args, **kwargs)

    def local_get(self, instance):
        return self.recall(instance)

    def local_set(self, instance, value):
        if not isinstance(value, self.valid_types):
            raise Exception('Only {} are valid types for {}, not {}'.format(self.valid_types, self.name, value))
