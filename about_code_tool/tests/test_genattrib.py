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

import os
import unittest


# from os.path import abspath, dirname, join

from about_code_tool import genattrib



TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
TESTDATA_DIR = os.path.join(TESTS_DIR, 'testdata')
GEN_LOCATION = os.path.join(TESTDATA_DIR, 'test_files_for_genabout')

class GenAttribTest(unittest.TestCase):
    def test_convert_dict_key_to_lower_case(self):
        test_input = [{'Directory': '/test_input/', 'file_name': 'test_input.c'}]
        expected = [{'directory': '/test_input/', 'file_name': 'test_input.c'}]
        result = genattrib.convert_dict_key_to_lower_case(test_input)
        self.assertEquals(expected, result)

    def test_check_no_about_file_existence(self):
        test_input = [{'Directory': '/test/', 'file_name': '/test.c'}]
        result = genattrib.check_about_file_existence_and_format(test_input)
        self.assertFalse(result)

    def test_check_have_about_file_existence(self):
        test_input = [{'Directory': '/test/', 'about_file': '/test.ABOUT'}]
        self.assertTrue(genattrib.check_about_file_existence_and_format(test_input) == test_input)

    def test_check_no_about_file_not_start_with_slash(self):
        test_input = [{'Directory': '/test/', 'file_name': 'test.c'}]
        self.assertFalse(genattrib.check_about_file_existence_and_format(test_input))

    def test_check_have_about_file_not_start_with_slash(self):
        test_input = [{'Directory': '/test/', 'about_file': 'test.ABOUT'}]
        expected = [{'Directory': '/test/', 'about_file': '/test.ABOUT'}]
        self.assertTrue(genattrib.check_about_file_existence_and_format(test_input) == expected)

    def test_update_path_to_about(self):
        test_input = ['/test/test1.ABOUT', '/test/test2/', 'test/test3.c']
        expected_list = ['/test/test1.ABOUT', '/test/test2/test2.ABOUT', 'test/test3.c.ABOUT']
        output = genattrib.update_path_to_about(test_input)
        self.assertTrue(expected_list == output)
