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

import io
import unittest

from attributecode import CRITICAL
from attributecode import DEBUG
from attributecode import ERROR
from attributecode import INFO
from attributecode import NOTSET
from attributecode import WARNING
from attributecode import cmd
from attributecode import Error

from testing_utils import run_about_command_test_click
from testing_utils import get_test_loc
from testing_utils import get_temp_dir
from testing_utils import get_temp_file

# NB: the test_report_errors* tests depend on py.test stdout/err capture capabilities


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
    assert 6 == ec
    out, err = capsys.readouterr()
    expected_out = [
        'Command completed with 6 errors or warnings.',
        'CRITICAL: msg1',
        'ERROR: msg2',
        'INFO: msg3',
        'WARNING: msg4',
        'DEBUG: msg4',
        'NOTSET: msg4']
    assert '' == err
    assert expected_out == out.splitlines(False)


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
    expected_out = [
        'Command completed with 3 errors or warnings.',
        'CRITICAL: msg1',
        'ERROR: msg2',
        'WARNING: msg4',
    ]
    assert '' == err
    assert expected_out == out.splitlines(False)


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
    assert severe_errors_count == 6
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
    assert severe_errors_count == 6
    out, err = capsys.readouterr()
    expected_out = [
        'Command completed with 6 errors or warnings.',
        'CRITICAL: msg1',
        'ERROR: msg2',
        'INFO: msg3',
        'WARNING: msg4',
        'DEBUG: msg4',
        'NOTSET: msg4'
    ]
    print("@@@@@@@@@@@@@@@@@@@@@@@@")
    print(out.splitlines(False))
    assert expected_out == out.splitlines(False)
    assert '' == err


def test_report_errors_can_write_to_logfile():
    errors = [
        Error(CRITICAL, 'msg1'),
        Error(ERROR, 'msg2'),
        Error(INFO, 'msg3'),
        Error(WARNING, 'msg4'),
        Error(DEBUG, 'msg4'),
        Error(NOTSET, 'msg4'),
        Error(WARNING, 'msg4'),
    ]

    result_file = get_temp_file()
    _ec = cmd.report_errors(errors, quiet=False, verbose=True,
                           log_file_loc=result_file)
    with io.open(result_file, 'r', encoding='utf-8', errors='replace') as rf:
        result = rf.read()
    expected = [
        'Command completed with 6 errors or warnings.',
        'CRITICAL: msg1',
        'ERROR: msg2',
        'INFO: msg3',
        'WARNING: msg4',
        'DEBUG: msg4',
        'NOTSET: msg4'
    ]
    assert expected == result.splitlines(False)


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
    assert severe_errors_count == 6


def test_get_error_messages():
    errors = [
        Error(CRITICAL, 'msg1'),
        Error(ERROR, 'msg2'),
        Error(INFO, 'msg3'),
        Error(WARNING, 'msg4'),
        Error(DEBUG, 'msg4'),
        Error(NOTSET, 'msg4'),
    ]

    emsgs, ec = cmd.get_error_messages(errors)
    assert 3 == ec
    expected = [
        'Command completed with 3 errors or warnings.',
        'CRITICAL: msg1',
        'ERROR: msg2',
        'WARNING: msg4',
    ]
    assert expected == emsgs


def test_get_error_messages_verbose():
    errors = [
        Error(CRITICAL, 'msg1'),
        Error(ERROR, 'msg2'),
        Error(INFO, 'msg3'),
        Error(WARNING, 'msg4'),
        Error(DEBUG, 'msg4'),
        Error(NOTSET, 'msg4'),
    ]

    emsgs, ec = cmd.get_error_messages(errors, verbose=True)
    assert 6 == ec
    expected = [
        'Command completed with 6 errors or warnings.',
        'CRITICAL: msg1',
        'ERROR: msg2',
        'INFO: msg3',
        'WARNING: msg4',
        'DEBUG: msg4',
        'NOTSET: msg4']
    assert expected == emsgs


class TestFilterError(unittest.TestCase):

    def test_filter_errors_default(self):
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

    def test_filter_errors_with_min(self):
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

    def test_filter_errors_no_errors(self):
        errors = [
            Error(INFO, 'msg3'),
            Error(DEBUG, 'msg4'),
            Error(NOTSET, 'msg4'),
        ]
        assert [] == cmd.filter_errors(errors)

    def test_filter_errors_none(self):
        assert [] == cmd.filter_errors([])


