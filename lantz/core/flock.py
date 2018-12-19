# -*- coding: utf-8 -*-
"""
    lantz.core.flock
    ~~~~~~~~~~~~~~~~

    A flock in lantz is a collection of drivers.

    :copyright: 2018 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""

import atexit

import serialize

from collections import defaultdict
from concurrent import futures
from types import MappingProxyType

from . import helpers


class Flock:
    """A collection of drivers
    """

    _yaml_dict = None
    _source_dict = None
    _constructors = None
    _dependencies = None

    def __init__(self):
        self._drivers = {}
        self._constructors = {}
        self._dependencies = defaultdict(set)
        self._state = defaultdict(dict)

    def add(self, driver, *dependencies):
        """Add a non instantiated driver to the flock.

        Parameters
        ----------
        driver : an instantiated driver.
            The driver
        dependencies:
            A list of device names
        """

        for dep in dependencies:
            if dep not in self._drivers:
                raise ValueError('%s is not a valid dependency as it is '
                                 'not yet in the flock' % dep)

        name = driver.name
        if not name.isidentifier():
            raise ValueError('%s is not a valid driver name within a flock. '
                             'Must be a valid python identifier.' % name)

        if name in dir(Flock):
            raise ValueError('%s is not a valid driver name within a flock. '
                             'Must be different from %s' % (name, dir(Flock)))

        if name in self._drivers:
            raise ValueError('%s is already taken within this flock')

        self._drivers[name] = driver
        for dep in dependencies:
            self._dependencies[name].add(dep)

    @property
    def dependencies(self):
        return MappingProxyType(self._dependencies)

    def __iter__(self):
        yield from self.values()

    def items(self):
        yield from self._drivers.items()

    def keys(self):
        yield from self._drivers.keys()

    def values(self):
        yield from self._drivers.values()

    def __getattr__(self, item):
        return self._drivers[item]

    def initialize(self, register_finalizer=False, on_initializing=None,
                   on_initialized=None, on_exception=None, concurrent=False):
        """Initialize the flock.

        Parameters
        ----------
        register_finalizer :
            register driver.finalize method to be called at python exit. (Default value = True)
        on_initializing :
            a callable to be executed BEFORE initialization.
            It takes the driver as the first argument. (Default value = None)
        on_initialized :
            a callable to be executed AFTER initialization.
            It takes the driver as the first argument. (Default value = None)
        on_exception :
            a callable to be executed in case an exception occurs.
            It takes the offending driver as the first argument and the
            exception as the second one. (Default value = None)
        concurrent :
            indicates that drivers with satisfied dependencies
            should be initialized concurrently. (Default value = False)
        """

        return initialize_many(self.values(), register_finalizer, on_initializing,
                               on_initialized, on_exception, concurrent,
                               dict(self._dependencies))

    def finalize(self, on_finalizing=None, on_finalized=None, on_exception=None,
                 concurrent=False):
        """Finalize

        Parameters
        ----------
        on_finalizing :
            a callable to be executed BEFORE finalization.
            It takes the driver as the first argument. (Default value = None)
        on_finalized :
            a callable to be executed AFTER finalization.
            It takes the driver as the first argument. (Default value = None)
        on_exception :
            a callable to be executed in case an exception occurs.
            It takes the offending driver as the first argument and the
            exception as the second one. (Default value = None)
        concurrent :
            indicates that drivers with satisfied dependencies
            are finalized concurrently. (Default value = False)
        """

        return finalize_many(self.values(), on_finalizing, on_finalized,
                             on_exception, concurrent,
                             dict(self._dependencies))

    @classmethod
    def parse(cls, flock, source):

        for name, info in source.get('drivers', {}).items():
            driver_cls = helpers.import_from_entrypoint(info['cls'])

            func_name = info.get('func', None)
            if func_name:
                driver_cls = getattr(driver_cls, func_name)

            driver = driver_cls(name=name,
                                *info.get('args', ()),
                                **info.get('kwargs', {}))

            driver.logger_name = info.get('logger_name', None)
            flock.add(driver, *info.get('dependencies', ()))
            flock._state[name] = info.get('state', {})

        return flock

    @classmethod
    def from_yaml(cls, filename):
        source = serialize.load(filename)

        f = Flock()
        f._source_dict = source
        return cls.parse(f, source)

    def to_yaml(self, filename):
        if not filename.endswith('.yaml'):
            filename += filename + '.yaml'

        self.record_state()

        drivers = {}

        for name, driver in self.items():
            previous = self._yaml_dict.get(name, {})

            d = dict(cls='%s:%s' % (driver.__class__.__module__,
                                    driver.__class__.__name__),
                     func=previous.get('func', None),
                     args=previous.get('args', ()),
                     kwargs=previous.get('kwargs', {}),
                     logger_name=driver.logger_name,
                     depends_on=self._dependencies[name],
                     state=driver.recall())
            drivers[name] = d

        d = dict(drivers=drivers,
                 )

        serialize.dump(d, filename)

    def record_state(self):
        """Record the recall state of each driver in the flock.
        """
        self._state = self.recall()

    def recall(self):
        """Return the last value seen for each feat for each driver in the flock.
        """
        return {name: driver for name, driver in self}

    def restore_state(self, state=None):
        """Restore a state.

        A state specifies for each feat, the value.

        Parameters
        ----------
        state : dict-like
            driver name: driver state
            (default = None, corresponding to use the last recorded state)

        """
        if state is None and self._state is None:
            raise ValueError('No recorded state')

        for name, driver_state in state.items():
            self._drivers[name].update(driver_state)

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, *args):
        self.finalize()


def initialize_many(drivers, register_finalizer=True,
                    on_initializing=None, on_initialized=None, on_exception=None,
                    concurrent=False, dependencies=None):
    """Initialize a group of drivers.

    Parameters
    ----------
    drivers :
        an iterable of drivers.
    register_finalizer :
        register driver.finalize method to be called at python exit. (Default value = True)
    on_initializing :
        a callable to be executed BEFORE initialization.
        It takes the driver as the first argument. (Default value = None)
    on_initialized :
        a callable to be executed AFTER initialization.
        It takes the driver as the first argument. (Default value = None)
    on_exception :
        a callable to be executed in case an exception occurs.
        It takes the offending driver as the first argument and the
        exception as the second one. (Default value = None)
    concurrent :
        indicates that drivers with satisfied dependencies
        should be initialized concurrently. (Default value = False)
    dependencies :
        indicates which drivers depend on others to be initialized.
        each key is a driver name, and the corresponding
        value is an iterable with its dependencies. (Default value = None)

    """

    if dependencies:
        names = {driver.name: driver for driver in drivers}

        groups = helpers.solve_dependencies(dependencies, set(names.keys()))
        drivers = tuple(tuple(names[name] for name in group) for group in groups)
        for subset in drivers:
            initialize_many(subset, register_finalizer,
                            on_initializing, on_initialized, on_exception,
                            concurrent)
        return

    if concurrent:
        def _finalize(d):
            def _inner_finalize(f):
                atexit.register(d.finalize)
            return _inner_finalize

        def _done(d):
            def _inner(f):
                ex = f.exception()
                if ex:
                    if not on_exception:
                        raise ex
                    on_exception(d, ex)
                else:
                    if on_initialized:
                        on_initialized(d)
            return _inner

        futs = []
        for driver in drivers:
            if on_initializing:
                on_initializing(driver)
            fut = driver.initialize_async()
            if register_finalizer:
                fut.add_done_callback(_finalize(driver))
            fut.add_done_callback(_done(driver))
            futs.append(fut)

        futures.wait(futs)
    else:
        for driver in drivers:
            if on_initializing:
                on_initializing(driver)
            try:
                driver.initialize()
            except Exception as ex:
                if not on_exception:
                    raise ex
                on_exception(driver, ex)
            else:
                if on_initialized:
                    on_initialized(driver)

            if register_finalizer:
                atexit.register(driver.finalize)


def finalize_many(drivers,
                  on_finalizing=None, on_finalized=None, on_exception=None,
                  concurrent=False, dependencies=None):
    """Finalize a group of drivers.

    Parameters
    ----------
    drivers :
        an iterable of drivers.
    on_finalizing :
        a callable to be executed BEFORE finalization.
        It takes the driver as the first argument. (Default value = None)
    on_finalized :
        a callable to be executed AFTER finalization.
        It takes the driver as the first argument. (Default value = None)
    on_exception :
        a callable to be executed in case an exception occurs.
        It takes the offending driver as the first argument and the
        exception as the second one. (Default value = None)
    concurrent :
        indicates that drivers with satisfied dependencies
        are finalized concurrently. (Default value = False)
    dependencies :
        indicates which drivers depend on others to be initialized.
        each key is a driver name, and the corresponding
        value is an iterable with its dependencies.
        The dependencies are used in reverse. (Default value = None)

    """

    if dependencies:
        names = {driver.name: driver for driver in drivers}

        groups = helpers.solve_dependencies(dependencies, set(names.keys()))
        drivers = tuple(tuple(names[name] for name in group) for group in groups)
        for subset in reversed(drivers):
            finalize_many(subset, on_finalizing, on_finalized, on_exception, concurrent)
        return

    if concurrent:
        def _done(d):
            def _inner(f):
                ex = f.exception()
                if ex:
                    if not on_exception:
                        raise ex
                    on_exception(d, ex)
                else:
                    if on_finalized:
                        on_finalized(d)
            return _inner

        futs = []
        for driver in drivers:
            if on_finalizing:
                on_finalizing(driver)
            fut = driver.finalize_async()
            fut.add_done_callback(_done(driver))
            futs.append(fut)

        futures.wait(futs)
    else:
        for driver in drivers:
            if on_finalizing:
                on_finalizing(driver)
            try:
                driver.finalize()
            except Exception as ex:
                if not on_exception:
                    raise ex
                on_exception(driver, ex)
            else:
                if on_finalized:
                    on_finalized(driver)
