#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2015 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

from about_code_tool import genattrib

from about_code_tool.tests.test_about import get_temp_file


TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
TESTDATA_DIR = os.path.join(TESTS_DIR, 'testdata')
GEN_LOCATION = os.path.join(TESTDATA_DIR, 'test_files_for_genabout')


class GenAttribTest(unittest.TestCase):
    def test_convert_dict_key_to_lower_case(self):
        test = [{'Directory': '/test/', 'file_name': 'test.c'}]
        expected = [{'directory': '/test/', 'file_name': 'test.c'}]
        result = genattrib.convert_dict_key_to_lower_case(test)
        self.assertEqual(expected, result)

    def test_check_no_about_file_existence(self):
        test = [{'Directory': '/test/', 'file_name': '/test.c'}]
        result = genattrib.check_about_file_existence_and_format(test)
        self.assertFalse(result)

    def test_check_have_about_file_existence(self):
        test = [{'Directory': '/test/', 'about_file': '/test.ABOUT'}]
        result = genattrib.check_about_file_existence_and_format(test)
        self.assertEqual(test, result)

    def test_check_no_about_file_not_start_with_slash(self):
        test = [{'Directory': '/test/', 'file_name': 'test.c'}]
        result = genattrib.check_about_file_existence_and_format(test)
        self.assertFalse(result)

    def test_check_have_about_file_not_start_with_slash(self):
        test = [{'Directory': '/test/', 'about_file': 'test.ABOUT'}]
        expected = [{'Directory': '/test/', 'about_file': '/test.ABOUT'}]
        result = genattrib.check_about_file_existence_and_format(test)
        self.assertEqual(expected, result)

    def test_update_path_to_about(self):
        test = ['/test/test1.ABOUT', '/test/test2/', 'test/test3.c']
        expected = ['/test/test1.ABOUT',
                    '/test/test2/test2.ABOUT',
                    'test/test3.c.ABOUT']
        result = genattrib.update_path_to_about(test)
        self.assertEqual(expected, result)

    def test_component_subset_to_sublist(self):
        test = [{'about_file': '/tmp/', 'notes': 'test'},
                {'about_file': '/tmp/t1/', 'dje_license': 'bsd-new'}]
        expected = ['/tmp/', '/tmp/t1/']
        result = genattrib.component_subset_to_sublist(test)
        self.assertEqual(expected, result)

    def test_genattrib_basic(self):
        self.maxDiff = None
        about_dir = 'about_code_tool/tests/testdata/genattrib/basic/'
        generated_attrib = get_temp_file('generated.html')
        args = [about_dir, generated_attrib]
        options = None
        genattrib_command_tester(args, options)
        result = open(generated_attrib).read()
        expected = [
            'ElasticSearch 1.6.0',
            'bootstrap 2.3.2',
            'djangosnippets.org_2413 2011-04-12',
            'Annotator 1.2.10',
            'component_4',
        ]
        for ex in expected:
            self.assertTrue(ex in result)

    def test_genattrib_basic_with_filter(self):
        self.maxDiff = None
        # note: this contains an about_files subdir that is the root of all ABOUT files in the "project"
        about_dir = 'about_code_tool/tests/testdata/genattrib/project'
        generated_attrib = get_temp_file('generated.html')
        # note: all the about_fioles columns are paths starting with /about_files
        filter_csv = 'about_code_tool/tests/testdata/genattrib/project_filter.csv'
        args = [about_dir, generated_attrib, filter_csv]
        options = None
        genattrib_command_tester(args, options)
        result = open(generated_attrib).read()
        expected = [
            'ElasticSearch 1.6.0',
            'bootstrap 2.3.2',
        ]
        for ex in expected:
            self.assertTrue(ex in result, ex)

        not_expected = [
            'Annotator 1.2.10',
            'component_4',
        'djangosnippets.org_2413 2011-04-12',
        ]
        for ex in not_expected:
            self.assertFalse(ex in result, ex)

    def test_genattrib_from_zipped_dir(self):
        self.maxDiff = None
        about_dir = 'about_code_tool/tests/testdata/genattrib/zipped_about.zip'
        generated_attrib = get_temp_file('generated.html')
        args = [about_dir, generated_attrib]
        options = None
        genattrib_command_tester(args, options)
        result = open(generated_attrib).read()
        expected = [
            'ElasticSearch 1.6.0',
            'bootstrap 2.3.2',
            'djangosnippets.org_2413 2011-04-12',
            'Annotator 1.2.10',
            'python-memcached 1.53',
            'component_94',
            'Groovy 2.4.0',
        ]
        for ex in expected:
            self.assertTrue(ex in result, ex)


    def test_genattrib_zip_with_filter(self):
        self.maxDiff = None
        # note: this contains an about_files subdir that is the root of all ABOUT files in the "project"
        about_dir = 'about_code_tool/tests/testdata/genattrib/about_files.zip'
        generated_attrib = get_temp_file('generated.html')
        # note: all the about_fioles columns are paths starting with /about_files
        filter_csv = 'about_code_tool/tests/testdata/genattrib/project_filter.csv'
        args = [about_dir, generated_attrib, filter_csv]
        options = None
        genattrib_command_tester(args, options)
        result = open(generated_attrib).read()
        expected = [
            'ElasticSearch 1.6.0',
            'bootstrap 2.3.2',
        ]
        for ex in expected:
            self.assertTrue(ex in result, ex)

        not_expected = [
            'Annotator 1.2.10',
            'component_4',
        'djangosnippets.org_2413 2011-04-12',
        ]
        for ex in not_expected:
            self.assertFalse(ex in result, ex)

def genattrib_command_tester(args, options):
    parser = genattrib.get_parser()
    options, args = parser.parse_args(args, options)
    genattrib.main(parser, options, args)
