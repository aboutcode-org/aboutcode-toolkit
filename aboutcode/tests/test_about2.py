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
import stat
import tempfile
import unittest
import logging
import codecs
import posixpath
import sys
import string

from aboutcode import about2
from aboutcode.about2 import Error
from aboutcode.about2 import (CRITICAL, ERROR, INFO,
                                    WARNING, DEBUG, NOTSET)


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


TESTDATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'testdata')


on_windows = 'win' in sys.platform
on_posix = not on_windows

def get_test_loc(path):
    """
    Return the location of a test file or directory given a path relative to
    the testdata directory.
    """
    path = about2.to_posix(path)
    path = about2.to_native(path)
    return os.path.join(TESTDATA_DIR, path)


def get_test_lines(path):
    """
    Return a list of text lines loaded from the location of a test file or
    directory given a path relative to the testdata directory.
    """
    with codecs.open(get_test_loc(path), 'rb', encoding='utf-8') as doc:
        return doc.readlines(True)


def create_dir(location):
    """
    Create directory or directory tree at location, ensuring it is readable
    and writeable.
    """
    if not os.path.exists(location):
        os.makedirs(location)
        os.chmod(location, stat.S_IRWXU | stat.S_IRWXG
                 | stat.S_IROTH | stat.S_IXOTH)


def build_temp_dir(prefix='test-about-code-'):
    """
    Create and return a new unique empty directory created in base_dir.
    """
    location = tempfile.mkdtemp(prefix=prefix)
    create_dir(location)
    return location


def get_temp_file(file_name='test-about-code-tempfile'):
    """
    Return a unique new temporary file location to a non-existing
    temporary file that can safely be created without a risk of name
    collision.
    """
    temp_dir = get_temp_dir()
    location = os.path.join(temp_dir, file_name)
    return location


def get_temp_dir(sub_dir_path=None):
    """
    Create a unique new temporary directory location. Create directories
    identified by sub_dir_path if provided in this temporary directory.
    Return the location for this unique directory joined with the
    sub_dir_path if any.
    """
    new_temp_dir = build_temp_dir()

    if sub_dir_path:
        # create a sub directory hierarchy if requested
        new_temp_dir = os.path.join(new_temp_dir, sub_dir_path)
        create_dir(new_temp_dir)
    return new_temp_dir


class FieldTest(unittest.TestCase):
    def test_Field_init(self):
        about2.Field()
        about2.StringField()
        about2.ListField()
        about2.UrlField()
        about2.BooleanField()
        about2.PathField()
        about2.TextField()

    def test_empty_Field_has_no_content(self):
        field = about2.Field()
        self.assertFalse(field.has_content)

    def test_PathField_check_location(self):
        test_file = 'license.LICENSE'
        field = about2.PathField(name='f', present=True)
        field.value = test_file
        base_dir = get_test_loc('fields')
        errors = field.validate(base_dir=base_dir)
        self.assertEqual([], errors)

        result = field.value[test_file]
        expected = posixpath.join(about2.to_posix(base_dir), test_file)
        self.assertEqual(expected, result)

    def test_PathField_check_missing_location(self):
        test_file = 'does.not.exist'
        field = about2.PathField(name='f', present=True)
        field.value = test_file
        base_dir = get_test_loc('fields')
        errors = field.validate(base_dir=base_dir)

        expected_errors = [
            Error(CRITICAL, u'Field f: Path does.not.exist not found')]
        self.assertEqual(expected_errors, errors)

        result = field.value[test_file]
        self.assertEqual(None, result)

    def test_TextField_loads_file(self):
        field = about2.TextField(name='f', present=True)
        field.value = 'license.LICENSE'

        base_dir = get_test_loc('fields')
        errors = field.validate(base_dir=base_dir)
        self.assertEqual([], errors)

        expected = [('license.LICENSE', u'some license text')]
        result = field.value.items()
        self.assertEqual(expected, result)


