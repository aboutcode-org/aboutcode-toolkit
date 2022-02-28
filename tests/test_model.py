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

import io
import json
import os
import posixpath
import shutil
import unittest

import mock
import saneyaml

from attributecode import CRITICAL
from attributecode import ERROR
from attributecode import INFO
from attributecode import WARNING
from attributecode import Error
from attributecode import model
from attributecode.util import add_unc, norm, on_windows
from attributecode.util import load_csv
from attributecode.util import to_posix
from attributecode.util import replace_tab_with_spaces

from testing_utils import extract_test_loc
from testing_utils import get_temp_dir
from testing_utils import get_temp_file
from testing_utils import get_test_loc


def check_csv(expected, result, regen=False, fix_cell_linesep=False):
    """
    Assert that the contents of two CSV files locations `expected` and
    `result` are equal.
    """
    if regen:
        shutil.copyfile(result, expected)
    expected = sorted([sorted(d.items()) for d in load_csv(expected)])
    result = [d.items() for d in load_csv(result)]
    if fix_cell_linesep:
        result = [list(fix_crlf(items)) for items in result]
    result = sorted(sorted(items) for items in result)

    assert expected == result


def fix_crlf(items):
    """
    Hackish... somehow the CVS returned on Windows is sometimes using a backward
    linesep convention:
    instead of LF inside cells and CRLF at EOL,
    they use CRLF everywhere.
    This is fixing this until we find can why
    """
    for key, value in items:
        if isinstance(value, str) and '\r\n' in value:
            value = value.replace('\r\n', '\n')
        yield key, value


def check_json(expected, result):
    """
    Assert that the contents of two JSON files are equal.
    """
    with open(expected) as e:
        expected = json.load(e, object_pairs_hook=dict)
    with open(result) as r:
        result = json.load(r, object_pairs_hook=dict)
    assert expected == result


def get_test_content(test_location):
    """
    Read file at test_location and return a unicode string.
    """
    return get_unicode_content(get_test_loc(test_location))


def get_unicode_content(location):
    """
    Read file at location and return a unicode string.
    """
    with io.open(location, encoding='utf-8', errors='replace') as doc:
        return doc.read()


