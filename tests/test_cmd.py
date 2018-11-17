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

def test_report_errors(capsys):
    errors = [
        Error(CRITICAL, 'msg1'),
        Error(ERROR, 'msg2'),
        Error(INFO, 'msg3'),
        Error(WARNING, 'msg4'),
        Error(DEBUG, 'msg4'),
        Error(NOTSET, 'msg4'),
    ]
    ec = cmd.report_errors(errors, quiet=False, verbose=True, log_file_loc=None)
    assert 3 == ec
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


def test_report_errors_without_verbose(capsys):
    errors = [
        Error(CRITICAL, 'msg1'),
        Error(ERROR, 'msg2'),
        Error(INFO, 'msg3'),
        Error(WARNING, 'msg4'),
        Error(DEBUG, 'msg4'),
        Error(NOTSET, 'msg4'),
    ]
    ec = cmd.report_errors(errors, quiet=False, verbose=False, log_file_loc=None)
    assert 3 == ec
    out, err = capsys.readouterr()
    expected_out = '''CRITICAL: msg1
ERROR: msg2
WARNING: msg4
'''
    assert '' == err
    assert expected_out == out


def test_report_errors_does_not_report_duplicate_errors(capsys):
    errors = [
        Error(CRITICAL, 'msg1'),
        Error(ERROR, 'msg2'),
        Error(INFO, 'msg3'),
        Error(WARNING, 'msg4'),
        Error(DEBUG, 'msg4'),
        Error(NOTSET, 'msg4'),
        # dupes
        Error(WARNING, 'msg4'),
        Error(CRITICAL, 'msg1'),
    ]
    severe_errors_count = cmd.report_errors(errors, quiet=True, verbose=True)
    assert severe_errors_count == 3


def test_report_errors_with_quiet_ignores_verbose_flag(capsys):
    errors = [
        Error(CRITICAL, 'msg1'),
        Error(ERROR, 'msg2'),
        Error(INFO, 'msg3'),
        Error(WARNING, 'msg4'),
        Error(DEBUG, 'msg4'),
        Error(NOTSET, 'msg4'),
        Error(WARNING, 'msg4'),
    ]
    severe_errors_count = cmd.report_errors(errors, quiet=True, verbose=True)
    assert severe_errors_count == 3
    out, err = capsys.readouterr()
    assert '' == out
    assert '' == err


def test_report_errors_with_quiet_ignores_verbose_flag2(capsys):
    errors = [
        Error(CRITICAL, 'msg1'),
        Error(ERROR, 'msg2'),
        Error(INFO, 'msg3'),
        Error(WARNING, 'msg4'),
        Error(DEBUG, 'msg4'),
        Error(NOTSET, 'msg4'),
        Error(WARNING, 'msg4'),
    ]
    severe_errors_count = cmd.report_errors(errors, quiet=True, verbose=False)
    assert severe_errors_count == 3
    out, err = capsys.readouterr()
    assert '' == out
    assert '' == err

def test_report_errors_with_verbose_flag(capsys):
    errors = [
        Error(CRITICAL, 'msg1'),
        Error(ERROR, 'msg2'),
        Error(INFO, 'msg3'),
        Error(WARNING, 'msg4'),
        Error(DEBUG, 'msg4'),
        Error(NOTSET, 'msg4'),
        Error(WARNING, 'msg4'),
    ]
    severe_errors_count = cmd.report_errors(errors, quiet=False, verbose=True)
    assert severe_errors_count == 3
    out, err = capsys.readouterr()
    expected_out = (
'''CRITICAL: msg1
ERROR: msg2
INFO: msg3
WARNING: msg4
DEBUG: msg4
NOTSET: msg4
''')
    assert expected_out == out
    assert '' == err

def test_filter_errors_default():
    errors = [
        Error(CRITICAL, 'msg1'),
        Error(ERROR, 'msg2'),
        Error(INFO, 'msg3'),
        Error(WARNING, 'msg4'),
        Error(DEBUG, 'msg4'),
        Error(NOTSET, 'msg4'),
    ]
    expected = [
        Error(CRITICAL, 'msg1'),
        Error(ERROR, 'msg2'),
        Error(WARNING, 'msg4'),
    ]
    assert expected == cmd.filter_errors(errors)


def test_filter_errors_with_min():
    errors = [
        Error(CRITICAL, 'msg1'),
        Error(ERROR, 'msg2'),
        Error(INFO, 'msg3'),
        Error(WARNING, 'msg4'),
        Error(DEBUG, 'msg4'),
        Error(NOTSET, 'msg4'),
    ]
    expected = [
        Error(CRITICAL, 'msg1'),
    ]
    assert expected == cmd.filter_errors(errors, CRITICAL)


def test_filter_errors_no_errors():
    errors = [
        Error(INFO, 'msg3'),
        Error(DEBUG, 'msg4'),
        Error(NOTSET, 'msg4'),
    ]
    assert [] == cmd.filter_errors(errors)


def test_filter_errors_none():
    assert [] == cmd.filter_errors([])


def test_parse_key_values_empty():
    assert ({}, []) == cmd.parse_key_values([])
    assert ({}, []) == cmd.parse_key_values(None)


def test_parse_key_values_simple():
    test = [
        'key=value',
        'This=THat',
        'keY=bar',
    ]
    expected = {
        'key': ['value', 'bar'],
        'this': ['THat']
        }
    keyvals, errors = cmd.parse_key_values(test)
    assert expected == keyvals
    assert not errors


def test_parse_key_values_with_errors():
    test = [
        'key',
        '=THat',
        'keY=',
        'FOO=bar'
    ]
    expected = {
        'foo': ['bar'],
    }
    keyvals, errors = cmd.parse_key_values(test)
    assert expected == keyvals
    expected = [
        'missing <key> in "=THat".',
        'missing <value> in "keY=".',
        'missing <value> in "key".'
    ]
    assert expected == errors