class ParseTest(unittest.TestCase):
    maxDiff = None
    def test_parse_can_parse_simple_fields(self):
        test = get_test_lines('parse/basic.about')

        errors, result = list(about2.parse(test))

        self.assertEqual([], errors)

        expected = [(u'single_line', u'optional'),
                    (u'other_field', u'value'),
                    ]
        self.assertEqual(expected, result)

    def test_parse_can_parse_continuations(self):
        test = get_test_lines('parse/continuation.about')
        errors, result = about2.parse(test)

        self.assertEqual([], errors)

        expected = [(u'single_line', u'optional'),
                    (u'other_field', u'value'),
                    (u'multi_line', u'some value\n'
                                     u'and more\n'
                                     u' and yet more')]
        self.assertEqual(expected, result)

    def test_parse_can_handle_complex_continuations(self):
        test = get_test_lines('parse/complex.about')
        errors, result = about2.parse(test)
        self.assertEqual([], errors)

        expected = [(u'single_line', u'optional'),
                    (u'other_field', u'value\n'),
                    (u'multi_line', u'some value\n'
                                     u'and more\n'
                                     u' and yet more\n'
                                     u'  '),
                    (u'yetanother', u'\nsdasd')]
        self.assertEqual(expected, result)

    def test_parse_can_load_location(self):
        test = get_test_loc('parse/complex.about')
        errors, result = about2.parse(test)
        self.assertEqual([], errors)

        expected = [(u'single_line', u'optional'),
                    (u'other_field', u'value' u'\n'),
                    (u'multi_line', u'some value\n'
                                     u'and more\n'
                                     u' and yet more\n'
                                     u'  '),
                    (u'yetanother', u'\n' u'sdasd')]
        self.assertEqual(expected, result)

    def test_parse_error_for_invalid_field_name(self):
        test = get_test_lines('parse/invalid_names.about')
        errors, result = about2.parse(test)
        expected = [(u'val3_id_', u'some:value'),
                    (u'VALE3_ID_', u'some:value')]
        self.assertEqual(expected, result)

        expected_errors = [
            Error(CRITICAL, "Invalid line: 0: u'invalid space:value\\n'"),
            Error(CRITICAL, "Invalid line: 1: u'other-field: value\\n'"),
            Error(CRITICAL, "Invalid line: 4: u'_invalid_dash: value\\n'"),
            Error(CRITICAL, "Invalid line: 5: u'3invalid_number: value\\n'"),
            Error(CRITICAL, "Invalid line: 6: u'invalid.dot: value'")
            ]
        self.assertEqual(expected_errors, errors)

    def test_parse_error_for_invalid_continuation(self):
        test = get_test_lines('parse/invalid_continuation.about')
        errors, result = about2.parse(test)
        expected = [(u'single_line', u'optional'),
                    (u'other_field', u'value'),
                    (u'multi_line', u'some value\n' u'and more')]
        self.assertEqual(expected, result)
        expected_errors = [
            Error(CRITICAL, "Invalid continuation line: 0:"
                            " u' invalid continuation1\\n'"),
            Error(CRITICAL, "Invalid continuation line: 7:"
                            " u' invalid continuation2\\n'")]
        self.assertEqual(expected_errors, errors)

    def test_parse_rejects_non_ascii_names_and_accepts_unicode_values(self):
        test = get_test_lines('parse/non_ascii_field_name_value.about')
        errors, result = about2.parse(test)
        expected = [(u'name', u'name'),
                    (u'about_resource', u'.'),
                    (u'owner', u'Mat\xedas Aguirre')]
        self.assertEqual(expected, result)

        expected_errors = [
            Error(CRITICAL, "Invalid line: 3: u'Mat\\xedas: unicode field name\\n'")]
        self.assertEqual(expected_errors, errors)

    def test_parse_handles_blank_lines_and_spaces_in_field_names(self):
        test = '''
name: test space
version: 0.7.0
about_resource: about.py
field with spaces: This is a test case for field with spaces
'''.splitlines(True)

        errors, result = about2.parse(test)

        expected = [('name', 'test space'),
                    ('version', '0.7.0'),
                    ('about_resource', 'about.py')]
        self.assertEqual(expected, result)

        expected_errors = [
            Error(CRITICAL, "Invalid line: 4: 'field with spaces: This is a test case for field with spaces\\n'")]
        self.assertEqual(expected_errors, errors)

    def test_parse_ignore_blank_lines_and_lines_without_no_colon(self):
        test = '''
name: no colon test
test
version: 0.7.0
about_resource: about.py
test with no colon
'''.splitlines(True)
        errors, result = about2.parse(test)

        expected = [('name', 'no colon test'),
                    ('version', '0.7.0'),
                    ('about_resource', 'about.py')]
        self.assertEqual(expected, result)

        expected_errors = [
            Error(CRITICAL, "Invalid line: 2: 'test\\n'"),
            Error(CRITICAL, "Invalid line: 5: 'test with no colon\\n'")]
        self.assertEqual(expected_errors, errors)


