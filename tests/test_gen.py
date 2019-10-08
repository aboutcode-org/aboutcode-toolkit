#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2014-2019 nexB Inc. http://www.nexb.com/ - All rights reserved.
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
import unittest

from testing_utils import get_temp_dir
from testing_utils import get_test_loc

from attributecode import ERROR
from attributecode import INFO
from attributecode import CRITICAL
from attributecode import Error
from attributecode import gen
from unittest.case import skip


class GenTest(unittest.TestCase):
    def test_check_duplicated_columns(self):
        test_file = get_test_loc('test_gen/dup_keys.csv')
        expected = [Error(ERROR, 'Duplicated column name(s): copyright with copyright\nPlease correct the input and re-run.')]
        result = gen.check_duplicated_columns(test_file)
        assert expected == result

    def test_check_duplicated_columns_handles_lower_upper_case(self):
        test_file = get_test_loc('test_gen/dup_keys_with_diff_case.csv')
        expected = [Error(ERROR, 'Duplicated column name(s): copyright with Copyright\nPlease correct the input and re-run.')]
        result = gen.check_duplicated_columns(test_file)
        assert expected == result

    def test_check_duplicated_about_resource(self):
        test_dict = [
            {'about_resource': '/test/test.c', 'version': '1.03', 'name': 'test.c'},
            {'about_resource': '/test/abc/', 'version': '1.0', 'name': 'abc'},
            {'about_resource': '/test/test.c', 'version': '1.04', 'name': 'test1.c'}]
        expected = [
            Error(CRITICAL,
                  "The input has duplicated values in 'about_resource' field: /test/test.c")]
        result = gen.check_duplicated_about_resource(test_dict)
        assert expected == result

    def test_check_newline_in_file_field(self):
        test_dict = [
            {'about_resource': '/test/test.c', 'name': 'test.c', 'notice_file': 'NOTICE\nNOTICE2'},
            {'about_resource': '/test/abc/', 'version': '1.0', 'name': 'abc'},
            {'about_resource': '/test/test.c', 'version': '1.04', 'name': 'test1.c'}]
        expected = [
            Error(CRITICAL,
                  "New line character detected in 'notice_file' for '/test/test.c' which is not supported."
                  "\nPlease use ',' to declare multiple files.")]
        result = gen.check_newline_in_file_field(test_dict)
        assert expected == result

    def test_load_inventory(self):
        location = get_test_loc('test_gen/inv.csv')
        base_dir = get_temp_dir()
        errors, abouts = gen.load_inventory(location, base_dir)

        expected_errors = [
            Error(INFO, 'Field custom1 is a custom field.'),
            Error(INFO, 'Field about_resource: Path')
        ]
        for exp, err in zip(expected_errors, errors):
            assert exp.severity == err.severity
            assert err.message.startswith(exp.message)

        expected = (
'''about_resource: .
name: AboutCode
version: 0.11.0
description: |
  multi
  line
custom1: |
  multi
  line
'''
        )
        result = [a.dumps() for a in abouts]
        assert expected == result[0]

    def test_load_inventory_with_errors(self):
        location = get_test_loc('test_gen/inv4.csv')
        base_dir = get_temp_dir()
        errors, abouts = gen.load_inventory(location, base_dir)

        expected_errors = [
            Error(CRITICAL, "Field name: 'confirmed copyright' contains illegal name characters: 0 to 9, a to z, A to Z and _."),
            Error(INFO, 'Field resource is a custom field.'),
            Error(INFO, 'Field test is a custom field.'),
            Error(INFO, 'Field about_resource: Path')
        ]
        # assert [] == errors
        for exp, err in zip(expected_errors, errors):
            assert exp.severity == err.severity
            assert err.message.startswith(exp.message)

        expected = (
            'about_resource: .\n'
            'name: AboutCode\n'
            'version: 0.11.0\n'
            'description: |\n'
            '  multi\n'
            '  line\n'
            # 'confirmed copyright: Copyright (c) nexB, Inc.\n'
            'resource: this.ABOUT\n'
            'test: This is a test\n'
        )
        result = [a.dumps() for a in abouts]
        assert expected == result[0]

    def test_generation_dir_endswith_space(self):
        location = get_test_loc('test_gen/inventory/complex/about_file_path_dir_endswith_space.csv')
        base_dir = get_temp_dir()
        errors, _abouts = gen.generate(location, base_dir)
        expected_errors_msg1 = 'contains directory name ends with spaces which is not allowed. Generation skipped.'
        expected_errors_msg2 = 'Field about_resource'
        assert errors
        assert len(errors) == 2
        assert expected_errors_msg1 in errors[0].message or expected_errors_msg1 in errors[1].message
        assert expected_errors_msg2 in errors[0].message or expected_errors_msg2 in errors[1].message

    def test_generation_with_no_about_resource(self):
        location = get_test_loc('test_gen/inv2.csv')
        base_dir = get_temp_dir()
        errors, abouts = gen.generate(location, base_dir)
        expected = OrderedDict([('.', None)])
        assert abouts[0].about_resource.value == expected
        assert len(errors) == 1

    def test_generation_with_no_about_resource_reference(self):
        location = get_test_loc('test_gen/inv3.csv')
        base_dir = get_temp_dir()

        errors, abouts = gen.generate(location, base_dir)
        expected = OrderedDict([('test.tar.gz', None)])

        assert abouts[0].about_resource.value == expected
        assert len(errors) == 1
        msg = 'Field about_resource'
        assert msg in errors[0].message

    def test_generation_with_no_about_resource_reference_no_resource_validation(self):
        location = get_test_loc('test_gen/inv3.csv')
        base_dir = get_temp_dir()

        errors, abouts = gen.generate(location, base_dir)
        expected = OrderedDict([('test.tar.gz', None)])

        assert abouts[0].about_resource.value == expected
        assert len(errors) == 1

    def test_generate(self):
        location = get_test_loc('test_gen/inv.csv')
        base_dir = get_temp_dir()

        errors, abouts = gen.generate(location, base_dir)
        msg1 = 'Field custom1 is a custom field.'
        msg2 = 'Field about_resource'

        assert msg1 in errors[0].message
        assert msg2 in errors[1].message

        result = [a.dumps() for a in abouts][0]
        expected = (
'''about_resource: .
name: AboutCode
version: 0.11.0
description: |
  multi
  line
custom1: |
  multi
  line
'''
        )
        assert expected == result

    @skip('FIXME: this test is making a failed, live API call')
    def test_generate_not_overwrite_original_license_file(self):
        location = get_test_loc('test_gen/inv5.csv')
        base_dir = get_temp_dir()
        reference_dir = None
        fetch_license = ['url', 'lic_key']

        _errors, abouts = gen.generate(
            location, base_dir, reference_dir, fetch_license)

        result = [a.dumps()for a in abouts][0]
        expected = (
            'about_resource: .\n'
            'name: AboutCode\n'
            'version: 0.11.0\n'
            'licenses:\n'
            '    -   file: this.LICENSE\n')
        assert expected == result

    def test_boolean_value_not_lost(self):
        location = get_test_loc('test_gen/inv6.csv')
        base_dir = get_temp_dir()

        _errors, abouts = gen.generate(location, base_dir)

        in_mem_result = [a.dumps() for a in abouts][0]
        expected = (u'about_resource: .\n'
                    u'name: AboutCode\n'
                    u'version: 0.11.0\n'
                    u'redistribute: yes\n'
                    u'attribute: yes\n'
                    u'modified: no\n')
        assert expected == in_mem_result