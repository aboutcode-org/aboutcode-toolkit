#!/usr/bin/env python
# -*- coding: utf8 -*-

# =============================================================================
#  Copyright (c) 2013 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#      http://www.apache.org/licenses/LICENSE-2.0
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# =============================================================================

from __future__ import print_function
from __future__ import with_statement

import os
import unittest
from os.path import abspath, dirname, join

from about_code_tool import genabout


TESTDATA_PATH = join(abspath(dirname(__file__)), 'testdata')
GEN_LOCATION = join(TESTDATA_PATH, 'test_files_for_genabout')


class GenAboutTest(unittest.TestCase):
    def test_read_input(self):
        gen = genabout.GenAbout()
        test_input = join(TESTDATA_PATH, "test_files_for_genabout/about.csv")
        list = gen.read_input(test_input, False)
        self.assertTrue(list, "List shouldn't be empty.")

    def test_read_input_missing_about_file(self):
        gen = genabout.GenAbout()
        test_input = join(TESTDATA_PATH, "test_files_for_genabout/missing_about_file.csv")
        list = gen.read_input(test_input, False)
        self.assertTrue(len(gen.errors) == 1, "This should return only 1 error.")
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(list, "The list should be empty.")

    def test_read_input_missing_about_resource(self):
        gen = genabout.GenAbout()
        test_input = join(TESTDATA_PATH, "test_files_for_genabout/missing_about_resource.csv")
        list = gen.read_input(test_input, False)
        self.assertTrue(len(gen.errors) == 1, "This should return only 1 error.")
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(list, "The list should be empty.")

    def test_read_input_missing_about_file_and_resource(self):
        gen = genabout.GenAbout()
        test_input = join(TESTDATA_PATH, "test_files_for_genabout/missing_about_file_and_resource.csv")
        list = gen.read_input(test_input, False)
        self.assertTrue(len(gen.errors) == 1, "This should return only 1 error.")
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(list, "The list should be empty.")

    def test_read_input_valid_and_invalid_rows(self):
        gen = genabout.GenAbout()
        test_input = join(TESTDATA_PATH, "test_files_for_genabout/valid_and_invalid_rows.csv")
        list = gen.read_input(test_input, False)
        self.assertTrue(len(gen.errors) == 2, "This should return 2 errors.")
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertTrue(len(list) == 1, "The length of the list should be 1.")

    def test_read_input_with_keys_mapping(self):
        gen = genabout.GenAbout()
        test_input = join(TESTDATA_PATH, "test_files_for_genabout/about-mapping-sample.csv")
        list = gen.read_input(test_input, True)
        self.assertTrue(list, "List shouldn't be empty.")

    def test_pre_generation_about_exists_action_0(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_PATH, "test_files_for_genabout/")
        action_num = '0'
        input_list = [[{'about_file': 'about.py.ABOUT', 'version': '0.8.1',
                        'about_resource': '.', 'name': 'ABOUT tool'}]]
        expected_output_list = []
        output_list = gen.pre_generation(gen_location, input_list, action_num, False)
        self.assertTrue(expected_output_list == output_list, "This output_list should be empty.")
        self.assertTrue(len(gen.warnings) == 1, "Should return 1 warnings.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_pre_generation_about_exists_action_1(self):
        gen = genabout.GenAbout()
        action_num = '1'
        input_list = [[{'about_file': 'about.py.ABOUT', 'version': '0.8.2',
                        'about_resource': '.', 'name': ''}]]
        expected_output_list = [[join(TESTDATA_PATH, 'test_files_for_genabout/about.py.ABOUT'),
                                 {'about_file': 'about.py.ABOUT', 'version': '0.8.2',
                                  'about_resource': '.', 'name': 'ABOUT tool'}]]
        output_list = gen.pre_generation(GEN_LOCATION, input_list, action_num, False)
        self.assertTrue(expected_output_list == output_list)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_pre_generation_about_exists_action_2(self):
        gen = genabout.GenAbout()
        action_num = '2'
        input_list = [[{'about_file': 'about.py.ABOUT', 'version': '0.8.2',
                        'about_resource': '.', 'name': '', 'test': 'test sample'}]]
        expected_output_list = [[join(TESTDATA_PATH, 'test_files_for_genabout/about.py.ABOUT'),
                                  {'test': 'test sample', 'about_file': 'about.py.ABOUT',
                                    'version': '0.8.1', 'about_resource': '.',
                                     'name': 'ABOUT tool'}]]
        output_list = gen.pre_generation(GEN_LOCATION, input_list, action_num, False)
        self.assertTrue(expected_output_list == output_list)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_pre_generation_about_exists_action_3(self):
        gen = genabout.GenAbout()
        action_num = '3'
        input_list = [[{'about_file': 'about.py.ABOUT', 'version': '0.8.2',
                        'about_resource': '.', 'name': '', 'test': 'test sample'}]]
        expected_output_list = [[join(TESTDATA_PATH, 'test_files_for_genabout/about.py.ABOUT'),
                                  {'about_file': 'about.py.ABOUT', 'version': '0.8.2',
                                    'about_resource': '.', 'name': '', 'test': 'test sample'}]]
        output_list = gen.pre_generation(GEN_LOCATION, input_list, action_num, False)
        self.assertTrue(expected_output_list == output_list)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_pre_generation_all_in_one(self):
        gen = genabout.GenAbout()
        action_num = '0'
        input_list = [[{'about_file': 'test_generation/elasticsearch.ABOUT',
                         'version': '0.19.8',
                         'about_resource': 'elasticsearch-0.19.8.zip',
                         'name': 'ElasticSearch'}]]
        expected_output_list = []
        output_list = gen.pre_generation(GEN_LOCATION, input_list, action_num, True)
        self.assertFalse(os.path.exists('testdata/test_files_for_genabout/test_generation'),
                          "This directory shouldn't be generaetd as the all_in_one is set to True.")
        self.assertTrue(expected_output_list == output_list, "This output_list should be empty.")
        self.assertTrue(len(gen.warnings) == 1, "Should return 1 warning.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_format_output(self):
        gen = genabout.GenAbout()
        input_list = [
            [join(TESTDATA_PATH, 'test_files_for_genabout/about.py.ABOUT'),
             {'about_file': 'about.py.ABOUT', 'version': '0.8.1',
              'about_resource': '.', 'name': 'ABOUT Tool'}]]
        expected_output = [
            [join(TESTDATA_PATH, 'test_files_for_genabout/about.py.ABOUT'),
            'about_resource: .\nname: ABOUT Tool\nversion: 0.8.1\n\n']]
        output = gen.format_output(input_list)
        self.assertEqual(expected_output, output)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_verify_license_files_exist(self):
        gen = genabout.GenAbout()
        input_list = [[{'version': '0.8.1', 'about_file': 'about.py.ABOUT',
                         'license_text_file': 'apache2.LICENSE.txt',
                          'name': 'ABOUT tool', 'about_resource': '.'}]]
        path = '.'
        expected_list = [['apache2.LICENSE.txt']]
        output = gen.verify_license_files(input_list, path)
        self.assertEqual(expected_list, output)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_verify_license_files_not_exist(self):
        gen = genabout.GenAbout()
        input_list = [[{'version': '0.8.1', 'about_file': 'about.py.ABOUT',
                         'license_text_file': 'not_exist.LICENSE.txt',
                          'name': 'ABOUT tool', 'about_resource': '.'}]]
        path = '.'
        expected_list = []
        output = gen.verify_license_files(input_list, path)
        self.assertTrue(expected_list == output)
        self.assertTrue(len(gen.warnings) == 1, "Should return 1 warning.")
        self.assertFalse(gen.errors, "No errors should be returned.")
