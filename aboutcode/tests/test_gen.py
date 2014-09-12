#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2014 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

from aboutcode import ERROR
from aboutcode import Error
from aboutcode import gen
from aboutcode import model

from aboutcode.tests import get_test_loc
from aboutcode.tests import get_temp_dir
from aboutcode import INFO
from aboutcode import CRITICAL
from aboutcode import WARNING
from aboutcode.tests import to_posix
import posixpath



class GenTest(unittest.TestCase):
    def test_check_duplicated_columns(self):
        test_file = get_test_loc('gen/dup_keys.csv')
        expected = [Error(ERROR, u'Duplicated column name(s): copyright with copyright')]
        result = gen.check_duplicated_columns(test_file)
        self.assertEqual(expected, result)

    def test_check_duplicated_columns_handles_lower_upper_case(self):
        test_file = get_test_loc('gen/dup_keys_with_diff_case.csv')
        expected = [Error(ERROR, u'Duplicated column name(s): copyright with Copyright')]
        result = gen.check_duplicated_columns(test_file)
        self.assertEqual(expected, result)

    def test_load_inventory(self):
        self.maxDiff = None
        location = get_test_loc('gen/inv.csv')
        base_dir = get_test_loc('inv')
        errors, abouts = gen.load_inventory(location, base_dir)
        expected_errors = [
            Error(INFO, u'Field custom1 is a custom field'),
            Error(CRITICAL, u'Field about_resource: Path . not found')]
        self.assertEqual(expected_errors, errors)

        expected = [u'about_resource: .\n'
                    u'name: AboutCode\n'
                    u'version: 0.11.0\n'
                    u'custom1: multi\n'
                    u' line\n']
        result = [a.dumps(with_absent=False, with_empty=False)
                        for a in abouts]
        self.assertEqual(expected, result)

    def test_generate(self):
        location = get_test_loc('gen/inv.csv')
        gen_dir = get_temp_dir()

        errors, abouts = gen.generate(location, 
                                      base_dir=gen_dir, 
                                      with_empty=False, with_absent=False)

        expected_errors = [Error(INFO, u'Field custom1 is a custom field')]
        self.assertEqual(expected_errors, errors)

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
        self.assertEqual(expected, on_disk_result)
        self.assertEqual(expected, in_mem_result)


    def atest_generate_complex_inventory(self):
        self.maxDiff = None
        location = get_test_loc('inventory/complex/about/expected.csv')
        gen_dir = get_temp_dir()

        errors, abouts = gen.generate(location, 
                                      base_dir=gen_dir, 
                                      with_empty=False, with_absent=False)

        expected_errors = [Error(INFO, u'Field custom1 is a custom field')]
        self.assertEqual(expected_errors, errors)

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
        self.assertEqual(expected, on_disk_result)
        self.assertEqual(expected, in_mem_result)

