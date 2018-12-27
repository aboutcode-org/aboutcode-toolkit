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
import os
import unittest

from aboutcode import ERROR
from aboutcode import CRITICAL
from aboutcode import Error
from aboutcode import gen
from aboutcode import model

from testing_utils import get_temp_dir
from testing_utils import get_test_loc


class GenTest(unittest.TestCase):

    def test_check_duplicated_about_file_path(self):
        test_dict = [
            {'about_file_path': '/test/test.c', 'version': '1.03', 'name': 'test.c'},
            {'about_file_path': '/test/abc/', 'version': '1.0', 'name': 'abc'},
            {'about_file_path': '/test/test.c', 'version': '1.04', 'name': 'test1.c'}]
        expected = [
            Error(CRITICAL,
                  "The input has duplicated values in 'about_file_path' field: /test/test.c")]
        result = gen.check_duplicated_about_file_path(test_dict)
        assert expected == result

    def test_load_inventory_base(self):
        location = get_test_loc('test_gen/inv.csv')
        target_dir = get_temp_dir()
        errors, abouts = gen.load_inventory(location, target_dir)

        expected_errors = []
        assert expected_errors == errors

        expected = [OrderedDict([
            ('about_resource', u'.'),
            ('name', u'AboutCode'),
            ('version', u'0.11.0'),
            ('description', u'multi\nline'),
            (u'custom1', u'multi\nline')
        ])]
        result = [a.to_dict() for a in abouts]
        assert expected == result

    def test_load_inventory_with_errors(self):
        location = get_test_loc('test_gen/inv4.csv')
        target_dir = get_temp_dir()
        errors, abouts = gen.load_inventory(location, target_dir)
        expected_errors = [
            Error(CRITICAL, 'Custom field name: \'Confirmed Copyright\' contains illegal characters. '
                  'Only these characters are allowed: ASCII letters, digits and "_" underscore. '
                  'The first character must be a letter.'),
            Error(CRITICAL, "Custom field name: 'Confirmed Copyright' must be lowercase."),
            Error(CRITICAL, "Custom field name: 'Resource' must be lowercase.")
        ]

        assert expected_errors == errors
        assert [] == abouts

    def test_generate_about_files_fails_to_generate_if_one_dir_endswith_space(self):
        location = get_test_loc('test_gen/inventory/complex/about_file_path_dir_endswith_space.csv')
        target_dir = get_temp_dir()
        errors, _abouts = gen.generate_about_files(location, target_dir)
        expected = [
            Error(ERROR, 'Invalid "about_file_path": must not end or start '
                  'with a space for: "about /about.ABOUT"')]
        assert expected == errors

    def test_generate_about_files_with_about_file_path_as_directory_generate_about_file_name(self):
        location = get_test_loc('test_gen/inv2.csv')
        target_dir = get_temp_dir()
        errors, abouts = gen.generate_about_files(location, target_dir)
        expected = []
        assert expected == errors

        expected = [OrderedDict([('about_resource', u'.'), ('name', u'AboutCode'), ('version', u'0.11.0')])]
        assert expected == [a.to_dict() for a in abouts]

        generated_about_loc = abouts[0].location
        assert generated_about_loc.endswith('ABOUT')
        about_file = model.About.load(generated_about_loc)
        expected = OrderedDict([('about_resource', u'.'), ('name', u'AboutCode'), ('version', u'0.11.0')])
        assert expected == about_file.to_dict()

    def test_generate_about_files_is_empty_and_has_errors_if_about_resource_reference_missing(self):
        location = get_test_loc('test_gen/inv3.csv')
        target_dir = get_temp_dir()

        errors, abouts = gen.generate_about_files(location, target_dir)
        expected = [
            Error(CRITICAL, 'Required field "about_resource" is missing.')
        ]
        assert expected == errors
        assert [] == abouts

    def test_generate_about_files_is_partial_and_has_errors_if_some_about_resource_reference_missing(self):
        location = get_test_loc('test_gen/inv_with_some_about_resource_missing.csv')
        target_dir = get_temp_dir()

        errors, abouts = gen.generate_about_files(location, target_dir)
        expected = [
            Error(CRITICAL,
                'Cannot create .ABOUT file for: "inv/test.tar.gz".\n'
                'Required field "about_resource" is missing.')
        ]
        assert expected == errors
        expected = [OrderedDict([('about_resource', u'inv/My.gz'), ('name', u'AboutCode'), ('version', u'0.11.0')])]
        assert expected == [a.to_dict() for a in abouts]
        assert 1 == len(os.listdir(target_dir))

    def test_generate_about_files_simple(self):
        location = get_test_loc('test_gen/inv.csv')
        target_dir = get_temp_dir()

        errors, abouts = gen.generate_about_files(location, target_dir)
        assert [] == errors

        result = [a.to_dict() for a in abouts]
        expected = [OrderedDict([
            ('about_resource', u'.'),
            ('name', u'AboutCode'),
            ('version', u'0.11.0'),
            ('description', u'multi\nline'),
            (u'custom1', u'multi\nline')])
        ]
        assert expected == result

        generated = os.listdir(os.path.join(target_dir, 'inv'))
        expected = ['this.ABOUT']
        assert expected == generated

    def test_generate_about_files_reuses_licenses_from_reference_dir(self):
        inventory_location = get_test_loc('test_gen/inv-with-complex-expression-and-notice.csv')
        target_dir = get_temp_dir()
        reference_dir = get_test_loc('test_gen/reference')

        errors, abouts = gen.generate_about_files(inventory_location, target_dir, reference_dir)
        expected_errors = []
        assert expected_errors == errors

        result = [a.to_dict() for a in abouts]
        expected = [
            OrderedDict([
                ('about_resource', u'some res'),
                ('name', u'AboutCode'),
                ('version', u'0.11.0'),
                ('license_expression', u'(mit AND bsd-new) OR gpl-2.0'),
                ('licenses', [
                    OrderedDict([('file', u'mit.LICENSE'), ('key', u'mit'),
                                 ('name', u'MIT License'), ('url', u'http://mit.license.com')]),
                    OrderedDict([('file', u'bsd-new.LICENSE'), ('key', u'bsd-new'),
                                 ('name', u'BSD License'), ('url', u'http://BSD.license.com')]),
                    OrderedDict([('file', u'gpl-2.0.LICENSE'), ('key', u'gpl-2.0'),
                                 ('name', u'GPL 2.0 License'), ('url', u'http://gpl.license.com')])]),
                ('notice_file', u'this.NOTICE'),
                (u'custom1', u'multi\nline')]),
            OrderedDict([
                ('about_resource', u'some other res'),
                ('name', u'MyNmae'),
                ('version', u'12'),
                ('license_expression', u'bsd-new'),
                ('licenses', [
                    OrderedDict([('file', u'bsd-new.LICENSE'), ('key', u'bsd-new'),
                                 ('name', u'BSD License'), ('url', u'http://BSD.license.com')])]),
                ('notice_file', u'that.NOTICE'),
                (u'custom1', u'multi\nline')])
        ]

        assert expected == result

        generated_files = os.listdir(os.path.join(target_dir, 'inv'))
        expected = [
            'bsd-new.LICENSE',
            'gpl-2.0.LICENSE',
            'mit.LICENSE',
            'that.ABOUT',
            'that.NOTICE',
            'this.ABOUT',
            'this.NOTICE',
        ]

        assert expected == sorted(generated_files)


