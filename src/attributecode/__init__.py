#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2017 nexB Inc. http://www.nexb.com/ - All rights reserved.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#      http://www.apache.org/licenses/LICENSE-2.0
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
import os

import attr
import saneyaml

try:
    # Python 2
    unicode  # NOQA
except NameError:  # pragma: nocover
    # Python 3
    unicode = str  # NOQA


__version__ = '4.0.0.pre1'

__about_spec_version__ = '4.0'

__copyright__ = """
Copyright (c) 2013-2018 nexB Inc. All rights reserved. http://dejacode.org
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


def message_converter(value):
    if value:
        if isinstance(value, unicode):
            value = clean_string(value)
        else:
            value = clean_string(unicode(repr(value), encoding='utf-8'))
            value = value.strip('"')
    return value


@attr.attributes()
class Error(object):
    """
    An Error data with a severity and message and an optional path attribute.
    """
    severity = attr.attrib()
    message = attr.attrib(converter=message_converter)
    # relative POSIX path of the ABOUT file
    path = attr.attrib(default=None)#, repr=False)

    def _get_values(self):
        sev = severities[self.severity]
        msg = clean_string(repr(self.message))
        return sev, msg

    def render(self):
        sev, msg = self._get_values()
        return '%(sev)s: %(msg)s' % locals()

    def to_dict(self, *args, **kwargs):
        """
        Return an ordered dict of self.
        """
        return attr.asdict(self, dict_factory=OrderedDict)


def clean_string(s):
    """
    Return a cleaned string for `s`, stripping eventual "u" prefixes
    from unicode representations.
    """
    if not s:
        return s
    if s.startswith(('u"', "u'")):
        s = s.lstrip('u')
    s = s.replace('[u"', '["')
    s = s.replace("[u'", "['")
    s = s.replace("(u'", "('")
    s = s.replace("(u'", "('")
    s = s.replace("{u'", "{'")
    s = s.replace("{u'", "{'")
    s = s.replace(" u'", " '")
    s = s.replace(" u'", " '")
    s = s.replace("\\\\", "\\")
    return s


# modeled after the logging levels
CRITICAL = 50
ERROR = 40
WARNING = 30
INFO = 20
DEBUG = 10
NOTSET = 0


severities = {
    CRITICAL : 'CRITICAL',
    ERROR : 'ERROR',
    WARNING : 'WARNING',
    INFO : 'INFO',
    DEBUG : 'DEBUG',
    NOTSET : 'NOTSET'
}
