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
import string
import unittest
from unittest.case import expectedFailure

from testing_utils import extract_test_loc
from testing_utils import get_test_loc
from testing_utils import on_posix
from testing_utils import on_windows

from attributecode import CRITICAL
from attributecode import Error
from attributecode import model
from attributecode import util


class UtilsTest(unittest.TestCase):

    def test_resource_name(self):
        expected = 'first'
        result = util.resource_name('some/things/first')
        assert expected == result

    def test_resource_name_with_extension(self):
        expected = 'first.ABOUT'
        result = util.resource_name('/some/things/first.ABOUT')
        assert expected == result

    def test_resource_name_for_dir(self):
        expected = 'first'
        result = util.resource_name('some/things/first/')
        assert expected == result

    def test_resource_name_windows(self):
        expected = r'first.'
        result = util.resource_name(r'c:\some\things\first.')
        assert expected == result

    def test_resource_name_mixed_windows_posix(self):
        expected = r'first'
        result = util.resource_name(r'c:\some/things\first')
        assert expected == result

    def test_resource_name_double_slash(self):
        expected = 'first'
        result = util.resource_name(r'some\thi ngs//first')
        assert expected == result

    def test_resource_name_punctuation(self):
        expected = '_$asafg:'
        result = util.resource_name('%6571351()2/75612$/_$asafg:')
        assert expected == result

    def test_resource_name_simple_slash(self):
        expected = ''
        result = util.resource_name('/')
        assert expected == result

    def test_resource_name_spaces(self):
        expected = ''
        result = util.resource_name('/  /  ')
        assert expected == result

    def test_resource_name_does_not_recurse_infinitely(self):
        expected = ''
        result = util.resource_name(' / ')
        assert expected == result

    def test_to_posix_from_win(self):
        test = r'c:\this\that'
        expected = 'c:/this/that'
        result = util.to_posix(test)
        assert expected == result

    def test_to_posix_from_posix(self):
        test = r'/this/that'
        expected = '/this/that'
        result = util.to_posix(test)
        assert expected == result

    def test_to_posix_from_mixed(self):
        test = r'/this/that\this'
        expected = '/this/that/this'
        result = util.to_posix(test)
        assert expected == result

    def test_to_native_from_win(self):
        test = r'c:\this\that'
        if on_posix:
            expected = 'c:/this/that'
        else:
            expected = test
        result = util.to_native(test)
        assert expected == result

    def test_to_native_from_posix(self):
        test = r'/this/that'
        if on_windows:
            expected = r'\this\that'
        else:
            expected = test
        result = util.to_native(test)
        assert expected == result

    def test_to_native_from_mixed(self):
        test = r'/this/that\this'
        if on_windows:
            expected = r'\this\that\this'
        else:
            expected = r'/this/that/this'
        result = util.to_native(test)
        assert expected == result

    def test_get_locations(self):
        test_dir = get_test_loc('locations')
        expected = sorted([
                    'locations/file with_spaces',
                    'locations/file1',
                    'locations/file2',
                    'locations/dir1/file2',
                    'locations/dir1/dir2/file1',
                    'locations/dir2/file1'])

        result = sorted(util.get_locations(test_dir))
        for i, res in enumerate(result):
            expect = expected[i]
            assert res.endswith(expect)

    def test_get_about_locations_with_no_ABOUT_files(self):
        test_dir = get_test_loc('locations')
        expected = []
        result = list(util.get_about_locations(test_dir))
        assert expected == result

    def test_get_about_locations_with_ABOUT_files(self):
        test_dir = get_test_loc('about_locations')
        expected = sorted([
                    'locations/file with_spaces.ABOUT',
                    'locations/dir1/file2.aBout',
                    'locations/dir1/dir2/file1.about',
                    ])

        result = sorted(util.get_about_locations(test_dir))
        for i, res in enumerate(result):
            expect = expected[i]
            assert res.endswith(expect)

    def test_invalid_chars_with_valid_chars(self):
        name = string.digits + string.ascii_letters + '_-.'
        result = util.invalid_chars(name)
        expected = []
        assert expected == result

    def test_invalid_chars_with_invalid_in_name_and_dir(self):
        result = util.invalid_chars('_$as/afg:')
        expected = [':']
        assert expected == result

    def test_invalid_chars_in_file_name(self):
        name = '%657!1351()275612$_$asafg:'
        result = util.invalid_chars(name)
        expected = ['%', '!', '(', ')', '$', '$', ':']
        assert expected == result

    def test_invalid_chars_with_space(self):
        result = util.invalid_chars('_ Hello')
        expected = [' ']
        assert expected == result

    def test_check_file_names_with_dupes_return_errors(self):
        paths = ['some/path', 'some/PAth']
        result = util.check_file_names(paths)
        expected = [Error(CRITICAL, "Duplicate files: 'some/PAth' and 'some/path' have the same case-insensitive file name")]
        assert expected == result

    def test_check_file_names_without_dupes_return_no_error(self):
        paths = ['some/path',
                 'some/otherpath']
        result = util.check_file_names(paths)
        expected = []
        assert expected == result

    def test_check_file_names_with_no_invalid_char_return_no_error(self):
        paths = [
            'locations/file',
            'locations/file1',
            'locations/file2',
            'locations/dir1/file2',
            'locations/dir1/dir2/file1',
            'locations/dir2/file1']

        expected = []
        result = util.check_file_names(paths)
        assert expected == result

    def test_check_file_names_with_invalid_chars_return_errors(self):
        paths = [
            'locations/file',
            'locations/file with space',
            'locations/dir1/dir2/file1',
            'locations/dir2/file1'
        ]

        expected = [Error(CRITICAL, "Invalid characters '  ' in file name at: 'locations/file with space'")]
        result = util.check_file_names(paths)

        assert expected[0].message == result[0].message
        assert expected == result

    def test_get_about_locations(self):
        location = get_test_loc('parse/complete')
        result = list(util.get_about_locations(location))
        expected = 'testdata/parse/complete/about.ABOUT'
        assert result[0].endswith(expected)

    def test_is_about_file(self):
        assert util.is_about_file('test.About')
        assert util.is_about_file('test2.aboUT')
        assert not util.is_about_file('no_about_ext.something')

    def test_get_relative_path(self):
        test = [('/some/path', '/some/path/file', 'file'),
                ('path', '/path/file', 'file'),
                ('/path', '/path/file', 'file'),
                ('/path/', '/path/file/', 'file'),
                ('/path/', 'path/', 'path'),
                ('/p1/p2/p3', '/p1/p2//p3/file', 'file'),
                (r'c:\some/path', 'c:/some/path/file', 'file'),
                (r'c:\\some\\path\\', 'c:/some/path/file', 'file'),
                ]
        for base_loc, full_loc, expected in test:
            result = util.get_relative_path(base_loc, full_loc)
            assert expected == result

    def test_get_relative_path_with_same_path_twice(self):
        test = [('/some/path/file', 'path/file'),
                ('/path/file', 'path/file'),
                ('/path/file/', 'path/file'),
                ('path/', 'path'),
                ('/p1/p2//p3/file', 'p3/file'),
                ('c:/some/path/file', 'path/file'),
                (r'c:\\some\\path\\file', 'path/file'),
                ]
        for loc, expected in test:
            result = util.get_relative_path(loc, loc)
            assert expected == result

    def test_get_mapping_key_order(self):
        import collections
        expected = collections.OrderedDict()
        expected['about_file_path'] = ''
        expected['name'] = ''
        expected['version'] = ''
        expected['copyright'] = ''
        expected['license_expression'] = ''
        expected['resource'] = ''
        expected_keys = expected.keys()
        result = util.get_mapping_key_order(mapping_file=False)
        assert expected_keys == result

    def test_get_mapping_key_order_with_mapping_file(self):
        import collections
        expected = collections.OrderedDict()
        expected['about_file_path'] = ''
        expected['name'] = ''
        expected['version'] = ''
        expected['description'] = ''
        expected['license_expression'] = ''
        expected['copyright'] = ''
        expected_keys = expected.keys()
        test_mapping_file = get_test_loc('mapping_config/mapping.config')
        result = util.get_mapping_key_order(test_mapping_file)
        assert expected_keys == result

    def test_load_csv_without_mapping(self):
        test_file = get_test_loc('util/about.csv')
        expected = [OrderedDict([
            ('about_file', 'about.ABOUT'),
            ('about_resource', '.'),
            ('name', 'ABOUT tool'),
            ('version', '0.8.1')])
        ]
        result = util.load_csv(test_file)
        assert expected == result

    def test_load_json_without_mapping(self):
        test_file = get_test_loc('load/expected.json')
        expected = [OrderedDict([
            ('about_file_path', '/load/this.ABOUT'),
            ('about_resource', '.'),
            ('name', 'AboutCode'),
            ('version', '0.11.0')])
        ]
        result = util.load_json(test_file)
        assert expected == result

    def test_load_json_with_mapping(self):
        test_file = get_test_loc('load/expected_need_mapping.json')
        expected = [dict(OrderedDict([
            ('about_file_path', '/load/this.ABOUT'),
            ('about_resource', '.'),
            ('version', '0.11.0'),
            ('name', 'AboutCode'),
        ])
        )]
        result = util.load_json(test_file, use_mapping=True)
        assert expected == result

    def test_load_non_list_json_with_mapping(self):
        test_file = get_test_loc('load/not_a_list_need_mapping.json')
        mapping_file = get_test_loc('custom-mapping-file/mapping.config')
        expected = [dict(OrderedDict([
            ('about_file_path', '/load/this.ABOUT'),
            ('about_resource', '.'),
            ('name', 'AboutCode'),
            ('version', '0.11.0'),
        ])
        )]
        result = util.load_json(test_file, use_mapping=False, mapping_file=mapping_file)
        assert expected == result

    def test_load_non_list_json(self):
        test_file = get_test_loc('load/not_a_list.json')
        expected = [OrderedDict([
            ('about_file_path', '/load/this.ABOUT'),
            ('version', '0.11.0'),
            ('about_resource', '.'),
            ('name', 'AboutCode'),
        ])
        ]
        result = util.load_json(test_file)
        assert expected == result

    def test_load_json_from_abc_mgr(self):
        test_file = get_test_loc('load/aboutcode_manager_exported.json')
        mapping_file = get_test_loc('custom-mapping-file/mapping.config')
        expected = [dict(OrderedDict(
                    [('license_expression', 'apache-2.0'),
                     ('copyright', 'Copyright (c) 2017 nexB Inc.'),
                     ('licenses', [{'key':'apache-2.0'}]),
                     ('copyrights', [{'statements':['Copyright (c) 2017 nexB Inc.']}]),
                     ('about_file_path', 'ScanCode'),
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
                    ]
                    ))]
        result = util.load_json(test_file, use_mapping=False, mapping_file=mapping_file)
        assert expected == result

    def test_load_json_from_scancode(self):
        test_file = get_test_loc('load/scancode_info.json')
        mapping_file = get_test_loc('custom-mapping-file/mapping.config')
        expected = [dict(OrderedDict(
                    [('about_file_path', 'Api.java'),
                     ('type', 'file'),
                     ('name', 'Api.java'),
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
                    ]
                    ))]
        result = util.load_json(test_file, use_mapping=False, mapping_file=mapping_file)
        assert expected == result

    def test_get_about_file_path_from_csv_using_mapping(self):
        test_file = get_test_loc('util/about.csv')
        expected = ['about.ABOUT']
        result = util.get_about_file_path(test_file, use_mapping=True)
        assert expected == result

    def test_get_about_file_path_from_json_using_mapping(self):
        test_file = get_test_loc('load/expected.json')
        expected = ['/load/this.ABOUT']
        result = util.get_about_file_path(test_file, use_mapping=True)
        assert expected == result

    # The column names should be converted to lowercase as the same behavior as
    # when user use the mapping.config
    @expectedFailure
    def test_load_csv_does_not_convert_column_names_to_lowercase(self):
        test_file = get_test_loc('util/about_key_with_upper_case.csv')
        expected = [OrderedDict(
                    [('about_file', 'about.ABOUT'),
                     ('about_resource', '.'),
                     ('nAme', 'ABOUT tool'),
                     ('Version', '0.8.1')])
                    ]
        result = util.load_csv(test_file)
        assert expected == result

    def test_get_locations_with_very_long_path(self):
        longpath = (
            u'longpath'
            u'/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            u'/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            u'/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            u'/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
        )
        test_loc = extract_test_loc('longpath.zip')
        result = list(util.get_locations(test_loc))
        assert any(longpath in r for r in result)

    def test_apply_mapping(self):
        about = [OrderedDict([
            ('about_resource', '.'),
            ('name', 'test'),
            ('confirmed version', '1'),
            ('confirmed copyright', 'Copyright (c) 2013-2017 nexB Inc.')
        ])]
        expected = [OrderedDict([
            ('about_resource', '.'),
            ('name', 'test'),
            ('version', '1'),
            ('copyright', 'Copyright (c) 2013-2017 nexB Inc.')
        ])]
        assert util.apply_mapping(about) == expected

    def test_check_duplicate_keys_about_file(self):
        test = '''
name: test
notes: some notes

license_expression: mit
notes: dup key here
            '''
        expected = ['notes']
        assert expected == util.check_duplicate_keys_about_file(test)

    def test_wrap_boolean_value(self):
        test = '''
name: test
notes: some notes

license_expression: mit
modified: yes
track_changes: no
            '''
        expected = '''
name: test
notes: some notes

license_expression: mit
modified: 'yes'
track_changes: 'no'
            '''
        assert expected == util.wrap_boolean_value(test)

    def test_check_duplicate_keys_about_file_with_multiline(self):
        test = '''
name: test
owner: test
notes: |
    String block here
license_expression: mit
owner: test1
notes: continuation
 line
description: sample
            '''
        expected = ['owner', 'notes']
        assert expected == util.check_duplicate_keys_about_file(test)

    def test_inventory_filter(self):
        test_loc = get_test_loc('basic')
        _errors, abouts = model.collect_inventory(test_loc)

        filter_dict = {'name': ['simple']}
        # The test loc has 2 .about files, only the simple.about is taken after
        # the filtering
        updated_abouts = util.inventory_filter(abouts, filter_dict)
        for about in updated_abouts:
            assert about.name.value == 'simple'

    def test_update_fieldnames(self):
        mapping_output = get_test_loc('util/mapping_output')
        fieldnames = ['about_file_path', 'name', 'version']
        expexted_fieldnames = ['about_file_path', 'Component', 'version']
        result = util.update_fieldnames(fieldnames, mapping_output)
        assert expexted_fieldnames == result

    def test_update_about_dictionary_keys(self):
        mapping_output = get_test_loc('util/mapping_output')
        about_ordered_dict = OrderedDict()
        about_ordered_dict['name'] = 'test.c'
        about_dict_list = [about_ordered_dict]
        expected_output_dict = OrderedDict()
        expected_output_dict['Component'] = 'test.c'
        expected_dict_list = [expected_output_dict]
        result = util.update_about_dictionary_keys(about_dict_list, mapping_output)
        assert expected_dict_list == result

    def test_ungroup_licenses(self):
        about = [OrderedDict([(u'key', u'mit'),
                              (u'name', u'MIT License'),
                              (u'file', u'mit.LICENSE'),
                              (u'url', u'https://enterprise.dejacode.com/urn/?urn=urn:dje:license:mit')]),
                 OrderedDict([(u'key', u'bsd-new'),
                              (u'name', u'BSD-3-Clause'),
                              (u'file', u'bsd-new.LICENSE'),
                              (u'url', u'https://enterprise.dejacode.com/urn/?urn=urn:dje:license:bsd-new')])]
        expected_lic_key = [u'mit', u'bsd-new']
        expected_lic_name = [u'MIT License', u'BSD-3-Clause']
        expected_lic_file = [u'mit.LICENSE', u'bsd-new.LICENSE']
        expected_lic_url = [u'https://enterprise.dejacode.com/urn/?urn=urn:dje:license:mit',
                    u'https://enterprise.dejacode.com/urn/?urn=urn:dje:license:bsd-new']
        lic_key, lic_name, lic_file, lic_url = util.ungroup_licenses(about)
        assert expected_lic_key == lic_key
        assert expected_lic_name == lic_name
        assert expected_lic_file == lic_file
        assert expected_lic_url == lic_url

    def test_format_about_dict_for_csv_output(self):
        about = [OrderedDict([
            (u'about_file_path', u'/input/about1.ABOUT'),
            (u'about_resource', [u'test.c']),
            (u'name', u'AboutCode-toolkit'),
            (u'license_expression', u'mit AND bsd-new'),
            (u'license_key', [u'mit', u'bsd-new'])])]

        expected = [OrderedDict([
            (u'about_file_path', u'/input/about1.ABOUT'),
            (u'about_resource', u'test.c'),
            (u'name', u'AboutCode-toolkit'),
            (u'license_expression', u'mit AND bsd-new'),
            (u'license_key', u'mit\nbsd-new')])]

        output = util.format_about_dict_for_csv_output(about)
        assert output == expected

    def test_format_about_dict_for_json_output(self):
        about = [OrderedDict([
            (u'about_file_path', u'/input/about1.ABOUT'),
            (u'about_resource', OrderedDict([(u'test.c', None)])),
            (u'name', u'AboutCode-toolkit'),
            (u'license_key', [u'mit', u'bsd-new'])])]

        expected = [OrderedDict([
            (u'about_file_path', u'/input/about1.ABOUT'),
            (u'about_resource', u'test.c'),
            (u'name', u'AboutCode-toolkit'),
            (u'licenses', [
                OrderedDict([(u'key', u'mit')]),
                OrderedDict([(u'key', u'bsd-new')])])])]

        output = util.format_about_dict_for_json_output(about)
        assert output == expected
