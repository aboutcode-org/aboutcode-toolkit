#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2014-2016 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

from __future__ import print_function

import unittest
import posixpath

from about_code_tool import Error
from about_code_tool import ERROR
from about_code_tool import INFO
from about_code_tool import CRITICAL

from about_code_tool import gen
from about_code_tool import model

from about_code_tool.tests import to_posix
from about_code_tool.tests import get_test_loc
from about_code_tool.tests import get_temp_dir
from unittest.case import expectedFailure
from collections import OrderedDict


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

    def test_load_inventory(self):
        self.maxDiff = None
        mapping = None
        location = get_test_loc('gen/inv.csv')
        base_dir = get_test_loc('inv')
        errors, abouts = gen.load_inventory(mapping, location, base_dir)
        expected_errors = [
            Error(INFO, u'Field custom1 is a custom field'),
            Error(CRITICAL, u'Field about_resource: Path . not found')]
        assert expected_errors == errors

        expected = [u'about_resource: .\n'
                    u'name: AboutCode\n'
                    u'version: 0.11.0\n'
                    u'custom1: |\n'
                    u'    multi\n'
                    u'    line\n']
        result = [a.dumps(with_absent=False, with_empty=False)
                        for a in abouts]
        assert expected == result

    def test_generation_dir_endswith_space(self):
        mapping = None
        location = get_test_loc('inventory/complex/about_file_path_dir_endswith_space.csv')
        gen_dir = get_temp_dir()

        errors, abouts = gen.generate(mapping, location,
                                      base_dir=gen_dir,
                                      with_empty=False, with_absent=False)

        expected_errors_msg = 'contains directory name ends with spaces which is not allowed. Generation skipped.'
        assert (len(errors) == 1, 'Should return 1 error.')
        assert expected_errors_msg in errors[0].message

    def test_generation_with_no_about_resource(self):
        mapping = None
        location = get_test_loc('gen/inv2.csv')
        gen_dir = get_temp_dir()

        errors, abouts = gen.generate(mapping, location,
                                      base_dir=gen_dir,
                                      with_empty=False, with_absent=False)
        expected_dict = OrderedDict()
        expected_dict[u'.'] = None

        assert abouts[0].about_resource.value == expected_dict
        assert len(errors) == 0

    def test_generation_with_no_about_resource_reference(self):
        mapping = None
        location = get_test_loc('gen/inv3.csv')
        gen_dir = get_temp_dir()

        errors, abouts = gen.generate(mapping, location,
                                      base_dir=gen_dir,
                                      with_empty=False, with_absent=False)
        expected_dict = OrderedDict()
        expected_dict[u'test.tar.gz'] = None

        assert abouts[0].about_resource.value == expected_dict
        assert len(errors) == 1
        msg = u'The reference file'
        assert msg in errors[0].message

    @expectedFailure
    def test_generate(self):
        location = get_test_loc('gen/inv.csv')
        gen_dir = get_temp_dir()

        errors, abouts = gen.generate(location, base_dir=gen_dir,
                                      with_empty=False, with_absent=False)

        expected_errors = [Error(INFO, u'Field custom1 is a custom field')]
        assert expected_errors == errors

        gen_loc = posixpath.join(to_posix(gen_dir), 'inv', 'this.ABOUT')
        about = model.About(location=gen_loc)
        on_disk_result = about.dumps(with_absent=False, with_empty=False)
        in_mem_result = [a.dumps(with_absent=False, with_empty=False)
                        for a in abouts][0]
        expected = (u'about_resource: .\n'
                    u'name: AboutCode\n'
                    u'version: 0.11.0\n'
                    u'custom1: |\n'
                    u'    multi\n'
                    u'    line\n')
        assert expected == on_disk_result
        assert expected == in_mem_result

    @expectedFailure
    def test_generate_complex_inventory(self):
        location = get_test_loc('inventory/complex/about/expected.csv')
        gen_dir = get_temp_dir()

        errors, abouts = gen.generate(location,
                                      base_dir=gen_dir,
                                      with_empty=False, with_absent=False)

        expected_errors = [Error(INFO, u'Field custom1 is a custom field')]
        assert expected_errors == errors

        gen_loc = posixpath.join(to_posix(gen_dir), 'inv', 'this.ABOUT')
        about = model.About(location=gen_loc)
        on_disk_result = about.dumps(with_absent=False, with_empty=False)
        in_mem_result = [a.dumps(with_absent=False, with_empty=False)
                        for a in abouts][0]
        expected = (u'about_resource: .\n'
                    u'name: AboutCode\n'
                    u'version: 0.11.0\n'
                    u'custom1: multi\n'
                    u' line\n')
        assert expected == on_disk_result
        assert expected == in_mem_result
