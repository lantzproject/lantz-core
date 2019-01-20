# -*- coding: utf-8 -*-
"""
    lantz.core.driver
    ~~~~~~~~~~~~~~~~~

    Implements the Driver base class.

    :copyright: 2018 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""

from collections import defaultdict, ChainMap

from PySignal import ClassSignal

from pimpmyclass.mixins import LogMixin, AsyncMixin, ObservableMixin, CacheMixin, StorageMixin

from . import helpers
from .feat import FeatProxy, DictFeatProxy
from .action import Action, ActionProxy
from .helpers import MISSING, Self, MetaSelf, Proxy
from .log import get_logger


_REGISTERED = defaultdict(int)


class MyDict(dict):
    pass


class Base(ObservableMixin, AsyncMixin, LogMixin, CacheMixin, StorageMixin):
    """Base class for all lantz objects.

    Provides:
    - Observables
    - Async capabilities for actions
    - Logging
    - Feat cache

    Parameters
    ----------
    name :
        name: easy to remember identifier given to the instance for logging
        purposes

    Returns
    -------

    """

    logger_name = None

    _get_logger = get_logger

    _observer_signal_init = ClassSignal

    # Dict[str, Feat] relating feat name to Feat instance
    _lantz_feats = MyDict()

    # Dict[str, DictFeat] relating dictfeat name to DictFeat instance
    _lantz_dictfeats = MyDict()

    # Dict[str, Action] relating action name to Action instance
    _lantz_actions = MyDict()

    _cache_unset_value = helpers.UNSET

    __name = ''

    def __init__(self, name=None):
        if name:
            self.name = name
        else:
            name = self.__class__.__name__
            self.name = '{}{:d}'.format(name, _REGISTERED[name])
            _REGISTERED[name] += 1

        if self.logger_name is None:
            self.logger_name = 'lantz.driver.' + self.name

        self.__keep_alive = []
        for feat_name, feat in self._lantz_feats.items():
            mods = dict(feat.config_iter(self))
            for attr_name, attr_value in mods.items():
                if not isinstance(attr_value, Self):
                    continue

                setter = _set(self, feat_name, attr_name)
                self.__keep_alive.append(setter)
                getattr(self, attr_value.item + '_changed').connect(setter)
                if attr_value.default is MISSING:
                    funcs_get = feat.post_get or ()
                    funcs_get.prepend(_raise_must_change(attr_value.item, feat_name, 'get'))

                    funcs_set = feat.pre_set or ()
                    funcs_set.prepend(_raise_must_change(attr_value.item, feat_name, 'set'))
                else:
                    feat.config_set(None, attr_name, attr_value.default)

        super().__init__()
        self._lantz_anyfeat = ChainMap(self._lantz_feats, self._lantz_dictfeats)
        self.log_info('Created ' + self.name)

    @property
    def name(self):
        """Get the name of this instrument.
        """
        return self.__name

    @name.setter
    def name(self, value):
        """Set the name to this instrument.
        """
        self.__name = value

    def __str__(self):
        classname = self.__class__.__name__
        return "{} {}".format(classname, self.name)

    def __repr__(self):
        classname = self.__class__.__name__
        return "<{}('{}')>".format(classname, self.name)

    @property
    def feats(self):
        """ """
        return Proxy(self, self._lantz_feats, FeatProxy)

    @property
    def dictfeats(self):
        """ """
        return Proxy(self, self._lantz_dictfeats, DictFeatProxy)

    @property
    def actions(self):
        """ """
        return Proxy(self, self._lantz_actions, ActionProxy)


class Driver(Base):
    """Base class for all drivers.

    Parameters
    ----------
    name :
        name: easy to remember identifier given to the instance for logging
        purposes

    Returns
    -------
    """

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, *args):
        self.finalize()

    @Action()
    def initialize(self):
        """ """
        pass

    @Action()
    def finalize(self):
        """ """
        pass


    @Action()
    def update(self, newstate=None, *, force=False, **kwargs):
        """Update driver.

        Parameters
        ----------
        newstate : dict.
            a dictionary containing the new driver state. (Default value = None)
        force : bool
            apply change even when the cache says it is not necessary. (Default value = False)
        **kwargs :
            a dictionary containing the new driver state to be merged with newstate.
        """

        newstate = helpers.merge_dicts(newstate, kwargs)
        if not newstate:
            raise ValueError('update() called with an empty dictionary')

        notfound = set(newstate.keys()) - set(self._lantz_anyfeat.keys())
        if notfound:
            raise ValueError('Not valid feats: %s' % notfound)

        for key, value in newstate.items():
            if force:
                self._lantz_anyfeat[key].invalidate_cache()
            setattr(self, key, value)

    @Action()
    def refresh(self, keys=None):
        """Refresh cache by reading values from the instrument.

        Parameters
        ----------
        keys : str or list or tuple or dict
            a string or list of strings with the properties to refresh.
            Default None, meaning all properties.
            If keys is a string, returns the value.
            If keys is a list/tuple, returns a tuple.
            If keys is a dict, returns a dict.

        Returns
        -------

        """
        if keys:
            if isinstance(keys, (list, tuple)):
                return tuple(getattr(self, key) for key in keys)
            elif isinstance(keys, dict):
                return {key: getattr(self, key) for key in keys.keys()}
            elif isinstance(keys, str):
                return getattr(self, keys)
            else:
                raise ValueError('keys must be a (str, list, tuple or dict)')

        # TODO: make this work for DictFeats
        dfeats = {key: getattr(self, key) for key in self._lantz_feats.keys()
                  if isinstance(key, str)}
        ddictfeats = {key: prop.getall(self) for key, prop in self._lantz_dictfeats.items()}

        return {**dfeats, **ddictfeats}

    def recall(self, keys=None):
        """Return the last value seen for a feat or a collection of feats.

        Parameters
        ----------
        keys : str or iterable of str, optional
            Name of the feat or feats to recall.
            Default is None, meaning all feats.

        Returns
        -------
        value of the feat or dict mapping feat to values.

        """

        return super().recall(keys or self._lantz_feats.keys())



def _raise_must_change(dependent, feat_name, operation):

    def _inner(value):
        raise Exception("You must get or set '{}' before trying to {} '{}'".format(dependent, operation, feat_name))
    return _inner


def _set(instance, feat_name, attr_name):
    def _inner(value, old_value):
        setattr(instance.feats[feat_name], attr_name, value)
    return _inner
