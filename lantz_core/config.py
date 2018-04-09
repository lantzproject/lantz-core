# -*- coding: utf-8 -*-
"""
    lantz.core.config
    ~~~~~~~~~~~~~~~~~

    This packages contains two parts:
    1) General for managing configuration in Lantz.
    2) The actual configuration values for lantz_core.

    The convention in Lantz is to define configuration values
    as an UPPERCASE named variable in a file named config.py in
    each subpackage. (e.g. VISA_BACKEND)

    To register that variable you should use the `register_and_get`
    function with two arguments: the global key and the default value.

    By convention the global key should be:

        <subpackage name>.<variable name>

    e.g.: core.visa_backend

    Registering the varible has the following benefits:
    1) You can override it in your system with a configuration file.
       The configuration file is a ini formated UTF-8 text file.
       The subpackage name is the section, and the variable name is the key.
       e.g.
       [core]
       visa_backend =

    2) You can override it in a particular run with an environmental variable
       which also overrides the value in the configuration file.
       The variable should be named named LANTZ_ followed by the key in uppercase and replacing dots by underscores.
       e.g. core.visa_backend -> LANTZ_CORE_VISA_BACKEND

    3) You can set/get the value via the `lantz config` utility.

    :copyright: 2018 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""

import configparser
import os
import sys


# =======================
# General stuff
# =======================

# Modified from Click
# https://raw.githubusercontent.com/pallets/click/master/click/utils.py

def _posixify(name):
    return '-'.join(name.split()).lower()


def get_app_dir(app_name, roaming=True, force_posix=False):
    r"""Returns the config folder for the application.  The default behavior
    is to return whatever is most appropriate for the operating system.

    To give you an idea, for an app called ``"Foo Bar"``, something like
    the following folders could be returned:

    Mac OS X:
      ``~/Library/Application Support/Foo Bar``
    Mac OS X (POSIX):
      ``~/.foo-bar``
    Unix:
      ``~/.config/foo-bar``
    Unix (POSIX):
      ``~/.foo-bar``
    Win XP (roaming):
      ``C:\Documents and Settings\<user>\Local Settings\Application Data\Foo Bar``
    Win XP (not roaming):
      ``C:\Documents and Settings\<user>\Application Data\Foo Bar``
    Win 7 (roaming):
      ``C:\Users\<user>\AppData\Roaming\Foo Bar``
    Win 7 (not roaming):
      ``C:\Users\<user>\AppData\Local\Foo Bar``

    .. versionadded:: 2.0

    :param app_name: the application name.  This should be properly capitalized
                     and can contain whitespace.
    :param roaming: controls if the folder should be roaming or not on Windows.
                    Has no affect otherwise.
    :param force_posix: if this is set to `True` then on any POSIX system the
                        folder will be stored in the home folder with a leading
                        dot instead of the XDG config home or darwin's
                        application support folder.
    """
    if sys.platform.startswith('win'):
        key = roaming and 'APPDATA' or 'LOCALAPPDATA'
        folder = os.environ.get(key)
        if folder is None:
            folder = os.path.expanduser('~')
        return os.path.join(folder, app_name)
    if force_posix:
        return os.path.join(os.path.expanduser('~/.' + _posixify(app_name)))
    if sys.platform == 'darwin':
        return os.path.join(os.path.expanduser(
            '~/Library/Application Support'), app_name)
    return os.path.join(
        os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
        _posixify(app_name))


CONFIG_FOLDER = get_app_dir('lantz')
os.makedirs(CONFIG_FOLDER, exist_ok=True)

CONFIG_FILE = os.path.join(CONFIG_FOLDER, 'config.cfg')
cfg = configparser.ConfigParser()
cfg.read(CONFIG_FILE)

# Configuration Value
# configuration key -> (source, configuration value)
# The source indicates how the value was defined:
# - env: from an environmental variable
#        named LANTZ_ followed by the key in uppercase and replacing dots by underscores.
#        eg. core.visa_backend becomes -> LANTZ_CORE_VISA_BACKEND
# - cfg: from the configuratio file.
# - mod: from the package.
FULL_CONFIG = {}


def register_and_get(key, default):

    source, val = 'env', os.getenv('LANTZ_' + key.replace('.', '_').upper(), None)

    key = key.lower()
    if val is None:
        section, subkey = key.split('.')
        try:
            source, val = 'cfg', cfg[section][subkey]
        except KeyError:
            source, val = 'mod', default

    FULL_CONFIG[key] = (source, val)

    return val


# ====================================
# Configuration Values for lantz_core
# ====================================

# Visa Backend use by Lantz
# valid values: any value accepted by pyvisa.
# e.g. @ni, @py, @sim, /path/to/library@ni
VISA_BACKEND = register_and_get('core.visa_backend', '')

from logging.handlers import DEFAULT_TCP_LOGGING_PORT

# The host of a TCP network socket where a log is sent.
TCP_LOGGING_HOST = register_and_get('core.tcp_logging_host', 'localhost')

# The port of a TCP network socket where a log is sent.
TCP_LOGGING_PORT = int(register_and_get('core.tcp_logging_port', DEFAULT_TCP_LOGGING_PORT))
