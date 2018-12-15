#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2014-2018 nexB Inc. http://www.nexb.com/ - All rights reserved.
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
import io
import unittest

import saneyaml

from attributecode import CRITICAL
from attributecode import Error
from attributecode import model
from attributecode.util import unique

from testing_utils import get_test_loc


try:
    # Python 2
    unicode  # NOQA
except NameError:  # pragma: nocover
    # Python 3
    unicode = str  # NOQA


def get_test_content(test_location):
    """
    Read file at test_location and return a unicode string.
    """
    return get_unicode_content(get_test_loc(test_location))


def get_unicode_content(location):
    """
    Read file at location and return a unicode string.
    """
    with io.open(location, encoding='utf-8') as doc:
        return doc.read()



class YamlParseTest(unittest.TestCase):
    maxDiff = None

    def test_saneyaml_load_can_parse_simple_fields(self):
        test = get_test_content('test_model/parse/basic.about')
        result = saneyaml.load(test)

        expected = [
            ('single_line', 'optional'),
            ('other_field', 'value'),
        ]

        assert expected == list(result.items())

    def test_saneyaml_load_does_not_convert_to_crlf(self):
        test = get_test_content('test_model/crlf/about.ABOUT')
        result = saneyaml.load(test)

        expected = [
            (u'about_resource', u'.'),
            (u'name', u'pytest'),
            (u'description', u'first line\nsecond line\nthird line\n'),
            (u'copyright', u'copyright')
        ]
        assert expected == list(result.items())

    def test_saneyaml_load_can_parse_continuations(self):
        test = get_test_content('test_model/parse/continuation.about')
        result = saneyaml.load(test)

        expected = [
            ('single_line', 'optional'),
            ('other_field', 'value'),
            (u'multi_line', u'some value and more and yet more')
        ]

        assert expected == list(result.items())

    def test_saneyaml_load_can_handle_multiline_texts_and_strips_text_fields(self):
        test = get_test_content('test_model/parse/complex.about')
        result = saneyaml.load(test)

        expected = [
            ('single_line', 'optional'),
            ('other_field', 'value'),
            ('multi_line', 'some value and more and yet more'),
            ('yetanother', 'sdasd')]

        assert expected == list(result.items())

    def test_saneyaml_load_can_parse_verbatim_text_unstripped(self):
        test = get_test_content('test_model/parse/continuation_verbatim.about')
        result = saneyaml.load(test)

        expected = [
            (u'single_line', u'optional'),
            (u'other_field', u'value'),
            (u'multi_line', u'some value  \n  and more  \n      and yet more   \n \n')
        ]

        assert expected == list(result.items())

    def test_saneyaml_load_report_error_for_invalid_field_name(self):
        test = get_test_content('test_model/parse/invalid_names.about')
        try:
            saneyaml.load(test)
            self.fail('Exception not raised')
        except Exception:
            pass

    def test_saneyaml_dangling_text_is_not_an_invalid_continuation(self):
        test = get_test_content('test_model/parse/invalid_continuation.about')
        result = saneyaml.load(test)
        expected = [
            (u'single_line', u'optional'),
            (u'other_field', u'value'),
            (u'multi_line', u'some value and more\ninvalid continuation2')
        ]
        assert expected == list(result.items())

    def test_saneyaml_load_accepts_unicode_keys_and_values(self):
        test = get_test_content('test_model/parse/non_ascii_field_name_value.about')
        result = saneyaml.load(test)
        expected = [
            ('name', 'name'),
            ('about_resource', '.'),
            ('owner', 'Matías Aguirre'),
            (u'matías', u'unicode field name')
        ]
        assert expected == list(result.items())

    def test_saneyaml_load_accepts_blank_lines_and_spaces_in_field_names(self):
        test = '''
name: test space
version: 0.7.0
about_resource: about.py
field with spaces: This is a test case for field with spaces
'''

        result = saneyaml.load(test)

        expected = [
            ('name', 'test space'),
            ('version', '0.7.0'),
            ('about_resource', 'about.py'),
            (u'field with spaces', u'This is a test case for field with spaces'),
        ]

        assert expected == list(result.items())

    def test_saneyaml_loads_blank_lines_and_lines_without_no_colon(self):
        test = '''
name: no colon test
test
version: 0.7.0
about_resource: about.py
test with no colon
'''
        try:
            saneyaml.load(test)
            self.fail('Exception not raised')
        except Exception:
            pass


