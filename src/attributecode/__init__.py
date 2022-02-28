#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) nexB Inc. http://www.nexb.com/ - All rights reserved.
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

from collections import namedtuple
import logging
import os

import saneyaml

__version__ = '7.0.0'

__about_spec_version__ = '3.2.3'

__copyright__ = """
Copyright (c) nexB Inc. All rights reserved. http://dejacode.org
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


class Error(namedtuple('Error', ['severity', 'message'])):
    """
    An Error data with a severity and message.
    """

    def __new__(self, severity, message):
        if message:
            if isinstance(message, str):
                message = self._clean_string(message)
            else:
                message = self._clean_string(repr(message))
                message = message.strip('"')

        return super(Error, self).__new__(
            Error, severity, message)

    def __repr__(self, *args, **kwargs):
        sev, msg = self._get_values()
        return 'Error(%(sev)s,  %(msg)s)' % locals()

    def __eq__(self, other):
        return repr(self) == repr(other)

    def _get_values(self):
        sev = severities[self.severity]
        msg = self._clean_string(repr(self.message))
        return sev, msg

    def render(self):
        sev, msg = self._get_values()
        return '%(sev)s: %(msg)s' % locals()

    def to_dict(self, *args, **kwargs):
        """
        Return an ordered dict of self.
        """
        return self._asdict()

    @staticmethod
    def _clean_string(s):
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