class TestParseKeyValues(unittest.TestCase):

    def test_parse_key_values_empty(self):
        assert ({}, []) == cmd.parse_key_values([])
        assert ({}, []) == cmd.parse_key_values(None)

    def test_parse_key_values_simple(self):
        test = [
            'key=value',
            'This=THat',
            'keY=bar',
        ]
        expected = {
            'key': 'bar',
            'this': 'THat'
            }
        keyvals, errors = cmd.parse_key_values(test)
        assert expected == keyvals
        assert not errors

    def test_parse_key_values_with_errors(self):
        test = [
            'key',
            '=THat',
            'keY=',
            'FOO=bar'
        ]
        expected = {
            'foo': 'bar',
        }
        keyvals, errors = cmd.parse_key_values(test)
        assert expected == keyvals
        expected = [
            'missing <key> in "=THat".',
            'missing <value> in "keY=".',
            'missing <value> in "key".'
        ]
        assert expected == errors

###############################################################################
# Run full cli command
###############################################################################


def check_about_stdout(options, expected_loc, regen=False):
    """
    Run the about command with the `options` list of options. Assert that
    command success and that the stdout is equal to the `expected_loc` test file
    content.
    """
    result = run_about_command_test_click(options)
    if regen:
        expected_file = get_test_loc(expected_loc, must_exists=False)
        with open(expected_file, 'w') as ef:
            ef.write(result.output)

    expected_file = get_test_loc(expected_loc, must_exists=True)
    with open(expected_file, 'r') as ef:
        expected = ef.read()

    print("!!!!!!!!!!!!!!!!!!!!")
    print(expected.splitlines(False))
    print("#####################")
    print(result.output.splitlines(False))
    assert expected.splitlines(False) == result.output.splitlines(False)


def test_about_help_text():
    check_about_stdout(['--help'], 'test_cmd/help/about_help.txt', regen=False)


def test_about_inventory_help_text():
    check_about_stdout(
        ['inventory', '--help'],
        'test_cmd/help/about_inventory_help.txt', regen=False)


def test_about_gen_help_text():
    check_about_stdout(
        ['gen', '--help'],
        'test_cmd/help/about_gen_help.txt', regen=False)


def test_about_gen_license_help_text():
    check_about_stdout(
        ['gen-license', '--help'],
        'test_cmd/help/about_gen_license_help.txt', regen=False)

def test_about_check_help_text():
    check_about_stdout(
        ['check', '--help'],
        'test_cmd/help/about_check_help.txt', regen=False)


def test_about_attrib_help_text():
    check_about_stdout(
        ['attrib', '--help'],
        'test_cmd/help/about_attrib_help.txt', regen=False)


def test_about_command_fails_with_an_unknown_subcommand():
    test_dir = get_temp_dir()
    result = run_about_command_test_click(['foo', test_dir], expected_rc=2)
    assert 'Error: No such command \'foo\'.' in result.output


def test_about_inventory_command_can_run_minimally_without_error():
    test_dir = get_test_loc('test_cmd/repository-mini')
    result = get_temp_file()
    run_about_command_test_click(['inventory', test_dir, result])


def test_about_gen_command_can_run_minimally_without_error():
    test_inv = get_test_loc('test_cmd/geninventory.csv')
    gen_dir = get_temp_dir()
    run_about_command_test_click(['gen', test_inv, gen_dir])


def test_about_attrib_command_can_run_minimally_without_error():
    test_dir = get_test_loc('test_cmd/repository-mini')
    result = get_temp_file()
    run_about_command_test_click(['attrib', test_dir, result])


def test_about_transform_command_can_run_minimally_without_error():
    test_file = get_test_loc('test_cmd/transform.csv')
    result = get_temp_file('file_name.csv')
    run_about_command_test_click(['transform', test_file, result])


def test_about_transform_help_text():
    check_about_stdout(
        ['transform', '--help'],
        'test_cmd/help/about_transform_help.txt', regen=False)


def test_about_transform_expanded_help_text():
    check_about_stdout(
        ['transform', '--help-format'],
        'test_cmd/help/about_transform_config_help.txt', regen=False)