class AboutTest(unittest.TestCase):

    def test_About_load_ignores_original_field_order_and_uses_standard_predefined_order(self):
        # fields in this file are not in the standard order
        test_file = get_test_loc('test_model/parse/ordered_fields.ABOUT')
        a = model.About.load(test_file)
        assert [] == a.errors

        expected_std = ['location', 'about_resource', 'name', 'version', 'download_url']
        expected_cust = sorted(['other', 'that'])
        standard, custom = a.fields()
        assert expected_std == standard
        assert expected_cust == sorted(custom)

    def test_About_duplicate_field_names_are_detected_with_different_case(self):
        test_file = get_test_loc('test_model/parse/dupe_field_name.ABOUT')
        try:
            model.About.load(test_file)
            self.fail('Exception not raised')
        except Exception as e:
            expected = (Error(CRITICAL, 'Invalid data: lowercased field names must be unique.'),)
            assert expected == e.args

    def test_About_duplicate_field_names_are_not_reported_if_same_value(self):
        test_file = get_test_loc('test_model/parse/dupe_field_name_no_new_value.ABOUT')
        try:
            model.About.load(test_file)
            self.fail('Exception not raised')
        except Exception as e:
            expected = (Error(CRITICAL,  'Invalid data: lowercased field names must be unique.'),)
            assert expected == e.args

    def test_About_fails_if_field_names_are_not_lowercase(self):
        test_file = get_test_loc('test_model/parser_tests/upper_field_names.ABOUT')
        try:
            model.About.load(test_file)
            self.fail('Exception not raised')
        except Exception as e:
            expected = (Error(CRITICAL,  'Invalid data: all field names must be lowercase.'),)
            assert expected ==e.args

    def test_About_with_existing_about_resource_has_no_error(self):
        test_file = get_test_loc('test_model/parser_tests/about_resource_field.ABOUT')
        a = model.About.load(test_file)
        assert [] == a.errors
        assert a.about_resource

    def test_About_has_errors_when_about_resource_does_not_exist(self):
        test_file = get_test_loc('test_model/parser_tests/missing_about_ref.ABOUT')
        about = model.About.load(test_file)
        about.check_files()

        expected = [
            Error(CRITICAL, 'File about_resource: "about_file_missing.c" does not exists')
        ]
        assert expected == about.errors

    def test_About_raise_exception_when_missing_required_fields_are_missing(self):
        test_file = get_test_loc('test_model/parse/missing_required.ABOUT')

        try:
            model.About.load(test_file)
            self.fail('Exception not raised')
        except Exception as e:
            expected = (
                Error(CRITICAL, 'Field "about_resource" is required and empty or missing.'),
            )
            assert expected == e.args

    def test_About_raise_exception_when_required_fields_are_empty(self):
        test_file = get_test_loc('test_model/parse/empty_required.ABOUT')
        try:
            model.About.load(test_file)
            self.fail('Exception not raised')
        except Exception as e:
            expected = (
                Error(CRITICAL, 'Field "about_resource" is required and empty or missing.'),
            )
            assert expected == e.args

    def test_About_has_no_errors_with_empty_notice_file_field(self):
        test_file = get_test_loc('test_model/parse/empty_notice_field.about')
        a = model.About.load(test_file)
        expected = []
        result = a.errors
        assert expected == result

    def test_About_custom_fields_are_never_ignored_unless_empty(self):
        test_file = get_test_loc('test_model/custom_fields/custom_fields.about')
        a = model.About.load(test_file)
        expected = {
            'single_line': 'README STUFF',
            'multi_line': 'line1\nline2',
            'other': 'sasasas',
        }

        assert expected == a.custom_fields

    def test_About_custom_fields_order_is_ignored_and_order_is_not_preserved(self):
        test_file = get_test_loc('test_model/custom_fields/custom_fields.about')
        a = model.About.load(test_file)
        result = sorted(a.custom_fields.items())
        expected = [
            (u'multi_line', u'line1\nline2'),
            (u'other', u'sasasas'),
            (u'single_line', u'README STUFF'),
        ]
        assert sorted(expected) == sorted(result)

    def test_About_has_info_for_custom_field_name(self):
        test_file = get_test_loc('test_model/parse/illegal_custom_field.about')
        about = model.About.load(test_file)
        assert [] == about.errors

    def test_About_check_files_collect_errors_if_path_missing(self):
        test_file = get_test_loc('test_model/parse/missing_notice_license_files.ABOUT')
        about = model.About.load(test_file)

        about.check_files()

        expected_errors = [
            Error(CRITICAL, 'File notice_file: "test.NOTICE" does not exists'),
            Error(CRITICAL, 'License file: "test.LICENSE" does not exists'),
        ]
        assert expected_errors == about.errors

        assert 'test.NOTICE' == about.notice_file

    def test_About_notice_and_license_text_are_loaded_from_file(self):
        test_file = get_test_loc('test_model/parse/license_file_notice_file.ABOUT')
        a = model.About.load(test_file)
        a.load_files()

        expected = '''Tester holds the copyright for test component. Tester relinquishes copyright of
this software and releases the component to Public Domain.

* Email Test@tester.com for any questions'''
        assert expected == a.licenses[0].text

        expected = '''Test component is released to Public Domain.'''
        assert expected == a.notice_text

    def test_About_license_and_notice_text_are_empty_if_field_missing(self):
        test_file = get_test_loc('test_model/parse/no_file_fields.ABOUT')
        a = model.About.load(test_file)
        assert [] == a.errors
        assert not a.notice_file
        assert [] == a.licenses

    def test_About_cannot_be_created_with_non_ascii_custom_field_names(self):
        test_file = get_test_loc('test_model/parse/non_ascii_field_name_value.about')
        try:
            model.About.load(test_file)
            self.fail('Exception not raised')
        except Exception as e:
            expected = (
                Error(CRITICAL,
                      'Custom field name: \'mat\xedas\' contains illegal characters. '
                      'Only these characters are allowed: ASCII letters, digits '
                      'and "_" underscore. The first character must be a letter.'),
                )
            assert expected == e.args

    def test_About_cannot_be_created_with_invalid_boolean_value(self):
        test_file = get_test_loc('test_model/parse/invalid_boolean.about')
        try:
            model.About.load(test_file)
            self.fail('Exception not raised')
        except Exception as e:
            expected = (
                Error(CRITICAL, "Field name: 'modified' has an invalid flag value: "
                      "'blah': should be one of yes or no or true or false."),
            )
            assert expected == e.args

    def test_About_contains_about_file_path(self):
        test_file = get_test_loc('test_model/serialize/about.ABOUT')
        # TODO: I am not sure this override of the about_file_path makes sense
        a = model.About.load(test_file)
        assert [] == a.errors

        expected = 'test_model/serialize/about.ABOUT'
        assert a.location.endswith(expected)

    def test_About_equals(self):
        test_file = get_test_loc('test_model/equal/complete/about.ABOUT')
        a = model.About.load(test_file)
        b = model.About.load(test_file)
        assert a == b

    def test_About_are_not_equal_with_small_text_differences(self):
        test_file = get_test_loc('test_model/equal/complete/about.ABOUT')
        about = model.About.load(location=test_file)

        test_file2 = get_test_loc('test_model/equal/complete2/about.ABOUT')
        about2 = model.About.load(test_file2)

        assert about.dumps() != about2.dumps()
        assert about != about2

    def test_get_field_names_only_returns_non_empties(self):
        a = model.About(about_resource='.', notice_file='sadasdasd')
        a.custom_fields['f'] = '1'
        expected = ['about_resource', 'notice_file'], ['f']
        assert expected == a.fields()


