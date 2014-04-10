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

from __future__ import print_function, with_statement

import os
import shutil
import tempfile
import unittest

from os.path import abspath, dirname, join

from about_code_tool import genabout


TESTDATA_PATH = join(abspath(dirname(__file__)), 'testdata')
GEN_LOCATION = join(TESTDATA_PATH, 'test_files_for_genabout')


class GenAboutTest(unittest.TestCase):
    def test_get_input_list(self):
        gen = genabout.GenAbout()
        test_input = join(TESTDATA_PATH, "test_files_for_genabout/about.csv")
        expected_list = [{'about_file': 'about.ABOUT', 'about_resource': '.',
                           'name': 'ABOUT tool', 'version': '0.8.1'}]
        list = gen.get_input_list(test_input)
        self.assertTrue(list == expected_list)

    def test_get_non_empty_rows_list(self):
        gen = genabout.GenAbout()
        input_list = [{'about_file': '/about.ABOUT', 'about_resource': '.',
                       'name': 'ABOUT tool', 'version': '0.8.1'},
                      {'about_file': '', 'about_resource': '',
                       'name': '', 'version': ''}]
        expected_list = [{'about_file': '/about.ABOUT', 'about_resource': '.',
                       'name': 'ABOUT tool', 'version': '0.8.1'}]
        output = gen.get_non_empty_rows_list(input_list)
        self.assertTrue(output == expected_list)

    
    def test_get_mapping_list(self):
        gen = genabout.GenAbout()
        expected_list = {'about_file': 'Directory/Filename',
                          'version': 'Confirmed Version',
                           'about_resource': 'file_name', 'name': 'Component'}
        output = gen.get_mapping_list()
        self.assertTrue(output == expected_list)

    def test_convert_input_list(self):
        gen = genabout.GenAbout()
        mapping_list = {'about_file': 'Directory/Filename',
                          'version': 'Confirmed Version',
                           'about_resource': 'file_name', 'name': 'Component'}
        input_list = [{'file_name': 'opensans', 'ignore field': 'i',
                       'Component': 'OpenSans Fonts', 'Confirmed Version': '1',
                       'Directory/Filename': '/extension/streamer/opensans/'}]
        expected_list = [{'about_file': '/extension/streamer/opensans/',
                          'name': 'OpenSans Fonts', 'ignore field': 'i',
                          'version': '1', 'about_resource': 'opensans'}]
        output = gen.convert_input_list(input_list, mapping_list)
        self.assertTrue(output == expected_list)

    def test_validate_value_in_essential_missing_about_file(self):
        gen = genabout.GenAbout()
        input = [{'about_file': '', 'about_resource': '.',
                       'name': 'ABOUT tool', 'version': '0.8.1'}]
        self.assertFalse(gen.validate_value_in_essential_fields(input))

    def test_validate_value_in_essential_missing_about_resource(self):
        gen = genabout.GenAbout()
        input = [{'about_file': '/about.ABOUT', 'about_resource': '',
                       'name': 'ABOUT tool', 'version': '0.8.1'}]
        self.assertFalse(gen.validate_value_in_essential_fields(input))

    def test_validate_value_in_essential_missing_all(self):
        gen = genabout.GenAbout()
        input = [{'about_file': '', 'about_resource': '',
                       'name': 'ABOUT tool', 'version': '0.8.1'}]
        self.assertFalse(gen.validate_value_in_essential_fields(input))

    def test_validate_value_in_essential_fields_no_missing(self):
        gen = genabout.GenAbout()
        input = [{'about_file': '/about.ABOUT', 'about_resource': '.',
                       'name': 'ABOUT tool', 'version': '0.8.1'}]
        self.assertTrue(gen.validate_value_in_essential_fields(input))

    def test_validate_duplication_have_dup(self):
        gen = genabout.GenAbout()
        input_list = [{'about_file': '/about.ABOUT', 'about_resource': '.',
                       'name': 'ABOUT tool', 'version': '0.8.1'},
                      {'about_file': '/about.ABOUT', 'about_resource': '.',
                       'name': 'ABOUT tool', 'version': ''}]
        self.assertTrue(gen.validate_duplication(input_list), "The list has duplication.")

    def test_validate_duplication_no_dup(self):
        gen = genabout.GenAbout()
        input_list = [{'about_file': '/about.ABOUT', 'about_resource': '.',
                       'name': 'ABOUT tool', 'version': '0.8.1'},
                      {'about_file': 'about1.ABOUT', 'about_resource': 'something',
                       'name': 'ABOUT tool', 'version': ''}]
        self.assertFalse(gen.validate_duplication(input_list), "The list has no duplication.")

    def test_validate_mandatory_fields_no_missing(self):
        gen = genabout.GenAbout()
        input_list = [{'about_file': '/about.ABOUT', 'about_resource': '.',
                       'name': 'ABOUT tool', 'version': '0.8.1'}]
        self.assertTrue(gen.validate_mandatory_fields(input_list))

    def test_validate_mandatory_fields_missing_about_file(self):
        gen = genabout.GenAbout()
        input_list = [{'about_resource': '.',
                       'name': 'ABOUT tool', 'version': '0.8.1'}]
        self.assertFalse(gen.validate_mandatory_fields(input_list))

    def test_validate_mandatory_fields_missing_about_resource(self):
        gen = genabout.GenAbout()
        input_list = [{'about_file': '/about.ABOUT', 'name': 'ABOUT tool',
                       'version': '0.8.1'}]
        self.assertFalse(gen.validate_mandatory_fields(input_list))

    def test_get_non_supported_fields(self):
        gen = genabout.GenAbout()
        input = [{'about_file': '', 'name': 'OpenSans Fonts',
                 'non_supported field': 'TEST', 'version': '1',
                 'about_resource': 'opensans'}]
        non_supported_list = gen.get_non_supported_fields(input)
        expected_list = ['non_supported field']
        self.assertTrue(non_supported_list == expected_list)

    def test_get_only_supported_fields(self):
        gen = genabout.GenAbout()
        input_list = [{'about_file': '/about.ABOUT', 'about_resource': '.',
                       'name': 'ABOUT tool', 'version': '0.8.1',
                       'non_supported': 'test'}]
        expected_list = [{'about_file': '/about.ABOUT', 'about_resource': '.',
                       'name': 'ABOUT tool', 'version': '0.8.1'}]
        ignore_key_list = ['non_supported']
        self.assertTrue(expected_list == gen.get_only_supported_fields(input_list, ignore_key_list))

    def test_get_dje_license_list_no_gen_license_with_no_license_text_file_key(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_PATH, "test_files_for_genabout/")
        input_list = [{'about_file': '/about.py.ABOUT', 'version': '0.8.1',
                        'about_resource': '.', 'name': 'ABOUT tool'}]
        expected_output_list = []
        gen_license = False
        lic_output_list = gen.get_dje_license_list(gen_location, input_list, gen_license)
        self.assertTrue(expected_output_list == lic_output_list)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_get_dje_license_list_no_gen_license_with_license_text_file_key_not_exist(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_PATH, "test_files_for_genabout/")
        input_list = [{'about_file': '/about.py.ABOUT', 'version': '0.8.1',
                        'about_resource': '.', 'name': 'ABOUT tool',
                        'license_text_file': 'not_exist.txt'}]
        expected_output_list = []
        gen_license = False
        lic_output_list = gen.get_dje_license_list(gen_location, input_list, gen_license)
        self.assertTrue(expected_output_list == lic_output_list)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertTrue(len(gen.errors) == 1, "Should return 1 error.")

    def test_get_dje_license_list_file_no_gen_license_with_license_text_file_key_exist(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_PATH, "test_files_for_genabout/")
        input_list = [{'about_file': '/about.py.ABOUT', 'version': '0.8.1',
                        'about_resource': '.', 'name': 'ABOUT tool',
                        'license_text_file': '../../../../apache2.LICENSE.txt'}]
        expected_output_list = []
        gen_license = False
        lic_output_list = gen.get_dje_license_list(gen_location, input_list, gen_license)
        self.assertTrue(expected_output_list == lic_output_list)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_get_dje_license_list_dir_no_gen_license_with_license_text_file_key_exist(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_PATH, "test_files_for_genabout/")
        input_list = [{'about_file': '/ABOUT/', 'version': '0.8.1',
                        'about_resource': '.', 'name': 'ABOUT tool',
                        'license_text_file': '../../../../apache2.LICENSE.txt'}]
        expected_output_list = []
        gen_license = False
        lic_output_list = gen.get_dje_license_list(gen_location, input_list, gen_license)
        self.assertTrue(expected_output_list == lic_output_list)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_get_dje_license_list_file_gen_license_with_license_text_file_key_exist(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_PATH, "test_files_for_genabout/")
        input_list = [{'about_file': '/about.py.ABOUT', 'version': '0.8.1',
                        'about_resource': '.', 'name': 'ABOUT tool',
                        'license_text_file': '../../../../apache2.LICENSE.txt'}]
        expected_output_list = []
        gen_license = True
        lic_output_list = gen.get_dje_license_list(gen_location, input_list, gen_license)
        self.assertTrue(expected_output_list == lic_output_list)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_get_dje_license_list_gen_license_with_dje_license_key_empty_license_text_file(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_PATH, "test_files_for_genabout/")
        input_list = [{'about_file': '/about.py.ABOUT', 'version': '0.8.1',
                        'about_resource': '.', 'name': 'ABOUT tool',
                        'license_text_file': '', 'dje_license_key': 'apache-2.0'}]
        expected_output_list = [('/', 'apache-2.0')]
        gen_license = True
        lic_output_list = gen.get_dje_license_list(gen_location, input_list, gen_license)
        self.assertTrue(expected_output_list == lic_output_list)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_get_dje_license_list_gen_license_with_empty_dje_license_key_empty_license_text_file(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_PATH, "test_files_for_genabout/")
        input_list = [{'about_file': '/about.py.ABOUT', 'version': '0.8.1',
                        'about_resource': '.', 'name': 'ABOUT tool',
                        'license_text_file': '', 'dje_license_key': ''}]
        expected_output_list = []
        gen_license = True
        lic_output_list = gen.get_dje_license_list(gen_location, input_list, gen_license)
        self.assertTrue(expected_output_list == lic_output_list)
        self.assertTrue(len(gen.warnings) == 1, "Should return 1 warning.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_get_dje_license_list_gen_license_with_dje_license_key_no_license_text_file(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_PATH, "test_files_for_genabout/")
        input_list = [{'about_file': '/about.py.ABOUT', 'version': '0.8.1',
                        'about_resource': '.', 'name': 'ABOUT tool',
                        'dje_license_key': 'apache-2.0'}]
        expected_output_list = [('/', 'apache-2.0')]
        gen_license = True
        lic_output_list = gen.get_dje_license_list(gen_location, input_list, gen_license)
        self.assertTrue(expected_output_list == lic_output_list)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_pre_generation_about_is_dir_exists_action_0(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_PATH, "test_files_for_genabout/")
        action_num = 0
        input_list = [{'about_file': '/TESTCASE/', 'version': '0.8.1',
                        'about_resource': '.', 'name': 'ABOUT tool'}]
        expected_output_list = [[join(TESTDATA_PATH, 'test_files_for_genabout/TESTCASE.ABOUT'),
                                 {'about_file': '/TESTCASE/', 'version': '0.8.1',
                                  'about_resource': '.', 'name': 'ABOUT tool'}]]
        output_list = gen.pre_generation(gen_location, input_list, action_num, False)
        self.assertTrue(expected_output_list == output_list, "This output_list should be empty.")
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_pre_generation_about_exists_action_0(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_PATH, "test_files_for_genabout/")
        action_num = 0
        input_list = [{'about_file': '/about.py.ABOUT', 'version': '0.8.1',
                        'about_resource': '.', 'name': 'ABOUT tool'}]
        expected_output_list = []
        output_list = gen.pre_generation(gen_location, input_list, action_num, False)
        self.assertTrue(expected_output_list == output_list, "This output_list should be empty.")
        self.assertTrue(len(gen.warnings) == 1, "Should return 1 warnings.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_pre_generation_about_exists_action_1(self):
        gen = genabout.GenAbout()
        action_num = 1
        input_list = [{'about_file': '/about.py.ABOUT', 'version': '0.8.2',
                        'about_resource': '.', 'name': ''}]
        expected_output_list = [[join(TESTDATA_PATH, 'test_files_for_genabout/about.py.ABOUT'),
                                 {'about_file': '/about.py.ABOUT', 'version': '0.8.2',
                                  'about_resource': '.', 'name': 'ABOUT tool'}]]
        output_list = gen.pre_generation(GEN_LOCATION, input_list, action_num, False)
        self.assertTrue(expected_output_list == output_list)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_pre_generation_about_exists_action_2(self):
        gen = genabout.GenAbout()
        action_num = 2
        input_list = [{'about_file': '/about.py.ABOUT', 'version': '0.8.2',
                        'about_resource': '.', 'name': '', 'test': 'test sample'}]
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
        action_num = 3
        input_list = [{'about_file': '/about.py.ABOUT', 'version': '0.8.2',
                        'about_resource': '.', 'name': '', 'test': 'test sample'}]
        expected_output_list = [[join(TESTDATA_PATH, 'test_files_for_genabout/about.py.ABOUT'),
                                  {'about_file': '/about.py.ABOUT', 'version': '0.8.2',
                                    'about_resource': '.', 'name': '', 'test': 'test sample'}]]
        output_list = gen.pre_generation(GEN_LOCATION, input_list, action_num, False)
        self.assertTrue(expected_output_list == output_list)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_pre_generation_all_in_one(self):
        gen = genabout.GenAbout()
        action_num = 0
        input_list = [{'about_file': 'test_generation/elasticsearch.ABOUT',
                         'version': '0.19.8',
                         'about_resource': 'elasticsearch-0.19.8.zip',
                         'name': 'ElasticSearch'}]
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
             {'about_file': '/about.py.ABOUT', 'version': '0.8.1',
              'about_resource': '.', 'name': 'ABOUT Tool'}]]
        expected_output = [
            [join(TESTDATA_PATH, 'test_files_for_genabout/about.py.ABOUT'),
            'about_resource: .\nname: ABOUT Tool\nversion: 0.8.1\n\n']]
        output = gen.format_output(input_list)
        self.assertEqual(expected_output, output)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_format_output_with_continuation(self):
        gen = genabout.GenAbout()
        input_list = [
            [join(TESTDATA_PATH, 'test_files_for_genabout/about.py.ABOUT'),
             {'about_file': '/about.py.ABOUT', 'version': '0.8.1',
              'about_resource': '.', 'name': 'ABOUT Tool',
              'readme': 'This is a readme test with \nline continuation.'}]]
        expected_output = [
            [join(TESTDATA_PATH, 'test_files_for_genabout/about.py.ABOUT'),
            'about_resource: .\nname: ABOUT Tool\nversion: 0.8.1\n\nreadme: This is a readme test with \n line continuation.\n']]
        output = gen.format_output(input_list)
        self.assertEqual(expected_output, output)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_verify_license_files_exist(self):
        gen = genabout.GenAbout()
        input_list = [{'version': '0.8.1', 'about_file': '/TESTCASE/',
                         'license_text_file': 'apache2.LICENSE.txt',
                          'name': 'ABOUT tool', 'about_resource': '.'}]
        path = '.'
        expected_list = [('./apache2.LICENSE.txt', '')]
        output = gen.verify_license_files(input_list, path, False)
        self.assertEqual(expected_list, output)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_verify_license_files_exist_license_in_project(self):
        gen = genabout.GenAbout()
        input_list = [{'version': '0.8.1', 'about_file': '/TESTCASE/',
                         'license_text_file': 'apache2.LICENSE.txt',
                          'name': 'ABOUT tool', 'about_resource': '.'}]
        path = '.'
        expected_list = [('./apache2.LICENSE.txt', '')]
        output = gen.verify_license_files(input_list, path, True)
        self.assertEqual(expected_list, output)
        self.assertFalse(gen.warnings, "No warnings should be returned.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_verify_license_files_not_exist(self):
        gen = genabout.GenAbout()
        input_list = [{'version': '0.8.1', 'about_file': '/about.py.ABOUT',
                         'license_text_file': 'not_exist.LICENSE.txt',
                          'name': 'ABOUT tool', 'about_resource': '.'}]
        path = '.'
        expected_list = []
        output = gen.verify_license_files(input_list, path, False)
        self.assertTrue(expected_list == output)
        self.assertTrue(len(gen.warnings) == 1, "Should return 1 warning.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_verify_license_files_not_exist_license_in_project(self):
        gen = genabout.GenAbout()
        input_list = [{'version': '0.8.1', 'about_file': '/TESTCASE/',
                         'license_text_file': 'not_exist.LICENSE.txt',
                          'name': 'ABOUT tool', 'about_resource': '.'}]
        path = '.'
        expected_list = []
        output = gen.verify_license_files(input_list, path, False)
        self.assertTrue(expected_list == output)
        self.assertTrue(len(gen.warnings) == 1, "Should return 1 warning.")
        self.assertFalse(gen.errors, "No errors should be returned.")

    def test_verify_license_files_no_key(self):
        gen = genabout.GenAbout()
        input_list = [{'version': '0.8.1', 'about_file': '/about.py.ABOUT',
                          'name': 'ABOUT tool', 'about_resource': '.'}]
        path = '.'
        self.assertRaises(Exception, gen.verify_license_files, input_list, path)

    def test_gen_license_list_license_text_file_no_value(self):
        gen = genabout.GenAbout()
        input_list = {'about_file': '/tmp/3pp/opensans/', 'name': 'OpenSans Fonts',
                       'version': '1', 'dje_license_key': 'apache-2.0',
                       'license_text_file': '', 'about_resource': 'opensans'}
        expected_list = ('/tmp/3pp', 'apache-2.0')
        output = gen.gen_license_list(input_list)
        self.assertTrue(expected_list == output)
        self.assertTrue(input_list['license_text_file'] == 'apache-2.0.LICENSE')

    def test_gen_license_list_no_license_text_file_key(self):
        gen = genabout.GenAbout()
        input_list = {'about_file': '/tmp/3pp/opensans/', 'name': 'OpenSans Fonts',
                       'version': '1', 'dje_license_key': 'apache-2.0',
                       'about_resource': 'opensans'}
        expected_list = ('/tmp/3pp', 'apache-2.0')
        output = gen.gen_license_list(input_list)
        self.assertTrue(expected_list == output)
        self.assertTrue(input_list['license_text_file'] == 'apache-2.0.LICENSE')

    def test_copy_license_files_test_path_not_endswith_slash(self):
        gen = genabout.GenAbout()
        input_list = [('apache2.LICENSE.txt', '.')]
        expected_list = ['apache2.LICENSE.txt']
        project_path = os.path.abspath('.')
        tmp_path = tempfile.mkdtemp()
        gen.copy_license_files(tmp_path, input_list)
        self.assertTrue(expected_list == os.listdir(tmp_path))
        # According to the doc, the user of mkdtemp() is responsible for
        # deleting the temporary directory and its contents when done with it.
        shutil.rmtree(tmp_path)

    def test_copy_license_files_test_path_endswith_slash(self):
        gen = genabout.GenAbout()
        input_list = [('apache2.LICENSE.txt', '.')]
        expected_list = ['apache2.LICENSE.txt']
        project_path = os.path.abspath('.')
        tmp_path = tempfile.mkdtemp() + '/'
        gen.copy_license_files(tmp_path, input_list)
        self.assertTrue(expected_list == os.listdir(tmp_path))
        # According to the doc, the user of mkdtemp() is responsible for
        # deleting the temporary directory and its contents when done with it.
        shutil.rmtree(tmp_path)

    def test_write_licenses(self):
        gen = genabout.GenAbout()
        tmp_license = tempfile.NamedTemporaryFile(suffix='.LICENSE', delete=True)
        tmp_license_context = 'This is a test.'
        input_list = [[tmp_license.name, tmp_license_context]]
        gen.write_licenses(input_list)
        self.assertTrue(os.path.exists(tmp_license.name))
        with open(tmp_license.name, "rU") as file_in:
            context = ''
            for line in file_in.readlines():
                context = line
        self.assertTrue(context == tmp_license_context)

