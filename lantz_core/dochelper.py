# -*- coding: utf-8 -*-
"""
    lantz.core.dochelper
    ~~~~~~~~~~~~~~~~~~~~

    Helper function to build driver documentation.

    :copyright: 2018 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""


def build_feat_doc(feat):
    """Build the documentation for a given feat.

    Parameters
    ----------
    feat : Feat
        the

    Returns
    -------
    str:
        new documentation.
    """
    if not hasattr(feat, '__original_doc__'):
        feat.__original_doc__ = feat.__doc__ or ''

    doc = ''
    predoc = ''

    modifiers = feat.modifiers[ALL_INSTANCES][NO_KEY]

    if isinstance(feat, DictFeat):
        predoc = ':keys: {}\n\n'.format(modifiers.get('keys', None) or 'ANY')

    if modifiers['values']:
        doc += ':values: {}\n'.format(modifiers['values'])
    if modifiers['units']:
        doc += ':units: {}\n'.format(modifiers['units'])
    if modifiers['limits']:
        doc += ':limits: {}\n'.format(modifiers['limits'])
    if modifiers['processors']:
        docpg = []
        docps = []
        for getp, setp in modifiers['processors']:
            if getp is not None:
                docpg.insert(0, '  - {}'.format(getp))
            if setp is not None:
                docps.append('  - {}'.format(setp))
            if docpg:
                doc += ':get procs: {}'.format('\n'.join(docpg))
            if docps:
                doc += ':set procs: {}'.format('\n'.join(docps))

    if predoc:
        predoc = '\n\n{}'.format(predoc)
    if doc:
        doc = '\n\n{}'.format(doc)

    feat.__doc__ = predoc + feat.__original_doc__ + doc