class UtilsTest(unittest.TestCase):

    def test_resource_name(self):
        expected = 'first'
        result = about2.resource_name('some/things/first')
        self.assertEqual(expected, result)

    def test_resource_name_with_extension(self):
        expected = 'first.ABOUT'
        result = about2.resource_name('/some/things/first.ABOUT')
        self.assertEqual(expected, result)

    def test_resource_name_for_dir(self):
        expected = 'first'
        result = about2.resource_name('some/things/first/')
        self.assertEqual(expected, result)

    def test_resource_name_windows(self):
        expected = r'first.'
        result = about2.resource_name(r'c:\some\things\first.')
        self.assertEqual(expected, result)

    def test_resource_name_mixed_windows_posix(self):
        expected = r'first'
        result = about2.resource_name(r'c:\some/things\first')
        self.assertEqual(expected, result)

    def test_resource_name_double_slash(self):
        expected = 'first'
        result = about2.resource_name(r'some\thi ngs//first')
        self.assertEqual(expected, result)

    def test_resource_name_punctuation(self):
        expected = '_$asafg:'
        result = about2.resource_name('%6571351()2/75612$/_$asafg:')
        self.assertEqual(expected, result)

    def test_resource_name_simple_slash(self):
        expected = ''
        result = about2.resource_name('/')
        self.assertEqual(expected, result)

    def test_resource_name_spaces(self):
        expected = ''
        result = about2.resource_name('/  /  ')
        self.assertEqual(expected, result)

    def test_resource_name_does_not_recurse_infinitely(self):
        expected = ''
        result = about2.resource_name(' / ')
        self.assertEqual(expected, result)

    def test_to_posix_from_win(self):
        test = r'c:\this\that'
        expected = 'c:/this/that'
        result = about2.to_posix(test)
        self.assertEqual(expected, result)

    def test_to_posix_from_posix(self):
        test = r'/this/that'
        expected = '/this/that'
        result = about2.to_posix(test)
        self.assertEqual(expected, result)

    def test_to_posix_from_mixed(self):
        test = r'/this/that\this'
        expected = '/this/that/this'
        result = about2.to_posix(test)
        self.assertEqual(expected, result)

    def test_to_native_from_win(self):
        test = r'c:\this\that'
        if on_posix:
            expected = 'c:/this/that'
        else:
            expected = test
        result = about2.to_native(test)
        self.assertEqual(expected, result)

    def test_to_native_from_posix(self):
        test = r'/this/that'
        if on_windows:
            expected = r'\this\that'
        else:
            expected = test
        result = about2.to_native(test)
        self.assertEqual(expected, result)

    def test_to_native_from_mixed(self):
        test = r'/this/that\this'
        if on_windows:
            expected = r'\this\that\this'
        else:
            expected = r'/this/that/this'
        result = about2.to_native(test)
        self.assertEqual(expected, result)

    def test_get_locations(self):
        test_dir = get_test_loc('locations')
        expected = sorted([
                    'locations/file with_spaces',
                    'locations/file1',
                    'locations/file2',
                    'locations/dir1/file2',
                    'locations/dir1/dir2/file1',
                    'locations/dir2/file1'])

        result = sorted(about2.get_locations(test_dir))
        for i, res in enumerate(result):
            expect = expected[i]
            self.assertTrue(res.endswith(expect),
                            '%(res)r does not ends with: %(expect)r'
                            % locals())

    def test_get_about_locations_with_no_ABOUT_files(self):
        test_dir = get_test_loc('locations')
        expected = []
        result = list(about2.get_about_locations(test_dir))
        self.assertEqual(expected, result)

    def test_get_about_locations_with_ABOUT_files(self):
        test_dir = get_test_loc('about_locations')
        expected = sorted([
                    'locations/file with_spaces.ABOUT',
                    'locations/dir1/file2.aBout',
                    'locations/dir1/dir2/file1.about',
                    ])

        result = sorted(about2.get_about_locations(test_dir))
        for i, res in enumerate(result):
            expect = expected[i]
            self.assertTrue(res.endswith(expect),
                            '%(res)r does not ends with: %(expect)r'
                            % locals())

    def test_invalid_chars_with_valid_chars(self):
        name = string.digits + string.ascii_letters + '_-.'
        result = about2.invalid_chars(name)
        expected = []
        self.assertEqual(expected, result)

    def test_invalid_chars_with_invalid_in_name_and_dir(self):
        result = about2.invalid_chars('_$as/afg:')
        expected = [':']
        self.assertEqual(expected, result)

    def test_invalid_chars_in_file_name(self):
        name = '%657!1351()275612$_$asafg:'
        result = about2.invalid_chars(name)
        expected = ['%', '!', '(', ')', '$', '$', ':']
        self.assertEqual(expected, result)

    def test_invalid_chars_with_space(self):
        result = about2.invalid_chars('_ Hello')
        expected = [' ']
        self.assertEqual(expected, result)

    def test_check_file_names_with_dupes_return_errors(self):
        paths = ['some/path',
                 'some/PAth']
        result = about2.check_file_names(paths)
        expected = [Error(CRITICAL, "Duplicate files: 'some/PAth' and 'some/path' have the same case-insensitive file name")]
        self.assertEqual(expected, result)

    def test_check_file_names_without_dupes_return_no_error(self):
        paths = ['some/path',
                 'some/otherpath']
        result = about2.check_file_names(paths)
        expected = []
        self.assertEqual(expected, result)

    def test_check_file_names_with_no_invalid_char_return_no_error(self):
        paths = ['locations/file',
                 'locations/file1',
                 'locations/file2',
                 'locations/dir1/file2',
                 'locations/dir1/dir2/file1',
                 'locations/dir2/file1']

        expected = []
        result = about2.check_file_names(paths)
        self.assertEqual(expected, result)

    def test_check_file_names_with_invalid_chars_return_errors(self):
        paths = ['locations/file',
                 'locations/file with space',
                 'locations/dir1/dir2/file1',
                 'locations/dir2/file1']

        expected = [Error(CRITICAL, "Invalid characters '  ' in file name at: 'locations/file with space'")]
        result = about2.check_file_names(paths)
        self.assertEqual(expected, result)

    def test_log_errors(self):
        errors = [Error(CRITICAL, 'msg1'),
                  Error(ERROR, 'msg2'),
                  Error(INFO, 'msg3'),
                  Error(WARNING, 'msg4'),
                  Error(DEBUG, 'msg4'),
                  Error(NOTSET, 'msg4'),
                  ]

        class MockLogger(object):
            logged = []
            def log(self, severity, message):
                self.logged.append((severity, message,))

        logger = MockLogger()
        about2.log_errors(errors, logger, level=NOTSET)
        result = logger.logged
        expected = [(CRITICAL, 'msg1'),
                    (ERROR, 'msg2'),
                    (INFO, 'msg3'),
                    (WARNING, 'msg4'),
                    (DEBUG, 'msg4'),
                    (NOTSET, 'msg4')]
        self.assertEqual(expected, result)

    def test_is_valid_url(self):
        self.assertTrue(about2.is_valid_url('http://www.google.com'))

    def test_is_valid_url_not_starting_with_www(self):
        self.assertTrue(about2.is_valid_url('https://nexb.com'))
        self.assertTrue(about2.is_valid_url('http://archive.apache.org/dist/httpcomponents/commons-httpclient/2.0/source/commons-httpclient-2.0-alpha2-src.tar.gz'))
        self.assertTrue(about2.is_valid_url('http://de.wikipedia.org/wiki/Elf (Begriffsklärung)'))
        self.assertTrue(about2.is_valid_url('http://nothing_here.com'))

    def test_is_valid_url_no_schemes(self):
        self.assertFalse(about2.is_valid_url('google.com'))
        self.assertFalse(about2.is_valid_url('www.google.com'))
        self.assertFalse(about2.is_valid_url(''))

    def test_is_valid_url_not_ends_with_com(self):
        self.assertTrue(about2.is_valid_url('http://www.google'))

    def test_is_valid_url_ends_with_slash(self):
        self.assertTrue(about2.is_valid_url('http://www.google.co.uk/'))

    def test_is_valid_url_empty_URL(self):
        self.assertFalse(about2.is_valid_url('http:'))

    def test_is_about_file(self):
        self.assertTrue(about2.is_about_file('test.About'))
        self.assertTrue(about2.is_about_file('test2.aboUT'))
        self.assertFalse(about2.is_about_file('no_about_ext.something'))



