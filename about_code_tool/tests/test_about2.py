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

from about_code_tool import about2
from about_code_tool.about2 import Error, CRITICAL,ERROR, INFO, WARNING

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


TESTDATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'testdata')


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

class AboutTest(unittest.TestCase):
    maxDiff = None
    def test_parse_can_parse_simple_fields(self):
        test = get_test_lines('parse/basic.about')

        errors, result = list(about2.parse(test))

        self.assertEqual([], errors)

        expected = [(u'single_line', [u'optional']),
                    (u'other_field', [u'value']),
                    ]
        self.assertEqual(expected, result)

    def test_parse_can_parse_continuations(self):
        test = get_test_lines('parse/continuation.about')
        errors, result = about2.parse(test)

        self.assertEqual([], errors)

        expected = [(u'single_line', [u'optional']),
                    (u'other_field', [u'value']),
                    (u'multi_line', [u'some value',
                                     u'and more',
                                     u' and yet more'])]
        self.assertEqual(expected, result)

    def test_parse_can_handle_complex_continuations(self):
        test = get_test_lines('parse/complex.about')
        errors, result = about2.parse(test)
        self.assertEqual([], errors)

        expected = [(u'single_line', [u'optional']),
                    (u'other_field', [u'value', u'']),
                    (u'multi_line', [u'some value',
                                     u'and more',
                                     u' and yet more',
                                     u'  ']),
                    (u'yetanother', [u'', u'sdasd'])]
        self.assertEqual(expected, result)

    def test_parse_can_load_location(self):
        test = get_test_loc('parse/complex.about')
        errors, result = about2.parse(test)
        self.assertEqual([], errors)

        expected = [(u'single_line', [u'optional']),
                    (u'other_field', [u'value', u'']),
                    (u'multi_line', [u'some value',
                                     u'and more',
                                     u' and yet more',
                                     u'  ']),
                    (u'yetanother', [u'', u'sdasd'])]
        self.assertEqual(expected, result)

    def test_parse_error_for_invalid_field_name(self):
        test = get_test_lines('parse/invalid_names.about')
        errors, result = about2.parse(test)
        expected = [(u'val3_id_', [u'some:value']),
                    (u'VALE3_ID_', [u'some:value'])]
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
        expected = [(u'single_line', [u'optional']),
                    (u'other_field', [u'value']),
                    (u'multi_line', [u'some value', u'and more'])]
        self.assertEqual(expected, result)
        expected_errors = [
            Error(CRITICAL, "Invalid continuation line: 0:"
                            " u' invalid continuation1\\n'"),
            Error(CRITICAL, "Invalid continuation line: 7:"
                            " u' invalid continuation2\\n'")]
        self.assertEqual(expected_errors, errors)

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

    def test_normalize_dupe_field_names(self):
        test_file = get_test_loc('parser_tests/dupe_field_name.ABOUT')
        a = about2.About(test_file)
        expected = [
            Error(WARNING, u"Field name: duplicated. Value: [u'Apache HTTP Server'] overridden with: [u'Apache HTTP Server dupe']"),
            Error(ERROR, u'Field about_resource: Unable to verify path: about_file_ref.c: No base directory provided')
            ]
        self.assertEqual(expected, a.errors)

    def test_hydrate_normalize_field_names_to_lowercase(self):
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
        errors = a.hydrate(fields)
        result = set([f.name for f in a.all_fields() if f.present])
        self.assertEqual(expected, result)

    def test_validate_about_resource_file_exist(self):
        test_file = get_test_loc('parser_tests/about_resource_field_present.ABOUT')
        a = about2.About(test_file)
        expected_errors = [
             Error(ERROR, u'Field about_resource: Unable to verify path: about_resource.c: No base directory provided'),
             Error(ERROR, u'Field notice_file: Unable to verify path: httpd.NOTICE: No base directory provided'),
             Error(ERROR, u'Field notice_file: No location available. Unable to load text at: httpd.NOTICE')]
        for e in expected_errors:
            self.assertTrue(e in a.errors)

        expected = 'about_resource.c'
        result = a.about_resource.value.keys()[0]
        self.assertEqual(expected, result)

    def test_about_file_with_no_about_resource(self):
        test_file = get_test_loc('parser_tests/.ABOUT')
        a = about2.About(test_file)
        expected = [
                    Error(CRITICAL, u'Field about_resource is required')
                    ]
        result = a.errors
        self.assertEqual(expected, result)

    def test_validate_has_error_when_file_does_not_exist(self):
        test_file = get_test_loc('parser_tests/missing_about_ref.ABOUT')
        a = about2.About(test_file)
        expected = [
            Error(ERROR, u'Field about_resource: Unable to verify path: about_file_missing.c: No base directory provided')]
        result = a.errors
        self.assertEqual(expected, result)

    def test_about_file_with_missing_required(self):
        test_file = get_test_loc('parse/missing_required.ABOUT')
        a = about2.About(test_file)
        expected = [Error(INFO, u'Field date is a custom field'),
            Error(INFO, u'Field license_spdx is a custom field'),
            Error(INFO, u'Field license_text_file is a custom field'),
            Error(CRITICAL, u'Field about_resource is required'),
            Error(CRITICAL, u'Field name is required'),
            Error(ERROR, u'Field notice_file: Unable to verify path: httpd.NOTICE: No base directory provided'),
            Error(ERROR, u'Field notice_file: No location available. Unable to load text at: httpd.NOTICE')]
        result = a.errors
        self.assertEqual(expected, result)

    def test_check_required_fields_about_resource(self):
        test_file = get_test_loc('parser_tests/missing_mand_values.ABOUT')
        a = about2.About(test_file)
        expected = [
            Error(INFO, u'Field date is a custom field'),
            Error(INFO, u'Field license_spdx is a custom field'),
            Error(INFO, u'Field license_text_file is a custom field'),
            Error(WARNING, u'Field version is present but empty'),
            Error(CRITICAL, u'Field about_resource is required and empty'),
            Error(CRITICAL, u'Field name is required and empty'),
            Error(ERROR, u'Field notice_file: Unable to verify path: httpd.NOTICE: No base directory provided'),
            Error(ERROR, u'Field notice_file: No location available. Unable to load text at: httpd.NOTICE')
 ]
        result = a.errors
        self.assertEqual(expected, result)

    def test_about_file_with_empty_notice_file(self):
        test_file = get_test_loc('parser_tests/about_file_ref.c.ABOUT')
        a = about2.About(test_file)
        expected = [
            Error(CRITICAL, u'Field about_resource is required'),
            Error(WARNING, u'Field notice_file is present but empty')]
        result = a.errors
        self.assertEqual(expected, result)
