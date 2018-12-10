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

import string
import unittest

import saneyaml

from attributecode import CRITICAL
from attributecode import Error
from attributecode import model
from attributecode import util

from testing_utils import on_posix
from testing_utils import on_windows


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
        name = string.digits + string.ascii_letters + '_-.'
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
        name = '%657!1351()275612$_$asafg:'
        result = util.invalid_chars(name)
        expected = ['%', '!', '(', ')', '$', '$', ':']
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

    def test_get_relative_path(self):
        test = [('/some/path', '/some/path/file', 'file'),
                ('path', '/path/file', 'file'),
                ('/path', '/path/file', 'file'),
                ('/path/', '/path/file/', 'file'),
                ('/p1/p2/p3', '/p1/p2//p3/file', 'file'),
                (r'c:\some/path', 'c:/some/path/file', 'file'),
                (r'c:\\some\\path\\', 'c:/some/path/file', 'file'),
                ]
        for base_loc, full_loc, expected in test:
            result = util.get_relative_path(base_loc, full_loc)
            assert expected == result

    def test_get_relative_path_with_same_path_raise_exception(self):
        try:
            util.get_relative_path('/some/path/file', '/some/path/file')
            self.fail('Exception not raised')
        except AssertionError as e:
            assert 'is the same as' in str(e)


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

    def test_unique_does_deduplicate_and_keep_ordering(self):
        items = ['a', 'b', 'd', 'b', 'c', 'a']
        expected = ['a', 'b', 'd', 'c']
        results = util.unique(items)
        assert expected == results

    def test_unique_can_handle_About_object(self):
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

        a = model.About.from_dict(test)
        c = model.About.from_dict(test)
        b = model.About.from_dict(test)

        abouts = [a, b, c]
        results = util.unique(abouts)
        assert [a] == results
