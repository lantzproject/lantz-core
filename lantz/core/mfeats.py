# -*- coding: utf-8 -*-
"""
    lantz.core.mfeat
    ~~~~~~~~~~~~~~~

    Message based Feat and DictFeat property-like classes.

    :copyright: 2018 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""

import collections
from string import Formatter

from .feat import Feat, DictFeat


def to_brackets(field_name, format_spec):
    """Return PEP 3101 format string with field name and format specification.
    """

    if format_spec:
        format_spec = ':' + format_spec
        return '{' + field_name + format_spec + '}'

    return '{' + field_name + '}'


def to_spec_brackets(format_spec):
    """Return PEP 3101 format string with format specification.
    """

    if format_spec:
        return '{' + ':' + format_spec + '}'

    return '{}'


def parse_cmd(format_string):
    """Parse a format string and return a dictionary linking field name to PEP 3101 with format specification.
    (Removes field names)
    """
    return {field_name: to_spec_brackets(format_spec)
            for (literal_text, field_name, format_spec, conversion) in Formatter().parse(format_string)
            if field_name is not None}


def check_values(format_string, values, msg):
    """Tries to format a given string for all values
    """
    for value in values:
        try:
            format_string.format(value)
        except Exception as e:
            raise ValueError("Could not format the '%s' into %s'.\n%s" % (value, msg, e))


class MFeatMixin:
    """"Mixin class for feats in message based drivers.

    Notice that the Feat class is built upon __set_name__ in order to have access
    to the actual class.
    """

    def __init__(self, get_cmd, set_cmd):

        # Notice that we DO NOT CALL super here.
        self.get_cmd = get_cmd
        self.set_cmd = set_cmd

    def __set_name__(self, owner, name):
        kwargs = self._build_feat_kwargs(owner, name)
        self._check_format_string()
        Feat.__init__(self, **kwargs)
        Feat.__set_name__(self, owner, name)

    def local_get(self, instance):
        if isinstance(self.get_cmd, str):
            return instance.get_query(self.get_cmd)
        else:
            msg, ans = self.get_cmd
            return instance.parse_query(msg, format=ans)

    def local_set(self, instance, value):
        return instance.set_query(self.set_cmd.format(value))

    def _check_values(self, format_string):
        """Implement to check if the value part of formatting string is valid.
        """
        raise NotImplementedError

    def _check_format_string(self):
        """Implement to check if a formatting string is valid.
        """
        if self.set_cmd:
            check_values(self.set_cmd, (self.get_initial_value(),), 'in set_cmd')

    def _build_feat_kwargs(self, owner, name):
        """Builds the kwargs to be delivered to the Feat constructor.
        """
        return dict(fget=self.local_get if self.get_cmd else None,
                    fset=self.local_set if self.set_cmd else None,)

    def get_initial_value(self):
        return self._get_initial_value()


class DictMFeatMixin(MFeatMixin):
    """"Mixin class for feats in message based drivers.
    """

    def __init__(self, get_cmd, set_cmd, keys=None):

        # Notice that we DO NOT CALL super here. We want a specific parent.
        MFeatMixin.__init__(self, get_cmd, set_cmd)
        self.keys = keys

    def __set_name__(self, owner, name):
        kwargs = self._build_feat_kwargs(owner, name)
        self._check_format_string()
        DictFeat.__init__(self, **kwargs)
        DictFeat.__set_name__(self, owner, name)

    def _check_values(self, spec):
        raise NotImplementedError

    def local_get(self, instance, key):
        if isinstance(self.get_cmd, str):
            return instance.get_query(self.get_cmd.format(key=key))
        else:
            msg, ans = self.get_cmd
            return instance.parse_query(msg, format=ans)

    def local_set(self, instance, key, value):
        return instance.set_query(self.set_cmd.format(key=key, value=value))

    def _check_format_string(self):
        keys = self.keys

        if isinstance(keys, dict):
            keys = list(keys.values())

        if self.get_cmd:
            parts = parse_cmd(self.get_cmd)
            if set(parts.keys()) != {'key'}:
                raise ValueError("Formatting keys in 'get_cmd' must be 'key'")

            if keys:
                check_values(parts.get('', parts.get('key')), keys, 'in the key of get_cmd')

        if self.set_cmd:
            parts = parse_cmd(self.set_cmd)
            if set(parts.keys()) != {'key', 'value'}:
                raise ValueError("Formatting keys in 'set_cmd' must be 'key' and 'value'")

            if keys:
                check_values(parts['key'], keys, 'in the key of set_cmd')

            self._check_values(parts['value'])

    def _build_feat_kwargs(self, owner, name):
        """Builds the kwargs to be delivered to the DictFeat constructor.
        """
        return {'keys': self.keys, **super()._build_feat_kwargs(owner, name)}

    def get_initial_value(self):
        if self.keys:
            return {k: self._get_initial_value() for k in self.keys}
        return collections.defaultdict(self._get_initial_value)


class BoolMixin:
    """Mixin class for boolean feats
    """

    def __init__(self, true_value, false_value):
        self.__true_value = true_value
        self.__false_value = false_value

    def _build_feat_kwargs(self, owner, name):

        if self.__true_value is None:
            if not hasattr(owner, 'DRIVER_TRUE'):
                raise ValueError("'true_value' has not been specified for '%s'\n"
                                 "Provide a value or set the DRIVER_TRUE class "
                                 "variable for the owner class (%s)" % (name, owner.__name__))

            self.__true_value = owner.DRIVER_TRUE

        if self.__false_value is None:
            if not hasattr(owner, 'DRIVER_FALSE'):
                raise ValueError("'false_value' has not been specified for '%s'\n"
                                 "Provide a value or set the DRIVER_FALSE class "
                                 "variable for the owner class (%s)" % (name, owner.__name__))

            self.__false_value = owner.DRIVER_FALSE

        return dict(values={True: self.__true_value, False: self.__false_value},
                    **super()._build_feat_kwargs(owner, name))

    def _check_values(self, format_string):

        values = (self.__true_value, self.__false_value)
        values = tuple(val for val in values if val is not None)

        if format_string:
            check_values(format_string, values, 'set_cmd')

    def get_initial_value(self):
        return False


class BoolFeat(BoolMixin, MFeatMixin, Feat):
    """A boolean Feat for message based drivers.

    If the True and False are not given,
        class attributes `DRIVER_TRUE` and `DRIVER_FALSE` will be used
    """

    def __init__(self, get_cmd, set_cmd, true_value=None, false_value=None):
        BoolMixin.__init__(self, true_value, false_value)
        MFeatMixin.__init__(self, get_cmd, set_cmd)

    def _check_format_string(self):
        self._check_values(self.set_cmd)


class BoolDictFeat(BoolMixin, DictMFeatMixin, DictFeat):
    """A boolean DictFeat for message based drivers.

    If the True and False are not given,
        class attributes `DRIVER_TRUE` and `DRIVER_FALSE` will be used
    """

    def __init__(self, get_cmd, set_cmd, true_value=None, false_value=None, keys=None):
        BoolMixin.__init__(self, true_value, false_value)
        DictMFeatMixin.__init__(self, get_cmd, set_cmd, keys)


class NumericMixin:

    def __init__(self, limits):
        self.__limits = limits

    def _build_feat_kwargs(self, owner, name):
        return dict(limits= self.__limits,
                    **super()._build_feat_kwargs(owner, name))

class IntMixin(NumericMixin):
    """Mixin class for Int Feats
    """

    def _build_feat_kwargs(self, owner, name):
        return dict(get_funcs=(int, ),
                    **super()._build_feat_kwargs(owner, name))

    def _get_initial_value(self):
        return 0

    def _check_values(self, format_string):
        pass


class FloatMixin(NumericMixin):
    """Mixin class for Float Feats
    """

    def _build_feat_kwargs(self, owner, name):
        return dict(get_funcs=(float, ),
                    **super()._build_feat_kwargs(owner, name))

    def _get_initial_value(self):
        return 0.0

    def _check_values(self, format_string):
        pass


class QuantityMixin:
    """Mixin class for Quantity Feats
    """

    def __init__(self, units, limits=None):
        self.__units = units
        self.__limits = limits
        self._internal_type = float

    def _build_feat_kwargs(self, owner, name):
        return dict(units=self.__units, limits= self.__limits,
                    **super()._build_feat_kwargs(owner, name))

    def _check_values(self, format_string):
        pass

    def _get_initial_value(self):
        return 0


class QuantityFeat(QuantityMixin, MFeatMixin, Feat):
    """A Quantity Feat for message based drivers.
    """

    def __init__(self, get_cmd, set_cmd, units=None, limits=None):
        MFeatMixin.__init__(self, get_cmd, set_cmd)
        QuantityMixin.__init__(self, units, limits)

    def _check_format_string(self):
        self._check_values(self.set_cmd)


class QuantityDictFeat(QuantityMixin, DictMFeatMixin, DictFeat):
    """A Quantity DictFeat for message based drivers.
    """

    def __init__(self, get_cmd, set_cmd, units=None, limits=None, keys=None):
        DictMFeatMixin.__init__(self, get_cmd, set_cmd, keys)
        QuantityMixin.__init__(self, units, limits)


class IntFeat(IntMixin, MFeatMixin, Feat):

    def __init__(self, get_cmd, set_cmd, limits=None):
        MFeatMixin.__init__(self, get_cmd, set_cmd)
        IntMixin.__init__(self, limits)


class IntDictFeat(IntMixin, DictMFeatMixin, DictFeat):

    def __init__(self, get_cmd, set_cmd, limits=None, keys=None):
        DictMFeatMixin.__init__(self, get_cmd, set_cmd, keys=keys)
        IntMixin.__init__(self, limits)


class FloatFeat(FloatMixin, MFeatMixin, Feat):

    def __init__(self, get_cmd, set_cmd, limits=None):
        MFeatMixin.__init__(self, get_cmd, set_cmd)
        FloatMixin.__init__(self, limits)


class FloatDictFeat(FloatMixin, DictMFeatMixin, DictFeat):

    def __init__(self, get_cmd, set_cmd, limits=None, keys=None):
        DictMFeatMixin.__init__(self, get_cmd, set_cmd, keys=keys)
        FloatMixin.__init__(self, limits)


class ValuesMixin:
    """Mixin class for a values feat.
    """

    def __init__(self, values):
        self.__values = values

    def _check_values(self, format_string):
        values = self.__values
        if isinstance(self.__values, dict):
            values = list(values.values())

        check_values(format_string, values, 'set_cmd')

    def _build_feat_kwargs(self, owner, name):
        return dict(values=self.__values,
                    **super()._build_feat_kwargs(owner, name))

    def get_initial_value(self):
        values = self.__values
        if isinstance(self.__values, dict):
            values = list(values.values())
        return values[0]


class ValuesFeat(ValuesMixin, MFeatMixin, Feat):

    def __init__(self, get_cmd, set_cmd, values):
        MFeatMixin.__init__(self, get_cmd, set_cmd)
        ValuesMixin.__init__(self, values)

    def _check_format_string(self):
        self._check_values(self.set_cmd)


class ValuesDictFeat(ValuesMixin, DictMFeatMixin, DictFeat):

    def __init__(self, get_cmd, set_cmd, values, keys=None):
        DictMFeatMixin.__init__(self, get_cmd, set_cmd, keys)
        ValuesMixin.__init__(self, values)

    def _check_values(self, format_string):
        values = self.values
        if isinstance(self.values, dict):
            values = list(values.values())

        check_values(format_string, values, 'set_cmd')


class EnumFeat(ValuesFeat):

    def __init__(self, get_cmd, set_cmd, enum_cls):
        values = {v: v.value for k, v in enum_cls.__members__.items()}
        values.update({k: v.value for k, v in enum_cls.__members__.items()})
        ValuesFeat.__init__(self, get_cmd, set_cmd, values)


class EnumDictFeat(ValuesDictFeat):

    def __init__(self, get_cmd, set_cmd, enum_cls, keys=None):
        values = {v: v.value for k, v in enum_cls.__members__.items()}
        values.update({k: v.value for k, v in enum_cls.__members__.items()})
        ValuesDictFeat.__init__(self, get_cmd, set_cmd, values, keys)
