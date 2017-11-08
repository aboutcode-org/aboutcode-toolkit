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

from collections import OrderedDict
import unittest

from testing_utils import get_temp_dir
from testing_utils import get_test_loc

from attributecode import ERROR
from attributecode import INFO
from attributecode import CRITICAL
from attributecode import Error
from attributecode import gen


class GenTest(unittest.TestCase):
    def test_check_duplicated_columns(self):
        test_file = get_test_loc('gen/dup_keys.csv')
        expected = [Error(ERROR, u'Duplicated column name(s): copyright with copyright\nPlease correct the input and re-run.')]
        result = gen.check_duplicated_columns(test_file)
        assert expected == result

    def test_check_duplicated_columns_handles_lower_upper_case(self):
        test_file = get_test_loc('gen/dup_keys_with_diff_case.csv')
        expected = [Error(ERROR, u'Duplicated column name(s): copyright with Copyright\nPlease correct the input and re-run.')]
        result = gen.check_duplicated_columns(test_file)
        assert expected == result

    def test_check_duplicated_about_file_path(self):
        test_dict = [{'about_file_path': u'/test/test.c', u'version': u'1.03', u'name': u'test.c'},
                     {'about_file_path': u'/test/abc/', u'version': u'1.0', u'name': u'abc'},
                     {'about_file_path': u'/test/test.c', u'version': u'1.04', u'name': u'test1.c'}]
        expected = [Error(CRITICAL, u'The input has duplicated values in \'about_file_path\' field: /test/test.c')]
        result = gen.check_duplicated_about_file_path(test_dict)
        assert expected == result

    def test_load_inventory(self):
        location = get_test_loc('gen/inv.csv')
        base_dir = get_test_loc('inv')
        errors, abouts = gen.load_inventory(location, base_dir)

        expected_errors = [
            Error(INFO, u'Field custom1 is not a supported field and is ignored.')]
        assert expected_errors == errors

        expected = [u'about_resource: .\n'
                    u'name: AboutCode\n'
                    u'version: 0.11.0\n'
                    u'description: |\n'
                    u'    multi\n'
                    u'    line\n']
        result = [a.dumps(with_absent=False, with_empty=False)
                        for a in abouts]
        assert expected == result

    def test_generation_dir_endswith_space(self):
        location = get_test_loc('inventory/complex/about_file_path_dir_endswith_space.csv')
        base_dir = get_temp_dir()
        errors, _abouts = gen.generate(location, base_dir)
        expected_errors_msg = 'contains directory name ends with spaces which is not allowed. Generation skipped.'
        assert errors
        assert len(errors) == 1
        assert expected_errors_msg in errors[0].message

    def test_generation_with_no_about_resource(self):
        location = get_test_loc('gen/inv2.csv')
        base_dir = get_temp_dir()
        errors, abouts = gen.generate(location, base_dir)
        expected_dict = OrderedDict()
        expected_dict[u'.'] = None
        assert abouts[0].about_resource.value == expected_dict
        assert len(errors) == 0

    def test_generation_with_no_about_resource_reference(self):
        location = get_test_loc('gen/inv3.csv')
        base_dir = get_temp_dir()

        errors, abouts = gen.generate(location, base_dir)
        expected_dict = OrderedDict()
        expected_dict[u'test.tar.gz'] = None

        assert abouts[0].about_resource.value == expected_dict
        assert len(errors) == 1
        msg = u'The reference file'
        assert msg in errors[0].message

    def test_generate(self):
        location = get_test_loc('gen/inv.csv')
        base_dir = get_temp_dir()

        errors, abouts = gen.generate(location, base_dir)
        expected_errors = [Error(INFO, u'Field custom1 is not a supported field and is ignored.')]
        assert expected_errors == errors

        in_mem_result = [a.dumps(with_absent=False, with_empty=False)
                        for a in abouts][0]
        expected = (u'about_resource: .\n'
                    u'name: AboutCode\n'
                    u'about_resource_path: .\n'
                    u'version: 0.11.0\n'
                    u'description: |\n'
                    u'    multi\n'
                    u'    line\n')
        assert expected == in_mem_result

    def test_deduplicate(self):
        items = ['a', 'b', 'd', 'b', 'c', 'a']
        expected = ['a', 'b', 'd', 'c']
        results = gen.deduplicate(items)
        assert expected == results