class FieldTest(unittest.TestCase):

    def test_Field_init(self):
        model.Field()
        model.StringField()
        model.ListField()
        model.UrlField()
        model.BooleanField()
        model.PathField()
        model.FileTextField()
        model.PackageUrlField()

    def test_empty_Field_has_no_content(self):
        field = model.Field()
        assert not field.has_content

    def test_empty_Field_has_default_value(self):
        field = model.Field()
        assert '' == field.value

    def test_PathField_check_location(self):
        test_file = 'license.LICENSE'
        field = model.PathField(name='f', value=test_file, present=True)
        base_dir = get_test_loc('test_model/base_dir')

        errors = field.validate(base_dir=base_dir)
        expected_errrors = []
        assert expected_errrors == errors

        result = field.value[test_file]
        expected = add_unc(posixpath.join(to_posix(base_dir), test_file))
        assert expected == result

    def test_PathField_check_missing_location(self):
        test_file = 'does.not.exist'
        field = model.PathField(name='f', value=test_file, present=True)
        base_dir = get_test_loc('test_model/base_dir')
        errors = field.validate(base_dir=base_dir)

        file_path = posixpath.join(base_dir, test_file)
        err_msg = 'Field f: Path %s not found' % file_path

        expected_errors = [
            Error(CRITICAL, err_msg)]
        assert expected_errors == errors

        result = field.value[test_file]
        assert None == result

    def test_TextField_loads_file(self):
        field = model.FileTextField(
            name='f', value='license.LICENSE', present=True)

        base_dir = get_test_loc('test_model/base_dir')
        errors = field.validate(base_dir=base_dir)
        assert [] == errors

        expected = {'license.LICENSE': 'some license text'}
        assert expected == field.value

    def test_PackageUrlField_is_valid_url(self):
        assert model.PackageUrlField.is_valid_purl('pkg:pypi/saneyaml@0.1')

    def test_PackageUrlField_is_valid_url_no_version(self):
        assert model.PackageUrlField.is_valid_purl('pkg:pypi/saneyaml')

    def test_UrlField_is_valid_url(self):
        assert model.UrlField.is_valid_url('http://www.google.com')

    def test_UrlField_is_valid_url_not_starting_with_www(self):
        assert model.UrlField.is_valid_url('https://nexb.com')
        assert model.UrlField.is_valid_url('http://archive.apache.org/dist/httpcomponents/commons-httpclient/2.0/source/commons-httpclient-2.0-alpha2-src.tar.gz')
        assert model.UrlField.is_valid_url('http://de.wikipedia.org/wiki/Elf (Begriffsklärung)')
        assert model.UrlField.is_valid_url('http://nothing_here.com')

    def test_UrlField_is_valid_url_no_schemes(self):
        assert not model.UrlField.is_valid_url('google.com')
        assert not model.UrlField.is_valid_url('www.google.com')
        assert not model.UrlField.is_valid_url('')

    def test_UrlField_is_valid_url_not_ends_with_com(self):
        assert model.UrlField.is_valid_url('http://www.google')

    def test_UrlField_is_valid_url_ends_with_slash(self):
        assert model.UrlField.is_valid_url('http://www.google.co.uk/')

    def test_UrlField_is_valid_url_empty_URL(self):
        assert not model.UrlField.is_valid_url('http:')

    def check_validate(self, field_class, value, expected, expected_errors):
        """
        Check field values after validation
        """
        field = field_class(name='s', value=value, present=True)
        # check that validate can be applied multiple times without side effects
        for _ in range(2):
            errors = field.validate()
            assert expected_errors == errors
            assert expected == field.value

    def test_StringField_validate_trailing_spaces_are_removed(self):
        field_class = model.StringField
        value = 'trailin spaces  '
        expected = 'trailin spaces'
        self.check_validate(field_class, value, expected, expected_errors=[])

    def test_ListField_contains_list_after_validate(self):
        value = 'string'
        field_class = model.ListField
        expected = [value]
        self.check_validate(field_class, value, expected, expected_errors=[])

    def test_ListField_contains_stripped_strings_after_validate(self):
        value = '''first line
                   second line  '''
        field_class = model.ListField
        expected = ['first line', 'second line']
        self.check_validate(field_class, value, expected, expected_errors=[])

    def test_PathField_contains_stripped_strings_after_validate(self):
        value = '''first line
                   second line  '''
        field_class = model.ListField
        expected = ['first line', 'second line']
        self.check_validate(field_class, value, expected, expected_errors=[])

    def test_PathField_contains_dict_after_validate(self):
        value = 'string'
        field_class = model.PathField
        expected = dict([('string', None)])
        expected_errors = [
            Error(ERROR, 'Field s: Unable to verify path: string: No base directory provided')
                          ]
        self.check_validate(field_class, value, expected, expected_errors)

    def test_SingleLineField_has_errors_if_multiline(self):
        value = '''line1
        line2'''
        field_class = model.SingleLineField
        expected = value
        expected_errors = [Error(ERROR, 'Field s: Cannot span multiple lines: line1\n        line2')]
        self.check_validate(field_class, value, expected, expected_errors)


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

    def test_saneyaml_load_can_parse_verbatim_tab_text_unstripped(self):
        test = get_test_content('test_model/parse/continuation_verbatim_with_tab.about')
        data = replace_tab_with_spaces(test)
        result = saneyaml.load(data)

        expected = [
            (u'single_line', u'optional'),
            (u'other_field', u'value'),
            (u'multi_line', u'This is a long description\nwith tab.\n')
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
            (u'Matías', u'unicode field name')
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
        a = model.About(test_file)
        assert [] == a.errors

        expected = ['about_resource', 'name', 'version', 'download_url']
        result = [f.name for f in a.all_fields() if f.present]
        assert expected == result

    def test_About_duplicate_field_names_are_detected_with_different_case(self):
        # This test is failing because the YAML does not keep the order when
        # loads the test files. For instance, it treat the 'About_Resource' as the
        # first element and therefore the dup key is 'about_resource'.
        test_file = get_test_loc('test_model/parse/dupe_field_name.ABOUT')
        a = model.About(test_file)
        expected = [
            Error(WARNING, 'Field About_Resource is a duplicate. Original value: "." replaced with: "new value"'),
            Error(WARNING, 'Field Name is a duplicate. Original value: "old" replaced with: "new"')
        ]

        result = a.errors
        assert sorted(expected) == sorted(result)

    def test_About_duplicate_field_names_are_not_reported_if_same_value(self):
        # This test is failing because the YAML does not keep the order when
        # loads the test files. For instance, it treat the 'About_Resource' as the
        # first element and therefore the dup key is 'about_resource'.
        test_file = get_test_loc('test_model/parse/dupe_field_name_no_new_value.ABOUT')
        a = model.About(test_file)
        expected = [
]
        result = a.errors
        assert sorted(expected) == sorted(result)

    def check_About_hydrate(self, about, fields):
        expected = set([
            'name',
            'homepage_url',
            'download_url',
            'version',
            'copyright',
            'date',
            'license_spdx',
            'license_text_file',
            'notice_file',
            'about_resource'])

        expected_errors = [
            Error(INFO, 'Custom Field: date'),
            Error(INFO, 'Custom Field: license_spdx'),
            Error(INFO, 'Custom Field: license_text_file')]

        errors = about.hydrate(fields)

        assert expected_errors == errors

        result = set([f.name for f in about.all_fields() if f.present])
        assert expected == result

    def test_About_hydrate_normalize_field_names_to_lowercase(self):
        test_content = get_test_content('test_gen/parser_tests/upper_field_names.ABOUT')
        fields = saneyaml.load(test_content).items()
        a = model.About()
        for _ in range(3):
            self.check_About_hydrate(a, fields)

    def test_About_with_existing_about_resource_has_no_error(self):
        test_file = get_test_loc('test_gen/parser_tests/about_resource_field.ABOUT')
        a = model.About(test_file)
        assert [] == a.errors
        result = a.about_resource.value['about_resource.c']
        # this means we have a location
        self.assertNotEqual([], result)

    def test_About_has_errors_when_about_resource_is_missing(self):
        test_file = get_test_loc('test_gen/parser_tests/.ABOUT')
        a = model.About(test_file)
        expected = [Error(CRITICAL, 'Field about_resource is required')]
        result = a.errors
        assert expected == result

    def test_About_has_errors_when_about_resource_does_not_exist(self):
        test_file = get_test_loc('test_gen/parser_tests/missing_about_ref.ABOUT')
        file_path = posixpath.join(posixpath.dirname(test_file), 'about_file_missing.c')
        a = model.About(test_file)
        err_msg = 'Field about_resource: Path %s not found' % file_path
        expected = [Error(INFO, err_msg)]
        result = a.errors
        assert expected == result

    def test_About_has_errors_when_missing_required_fields_are_missing(self):
        test_file = get_test_loc('test_model/parse/missing_required.ABOUT')
        a = model.About(test_file)
        expected = [
            Error(CRITICAL, 'Field about_resource is required'),
            Error(CRITICAL, 'Field name is required'),
        ]
        result = a.errors
        assert expected == result

    def test_About_has_errors_when_required_fields_are_empty(self):
        test_file = get_test_loc('test_model/parse/empty_required.ABOUT')
        a = model.About(test_file)
        expected = [
            Error(CRITICAL, 'Field about_resource is required and empty'),
            Error(CRITICAL, 'Field name is required and empty'),
        ]
        result = a.errors
        assert expected == result

    def test_About_has_errors_with_empty_notice_file_field(self):
        test_file = get_test_loc('test_model/parse/empty_notice_field.about')
        a = model.About(test_file)
        expected = [
            Error(INFO, 'Field notice_file is present but empty.')]
        result = a.errors
        assert expected == result

    def test_About_custom_fields_are_never_ignored(self):
        test_file = get_test_loc('test_model/custom_fields/custom_fields.about')
        a = model.About(test_file)
        result = [(n, f.value) for n, f in a.custom_fields.items()]
        expected = [
            (u'single_line', u'README STUFF'),
            (u'multi_line', u'line1\nline2'),
            (u'other', u'sasasas'),
            (u'empty', u'')
        ]

        assert expected == result

    def test_About_custom_fields_are_not_ignored_and_order_is_preserved(self):
        test_file = get_test_loc('test_model/custom_fields/custom_fields.about')
        a = model.About(test_file)
        result = [(n, f.value) for n, f in a.custom_fields.items()]
        expected = [
            (u'single_line', u'README STUFF'),
            (u'multi_line', u'line1\nline2'),
            (u'other', u'sasasas'),
            (u'empty', u'')
        ]
        assert sorted(expected) == sorted(result)

    def test_About_has_errors_for_illegal_custom_field_name(self):
        test_file = get_test_loc('test_model/parse/illegal_custom_field.about')
        a = model.About(test_file)
        expected_errors = [
            Error(INFO, 'Custom Field: hydrate'),
            Error(CRITICAL, "Internal error with custom field: 'hydrate': 'illegal name'.")
        ]

        assert expected_errors == a.errors
        assert not hasattr(getattr(a, 'hydrate'), 'value')
        field = list(a.custom_fields.values())[0]
        assert 'hydrate' == field.name
        assert 'illegal name' == field.value

    def test_About_file_fields_are_empty_if_present_and_path_missing(self):
        test_file = get_test_loc('test_model/parse/missing_notice_license_files.ABOUT')
        a = model.About(test_file)

        file_path1 = posixpath.join(posixpath.dirname(test_file), 'test.LICENSE')
        file_path2 = posixpath.join(posixpath.dirname(test_file), 'test.NOTICE')

        err_msg1 = Error(CRITICAL, 'Field license_file: Path %s not found' % file_path1)
        err_msg2 = Error(CRITICAL, 'Field notice_file: Path %s not found' % file_path2)

        expected_errors = [err_msg1, err_msg2]
        assert expected_errors == a.errors

        assert {'test.LICENSE': None} == a.license_file.value
        assert {'test.NOTICE': None} == a.notice_file.value

    def test_About_notice_and_license_text_are_loaded_from_file(self):
        test_file = get_test_loc('test_model/parse/license_file_notice_file.ABOUT')
        a = model.About(test_file)

        expected = '''Tester holds the copyright for test component. Tester relinquishes copyright of
this software and releases the component to Public Domain.

* Email Test@tester.com for any questions'''

        result = a.license_file.value['license_text.LICENSE']
        assert expected == result

        expected = '''Test component is released to Public Domain.'''
        result = a.notice_file.value['notice_text.NOTICE']
        assert expected == result

    def test_About_license_and_notice_text_are_empty_if_field_missing(self):
        test_file = get_test_loc('test_model/parse/no_file_fields.ABOUT')
        a = model.About(test_file)
        assert [] == a.errors
        assert {} == a.license_file.value
        assert {} == a.notice_file.value

    def test_About_rejects_non_ascii_names_and_accepts_unicode_values(self):
        test_file = get_test_loc('test_model/parse/non_ascii_field_name_value.about')
        a = model.About(test_file)
        expected = [
            Error(ERROR, "Field name: ['mat\xedas'] contains illegal name characters (or empty spaces) and is ignored.")
        ]
        assert expected == a.errors

    def test_About_invalid_boolean_value(self):
        test_file = get_test_loc('test_model/parse/invalid_boolean.about')
        a = model.About(test_file)
        expected_msg = "Field modified: Invalid flag value: 'blah'"
        assert expected_msg in a.errors[0].message

    def test_About_boolean_value(self):
        test_file = get_test_loc('test_model/parse/boolean_data.about')
        a = model.About(test_file)
        expected_msg = "Field track_changes is present but empty."
        assert expected_msg in a.errors[0].message
        # Context of the test file
        """
        about_resource: .
        name: boolean_data
        attribute: False
        modified: true
        internal_use_only: no
        redistribute: yes
        track_changes:
        """
        assert a.attribute.value is False
        assert a.modified.value is True
        assert a.internal_use_only.value is False
        assert a.redistribute.value is True
        assert a.track_changes.value is None

    def test_About_contains_about_file_path(self):
        test_file = get_test_loc('test_model/serialize/about.ABOUT')
        # TODO: I am not sure this override of the about_file_path makes sense
        a = model.About(test_file, about_file_path='complete/about.ABOUT')
        assert [] == a.errors
        expected = 'complete/about.ABOUT'
        result = a.about_file_path
        assert expected == result

    def test_About_equals(self):
        test_file = get_test_loc('test_model/equal/complete/about.ABOUT')
        a = model.About(test_file, about_file_path='complete/about.ABOUT')
        b = model.About(test_file, about_file_path='complete/about.ABOUT')
        assert a == b

    def test_About_are_not_equal_with_small_text_differences(self):
        test_file = get_test_loc('test_model/equal/complete2/about.ABOUT')
        a = model.About(test_file, about_file_path='complete2/about.ABOUT')
        test_file2 = get_test_loc('test_model/equal/complete/about.ABOUT')
        b = model.About(test_file2, about_file_path='complete/about.ABOUT')
        assert a.dumps() != b.dumps()
        assert a != b

    def test_get_field_names_only_returns_non_empties(self):
        a = model.About()
        a.custom_fields['f'] = model.StringField(
            name='f', value='1', present=True)
        b = model.About()
        b.custom_fields['g'] = model.StringField(
            name='g', value='1', present=True)
        abouts = [a, b]
        # ensure all fields (including custom fields) and
        # about_resource are collected in the correct order
        expected = [
            model.About.ABOUT_RESOURCE_ATTR, 'name', 'f', 'g'
        ]
        result = model.get_field_names(abouts)
        assert expected == result

    def test_get_field_names_does_not_return_duplicates_custom_fields(self):
        a = model.About()
        a.custom_fields['f'] = model.StringField(name='f', value='1',
                                                 present=True)
        a.custom_fields['cf'] = model.StringField(name='cf', value='1',
                                                 present=True)
        b = model.About()
        b.custom_fields['g'] = model.StringField(name='g', value='1',
                                                 present=True)
        b.custom_fields['cf'] = model.StringField(name='cf', value='2',
                                                 present=True)
        abouts = [a, b]
        # ensure all fields (including custom fields) and
        # about_resource are collected in the correct order
        expected = [
            'about_resource',
            'name',
            'cf',
            'f',
            'g',
            ]
        result = model.get_field_names(abouts)
        assert expected == result

    def test_comma_in_license(self):
        test_file = get_test_loc('test_model/special_char/about.ABOUT')
        a = model.About(test_file)
        expected = Error(ERROR, "The following character(s) cannot be in the license_key: [',']")
        assert a.errors[0] == expected

    def test_load_dict_issue_433(self):
        package_data = {
            'about_resource': 'package1.zip',
            'name': 'package',
            'version': '1.0',
            'copyright': 'copyright on package',
            'license_expression': 'license1 AND license2',
            'notice_file': 'package1.zip.NOTICE',
            'licenses': [
                {'key': 'license1', 'name': 'License1', 'file': 'license1.LICENSE', 'url': 'some_url', 'spdx_license_key': 'key'},
                {'key': 'license2', 'name': 'License2', 'file': 'license2.LICENSE', 'url': 'some_url', 'spdx_license_key': 'key'},
            ],
        }
        about = model.About()
        about.load_dict(package_data, base_dir='')
        as_dict = about.as_dict()
        expected = '''about_resource: package1.zip
name: package
version: '1.0'
license_expression: license1 AND license2
copyright: copyright on package
notice_file: package1.zip.NOTICE
licenses:
  - key: license1
    name: License1
    file: license1.LICENSE
    url: some_url
    spdx_license_key: key
  - key: license2
    name: License2
    file: license2.LICENSE
    url: some_url
    spdx_license_key: key
'''
        lic_dict = {u'license1': [u'License1', u'license1.LICENSE',u'', u'some_url', 'key'], u'license2' : [u'License2', u'license2.LICENSE', u'', u'some_url', 'key']}
        assert about.dumps(lic_dict) == expected


class SerializationTest(unittest.TestCase):

    def test_About_dumps(self):
        test_file = get_test_loc('test_model/dumps/about.ABOUT')
        a = model.About(test_file)
        assert [] == a.errors

        expected = '''about_resource: .
name: AboutCode
version: 0.11.0
description: |
  AboutCode is a tool
  to process ABOUT files.
  An ABOUT file is a file.
homepage_url: http://dejacode.org
license_expression: apache-2.0
copyright: Copyright (c) 2013-2014 nexB Inc.
notice_file: NOTICE
owner: nexB Inc.
author: Jillian Daguil, Chin Yeung Li, Philippe Ombredanne, Thomas Druez
vcs_tool: git
vcs_repository: https://github.com/dejacode/about-code-tool.git
licenses:
  - key: apache-2.0
    name: Apache 2.0
    file: apache-2.0.LICENSE
'''
        result = a.dumps()
        assert expected == result

    def test_About_dumps_does_all_non_empty_present_fields(self):
        test_file = get_test_loc('test_model/parse/complete2/about.ABOUT')
        a = model.About(test_file)
        expected_error = [
            Error(INFO, 'Custom Field: custom1'),
            Error(INFO, 'Custom Field: custom2'),
            Error(INFO, 'Field custom2 is present but empty.')
        ]
        assert sorted(expected_error) == sorted(a.errors)

        expected = '''about_resource: .
name: AboutCode
version: 0.11.0
custom1: |
  multi
  line
'''
        result = a.dumps()
        assert expected == result

    def test_About_dumps_with_different_boolean_value(self):
        test_file = get_test_loc('test_model/parse/complete2/about2.ABOUT')
        a = model.About(test_file)
        expected_error_msg = "Field track_changes: Invalid flag value: 'blah' is not one of"
        assert len(a.errors) == 1
        assert expected_error_msg in a.errors[0].message

        expected = '''about_resource: .

name: AboutCode
version: 0.11.0

redistribute: no
attribute: yes
modified: yes
'''

        result = a.dumps()
        assert set(expected) == set(result)

    def test_About_dumps_all_non_empty_fields(self):
        test_file = get_test_loc('test_model/parse/complete2/about.ABOUT')
        a = model.About(test_file)
        expected_error = [
            Error(INFO, 'Custom Field: custom1'),
            Error(INFO, 'Custom Field: custom2'),
            Error(INFO, 'Field custom2 is present but empty.')
        ]
        assert sorted(expected_error) == sorted(a.errors)

        expected = '''about_resource: .
name: AboutCode
version: 0.11.0
custom1: |
  multi
  line
'''
        result = a.dumps()
        assert expected == result

    def test_About_as_dict_contains_special_paths(self):
        test_file = get_test_loc('test_model/special/about.ABOUT')
        a = model.About(test_file, about_file_path='complete/about.ABOUT')
        expected_errors = []
        assert expected_errors == a.errors
        as_dict = a.as_dict()
        expected = 'complete/about.ABOUT'
        result = as_dict[model.About.ABOUT_FILE_PATH_ATTR]
        assert expected == result

    def test_load_dump_is_idempotent(self):
        test_file = get_test_loc('test_model/this.ABOUT')
        a = model.About()
        a.load(test_file)
        dumped_file = get_temp_file('that.ABOUT')
        a.dump(dumped_file)

        expected = get_unicode_content(test_file).splitlines()
        result = get_unicode_content(dumped_file).splitlines()
        # Ignore comment and empty line
        filtered_result = []
        for line in result:
            if not line.startswith('#') and not line == '':
                filtered_result.append(line)
        assert expected == filtered_result

    def test_load_can_load_unicode(self):
        test_file = get_test_loc('test_model/unicode/nose-selecttests.ABOUT')
        a = model.About()
        a.load(test_file)
        file_path = posixpath.join(posixpath.dirname(test_file), 'nose-selecttests-0.3.zip')
        err_msg = 'Field about_resource: Path %s not found' % file_path
        errors = [
            Error(INFO, 'Custom Field: dje_license'),
            Error(INFO, 'Custom Field: license_text_file'),
            Error(INFO, 'Custom Field: scm_tool'),
            Error(INFO, 'Custom Field: scm_repository'),
            Error(INFO, 'Custom Field: test'),
            Error(INFO, err_msg)]

        assert errors == a.errors
        assert 'Copyright (c) 2012, Domen Kožar' == a.copyright.value

    def test_load_non_unicode(self):
        test_file = get_test_loc('test_model/unicode/not-unicode.ABOUT')
        a = model.About()
        a.load(test_file)
        err = a.errors[0]
        assert CRITICAL == err.severity
        assert 'Cannot load invalid ABOUT file' in err.message

    def test_as_dict_load_dict_ignores_empties(self):
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

        expected = {
            'about_file_path': None,
            'about_resource': dict([('.', None)]),
            'copyright': 'Copyright (c) 2013-2014 nexB Inc.',
            'custom1': 'some custom',
            'description': 'AboutCode is a tool\nfor files.',
            'license_expression': 'apache-2.0',
            'name': 'AboutCode',
            'owner': 'nexB Inc.'}

        a = model.About()
        base_dir = 'some_dir'
        a.load_dict(test, base_dir)
        as_dict = a.as_dict()
        # FIXME: why converting back to dict?
        assert expected == dict(as_dict)

    def test_load_dict_as_dict_is_idempotent_ignoring_special(self):
        test = {
            'about_resource': ['.'],
            'attribute': 'yes',
            'author': 'Jillian Daguil, Chin Yeung Li, Philippe Ombredanne, Thomas Druez',
            'copyright': 'Copyright (c) 2013-2014 nexB Inc.',
            'description': 'AboutCode is a tool to process ABOUT files. An ABOUT file is a file.',
            'homepage_url': 'http://dejacode.org',
            'license_expression': 'apache-2.0',
            'name': 'AboutCode',
            'owner': 'nexB Inc.',
            'vcs_repository': 'https://github.com/dejacode/about-code-tool.git',
            'vcs_tool': 'git',
            'version': '0.11.0'}
        a = model.About()
        base_dir = 'some_dir'
        a.load_dict(test, base_dir)
        as_dict = a.as_dict()

        expected = {
            'about_file_path': None,
            'about_resource': dict([('.', None)]),
            'attribute': 'yes',
            'author': 'Jillian Daguil, Chin Yeung Li, Philippe Ombredanne, Thomas Druez',
            'copyright': 'Copyright (c) 2013-2014 nexB Inc.',
            'description': 'AboutCode is a tool to process ABOUT files. An ABOUT file is a file.',
            'homepage_url': 'http://dejacode.org',
            'license_expression': 'apache-2.0',
            'name': 'AboutCode',
            'owner': 'nexB Inc.',
            'vcs_repository': 'https://github.com/dejacode/about-code-tool.git',
            'vcs_tool': 'git',
            'version': '0.11.0'}

        assert expected == dict(as_dict)

    def test_about_model_class_from_dict_constructor(self):
        about_data = {
            'about_resource': ['.'],
            'attribute': 'yes',
            'author': 'Jillian Daguil, Chin Yeung Li, Philippe Ombredanne, Thomas Druez',
            'copyright': 'Copyright (c) 2013-2014 nexB Inc.',
            'description': 'AboutCode is a tool to process ABOUT files. An ABOUT file is a file.',
            'homepage_url': 'http://dejacode.org',
            'license_expression': 'apache-2.0',
            'name': 'AboutCode',
            'owner': 'nexB Inc.',
            'vcs_repository': 'https://github.com/dejacode/about-code-tool.git',
            'vcs_tool': 'git',
            'version': '0.11.0',
        }

        about = model.About.from_dict(about_data)
        assert isinstance(about, model.About)

        about_data.update({
            'about_file_path': None,
            'about_resource': dict([('.', None)]),
        })
        assert about_data == about.as_dict()

    def test_write_output_csv(self):
        path = 'test_model/this.ABOUT'
        test_file = get_test_loc(path)
        abouts = model.About(location=test_file, about_file_path=path)

        result = get_temp_file()
        model.write_output([abouts], result, format='csv')

        expected = get_test_loc('test_model/expected.csv')
        check_csv(expected, result)

    def test_write_output_csv_with_multiple_files(self):
        path = 'test_model/multiple_files.ABOUT'
        test_file = get_test_loc(path)
        abouts = model.About(location=test_file, about_file_path=path)

        result = get_temp_file()
        model.write_output([abouts], result, format='csv')

        expected = get_test_loc('test_model/multiple_files_expected.csv')
        check_csv(expected, result)

    def test_write_output_json(self):
        path = 'test_model/this.ABOUT'
        test_file = get_test_loc(path)
        abouts = model.About(location=test_file, about_file_path=path)

        result = get_temp_file()
        model.write_output([abouts], result, format='json')

        expected = get_test_loc('test_model/expected.json')
        check_json(expected, result)

    def test_android_module_license(self):
        path = 'test_model/android/single_license.c.ABOUT'
        test_file = get_test_loc(path)
        abouts = model.About(location=test_file, about_file_path=path)

        parent_dir = get_temp_dir()
        abouts.android_module_license(parent_dir)
        assert os.path.exists(os.path.join(parent_dir, 'MODULE_LICENSE_PUBLIC_DOMAIN'))

    def test_android_module_multi_licenses(self):
        path = 'test_model/android/multi_license.c.ABOUT'
        test_file = get_test_loc(path)
        abouts = model.About(location=test_file, about_file_path=path)

        parent_dir = get_temp_dir()
        abouts.android_module_license(parent_dir)
        assert os.path.exists(os.path.join(parent_dir, 'MODULE_LICENSE_BSD_NEW'))
        assert os.path.exists(os.path.join(parent_dir, 'MODULE_LICENSE_BSD_SIMPLIFIED'))

    def test_android_notice(self):
        path = 'test_model/android/single_license.c.ABOUT'
        test_file = get_test_loc(path)
        abouts = model.About(location=test_file, about_file_path=path)

        parent_dir = get_temp_dir()
        notice_path, notice_context = abouts.android_notice(parent_dir)
        expected_path = os.path.join(parent_dir, 'NOTICE')
        assert os.path.normpath(notice_path) == expected_path

        expected_notice = '''Copyright (c) xyz

This component is released to the public domain by the author.

'''
        assert notice_context == expected_notice


class CollectorTest(unittest.TestCase):

    def test_collect_inventory_return_errors(self):
        test_loc = get_test_loc('test_model/collect_inventory_errors')
        errors, _abouts = model.collect_inventory(test_loc)
        file_path1 = posixpath.join(test_loc, 'distribute_setup.py')
        file_path2 = posixpath.join(test_loc, 'date_test.py')

        err_msg1 = 'non-supported_date_format.ABOUT: Field about_resource: Path %s not found' % file_path1
        err_msg2 = 'supported_date_format.ABOUT: Field about_resource: Path %s not found' % file_path2
        expected_errors = [
            Error(INFO, "Field ['date'] is a custom field."),
            Error(INFO, err_msg1),
            Error(INFO, err_msg2)]
        assert sorted(expected_errors) == sorted(errors)

    def test_collect_inventory_with_long_path(self):
        test_loc = extract_test_loc('test_model/longpath.zip')
        _errors, abouts = model.collect_inventory(test_loc)
        assert 2 == len(abouts)

        expected_paths = (
            'longpath/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/non-supported_date_format.ABOUT',
            'longpath/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/supported_date_format.ABOUT'
        )
        results = [a.about_file_path for a in abouts]
        assert all(r.endswith(expected_paths) for r in results)

        expected_name = ['distribute', 'date_test']
        result_name = [a.name.value for a in abouts]
        assert sorted(expected_name) == sorted(result_name)

    def test_collect_inventory_can_collect_a_single_file(self):
        test_loc = get_test_loc('test_model/single_file/django_snippets_2413.ABOUT')
        _errors, abouts = model.collect_inventory(test_loc)
        assert 1 == len(abouts)
        expected = ['single_file/django_snippets_2413.ABOUT']
        result = [a.about_file_path for a in abouts]
        assert expected == result

    def test_collect_inventory_return_no_warnings_and_model_can_use_relative_paths(self):
        test_loc = get_test_loc('test_model/rel/allAboutInOneDir')
        errors, _abouts = model.collect_inventory(test_loc)
        expected_errors = []
        result = [(level, e) for level, e in errors if level > INFO]
        assert expected_errors == result

    def test_collect_inventory_populate_about_file_path(self):
        test_loc = get_test_loc('test_model/inventory/complete')
        errors, abouts = model.collect_inventory(test_loc)
        assert [] == errors
        expected = 'about.ABOUT'
        result = abouts[0].about_file_path
        assert expected == result

    def test_collect_inventory_with_multi_line(self):
        test_loc = get_test_loc('test_model/parse/multi_line_license_expresion.ABOUT')
        errors, abouts = model.collect_inventory(test_loc)
        assert [] == errors
        expected_lic_url = [
            'https://enterprise.dejacode.com/urn/?urn=urn:dje:license:mit',
            'https://enterprise.dejacode.com/urn/?urn=urn:dje:license:apache-2.0']
        returned_lic_url = abouts[0].license_url.value
        assert expected_lic_url == returned_lic_url

    def test_collect_inventory_with_license_expression(self):
        test_loc = get_test_loc('test_model/parse/multi_line_license_expresion.ABOUT')
        errors, abouts = model.collect_inventory(test_loc)
        assert [] == errors
        expected_lic = 'mit or apache-2.0'
        returned_lic = abouts[0].license_expression.value
        assert expected_lic == returned_lic

    def test_collect_inventory_always_collects_custom_fieldsg(self):
        test_loc = get_test_loc('test_model/inventory/custom_fields.ABOUT')
        errors, abouts = model.collect_inventory(test_loc)
        expected_msg = "Field ['resource', 'custom_mapping'] is a custom field."
        assert len(errors) == 1
        assert expected_msg in errors[0].message
        # The value of the custom field: 'resource' is collected
        assert abouts[0].resource.value

    def test_collect_inventory_does_not_raise_error_and_maintains_order_on_custom_fields(self):
        test_loc = get_test_loc('test_model/inventory/custom_fields2.ABOUT')
        errors, abouts = model.collect_inventory(test_loc)
        expected_errors = [
            Error(INFO, "Field ['resource', 'custom_mapping'] is a custom field.")
        ]
        assert expected_errors == errors
        expected = [u'about_resource: .\nname: test\nresource: .\ncustom_mapping: test\n']
        assert expected == [a.dumps() for a in abouts]

    def test_parse_license_expression(self):
        spec_char, returned_lic = model.parse_license_expression('mit or apache-2.0')
        expected_lic = ['mit', 'apache-2.0']
        expected_spec_char = []
        assert expected_lic == returned_lic
        assert expected_spec_char == spec_char

    def test_parse_license_expression_with_special_chara(self):
        spec_char, returned_lic = model.parse_license_expression('mit, apache-2.0')
        expected_lic = []
        expected_spec_char = [',']
        assert expected_lic == returned_lic
        assert expected_spec_char == spec_char

    def test_collect_inventory_works_with_relative_paths(self):
        # FIXME: This test need to be run under src/attributecode/
        # or otherwise it will fail as the test depends on the launching
        # location
        test_loc = get_test_loc('test_model/inventory/relative')
        # Use '.' as the indication of the current directory
        test_loc1 = test_loc + '/./'
        # Use '..' to go back to the parent directory
        test_loc2 = test_loc + '/../relative'
        errors1, abouts1 = model.collect_inventory(test_loc1)
        errors2, abouts2 = model.collect_inventory(test_loc2)
        assert [] == errors1
        assert [] == errors2
        expected = 'about.ABOUT'
        result1 = abouts1[0].about_file_path
        result2 = abouts2[0].about_file_path
        assert expected == result1
        assert expected == result2

    def test_collect_inventory_basic_from_directory(self):
        location = get_test_loc('test_model/inventory/basic')
        result = get_temp_file()
        errors, abouts = model.collect_inventory(location)

        model.write_output(abouts, result, format='csv')

        expected_errors = []
        assert expected_errors == errors

        expected = get_test_loc('test_model/inventory/basic/expected.csv')
        check_csv(expected, result)

    def test_collect_inventory_with_about_resource_path_from_directory(self):
        location = get_test_loc('test_model/inventory/basic_with_about_resource_path')
        result = get_temp_file()
        errors, abouts = model.collect_inventory(location)

        model.write_output(abouts, result, format='csv')

        expected_errors = []
        assert expected_errors == errors

        expected = get_test_loc('test_model/inventory/basic_with_about_resource_path/expected.csv')
        check_csv(expected, result)

    def test_collect_inventory_with_no_about_resource_from_directory(self):
        location = get_test_loc('test_model/inventory/no_about_resource_key')
        result = get_temp_file()
        errors, abouts = model.collect_inventory(location)

        model.write_output(abouts, result, format='csv')

        expected_errors = [Error(CRITICAL, 'about/about.ABOUT: Field about_resource is required')]
        assert expected_errors == errors

    def test_collect_inventory_complex_from_directory(self):
        location = get_test_loc('test_model/inventory/complex')
        result = get_temp_file()
        errors, abouts = model.collect_inventory(location)

        model.write_output(abouts, result, format='csv')

        assert all(e.severity == INFO for e in errors)

        expected = get_test_loc('test_model/inventory/complex/expected.csv')
        check_csv(expected, result, fix_cell_linesep=True, regen=False)

    def test_collect_inventory_does_not_convert_lf_to_crlf_from_directory(self):
        location = get_test_loc('test_model/crlf/about.ABOUT')
        result = get_temp_file()
        errors, abouts = model.collect_inventory(location)
        model.write_output(abouts, result, format='csv')
        assert all(e.severity == INFO for e in errors)

        expected = get_test_loc('test_model/crlf/expected.csv')
        check_csv(expected, result, fix_cell_linesep=True, regen=False)

    def test_copy_redist_src_no_structure(self):
        test_loc = get_test_loc('test_model/redistribution/')
        copy_list = [get_test_loc('test_model/redistribution/this.c'), get_test_loc('test_model/redistribution/test/subdir')]
        output = get_temp_dir()

        expected_file = ['this.c', 'subdir']

        with_structure = False
        err = model.copy_redist_src(copy_list, test_loc, output, with_structure)

        assert err == []

        from os import listdir
        copied_files = listdir(output)
        assert len(expected_file) == len(copied_files)
        assert err == []
        for file in expected_file:
            assert file in copied_files

    def test_copy_redist_src_with_structure(self):
        test_loc = get_test_loc('test_model/redistribution/')
        copy_list = [get_test_loc('test_model/redistribution/this.c'), get_test_loc('test_model/redistribution/test/subdir')]
        output = get_temp_dir()

        expected_file = ['this.c', 'test']

        with_structure = True
        err = model.copy_redist_src(copy_list, test_loc, output, with_structure)

        assert err == []

        from os import listdir
        copied_files = listdir(output)
        assert len(expected_file) == len(copied_files)
        assert err == []
        for file in expected_file:
            assert file in copied_files

    def test_get_copy_list(self):
        location = get_test_loc('test_model/redistribution/')
        result = get_temp_file()
        errors, abouts = model.collect_inventory(location)
        copy_list, err = model.get_copy_list(abouts, location)
        assert err == []
        expected = [os.path.join(location, 'this.c'), os.path.join(location, 'test/subdir')]
        if on_windows:
            norm_list = []
            for c in copy_list:
                norm_list.append(norm(c))
            assert norm_list == expected
        else:
            assert copy_list == expected


class FetchLicenseTest(unittest.TestCase):

    @mock.patch.object(model, 'urlopen')
    def test_valid_api_url(self, mock_data):
        mock_data.return_value = ''
        assert model.valid_api_url('non_valid_url') is False

    @mock.patch('attributecode.util.have_network_connection')
    @mock.patch('attributecode.model.valid_api_url')
    def test_pre_process_and_fetch_license_dict_dje(self, have_network_connection, valid_api_url):
        have_network_connection.return_value = True
        valid_api_url.return_value = False
        error_msg = (
            'Network problem. Please check your Internet connection. '
            'License generation is skipped.')
        expected = ({}, [Error(ERROR, error_msg)])
        assert model.pre_process_and_fetch_license_dict([]) == expected

        valid_api_url.return_value = True
        expected = ({}, [])
        assert model.pre_process_and_fetch_license_dict([]) == expected

    @mock.patch('attributecode.util.have_network_connection')
    @mock.patch('attributecode.model.valid_api_url')
    def test_pre_process_and_fetch_license_dict_licensedb(self, have_network_connection, valid_api_url):
        have_network_connection.return_value = False
        valid_api_url.return_value = False
        error_msg = (
            'Network problem. Please check your Internet connection. '
            'License generation is skipped.')
        expected = ({}, [Error(ERROR, error_msg)])
        assert model.pre_process_and_fetch_license_dict([]) == expected

        have_network_connection.return_value = True
        valid_api_url.return_value = True
        expected = ({}, [])

        assert model.pre_process_and_fetch_license_dict([]) == expected