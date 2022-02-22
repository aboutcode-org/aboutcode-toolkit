#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) nexB Inc. http://www.nexb.com/ - All rights reserved.
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

import string
import unittest

import saneyaml

from testing_utils import extract_test_loc
from testing_utils import get_test_loc
from testing_utils import get_temp_dir
from testing_utils import on_posix
from testing_utils import on_windows

from attributecode import CRITICAL
from attributecode import Error
from attributecode import model
from attributecode import util


class TestResourcePaths(unittest.TestCase):

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

    def test_invalid_chars_with_valid_chars(self):
        name = string.digits + string.ascii_letters + '_-.+'
        result = util.invalid_chars(name)
        expected = []
        assert expected == result

    def test_space_is_valid_chars(self):
        result = util.invalid_chars(' ')
        expected = []
        assert expected == result

    def test_invalid_chars_with_invalid_in_name_and_dir(self):
        result = util.invalid_chars('_$as/afg:')
        expected = [':']
        assert expected == result

    def test_invalid_chars_in_file_name(self):
        name = '%657!1351()275612$_$asafg:~|[]{}+-.'
        result = util.invalid_chars(name)
        expected = ['!', '$', '$', ':']
        assert expected == result

    def test_invalid_chars_with_space_is_valid(self):
        result = util.invalid_chars('_ Hello')
        expected = []
        assert expected == result

    def test_check_file_names_with_dupes_return_errors(self):
        paths = ['some/path', 'some/PAth']
        result = util.check_file_names(paths)
        expected = [
            Error(
                CRITICAL,
                "Duplicate files: 'some/PAth' and 'some/path' have the same case-insensitive file name")
            ]
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
            'locations/dir2/file1',
            'Accessibilité/ périmètre'
        ]
        import sys
        if sys.version_info[0] < 3:  # python2
            expected = [Error(CRITICAL, b"Invalid characters '\xe9\xe8' in file name at: 'Accessibilit\xe9/ p\xe9rim\xe8tre'")]
        else:
            expected = [Error(CRITICAL, "Invalid characters 'éè' in file name at: 'Accessibilité/ périmètre'")]
        result = util.check_file_names(paths)

        assert expected[0].message == result[0].message
        assert expected == result

    def test_is_about_file(self):
        assert util.is_about_file('test.About')
        assert util.is_about_file('test2.aboUT')
        assert not util.is_about_file('no_about_ext.something')
        assert not util.is_about_file('about')
        assert not util.is_about_file('about.txt')

    def test_is_about_file_is_false_if_only_bare_extension(self):
        assert not util.is_about_file('.ABOUT')

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


class TestGetLocations(unittest.TestCase):

    def test_get_locations(self):
        test_dir = get_test_loc('test_util/about_locations')
        expected = sorted([
            'file with_spaces.ABOUT',
            'file1',
            'file2',
            'dir1/file2',
            'dir1/file2.aBout',
            'dir1/dir2/file1.about',
            'dir2/file1'])

        result = sorted(util.get_locations(test_dir))
        result = [l.partition('/about_locations/')[-1] for l in result]
        assert expected == result

    def test_get_about_locations(self):
        test_dir = get_test_loc('test_util/about_locations')
        expected = sorted([
            'file with_spaces.ABOUT',
            'dir1/file2.aBout',
            'dir1/dir2/file1.about',
        ])

        result = sorted(util.get_about_locations(test_dir))
        result = [l.partition('/about_locations/')[-1] for l in result]
        assert expected == result

    def test_get_locations_can_yield_a_single_file(self):
        test_file = get_test_loc('test_util/about_locations/file with_spaces.ABOUT')
        result = list(util.get_locations(test_file))
        assert 1 == len(result)

    def test_get_about_locations_for_about(self):
        location = get_test_loc('test_util/get_about_locations')
        result = list(util.get_about_locations(location))
        expected = 'get_about_locations/about.ABOUT'
        assert result[0].endswith(expected)

    # FIXME: these are not very long/deep paths
    def test_get_locations_with_very_long_path(self):
        longpath = (
            'longpath'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
        )
        test_loc = extract_test_loc('test_util/longpath.zip')
        result = list(util.get_locations(test_loc))
        assert any(longpath in r for r in result)


