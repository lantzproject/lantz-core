

def config(args=None):
    """Get or set configuration variables.

    Example
    -------

    $ lantz config core.visa_backend "@py"
    """

    import argparse
    import sys

    from .config import CONFIG_FILE, FULL_CONFIG, cfg

    parser = argparse.ArgumentParser(description='Lantz Configuration')
    parser.add_argument('key', nargs='?', help='Configuration key', default=None)
    parser.add_argument('value', nargs='?', help='Configuration value', default=None)
    parser.add_argument('--show-all', action='store_true')
    parser.add_argument('--show-path', action='store_true')

    args = parser.parse_args(args)

    if args.show_path:
        print('Configuration file: %s' % CONFIG_FILE)

    if args.show_all:
        if args.key is None:
            for key in sorted(FULL_CONFIG.keys()):
                source, val = FULL_CONFIG[key]
                print('%s: %s = %s' % (source, key, val))
        else:
            key = args.key.lower()
            if key not in FULL_CONFIG:
                print('%s is not a valid key' % args.key)

            if args.value is None:
                source, val = FULL_CONFIG[key]
                print('%s: %s = %s' % (source, key, val))
            else:
                print('actual argument is not compatible with a set operation.')
                sys.exit(1)

    else:
        if args.key is None:
            for section in cfg.sections():
                for subkey in cfg[section].keys():
                    print('%s.%s = %s' % (section, subkey, cfg[section][subkey]))
        else:
            key = args.key.lower()
            if key not in FULL_CONFIG:
                print('%s is not a valid key' % args.key)
                sys.exit(1)

            section, subkey = key.split('.')
            if args.value is None:
                try:
                    print('%s' % cfg[section][subkey])
                except KeyError:
                    pass
            else:
                if section not in cfg:
                    cfg[section] = {}
                cfg[section][subkey] = args.value

                with open(CONFIG_FILE, 'w') as fo:
                    cfg.write(fo)


if __name__ == '__main__':
    config()
