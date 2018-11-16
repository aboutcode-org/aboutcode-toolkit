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

from collections import namedtuple
import logging

try:
    basestring  # Python 2
except NameError:
    basestring = str  # Python 3 #NOQA


__version__ = '3.3.0'


__about_spec_version__ = '3.1'

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


class Error(namedtuple('Error', ['severity', 'message'])):
    """
    An Error data with a severity and message.
    """
    def __new__(self, severity, message):
        if message:
            if isinstance(message, basestring):
                message = clean_string(message)
            else:
                message = clean_string(repr(message))

        return super(Error, self).__new__(
            Error, severity, message)

    def __repr__(self, *args, **kwargs):
        sev = severities[self.severity]
        msg = clean_string(repr(self.message))
        return 'Error(%(sev)s, %(msg)s)' % locals()


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
    CRITICAL : u'CRITICAL',
    ERROR : u'ERROR',
    WARNING : u'WARNING',
    INFO : u'INFO',
    DEBUG : u'DEBUG',
    NOTSET : u'NOTSET'
    }