class TestCsv(unittest.TestCase):

    def test_load_csv_without_mapping(self):
        test_file = get_test_loc('test_util/csv/about.csv')
        expected = [dict([
            ('about_file', 'about.ABOUT'),
            ('about_resource', '.'),
            ('name', 'ABOUT tool'),
            ('version', '0.8.1')])
        ]
        result = util.load_csv(test_file)
        assert expected == result

    def test_load_csv_load_rows(self):
        test_file = get_test_loc('test_util/csv/about.csv')
        expected = [dict([
            ('about_file', 'about.ABOUT'),
            ('about_resource', '.'),
            ('name', 'ABOUT tool'),
            ('version', '0.8.1')])
        ]
        result = util.load_csv(test_file)
        assert expected == result

    def test_load_csv_does_convert_column_names_to_lowercase(self):
        test_file = get_test_loc('test_util/csv/about_key_with_upper_case.csv')
        expected = [dict(
                    [('about_file', 'about.ABOUT'),
                     ('about_resource', '.'),
                     ('name', 'ABOUT tool'),
                     ('version', '0.8.1')])
                    ]
        result = util.load_csv(test_file)
        assert expected == result

    def test_format_about_dict_output(self):
        about = [dict([
            (u'about_file_path', u'/input/about1.ABOUT'),
            (u'about_resource', [u'test.c']),
            (u'name', u'AboutCode-toolkit'),
            (u'license_expression', u'mit AND bsd-new'),
            (u'license_key', [u'mit', u'bsd-new'])])]

        expected = [dict([
            (u'about_file_path', u'/input/about1.ABOUT'),
            (u'about_resource', u'test.c'),
            (u'name', u'AboutCode-toolkit'),
            (u'license_expression', u'mit AND bsd-new'),
            (u'license_key', u'mit\nbsd-new')])]

        output = util.format_about_dict_output(about)
        assert output == expected

    def test_load_csv_microsoft_utf_8(self):
        test_file = get_test_loc('test_util/csv/test_ms_utf8.csv')
        expected = [dict([(u'about_resource', u'/myFile'), (u'name', u'myName')])]
        result = util.load_csv(test_file)
        assert expected == result

    def test_load_csv_utf_8(self):
        test_file = get_test_loc('test_util/csv/test_utf8.csv')
        expected = [dict([(u'about_resource', u'/myFile'), (u'name', u'\u540d')])]
        result = util.load_csv(test_file)
        assert expected == result


