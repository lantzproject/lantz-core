# -*- coding: utf-8 -*-
"""
    lantz.core.helpers
    ~~~~~~~~~~~~~~~~~~

    An automation and instrumentation toolkit with a clean, well-designed and
    consistent interface.

    :copyright: 2018 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""


from collections import UserDict


class NamedObject(object):
    """A class to construct named sentinels.
    """

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __hash__(self):
        return id(self)

    def __deepcopy__(self, memo):
        return self


#: Indicates that a feat/dict feat value has not been set or get yet
#: and therefore it is not in the cache.
UNSET = NamedObject('UNSET')

# Indicates that the value was not provided, typically in the constructor
MISSING = NamedObject('MISSING')

ALL_INSTANCES = NamedObject('ALL_INSTANCES')
NO_KEY = NamedObject('NO_KEY')



class UnsetDict(UserDict):
    """Dictionary that returns UNSET
    """
    def __missing__(self, key):
        return UNSET


def merge_dicts(*args):
    """Merge multiple dictionaries in a new one
    treating None as an empty dictionary.

    merge_dicts(dict1, [dict2 [...]]) -> dict1.update(dict2);dict1.update ...

    Parameters
    ----------
    *args : dict-like


    Returns
    -------
    dict

    Example
    -------
    >>> d1 = dict(a=1, b=2)
    >>> d2 = dict(b=3, c=4)
    >>> merge_dicts(d1, None, d2)
    {a: 1, b: 3, c: 4}
    """

    args = (arg for arg in args if arg)

    out = {}

    for arg in args:
        out.update(arg)

    return out


def keep_if_not(_skip=None, **kwargs):
    return {k: v for k, v in kwargs.items() if v is not _skip}


def solve_dependencies(dependencies, all_members=None):
    """Solve a dependency graph.

    Parameters
    ----------
    dependencies : dict
        For each key, the value is an iterable indicating its dependencies.
    all_members : iterable, optional
        List of all keys in the graph.
        Useful to guarantee that all keys will be in the result even
        if they are disconnected from the graph.
        (Default value: empty)

    Returns
    -------
    list of sets
        Each set contains tasks that depend only on the tasks
        in the previous set in the list.

    """
    d = dict((key, set(value)) for key, value in dependencies.items())

    if all_members:
        d.update({key: set() for key in all_members if key not in d})
    r = []

    while d:
        # values not in keys (items without dep)
        t = set(i for v in d.values() for i in v) - set(d.keys())
        # and keys without value (items without dep)
        t.update(k for k, v in d.items() if not v)
        # can be done right away
        r.append(t)
        # and cleaned up
        d = dict(((k, v - t) for k, v in d.items() if v))

    return r


def lengther(s, item=None):
    if not s:
        return None

    if not isinstance(s, (list, tuple)):
        return 0

    if item is None:
        return len(s)
    else:
        return len(s[item])


def tuplify(a, n):
    if isinstance(a, (tuple, list)):
        return a
    else:
        return (a, ) * n


def tuplify_many(*args_item):
    lens = [lengther(arg) for arg, item in args]
    mx = max(val for val in lens if val is not None)
    mn = min(val for val in lens if val is not None)
    if mx != mn:
        raise ValueError('All tuples must be the same length '
                         'when specifing multiple modifiers.')

    if mx == 0:
        return args


def import_from_entrypoint(object_ref):
    import importlib
    modname, qualname_separator, qualname = object_ref.partition(':')
    obj = importlib.import_module(modname)
    if qualname_separator:
        for attr in qualname.split('.'):
            obj = getattr(obj, attr)

    return obj


class MetaSelf(type):
    """Metaclass for Self object"""

    def __getattr__(self, item):
        return Self(item)


class Self(metaclass=MetaSelf):
    """Self objects are used in during Driver class declarations
    to refer to the object that is going to be instantiated.

    Example
    -------
    >>> Self.units('s')
    <Self.units('s')>
    """

    def __init__(self, item, default=MISSING):
        self.item = item
        self.default = default

    def __get__(self, instance, owner=None):
        return getattr(instance, self.item)

    def __call__(self, default_value):
        self.default = default_value
        return self

    def __repr__(self):
        return "<Self.{}('{}')>".format(self.item, self.default)


class Proxy(object):
    """Read only dictionary that maps feat name to Proxy objects"""

    def __init__(self, instance, collection, callable):
        self.instance = instance
        self.collection = collection
        self.callable = callable

    def __contains__(self, item):
        return item in self.collection

    def __getattr__(self, item):
        return self.callable(self.instance, self.collection[item])

    def __getitem__(self, item):
        return self.callable(self.instance, self.collection[item])

    def items(self):
        """ """
        for key, value in self.collection.items():
            yield key, self.callable(self.instance, value)

    def keys(self):
        """ """
        for key in self.collection.keys():
            yield key