class SerializationTest(unittest.TestCase):

    def test_About_dumps(self):
        test_file = get_test_loc('test_model/dumps/about.ABOUT')
        a = model.About.load(test_file)
        assert [] == a.errors

        expected = '''about_resource: .
name: AboutCode
version: 0.11.0
description: |
    AboutCode is a tool
    to process ABOUT files.
    An ABOUT file is a file.
homepage_url: http://dejacode.org
copyright: Copyright (c) 2013-2014 nexB Inc.
license_expression: apache-2.0
licenses:
  - file: apache-2.0.LICENSE
    key: apache-2.0
notice_file: NOTICE
owner: nexB Inc.
vcs_tool: git
vcs_repository: https://github.com/dejacode/about-code-tool.git
author:
  - Jillian Daguil
  - Chin Yeung Li
  - Philippe Ombredanne
  - Thomas Druez
'''

        expected = model.About.loads(expected)
        result = model.About.loads(a.dumps())
        assert expected.to_dict() == result.to_dict()

    def test_About_dumps_does_all_non_empty_present_fields(self):
        test_file = get_test_loc('test_model/parse/complete2/about.ABOUT')
        a = model.About.load(test_file)
        assert [] == a.errors

        expected = '''about_resource: .
name: AboutCode
version: 0.11.0
custom1: |
  multi
  line
'''
        result = a.dumps()
        assert expected == result

    def test_About_is_not_created_with_invalid_flag_value(self):
        test_file = get_test_loc('test_model/parse/complete2/about2.ABOUT')
        try:
            model.About.load(test_file)
            self.fail('Exception not raised')
        except Exception as e:
            expected_error = (
                Error(CRITICAL,
                      "Field name: 'track_changes' has an invalid flag value: 'blah':"
                      " should be one of yes or no or true or false."),
            )
            assert expected_error == e.args

    def test_About_dumps_all_non_empty_fields(self):
        test_file = get_test_loc('test_model/parse/complete2/about.ABOUT')
        a = model.About.load(test_file)
        assert [] == a.errors

        expected = '''about_resource: .
name: AboutCode
version: 0.11.0
custom1: |
  multi
  line
'''
        result = a.dumps()
        assert expected == result

    def test_About_to_dict_contains_special_paths(self):
        test_file = get_test_loc('test_model/special/about.ABOUT')
        a = model.About.load(test_file)
        assert [] == sorted(a.errors)

        result = a.to_dict()
        expected = OrderedDict([
            ('about_resource', '.'),
            ('name', 'AboutCode'),
            ('version', '0.11.0'),
            ('description', 'AboutCode is a tool \nto process ABOUT files. \nAn ABOUT file is a file.'),
            ('homepage_url', 'http://dejacode.org'),
            ('copyright', 'Copyright (c) 2013-2014 nexB Inc.'),
            ('license_expression', 'apache-2.0'),
            ('licenses', [OrderedDict([
                ('file', 'apache-2.0.LICENSE'),
                ('key', 'apache-2.0'),
                ])]),
            ('notice_file', 'NOTICE'),
            ('owner', 'nexB Inc.'),
            ('vcs_tool', 'git'),
            ('vcs_repository', 'https://github.com/dejacode/about-code-tool.git'),
            ('author', ['Jillian Daguil', 'Chin Yeung Li', 'Philippe Ombredanne', 'Thomas Druez']),
            ('license_file', 'apache-2.0.LICENSE'),
            ('license_key', 'apache-2.0'),
        ])
        assert expected == result

    def test_load_dump_is_idempotent(self):
        test_file = get_test_loc('test_model/this.ABOUT')
        a = model.About.load(test_file)
        expected = get_unicode_content(test_file).splitlines()
        result = a.dumps().splitlines()
        assert expected == result

    def test_load_can_load_unicode(self):
        test_file = get_test_loc('test_model/unicode/nose-selecttests.ABOUT')
        a = model.About.load(test_file)
        a.check_files()
        errors = [
            Error(CRITICAL, 'File about_resource: "nose-selecttests-0.3.zip" does not exists'),
        ]

        assert errors == unique(a.errors)
        assert 'Copyright (c) 2012, Domen Kožar' == a.copyright

    def test_load_raise_exception_for_non_unicode(self):
        test_file = get_test_loc('test_model/unicode/not-unicode.ABOUT')
        try:
            model.About.load(test_file)
            self.fail('Exception not raised')
        except UnicodeDecodeError:
            pass

    def test_to_dict_load_dict_ignores_empties(self):
        test = {
            'about_resource': '.',
            'author': '',
            'copyright': 'Copyright (c) 2013-2014 nexB Inc.',
            'custom1': 'some custom',
            'custom_empty': '',
            'description': 'AboutCode is a tool\nfor files.',
            'license_expression': 'apache-2.0',
            'name': 'AboutCode',
            'owner': 'nexB Inc.'}

        expected = OrderedDict([
            ('about_resource', u'.'),
            ('name', u'AboutCode'),
            ('description', u'AboutCode is a tool\nfor files.'),
            ('copyright', u'Copyright (c) 2013-2014 nexB Inc.'),
            ('license_expression', u'apache-2.0'),
            ('licenses', [OrderedDict([
                ('file', u'apache-2.0.LICENSE'),
                ('key', u'apache-2.0'),
                ])]),
            ('owner', u'nexB Inc.'),
            (u'custom1', u'some custom')]
        )

        a = model.About.from_dict(test)
        assert expected == a.to_dict()

    def test_load_dict_as_dict_is_idempotent_ignoring_special(self):
        test = {
            'about_resource': '.',
            'attribute': 'yes',
            'author': ['Jillian Daguil, Chin Yeung Li, Philippe Ombredanne, Thomas Druez'],
            'copyright': 'Copyright (c) 2013-2014 nexB Inc.',
            'description': 'AboutCode is a tool to process ABOUT files. An ABOUT file is a file.',
            'homepage_url': 'http://dejacode.org',
            'license_expression': 'apache-2.0',
            'name': 'AboutCode',
            'owner': 'nexB Inc.',
            'vcs_repository': 'https://github.com/dejacode/about-code-tool.git',
            'vcs_tool': 'git',
            'version': '0.11.0'}

        a = model.About.from_dict(test)

        expected = {
            'about_resource': '.',
            'attribute': True,
            'author': ['Jillian Daguil, Chin Yeung Li, Philippe Ombredanne, Thomas Druez'],
            'copyright': 'Copyright (c) 2013-2014 nexB Inc.',
            'description': 'AboutCode is a tool to process ABOUT files. An ABOUT file is a file.',
            'homepage_url': 'http://dejacode.org',
            'license_expression': 'apache-2.0',
            'licenses': [OrderedDict([
                ('file', u'apache-2.0.LICENSE'),
                ('key', u'apache-2.0'),
                ])],
            'name': 'AboutCode',
            'owner': 'nexB Inc.',
            'vcs_repository': 'https://github.com/dejacode/about-code-tool.git',
            'vcs_tool': 'git',
            'version': '0.11.0'}

        assert expected == dict(a.to_dict())

    def test_about_model_class_from_dict_constructor(self):
        data = OrderedDict([
            ('about_resource', '.'),
            ('name', 'AboutCode'),
            ('version', '0.11.0'),
            ('description', 'AboutCode is a tool to process ABOUT files. An ABOUT file is a file.'),
            ('homepage_url', 'http://dejacode.org'),
            ('copyright', 'Copyright (c) 2013-2014 nexB Inc.'),
            ('license_expression', 'apache-2.0'),
            ('attribute', True),
            ('licenses', [OrderedDict([
                ('file', 'apache-2.0.LICENSE'),
                ('key', 'apache-2.0'),
                ])]),
            ('owner', 'nexB Inc.'),
            ('vcs_tool', 'git'),
            ('vcs_repository', 'https://github.com/dejacode/about-code-tool.git'),
            ('author', [
                'Jillian Daguil, Chin Yeung Li, Philippe Ombredanne, Thomas Druez'])])
        about = model.About.from_dict(data)
        assert data.items() == about.to_dict().items()


class ReferenceTest(unittest.TestCase):

    def test_get_reference_licenses_can_load_non_utf_files(self):
        test_dir = get_test_loc('test_model/reference')
        notices_by_name, licenses_by_key = model.get_reference_licenses(test_dir)
        assert ['bad.NOTICE'] == list(notices_by_name.keys())
        assert ['weird'] == list(licenses_by_key.keys())
