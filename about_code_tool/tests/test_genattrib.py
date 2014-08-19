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

from __future__ import print_function, with_statement # We require Python 2.6 or later

import os
import shutil
import tempfile
import unittest

from os.path import abspath, dirname, join

from about_code_tool import genattrib


TESTDATA_PATH = join(abspath(dirname(__file__)), 'testdata')
GEN_LOCATION = join(TESTDATA_PATH, 'test_files_for_genabout')

class GenAttribTest(unittest.TestCase):
    def test_convert_dict_key_to_lower_case(self):
        input_list = [{'Directory': '/test/', 'file_name': 'test.c'}]
        expected_list = [{'directory': '/test/', 'file_name': 'test.c'}]
        output = genattrib.convert_dict_key_to_lower_case(input_list)
        self.assertEquals(output, expected_list)

    def test_check_no_about_file_existance(self):
        input_list = [{'Directory': '/test/', 'file_name': '/test.c'}]
        self.assertFalse(genattrib.check_about_file_existance_and_format(input_list))

    def test_check_have_about_file_existance(self):
        input_list = [{'Directory': '/test/', 'about_file': '/test.ABOUT'}]
        self.assertTrue(genattrib.check_about_file_existance_and_format(input_list) == input_list)

    def test_check_no_about_file_not_start_with_slash(self):
        input_list = [{'Directory': '/test/', 'file_name': 'test.c'}]
        self.assertFalse(genattrib.check_about_file_existance_and_format(input_list))

    def test_check_have_about_file_not_start_with_slash(self):
        input_list = [{'Directory': '/test/', 'about_file': 'test.ABOUT'}]
        expected_list = [{'Directory': '/test/', 'about_file': '/test.ABOUT'}]
        self.assertTrue(genattrib.check_about_file_existance_and_format(input_list) == expected_list)

    def test_update_path_to_about(self):
        input_list = ['/test/test1.ABOUT', '/test/test2/', 'test/test3.c']
        expected_list = ['/test/test1.ABOUT', '/test/test2/test2.ABOUT', 'test/test3.c.ABOUT']
        output = genattrib.update_path_to_about(input_list)
        self.assertTrue(expected_list == output)



