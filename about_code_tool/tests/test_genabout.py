#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2016 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

from os.path import abspath
from os.path import dirname
from os.path import join

from about_code_tool import genabout
from about_code_tool.tests.tstutil import get_temp_dir
from about_code_tool.tests import test_about


TESTDATA_DIR = join(abspath(dirname(__file__)), 'testdata')
GEN_LOCATION = join(TESTDATA_DIR, 'test_files_for_genabout')


class GenAboutTest(unittest.TestCase):
    def test_load_data_from_csv(self):
        test_file = join(TESTDATA_DIR, 'test_files_for_genabout/about.csv')
        expected = [
            {
             'about_file': 'about.ABOUT',
             'about_resource': '.',
             'name': 'ABOUT tool',
             'version': '0.8.1'
             }
        ]
        result = genabout.load_data_from_csv(test_file)
        self.assertEqual(expected, result)

    def test_load_data_from_csv_with_trailing_spaces(self):
        test_file = join(TESTDATA_DIR, 'test_files_for_genabout/about_with_trailling_spaces.csv')
        expected = [{'about_file': 'about.c',
                     'about_resource': '.',
                     'name': 'ABOUT tool',
                     'version': '0.8.1'}]
        result = genabout.load_data_from_csv(test_file)
        self.assertEqual(expected, result)

    def test_load_data_from_csv_does_converts_all_keys_to_lower(self):
        test_input = join(TESTDATA_DIR, 'test_files_for_genabout/about_key_with_upper_case.csv')
        expected = [{'about_file': 'about.ABOUT',
                     'about_resource': '.',
                     'name': 'ABOUT tool',
                     'version': '0.8.1'}]
        result = genabout.load_data_from_csv(test_input)
        self.assertEqual(expected, result)

    def test_filter_dicts_of_empty_values(self):
        test_abouts = [
            {'about_file': '/about.ABOUT',
             'about_resource': '.',
             'name': 'ABOUT tool',
             'version': '0.8.1'},
            {'about_file': '',
             'about_resource': '',
             'name': '',
             'version': ''}
        ]

        expected = [{'about_file': '/about.ABOUT',
                     'about_resource': '.',
                     'name': 'ABOUT tool',
                     'version': '0.8.1'}]

        result = genabout.filter_dicts_of_empty_values(test_abouts)
        self.assertEqual(expected, result)

    def test_filter_dicts_of_empty_values_does_not_filter_data_with_value(self):
        test_abouts = [{'asaszname': '', 'version': '1'}]
        result = genabout.filter_dicts_of_empty_values(test_abouts)
        self.assertEqual(test_abouts, result)

    def test_filter_dicts_of_empty_values_does_filter_data_with_empty_string_values(self):
        test_abouts = [{'asaszname': '', 'version': ''}]
        result = genabout.filter_dicts_of_empty_values(test_abouts)
        self.assertEqual([], result)

    def test_filter_dicts_of_empty_values_does_filter_data_with_space_only_values(self):
        test_abouts = [{'asaszname': ' ', 'version': ' '}]
        result = genabout.filter_dicts_of_empty_values(test_abouts)
        self.assertEqual([], result)

    def test_validate_value_in_essential_missing_about_file(self):
        gen = genabout.GenAbout()
        test_fields = [{'about_file': '',
                        'about_resource': '.',
                        'name': 'ABOUT tool',
                        'version': '0.8.1'}]

        result = gen.validate_value_in_essential_fields(test_fields)
        self.assertFalse(result)

    def test_validate_value_in_essential_missing_about_resource(self):
        gen = genabout.GenAbout()
        test_fields = [{'about_file': '/about.ABOUT',
                        'about_resource': '',
                        'name': 'ABOUT tool',
                        'version': '0.8.1'}]

        result = gen.validate_value_in_essential_fields(test_fields)
        self.assertTrue(result)

    def test_validate_value_in_essential_missing_all(self):
        gen = genabout.GenAbout()
        test_fields = [{'about_file': '',
                        'about_resource': '',
                        'name': 'ABOUT tool',
                        'version': '0.8.1'}]

        result = gen.validate_value_in_essential_fields(test_fields)
        self.assertFalse(result)

    def test_validate_value_in_essential_fields_no_missing(self):
        gen = genabout.GenAbout()
        test_fields = [{'about_file':
                        '/about.ABOUT',
                        'about_resource': '.',
                        'name': 'ABOUT tool',
                        'version': '0.8.1'}]
        self.assertTrue(gen.validate_value_in_essential_fields(test_fields))

    def test_has_duplicate_about_file_paths_with_duplicates(self):
        test_fields = [{'about_file': '/about.ABOUT',
                       'about_resource': '.',
                       'name': 'ABOUT tool', 'version': '0.8.1'},
                      {'about_file': '/about.ABOUT',
                       'about_resource': '.',
                       'name': 'ABOUT tool',
                       'version': ''}]

        result = genabout.has_duplicate_about_file_paths(test_fields)
        self.assertTrue(result)

    def test_has_duplicate_about_file_paths_with_no_duplicates(self):
        test_fields = [{'about_file': '/about.ABOUT',
                       'about_resource': '.',
                       'name': 'ABOUT tool',
                       'version': '0.8.1'},
                      {'about_file': 'about1.ABOUT',
                       'about_resource': 'something',
                       'name': 'ABOUT tool',
                       'version': ''}]

        result = genabout.has_duplicate_about_file_paths(test_fields)
        self.assertFalse(result)

    def test_get_duplicated_keys_have_dup(self):
        gen = genabout.GenAbout()
        test_file = join(TESTDATA_DIR, 'test_files_for_genabout/dup_keys.csv')
        expected = ['copyright', 'copyright']
        result = gen.get_duplicated_keys(test_file)
        self.assertEqual(expected, result)

    def test_get_duplicated_keys_have_dup_diff_case(self):
        gen = genabout.GenAbout()
        test_file = join(TESTDATA_DIR, 'test_files_for_genabout/dup_keys_with_diff_case.csv')

        expected = ['copyright', 'Copyright']
        result = gen.get_duplicated_keys(test_file)
        self.assertEqual(expected, result)

    def test_validate_mandatory_fields_no_missing(self):
        gen = genabout.GenAbout()
        test_fields = [{'about_file': '/about.ABOUT',
                        'about_resource': '.',
                        'name': 'ABOUT tool',
                        'version': '0.8.1'}]
        result = gen.validate_mandatory_fields(test_fields)
        self.assertTrue(result)

    def test_validate_mandatory_fields_missing_about_file(self):
        gen = genabout.GenAbout()
        test_fields = [{'about_resource': '.',
                        'name': 'ABOUT tool',
                        'version': '0.8.1'}]
        result = gen.validate_mandatory_fields(test_fields)
        self.assertFalse(result)

    def test_validate_mandatory_fields_missing_about_resource(self):
        gen = genabout.GenAbout()
        test_fields = [{'about_file': '/about.ABOUT',
                        'name': 'ABOUT tool',
                        'version': '0.8.1'}]
        result = gen.validate_mandatory_fields(test_fields)
        self.assertTrue(result)

    def test_get_unknown_fields_with_no_user_keys(self):
        test_abouts = [{'about_file': '',
                        'name': 'OpenSans Fonts',
                        'non_supported field': 'TEST',
                        'version': '1',
                        'about_resource': 'opensans'}]
        user_keys = []
        result = genabout.get_unknown_fields(test_abouts, user_keys)
        expected = ['non_supported field']
        self.assertEqual(expected, result)

    def test_get_unknown_fields__with_user_keys(self):
        test_fields = [{'about_file': '',
                        'name': 'OpenSans Fonts',
                        'non_supported field': 'TEST',
                        'version': '1',
                        'about_resource': 'opensans'}]

        user_keys = ['non_supported field']
        result = genabout.get_unknown_fields(test_fields, user_keys)
        expected = []
        self.assertEqual(expected, result)

    def test_get_only_supported_fields(self):
        gen = genabout.GenAbout()
        test_fields = [{'about_file': '/about.ABOUT',
                        'about_resource': '.',
                        'name': 'ABOUT tool',
                        'version': '0.8.1',
                        'non_supported': 'test'}]

        expected = [{'about_file': '/about.ABOUT',
                     'about_resource': '.',
                     'name': 'ABOUT tool',
                     'version': '0.8.1'}]

        results = gen.get_only_supported_fields(test_fields, ['non_supported'])
        self.assertEqual(expected, results)

    def test_get_dje_license_list_no_gen_license_with_no_license_text_file(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_DIR, 'test_files_for_genabout/')

        test_fields = [{'about_file': '/about.py.ABOUT',
                        'version': '0.8.1',
                        'about_resource': '.',
                        'name': 'ABOUT tool'}]

        gen_license = False
        dje_license_dict = {}
        lic_output_list = gen.get_dje_license_list(gen_location,
                                                   test_fields,
                                                   gen_license,
                                                   dje_license_dict)
        expected = []
        self.assertEqual(expected, lic_output_list)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_get_dje_license_list_no_gen_license_with_license_text_file_key_not_exist(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_DIR, 'test_files_for_genabout/')

        test_fields = [{'about_file': '/about.py.ABOUT',
                        'version': '0.8.1',
                        'about_resource': '.',
                        'name': 'ABOUT tool',
                        'license_text_file': 'not_exist.txt'}]
        expected = []
        gen_license = False
        dje_license_dict = {}
        result = gen.get_dje_license_list(gen_location,
                                          test_fields,
                                          gen_license,
                                          dje_license_dict)
        self.assertEqual(expected, result)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertEqual(1, len(gen.errors))

    def test_get_dje_license_list_file_no_gen_license_with_license_text_file_key_exist(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_DIR, 'test_files_for_genabout/')
        test_fields = [{'about_file': '/about.py.ABOUT',
                        'version': '0.8.1',
                        'about_resource': '.',
                        'name': 'ABOUT tool',
                        'license_text_file': 'apache-2.0.LICENSE'}]
        result = gen.get_dje_license_list(gen_location=gen_location,
                                          input_list=test_fields,
                                          gen_license=False,
                                          dje_license_dict={})
        expected = []
        self.assertEqual(expected, result)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_get_dje_license_list_dir_no_gen_license_with_license_text_file_key_exist(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_DIR, 'test_files_for_genabout/')
        test_fields = [{'about_file': '/ABOUT/',
                        'version': '0.8.1',
                        'about_resource': '.',
                        'name': 'ABOUT tool',
                        'license_text_file':
                            '../apache-2.0.LICENSE'}]
        expected = []
        result = gen.get_dje_license_list(gen_location,
                                                   test_fields,
                                                   gen_license=False,
                                                   dje_license_dict={})
        self.assertEqual(expected, result)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_get_dje_license_list_file_gen_license_with_license_text_file_key_exist(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_DIR, 'test_files_for_genabout/')
        test_fields = [{'about_file': '/about.py.ABOUT',
                        'version': '0.8.1',
                        'about_resource': '.',
                        'name': 'ABOUT tool',
                        'dje_license': 'Apache License 2.0',
                        'license_text_file': '../../../../apache-2.0.LICENSE'}]
        gen_license = True
        dje_license_dict = {'Apache License 2.0': [u'apache-2.0',
                                                   'test context']}
        lic_output_list = gen.get_dje_license_list(gen_location,
                                                   test_fields,
                                                   gen_license,
                                                   dje_license_dict)
        expected = []
        self.assertEqual(expected, lic_output_list)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_get_dje_license_list_gen_license_with_dje_license_key_empty_license_text_file(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_DIR, 'test_files_for_genabout/')
        test_fields = [{'about_file': '/about.py.ABOUT',
                        'version': '0.8.1',
                        'about_resource': '.',
                        'name': 'ABOUT tool',
                        'dje_license_key': 'apache-2.0',
                        'dje_license_name': 'Apache License 2.0',
                        'license_text_file': ''}]
        gen_license = True
        dje_license_dict = {'Apache License 2.0': [u'apache-2.0',
                                                   'test context']}
        result = gen.get_dje_license_list(gen_location,
                                          test_fields,
                                          gen_license,
                                          dje_license_dict)

        self.assertEqual(test_fields[0]['license_text_file'],
                         'apache-2.0.LICENSE')

        expected = [('/', 'Apache License 2.0')]
        self.assertEqual(expected, result)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_get_dje_license_list_gen_license_with_empty_dje_license_key_empty_license_text_file(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_DIR, 'test_files_for_genabout/')
        test_fields = [{'about_file': '/about.py.ABOUT',
                        'version': '0.8.1',
                        'about_resource': '.',
                        'name': 'ABOUT tool',
                        'license_text_file': '',
                        'dje_license_key': ''}]
        gen_license = True
        dje_license_dict = {'Apache License 2.0': [u'apache-2.0',
                                                   'test context']}
        result = gen.get_dje_license_list(gen_location,
                                          test_fields,
                                          gen_license,
                                          dje_license_dict)

        expected = []
        self.assertEqual(expected, result)
        self.assertTrue(len(gen.warnings) == 1, 'Should return 1 warning.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_get_dje_license_list_gen_license_with_dje_license_key_no_license_text_file(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_DIR, 'test_files_for_genabout/')

        test_fields = [{'about_file': '/about.py.ABOUT',
                        'version': '0.8.1',
                        'about_resource': '.',
                        'name': 'ABOUT tool',
                        'dje_license_name': 'Apache License 2.0',
                        'dje_license_key': 'apache-2.0'}]

        expected = [('/', 'Apache License 2.0')]
        gen_license = True
        dje_license_dict = {'Apache License 2.0': [u'apache-2.0',
                                                   'test context']}
        result = gen.get_dje_license_list(gen_location,
                                          test_fields,
                                          gen_license,
                                          dje_license_dict)
        for line in test_fields:
            self.assertEqual(line['license_text_file'], 'apache-2.0.LICENSE')
        self.assertEqual(expected, result)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_pre_generation_about_is_dir_exists_action_0(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_DIR, 'test_files_for_genabout/')
        test_fields = [{'about_file': '/TESTCASE/',
                        'version': '0.8.1',
                        'about_resource': '.',
                        'name': 'ABOUT tool'}]

        expected = [[join(TESTDATA_DIR, 'test_files_for_genabout/TESTCASE',
                          'TESTCASE.ABOUT'),
                     {'about_file': '/TESTCASE/',
                      'version': '0.8.1',
                      'about_resource': '.',
                      'name': 'ABOUT tool'}]]

        result = gen.pre_generation(gen_location,
                                         test_fields,
                                         action_num=0)
        self.assertEqual(expected, result)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_pre_generation_about_exists_action_0(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_DIR, 'test_files_for_genabout/')
        test_fields = [{'about_file': '/about.py.ABOUT',
                        'version': '0.8.1',
                        'about_resource': '.',
                        'name': 'ABOUT tool'}]
        expected = []
        result = gen.pre_generation(gen_location,
                                         test_fields,
                                         action_num=0)
        self.assertEqual(expected, result)
        self.assertTrue(len(gen.warnings) == 1, 'Should return 1 warnings.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_pre_generation_about_exists_action_1(self):
        gen = genabout.GenAbout()
        test_fields = [{'about_file': '/about.py.ABOUT',
                        'version': '0.8.2',
                        'about_resource': '.',
                        'name': ''}]

        expected = [[join(TESTDATA_DIR, 'test_files_for_genabout',
                          'about.py.ABOUT'),
                     {'about_file': '/about.py.ABOUT',
                      'version': '0.8.2',
                      'about_resource': '.',
                      'name': 'ABOUT tool'}]]

        result = gen.pre_generation(GEN_LOCATION, test_fields,
                                    action_num=1)
        self.assertEqual(expected, result)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_pre_generation_about_exists_action_2(self):
        gen = genabout.GenAbout()
        test_input = [{'about_file': '/about.py.ABOUT',
                       'version': '0.8.2',
                       'about_resource': '.',
                       'name': '',
                       'test': 'test sample'}]

        expected = [[join(TESTDATA_DIR, 'test_files_for_genabout',
                          'about.py.ABOUT'),
                     {'about_file': 'about.py.ABOUT',
                      'name': 'ABOUT tool',
                      'version': '0.8.1',
                      'test': 'test sample',
                      'about_resource': '.'}]]

        result = gen.pre_generation(GEN_LOCATION,
                                    test_input,
                                    action_num=2)
        self.assertEqual(expected, result)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_pre_generation_about_exists_action_3(self):
        gen = genabout.GenAbout()
        test_fields = [{'about_file': '/about.py.ABOUT',
                        'version': '0.8.2',
                        'about_resource': '.',
                        'name': '',
                        'test': 'test sample'}]
        expected = [[join(TESTDATA_DIR, 'test_files_for_genabout',
                          'about.py.ABOUT'),
                     {'about_file': '/about.py.ABOUT',
                      'version': '0.8.2',
                      'about_resource': '.',
                      'name': '',
                      'test': 'test sample'}]]

        result = gen.pre_generation(GEN_LOCATION,
                                    test_fields,
                                    action_num=3)

        self.assertEqual(expected, result)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_pre_generation_dir_endswith_space(self):
        gen = genabout.GenAbout()
        test_fields = [{'about_file': '/abc /about.py.ABOUT',
                        'version': '0.8.2',
                        'about_resource': '.',
                        'name': '',
                        'test': 'test sample'}]

        result = gen.pre_generation(GEN_LOCATION,
                                    test_fields,
                                    action_num=0)

        self.assertTrue(len(gen.errors) == 1, 'Should return 1 error.')
        self.assertTrue(gen.errors, 'It should prompt error because directory ends with sapce')

    def test_format_output(self):
        gen = genabout.GenAbout()
        test_fields = [
            [join(TESTDATA_DIR, 'test_files_for_genabout/about.py.ABOUT'),
             {'about_file': '/about.py.ABOUT',
              'version': '0.8.1',
              'about_resource': '.',
              'name': 'ABOUT Tool'}]]
        expected = [[join(TESTDATA_DIR,
                          'test_files_for_genabout/about.py.ABOUT'),
                     'about_resource: .\nname: ABOUT Tool\nversion: 0.8.1\n\n']]
        result = gen.format_output(test_fields)
        self.assertEqual(expected, result)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_format_output_with_continuation(self):
        gen = genabout.GenAbout()
        test_fields = [[join(TESTDATA_DIR, 'test_files_for_genabout/about.py.ABOUT'),
                        {'about_file': '/about.py.ABOUT',
                         'version': '0.8.1',
                         'about_resource': '.',
                         'name': 'ABOUT Tool',
                         'readme': 'This is a readme test with \nline continuation.'}]]
        expected = [[join(TESTDATA_DIR, 'test_files_for_genabout/about.py.ABOUT'),
                     'about_resource: .\nname: ABOUT Tool\n'
                     'version: 0.8.1\n\n'
                     'readme: This is a readme test with \n line continuation.\n']]
        result = gen.format_output(test_fields)
        self.assertEqual(expected, result)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_verify_files_existence_exist(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_DIR, 'test_files_for_genabout/')
        test_fields = [{'version': '0.8.1',
                        'about_file': '/TESTCASE/',
                        'license_text_file': 'apache-2.0.LICENSE',
                        'name': 'ABOUT tool',
                        'about_resource': '.'}]
        expected = [(join(gen_location, 'apache-2.0.LICENSE'), 'TESTCASE')]
        result = gen.verify_files_existence(input_list=test_fields,
                                            project_dir=gen_location,
                                            file_in_project=False)
        print(result)
        self.assertEqual(expected, result)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_verify_files_existence_exist_license_in_project(self):
        gen = genabout.GenAbout()
        gen_location = join(TESTDATA_DIR, 'test_files_for_genabout/')
        test_fields = [{'version': '0.8.1',
                        'about_file': '.',
                        'license_text_file': 'apache-2.0.LICENSE',
                        'name': 'ABOUT tool',
                        'about_resource': '.'}]
        expected = [(join(gen_location, 'apache-2.0.LICENSE'), '')]
        result = gen.verify_files_existence(input_list=test_fields,
                                            project_dir=gen_location,
                                            file_in_project=True)
        self.assertEqual(expected, result)
        self.assertFalse(gen.warnings, 'No warnings should be returned.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_verify_files_existence_not_exist(self):
        gen = genabout.GenAbout()
        test_fields = [{'version': '0.8.1',
                        'about_file': '/about.py.ABOUT',
                        'license_text_file': 'not_exist.LICENSE.txt',
                        'name': 'ABOUT tool',
                        'about_resource': '.'}]
        expected = []
        result = gen.verify_files_existence(input_list=test_fields,
                                            project_dir='.',
                                            file_in_project=False)
        self.assertEqual(expected, result)
        self.assertTrue(len(gen.warnings) == 1, 'Should return 1 warning.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_verify_files_existence_not_exist_license_in_project(self):
        gen = genabout.GenAbout()
        test_fields = [{'version': '0.8.1',
                        'about_file': '/TESTCASE/',
                        'license_text_file': 'not_exist.LICENSE.txt',
                        'name': 'ABOUT tool',
                        'about_resource': '.'}]
        expected_list = []
        result = gen.verify_files_existence(input_list=test_fields,
                                            project_dir='.',
                                            file_in_project=False)
        self.assertEqual(expected_list, result)
        self.assertTrue(len(gen.warnings) == 1, 'Should return 1 warning.')
        self.assertFalse(gen.errors, 'No errors should be returned.')

    def test_verify_files_existence_no_key(self):
        gen = genabout.GenAbout()
        test_fields = [{'version': '0.8.1',
                        'about_file': '/about.py.ABOUT',
                        'name': 'ABOUT tool',
                        'about_resource': '.'}]
        self.assertRaises(Exception,
                          gen.verify_files_existence,
                          input_list=test_fields,
                          project_dir='.')

    def test_gen_license_list_license_text_file_no_value(self):
        gen = genabout.GenAbout()
        test_fields = {'about_file': '/tmp/3pp/opensans/',
                       'name': 'OpenSans Fonts',
                       'version': '1',
                       'dje_license': 'apache-2.0',
                       'dje_license_name': 'Apache License 2.0',
                       'license_text_file': '',
                       'about_resource': 'opensans'}
        expected = ('/tmp/3pp/opensans', 'Apache License 2.0')
        result = gen.gen_license_list(test_fields)
        self.assertEqual(expected, result)

    def test_gen_license_list_no_license_text_file_key(self):
        gen = genabout.GenAbout()
        test_fields = {'about_file': '/tmp/3pp/opensans/',
                       'name': 'OpenSans Fonts',
                       'version': '1',
                       'dje_license': 'apache-2.0',
                       'dje_license_name': 'Apache License 2.0',
                       'about_resource': 'opensans'}
        expected = ('/tmp/3pp/opensans', 'Apache License 2.0')
        result = gen.gen_license_list(test_fields)
        self.assertEqual(expected, result)

    def test_copy_files_test_path_not_endswith_slash(self):
        gen = genabout.GenAbout()
        test = [(join(TESTDATA_DIR, 'test_files_for_genabout/apache-2.0.LICENSE'), '.')]
        test_dir = get_temp_dir()
        gen.copy_files(test_dir, test)
        expected = ['apache-2.0.LICENSE']
        self.assertEqual(expected, os.listdir(test_dir))

    def test_copy_files_test_path_endswith_slash(self):
        gen = genabout.GenAbout()
        test = [(join(TESTDATA_DIR, 'test_files_for_genabout/apache-2.0.LICENSE'), '.')]
        expected = ['apache-2.0.LICENSE']
        test_dir = get_temp_dir() + '/'
        gen.copy_files(test_dir, test)
        self.assertEqual(expected, os.listdir(test_dir))

    def test_write_licenses(self):
        gen = genabout.GenAbout()
        license_text_file = test_about.get_temp_file()
        license_text = 'This is a test.'
        test = [[license_text_file, license_text]]
        gen.write_licenses(test)
        result = open(license_text_file, 'rU').readlines()
        self.assertEqual([license_text], result)

    def test_process_dje_licenses(self):
        gen = genabout.GenAbout()
        test_license_list = [('/', 'test')]
        test_license_dict = {'test': [u'test_key', u'This is a test license.']}
        test_path = '/test'
        expected = [[join(u'/test', 'test_key.LICENSE'), 'This is a test license.']]
        result = gen.process_dje_licenses(test_license_list, test_license_dict, test_path)
        self.assertEqual(expected, result)

    def test_update_about_resource_about_file_and_field_exist(self):
        gen = genabout.GenAbout()
        test_fields = {'about_resource': 'test_fields.c',
                       'about_file': '/tmp/test_fields.c'}

        expected = {'about_resource': 'test_fields.c',
                    'about_file': '/tmp/test_fields.c'}

        gen.update_about_resource(test_fields, about_file_exist=True)
        # ensure the dict is not modified
        self.assertEqual(expected, test_fields)

    def test_update_about_resource_about_file_and_field_not_exist_isFile(self):
        gen = genabout.GenAbout()
        test_fields = {'about_file': '/tmp/test.c'}
        expected = {'about_file': '/tmp/test.c',
                    'about_resource': 'test.c'}
        gen.update_about_resource(test_fields, about_file_exist=True)
        # FIXME: calling a function should not have side effects
        self.assertEqual(expected, test_fields,)

    def test_update_about_resource_about_file_and_field_not_exist_isdir(self):
        gen = genabout.GenAbout()
        test_fields = {'about_file': '/tmp/test/'}
        expected = {'about_file': '/tmp/test/', 'about_resource': '.'}
        about_file_exist = True
        gen.update_about_resource(test_fields, about_file_exist)
        self.assertEqual(test_fields, expected)

    def test_update_about_resource_no_about_file_field_exist(self):
        gen = genabout.GenAbout()
        test_fields = {'about_resource': 'test.c',
                       'about_file': '/tmp/test.c'}
        expected_fields = {'about_resource': 'test.c',
                       'about_file': '/tmp/test.c'}
        about_file_exist = False
        gen.update_about_resource(test_fields, about_file_exist)
        self.assertTrue(test_fields == expected_fields, 'The dict should not be changed.')

    def test_update_about_resource_no_about_file_no_field_isFile(self):
        gen = genabout.GenAbout()
        test_fields = {'about_file': '/tmp/test.c'}
        expected = {'about_file': '/tmp/test.c',
                    'about_resource': 'test.c'}
        about_file_exist = False
        gen.update_about_resource(test_fields, about_file_exist)
        self.assertEqual(test_fields, expected)

    def test_update_about_resource_no_about_file_no_field_isdir(self):
        gen = genabout.GenAbout()
        test_fields = {'about_file': '/tmp/test/'}
        expected = {'about_file': '/tmp/test/', 'about_resource': '.'}
        about_file_exist = False
        gen.update_about_resource(test_fields, about_file_exist)
        self.assertEqual(test_fields, expected)
