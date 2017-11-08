#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2014-2017 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

from attributecode import CRITICAL
from attributecode import DEBUG
from attributecode import ERROR
from attributecode import INFO
from attributecode import NOTSET
from attributecode import WARNING
from attributecode import cmd
from attributecode import Error


# NB: these tests depends on py.test stdout/err capture capabilities
def test_log_errors(capsys):
    quiet = False
    errors = [Error(CRITICAL, 'msg1'),
              Error(ERROR, 'msg2'),
              Error(INFO, 'msg3'),
              Error(WARNING, 'msg4'),
              Error(DEBUG, 'msg4'),
              Error(NOTSET, 'msg4'),
              ]
    cmd.log_errors(errors, quiet, base_dir='')
    out, err = capsys.readouterr()
    expected_out = '''CRITICAL: msg1
ERROR: msg2
INFO: msg3
WARNING: msg4
DEBUG: msg4
NOTSET: msg4
'''
    assert '' == err
    assert expected_out == out


def test_log_errors_with_quiet(capsys):
    quiet = True
    errors = [Error(CRITICAL, 'msg1'),
              Error(ERROR, 'msg2'),
              Error(INFO, 'msg3'),
              Error(WARNING, 'msg4'),
              Error(DEBUG, 'msg4'),
              Error(NOTSET, 'msg4'),
              ]
    cmd.log_errors(errors, quiet, base_dir='')
    out, err = capsys.readouterr()
    assert '' == out
    assert '' == err    