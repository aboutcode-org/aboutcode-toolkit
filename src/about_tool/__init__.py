#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2015 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

from collections import namedtuple
import logging

__version__ = '3.0.0.dev3'

__about_spec_version__ = '2.0.0.dev2'

__copyright__ = """
Copyright (c) 2013-2016 nexB Inc. All rights reserved. http://dejacode.org
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

Error = namedtuple('Error', ['severity', 'message'])

def error_repr(self):
    sev = severities[self.severity]
    msg = self.message
    return 'Error(%(sev)s, %(msg)r)' % locals()

Error.__repr__ = error_repr


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