class AboutTest(unittest.TestCase):

    def test_About_duplicate_field_names_are_detected_with_different_case(self):
        test_file = get_test_loc('parse/dupe_field_name.ABOUT')
        a = about2.About(test_file)
        expected = [
            Error(WARNING, u'Field Name is a duplicate. Original value: "old" replaced with: "new"'),
            Error(INFO, u'Field About_Resource is a duplicate with the same value as before.')]
        result = a.errors
        self.assertEqual(expected, result)

    def test_About_hydrate_normalize_field_names_to_lowercase(self):
        test_file = get_test_loc('parser_tests/upper_field_names.ABOUT')
        a = about2.About()
        expected = set([
            'name',
            'home_url',
            'download_url',
            'version',
            'date',
            'license_spdx',
            'license_text_file',
            'copyright',
            'notice_file',
            'about_resource'])
        errors, fields = about2.parse(test_file)
        self.assertEqual([], errors)

        expected_errors = [
            Error(INFO, u'Field date is a custom field'),
            Error(INFO, u'Field license_spdx is a custom field'),
            Error(INFO, u'Field license_text_file is a custom field')]
        errors = a.hydrate(fields)
        self.assertEqual(expected_errors, errors)
        result = set([f.name for f in a.all_fields() if f.present])
        self.assertEqual(expected, result)

    def test_About_with_existing_about_resource_has_no_error(self):
        test_file = get_test_loc('parser_tests/about_resource_field_present.ABOUT')
        a = about2.About(test_file)
        self.assertEqual([], a.errors)
        result = a.about_resource.value['about_resource.c']
        # this means we have a location
        print(result)
        self.assertNotEqual([], result)

    def test_About_has_errors_when_about_resource_is_missing(self):
        test_file = get_test_loc('parser_tests/.ABOUT')
        a = about2.About(test_file)
        expected = [
                    Error(CRITICAL, u'Field about_resource is required')
                    ]
        result = a.errors
        self.assertEqual(expected, result)

    def test_About_has_errors_when_about_resource_does_not_exist(self):
        test_file = get_test_loc('parser_tests/missing_about_ref.ABOUT')
        a = about2.About(test_file)
        expected = [
            Error(CRITICAL, u'Field about_resource: Path about_file_missing.c not found')]
        result = a.errors
        self.assertEqual(expected, result)

    def test_About_has_errors_when_missing_required_fields_are_missing(self):
        test_file = get_test_loc('parse/missing_required.ABOUT')
        a = about2.About(test_file)
        expected = [
            Error(CRITICAL, u'Field about_resource is required'),
            Error(CRITICAL, u'Field name is required'),
            ]
        result = a.errors
        self.assertEqual(expected, result)

    def test_About_has_errors_when_required_fields_are_empty(self):
        test_file = get_test_loc('parse/empty_required.ABOUT')
        a = about2.About(test_file)
        expected = [
            Error(CRITICAL, u'Field about_resource is required and empty'),
            Error(CRITICAL, u'Field name is required and empty'),
            ]
        result = a.errors
        self.assertEqual(expected, result)

    def test_About_has_errors_with_empty_notice_file_field(self):
        test_file = get_test_loc('parse/empty_notice_field.about')
        a = about2.About(test_file)
        expected = [
            Error(WARNING, u'Field notice_file is present but empty')]
        result = a.errors
        self.assertEqual(expected, result)

    def test_About_custom_fields_are_collected_correctly(self):
        test_file = get_test_loc('parse/custom_fields.about')
        a = about2.About(test_file)
        result = [(n, f.value) for n, f in a.custom_fields.items()]
        expected = [
            (u'single_line', u'README STUFF'),
            (u'multi_line', u'line1\nline2'),
            (u'empty', None)]
        self.assertEqual(expected, result)

    def test_About_has_errors_for_illegal_custom_field_name(self):
        test_file = get_test_loc('parse/illegal_custom_field.about')
        a = about2.About(test_file)
        result = a.custom_fields.items()
        expected = [
            ]
        self.assertEqual(expected, result)

    def test_About_file_fields_are_empty_if_present_and_path_missing(self):
        test_file = get_test_loc('parse/missing_notice_license_files.ABOUT')
        a = about2.About(test_file)
        expected_errors = [
            Error(CRITICAL, u'Field license_file: Path test.LICENSE not found'),
            Error(CRITICAL, u'Field notice_file: Path test.NOTICE not found'),
            ]
        self.assertEqual(expected_errors, a.errors)
        expected = [(u'test.LICENSE', None)]
        result = a.license_file.value.items()
        self.assertEqual(expected, result)

        expected = [(u'test.NOTICE', None)]
        result = a.notice_file.value.items()
        self.assertEqual(expected, result)

    def test_About_notice_and_license_text_are_loaded_from_file(self):
        test_file = get_test_loc('parse/license_file_notice_file.ABOUT')
        a = about2.About(test_file)

        expected = '''Tester holds the copyright for test component. Tester relinquishes copyright of
this software and releases the component to Public Domain.

* Email Test@tester.com for any questions'''

        result = a.license_file.value['license_text.LICENSE']
        self.assertEqual(expected, result)

        expected = '''Test component is released to Public Domain.'''
        result = a.notice_file.value['notice_text.NOTICE']
        self.assertEqual(expected, result)

    def test_About_license_and_notice_text_are_empty_if_field_missing(self):
        test_file = get_test_loc('parse/no_file_fields.ABOUT')
        a = about2.About(test_file)

        expected_errors = []
        self.assertEqual(expected_errors, a.errors)

        result = a.license_file.value
        self.assertEqual(None, result)

        result = a.notice_file.value
        self.assertEqual(None, result)

    def test_About_rejects_non_ascii_names_and_accepts_unicode_values(self):
        a = about2.About(get_test_loc('parse/non_ascii_field_name_value.about'))
        result = a.errors
        expected = [
                    Error(CRITICAL, "Invalid line: 3: u'Mat\\xedas: unicode field name\\n'")
                    ]
        self.assertEqual(expected, result)