class TestJson(unittest.TestCase):

    def test_load_json(self):
        test_file = get_test_loc('test_util/json/expected.json')
        expected = [dict([
            ('about_file_path', '/load/this.ABOUT'),
            ('about_resource', '.'),
            ('name', 'AboutCode'),
            ('version', '0.11.0')])
        ]
        result = util.load_json(test_file)
        assert expected == result

    def test_load_json2(self):
        test_file = get_test_loc('test_util/json/expected_need_mapping.json')
        expected = [dict(dict([
            ('about_file', '/load/this.ABOUT'),
            ('about_resource', '.'),
            ('version', '0.11.0'),
            ('name', 'AboutCode'),
        ])
        )]
        result = util.load_json(test_file)
        assert expected == result

    def test_load_non_list_json(self):
        test_file = get_test_loc('test_util/json/not_a_list_need_mapping.json')
        # FIXME: why this dict nesting??
        expected = [dict(dict([
            ('about_resource', '.'),
            ('name', 'AboutCode'),
            ('path', '/load/this.ABOUT'),
            ('version', '0.11.0'),
        ])
        )]
        result = util.load_json(test_file)
        assert expected == result

    def test_load_non_list_json2(self):
        test_file = get_test_loc('test_util/json/not_a_list.json')
        expected = [dict([
            ('about_file_path', '/load/this.ABOUT'),
            ('version', '0.11.0'),
            ('about_resource', '.'),
            ('name', 'AboutCode'),
        ])
        ]
        result = util.load_json(test_file)
        assert expected == result

    def test_load_json_from_abc_mgr(self):
        test_file = get_test_loc('test_util/json/aboutcode_manager_exported.json')
        expected = [dict(dict([
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
        result = util.load_json(test_file)
        assert expected == result

    def test_load_json_from_scancode(self):
        test_file = get_test_loc('test_util/json/scancode_info.json')
        expected = [dict(dict([
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
        result = util.load_json(test_file)
        assert expected == result

    def test_format_about_dict_for_json_output(self):
        about = [dict([
            (u'about_file_path', u'/input/about1.ABOUT'),
            (u'about_resource', dict([(u'test.c', None)])),
            (u'name', u'AboutCode-toolkit'),
            (u'license_key', [u'mit', u'bsd-new'])])]

        expected = [dict([
            (u'about_file_path', u'/input/about1.ABOUT'),
            (u'about_resource', u'test.c'),
            (u'name', u'AboutCode-toolkit'),
            (u'licenses', [
                dict([(u'key', u'mit')]),
                dict([(u'key', u'bsd-new')])])])]

        output = util.format_about_dict_for_json_output(about)
        assert output == expected


class TestMiscUtils(unittest.TestCase):

    def test_load_yaml_about_file_with_no_dupe(self):
        test = '''
name: test

license_expression: mit
notes: dup key here
            '''
        saneyaml.load(test, allow_duplicate_keys=False)

    def test_load_yaml_about_file_raise_exception_on__duplicate(self):
        test = '''
name: test
notes: some notes
notes: dup key here

notes: dup key here
license_expression: mit
notes: dup key here
            '''
        try:
            saneyaml.load(test, allow_duplicate_keys=False)
            self.fail('Exception not raised')
        except saneyaml.UnsupportedYamlFeatureError as e :
            assert 'Duplicate key in YAML source: notes' == str(e)

    def test_load_yaml_about_file_raise_exception_on_invalid_yaml_ignore_non_key_line(self):
        test = '''
name: test
- notes: some notes
  - notes: dup key here
# some

notes: dup key here
license_expression: mit
notes dup key here
            '''
        try:
            saneyaml.load(test, allow_duplicate_keys=False)
            self.fail('Exception not raised')
        except Exception:
            pass

    def test_load_yaml_about_file_with_multiline(self):
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
        try:
            saneyaml.load(test, allow_duplicate_keys=False)
            self.fail('Exception not raised')
        except saneyaml.UnsupportedYamlFeatureError as e :
            # notes: exceptio is rasied only for the first dupe
            assert 'Duplicate key in YAML source: owner' == str(e)

    def test_ungroup_licenses(self):
        about = [
            dict([
                (u'key', u'mit'),
                (u'name', u'MIT License'),
                (u'file', u'mit.LICENSE'),
                (u'url', u'https://enterprise.dejacode.com/urn/?urn=urn:dje:license:mit'),
                (u'spdx_license_key', u'MIT')]),
            dict([
                (u'key', u'bsd-new'),
                (u'name', u'BSD-3-Clause'),
                (u'file', u'bsd-new.LICENSE'),
                (u'url', u'https://enterprise.dejacode.com/urn/?urn=urn:dje:license:bsd-new'),
                (u'spdx_license_key', u'BSD-3-Clause')])
        ]
        expected_lic_key = [u'mit', u'bsd-new']
        expected_lic_name = [u'MIT License', u'BSD-3-Clause']
        expected_lic_file = [u'mit.LICENSE', u'bsd-new.LICENSE']
        expected_lic_url = [
            u'https://enterprise.dejacode.com/urn/?urn=urn:dje:license:mit',
            u'https://enterprise.dejacode.com/urn/?urn=urn:dje:license:bsd-new']
        expected_spdx = [u'MIT', u'BSD-3-Clause']
        lic_key, lic_name, lic_file, lic_url, spdx_lic_key, lic_score = util.ungroup_licenses(about)
        assert expected_lic_key == lic_key
        assert expected_lic_name == lic_name
        assert expected_lic_file == lic_file
        assert expected_lic_url == lic_url
        assert expected_spdx == spdx_lic_key

    def test_unique_does_deduplicate_and_keep_ordering(self):
        items = ['a', 'b', 'd', 'b', 'c', 'a']
        expected = ['a', 'b', 'd', 'c']
        results = util.unique(items)
        assert expected == results

    def test_unique_can_handle_About_object(self):
        base_dir = 'some_dir'
        test = {
            'about_resource': '.',
            'author': '',
            'copyright': 'Copyright (c) 2013-2014 nexB Inc.',
            'custom1': 'some custom',
            'custom_empty': '',
            'description': 'AboutCode is a tool\nfor files.',
            'license': 'apache-2.0',
            'name': 'AboutCode',
            'owner': 'nexB Inc.'
        }

        a = model.About()
        a.load_dict(test, base_dir)

        c = model.About()
        c.load_dict(test, base_dir)

        b = model.About()
        test.update(dict(about_resource='asdasdasd'))
        b.load_dict(test, base_dir)

        abouts = [a, b]
        results = util.unique(abouts)
        assert [a] == results

    def test_copy_license_notice_files(self):
        base_dir = get_temp_dir()
        reference_dir = get_test_loc('test_util/licenses')
        fields = [(u'license_expression', u'mit or public-domain'),
                  (u'about_resource', u'.'),
                  (u'name', u'test'),
                  (u'license_key', [u'mit', u'public-domain']),
                  (u'license_file', [u'mit.LICENSE, mit2.LICENSE', u'public-domain.LICENSE'])]
        util.copy_license_notice_files(fields, base_dir, reference_dir, '')
        licenses = ['mit.LICENSE', 'mit2.LICENSE', 'public-domain.LICENSE']
        from os import listdir
        copied_files = listdir(base_dir)
        assert len(licenses) == len(copied_files)
        for license in licenses:
            assert license in copied_files

    def test_copy_file(self):
        des = get_temp_dir()
        test_file = get_test_loc('test_util/licenses/mit.LICENSE')
        licenses = ['mit.LICENSE']
        err = util.copy_file(test_file, des)
        from os import listdir
        copied_files = listdir(des)
        assert len(licenses) == len(copied_files)
        assert err == ''
        for license in licenses:
            assert license in copied_files

    def test_copy_file_with_dir(self):
        des = get_temp_dir()
        test_dir = get_test_loc('test_util/licenses/')
        licenses = ['mit.LICENSE', 'mit2.LICENSE', 'public-domain.LICENSE']
        err = util.copy_file(test_dir, des)
        assert err == ''

        import os
        files_list = []
        dir_list = []
        # Get the directories and files in the 'des' recursively
        for root, dir, files in os.walk(des):
            for d in dir:
                dir_list.append(d)
            for f in files:
                files_list.append(f)

        # assert dir_list == [u'licenses']
        assert len(licenses) == len(files_list)
        for license in licenses:
            assert license in files_list