class TestJson(unittest.TestCase):

    def test_load_json(self):
        test_file = get_test_loc('test_gen/json/expected.json')
        expected = [OrderedDict([
            ('about_file_path', '/load/this.ABOUT'),
            ('about_resource', '.'),
            ('name', 'AboutCode'),
            ('version', '0.11.0')])
        ]
        result = gen.load_json(test_file)
        assert expected == result

    def test_load_json2(self):
        test_file = get_test_loc('test_gen/json/expected_need_mapping.json')
        expected = [dict(OrderedDict([
            ('about_file', '/load/this.ABOUT'),
            ('about_resource', '.'),
            ('version', '0.11.0'),
            ('name', 'AboutCode'),
        ])
        )]
        result = gen.load_json(test_file)
        assert expected == result

    def test_load_non_list_json(self):
        test_file = get_test_loc('test_gen/json/not_a_list_need_mapping.json')
        # FIXME: why this dict nesting??
        expected = [dict(OrderedDict([
            ('about_resource', '.'),
            ('name', 'AboutCode'),
            ('path', '/load/this.ABOUT'),
            ('version', '0.11.0'),
        ])
        )]
        result = gen.load_json(test_file)
        assert expected == result

    def test_load_non_list_json2(self):
        test_file = get_test_loc('test_gen/json/not_a_list.json')
        expected = [OrderedDict([
            ('about_file_path', '/load/this.ABOUT'),
            ('about_resource', '.'),
            ('name', 'AboutCode'),
            ('version', '0.11.0'),
        ])
        ]
        result = gen.load_json(test_file)
        assert expected == result

    def test_load_json_from_abc_mgr(self):
        test_file = get_test_loc('test_gen/json/aboutcode_manager_exported.json')
        expected = [dict(OrderedDict([
            ('license_expression', 'apache-2.0'),
            ('copyright', 'Copyright (c) 2017 nexB Inc.'),
            ('licenses', [{'key':'apache-2.0'}]),
            ('copyrights', [{'statements':['Copyright (c) 2017 nexB Inc.']}]),
            ('path', 'ScanCode'),
            ('review_status', 'Analyzed'),
            ('name', 'ScanCode'),
            ('version', '2.2.1'),
            ('owner', 'nexB Inc.'),
            ('code_type', 'Source'),
            ('is_modified', False),
            ('is_deployed', False),
            ('feature', ''),
            ('purpose', ''),
            ('homepage_url', None),
            ('download_url', None),
            ('license_url', None),
            ('notice_url', None),
            ('programming_language', 'Python'),
            ('notes', ''),
            ('fileId', 8458),
        ]))]
        result = gen.load_json(test_file)
        assert expected == result

    def test_load_json_from_scancode(self):
        test_file = get_test_loc('test_gen/json/scancode_info.json')
        expected = [dict(OrderedDict([
            ('type', 'file'),
            ('name', 'Api.java'),
            ('path', 'Api.java'),
            ('base_name', 'Api'),
            ('extension', '.java'),
            ('size', 5074),
            ('date', '2017-07-15'),
            ('sha1', 'c3a48ec7e684a35417241dd59507ec61702c508c'),
            ('md5', '326fb262bbb9c2ce32179f0450e24601'),
            ('mime_type', 'text/plain'),
            ('file_type', 'ASCII text'),
            ('programming_language', 'Java'),
            ('is_binary', False),
            ('is_text', True),
            ('is_archive', False),
            ('is_media', False),
            ('is_source', True),
            ('is_script', False),
            ('files_count', 0),
            ('dirs_count', 0),
            ('size_count', 0),
            ('scan_errors', []),
        ]))]
        result = gen.load_json(test_file)
        assert expected == result


class TestCsv(unittest.TestCase):

    def test_load_csv_without_mapping(self):
        test_file = get_test_loc('test_gen/csv/about.csv')
        expected = [OrderedDict([
            ('about_file', 'about.ABOUT'),
            ('about_resource', '.'),
            ('name', 'ABOUT tool'),
            ('version', '0.8.1')
        ])]
        result = list(gen.load_csv(test_file))
        assert expected == result

    def test_load_csv_load_rows(self):
        test_file = get_test_loc('test_gen/csv/about.csv')
        expected = [OrderedDict([
            ('about_file', 'about.ABOUT'),
            ('about_resource', '.'),
            ('name', 'ABOUT tool'),
            ('version', '0.8.1')
        ])]
        result = list(gen.load_csv(test_file))
        assert expected == result

    def test_load_csv_does_not_convert_column_names_to_lowercase(self):
        test_file = get_test_loc('test_gen/csv/about_key_with_upper_case.csv')
        expected = [OrderedDict([
            ('about_file', 'about.ABOUT'),
            ('about_resource', '.'),
            ('nAme', 'ABOUT tool'),
            ('Version', '0.8.1')
        ])]
        result = list(gen.load_csv(test_file))
        assert expected == result
