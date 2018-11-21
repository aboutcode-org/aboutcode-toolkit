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
import json
import posixpath
import shutil
import unittest

import mock

from attributecode import CRITICAL
from attributecode import ERROR
from attributecode import INFO
from attributecode import WARNING
from attributecode import DEFAULT_MAPPING
from attributecode import Error
from attributecode import model
from attributecode.util import add_unc
from attributecode.util import load_csv
from attributecode.util import to_posix

from testing_utils import extract_test_loc
from testing_utils import get_temp_file
from testing_utils import get_test_loc
import saneyaml


def check_csv(expected, result, regen=False):
    """
    Assert that the contents of two CSV files locations `expected` and
    `result` are equal.
    """
    if regen:
        shutil.copyfile(result, expected)
    expected = sorted([sorted(d.items()) for d in load_csv(expected)])
    result = sorted([sorted(d.items()) for d in load_csv(result)])
    assert expected == result


def check_json(expected, result):
    """
    Assert that the contents of two JSON files are equal.
    """
    with open(expected) as e:
        expected = json.load(e, object_pairs_hook=OrderedDict)
    with open(result) as r:
        result = json.load(r, object_pairs_hook=OrderedDict)
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
    with io.open(location, encoding='utf-8') as doc:
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

    def test_empty_Field_has_no_content(self):
        field = model.Field()
        assert not field.has_content

    def test_empty_Field_has_default_value(self):
        field = model.Field()
        assert '' == field.value

    def test_PathField_check_location(self):
        test_file = 'license.LICENSE'
        field = model.PathField(name='f', value=test_file, present=True)
        base_dir = get_test_loc('test_model/fields')

        errors = field.validate(base_dir=base_dir)
        expected_errrors = []
        assert expected_errrors == errors

        result = field.value[test_file]
        expected = add_unc(posixpath.join(to_posix(base_dir), test_file))
        assert expected == result

    def test_PathField_check_missing_location(self):
        test_file = 'does.not.exist'
        field = model.PathField(name='f', value=test_file, present=True)
        base_dir = get_test_loc('test_model/fields')
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

        base_dir = get_test_loc('test_model/fields')
        errors = field.validate(base_dir=base_dir)
        assert [] == errors

        expected = {'license.LICENSE': 'some license text'}
        assert expected == field.value

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
        expected = OrderedDict([('string', None)])
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
            Error(WARNING, 'Field Name is a duplicate. Original value: "old" replaced with: "new"'),
            Error(INFO, 'Field About_Resource is a duplicate with the same value as before.')]
        result = a.errors
        assert sorted(expected) == sorted(result)

    def check_About_hydrate(self, about, fields):
        expected = set([
            'name',
            'homepage_url',
            'download_url',
            'version',
            'copyright',
            'notice_file',
            'about_resource'])

        expected_errors = [
            Error(INFO, 'Field date is not a supported field and is ignored.'),
            Error(INFO, 'Field license_spdx is not a supported field and is ignored.'),
            Error(INFO, 'Field license_text_file is not a supported field and is ignored.')]

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
            Error(WARNING, 'Field notice_file is present but empty')]
        result = a.errors
        assert expected == result

    def test_About_custom_fields_are_ignored_if_not_in_mapping(self):
        test_file = get_test_loc('test_model/custom_fields/custom_fields.about')
        a = model.About(test_file)
        result = [(n, f.value) for n, f in a.custom_fields.items()]
        assert not result

    def test_About_custom_fields_are_not_ignored_if_in_mapping(self):
        test_file = get_test_loc('test_model/custom_fields/custom_fields.about')
        test_mapping = get_test_loc('test_model/custom_fields/mapping.config')
        a = model.About(test_file, mapping_file=test_mapping)
        result = [(n, f.value) for n, f in a.custom_fields.items()]
        expected = [
            ('empty', ''),
            ('single_line', 'README STUFF'),
            ('multi_line', 'line1\nline2'),
        ]
        assert sorted(expected) == sorted(result)

    def test_About_has_errors_for_illegal_custom_field_name(self):
        test_file = get_test_loc('test_model/parse/illegal_custom_field.about')
        a = model.About(test_file)
        result = a.custom_fields
        assert {} == result

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

        expected_errors = []
        assert expected_errors == a.errors

        result = a.license_file.value
        assert {} == result

        result = a.notice_file.value
        assert {} == result

    def test_About_rejects_non_ascii_names_and_accepts_unicode_values(self):
        test_file = get_test_loc('test_model/parse/non_ascii_field_name_value.about')
        a = model.About(test_file)
        result = a.errors
        expected = [
            Error(INFO, 'Field Mat\xedas is not a supported field and is ignored.')]
        assert expected == result

    def test_About_invalid_boolean_value(self):
        test_file = get_test_loc('test_model/parse/invalid_boolean.about')
        a = model.About(test_file)
        expected_msg = "Field modified: Invalid flag value: 'blah'"
        assert expected_msg in a.errors[0].message

    def test_About_contains_about_file_path(self):
        test_file = get_test_loc('test_model/parse/complete/about.ABOUT')
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
        assert a == b

    def test_field_names(self):
        a = model.About()
        a.custom_fields['f'] = model.StringField(name='f', value='1',
                                                 present=True)
        b = model.About()
        b.custom_fields['g'] = model.StringField(name='g', value='1',
                                                 present=True)
        abouts = [a, b]
        # ensure that custom fields and about file path are collected
        # and that all fields are in the correct order
        expected = [
            model.About.about_file_path_attr,
            # model.About.about_resource_path_attr,
            'about_resource',
            'name',
            'version',
            'download_url',
            'description',
            'homepage_url',
            'notes',
            'license_expression',
            'license_key',
            'license_name',
            'license_file',
            'license_url',
            'copyright',
            'notice_file',
            'notice_url',
            'redistribute',
            'attribute',
            'track_changes',
            'modified',
            'internal_use_only',
            'changelog_file',
            'owner',
            'owner_url',
            'contact',
            'author',
            'author_file',
            'vcs_tool',
            'vcs_repository',
            'vcs_path',
            'vcs_tag',
            'vcs_branch',
            'vcs_revision',
            'checksum_md5',
            'checksum_sha1',
            'checksum_sha256',
            'spec_version',
            'f',
            'g']
        result = model.field_names(abouts)
        assert expected == result

    def test_field_names_does_not_return_duplicates_custom_fields(self):
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
        # ensure that custom fields and about file path are collected
        # and that all fields are in the correct order
        # FIXME: this is not USED
        expected = [
            'about_resource',
            'name',
            'cf',
            'f',
            'g',
            ]
        result = model.field_names(abouts, with_paths=False, with_absent=False, with_empty=False)
        assert expected == result


class SerializationTest(unittest.TestCase):
    def test_About_dumps(self):
        test_file = get_test_loc('test_model/parse/complete/about.ABOUT')
        a = model.About(test_file)
        assert [] == a.errors

        expected = '''about_resource: .
name: AboutCode
version: 0.11.0
copyright: Copyright (c) 2013-2014 nexB Inc.
license_expression: apache-2.0
author:
  - Jillian Daguil
  - Chin Yeung Li
  - Philippe Ombredanne
  - Thomas Druez
description: |
  AboutCode is a tool
  to process ABOUT files.
  An ABOUT file is a file.
homepage_url: http://dejacode.org
licenses:
  - key: apache-2.0
    file: apache-2.0.LICENSE
notice_file: NOTICE
owner: nexB Inc.
vcs_repository: https://github.com/dejacode/about-code-tool.git
vcs_tool: git
'''
        result = a.dumps(mapping_file=DEFAULT_MAPPING)
        assert expected == result


    def test_About_dumps_does_not_dump_not_present_with_absent_False(self):
        test_file = get_test_loc('test_model/parse/complete2/about.ABOUT')
        a = model.About(test_file)
        expected_error = [
            Error(INFO, 'Field custom1 is not a supported field and is ignored.'),
            Error(INFO, 'Field custom2 is not a supported field and is ignored.')]
        assert sorted(expected_error) == sorted(a.errors)

        expected = '''about_resource: .
name: AboutCode
version: 0.11.0
'''
        result = a.dumps(with_absent=False)
        assert set(expected) == set(result)

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

        result = a.dumps(mapping_file=False)
        assert set(expected) == set(result)

    def test_About_dumps_does_not_dump_present__empty_with_absent_False(self):
        test_file = get_test_loc('test_model/parse/complete2/about.ABOUT')
        a = model.About(test_file)
        expected_error = [
            Error(INFO, 'Field custom1 is not a supported field and is ignored.'),
            Error(INFO, 'Field custom2 is not a supported field and is ignored.')]
        assert sorted(expected_error) == sorted(a.errors)

        expected = '''about_resource: .
name: AboutCode
version: 0.11.0
'''
        result = a.dumps(mapping_file=False, with_absent=False, with_empty=False)
        assert expected == result

    def test_About_as_dict_contains_special_paths(self):
        test_file = get_test_loc('test_model/parse/complete/about.ABOUT')
        a = model.About(test_file, about_file_path='complete/about.ABOUT')
        expected_errors = []
        assert expected_errors == a.errors
        as_dict = a.as_dict(with_paths=True, with_empty=False, with_absent=False)
        expected = 'complete/about.ABOUT'
        result = as_dict[model.About.about_file_path_attr]
        assert expected == result

    def test_load_dump_is_idempotent(self):
        test_file = get_test_loc('test_model/this.ABOUT')
        a = model.About()
        a.load(test_file)
        dumped_file = get_temp_file('that.ABOUT')
        a.dump(dumped_file, mapping_file=False, with_absent=False, with_empty=False)

        expected = get_unicode_content(test_file).splitlines()
        result = get_unicode_content(dumped_file).splitlines()
        assert expected == result

    def test_load_can_load_unicode(self):
        test_file = get_test_loc('test_model/unicode/nose-selecttests.ABOUT')
        a = model.About()
        a.load(test_file)
        file_path = posixpath.join(posixpath.dirname(test_file), 'nose-selecttests-0.3.zip')
        err_msg = 'Field about_resource: Path %s not found' % file_path
        errors = [
            Error(INFO, 'Field dje_license is not a supported field and is ignored.'),
            Error(INFO, 'Field license_text_file is not a supported field and is ignored.'),
            Error(INFO, 'Field scm_tool is not a supported field and is ignored.'),
            Error(INFO, 'Field scm_repository is not a supported field and is ignored.'),
            Error(INFO, 'Field test is not a supported field and is ignored.'),
            Error(INFO, err_msg)]

        assert errors == a.errors
        assert 'Copyright (c) 2012, Domen Kožar' == a.copyright.value

    def test_load_has_errors_for_non_unicode(self):
        test_file = get_test_loc('test_model/unicode/not-unicode.ABOUT')
        a = model.About()
        a.load(test_file)
        err = a.errors[0]
        assert CRITICAL == err.severity
        assert 'Cannot load invalid ABOUT file' in err.message
        assert 'UnicodeDecodeError' in err.message

    def test_as_dict_load_dict_is_idempotent(self):
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
            'about_resource': OrderedDict([('.', None)]),
            'author': '',
            'copyright': 'Copyright (c) 2013-2014 nexB Inc.',
            'description': 'AboutCode is a tool\nfor files.',
            'license_expression': 'apache-2.0',
            'name': 'AboutCode',
            'owner': 'nexB Inc.'}

        a = model.About()
        base_dir = 'some_dir'
        a.load_dict(test, base_dir)
        as_dict = a.as_dict(with_paths=False, with_absent=False, with_empty=True)
        # FIXME: why converting back to dict?
        assert expected == dict(as_dict)

    def test_load_dict_as_dict_is_idempotent(self):
        test = {
            'about_resource': ['.'],
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
        a = model.About()
        base_dir = 'some_dir'
        a.load_dict(test, base_dir)
        as_dict = a.as_dict(with_paths=False, with_absent=False, with_empty=True)

        expected = {
            'about_resource': OrderedDict([('.', None)]),
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

        assert expected == dict(as_dict)

    def test_write_output_csv(self):
        path = 'test_model/this.ABOUT'
        test_file = get_test_loc(path)
        abouts = model.About(location=test_file, about_file_path=path)

        result = get_temp_file()
        model.write_output([abouts], result, format='csv')

        expected = get_test_loc('test_model/expected.csv')
        check_csv(expected, result)

    def test_write_output_json(self):
        path = 'test_model/this.ABOUT'
        test_file = get_test_loc(path)
        abouts = model.About(location=test_file, about_file_path=path)

        result = get_temp_file()
        model.write_output([abouts], result, format='json')

        expected = get_test_loc('test_model/expected.json')
        check_json(expected, result)


class CollectorTest(unittest.TestCase):

    def test_collect_inventory_return_errors(self):
        test_loc = get_test_loc('test_model/collect_inventory_errors')
        errors, _abouts = model.collect_inventory(test_loc)
        file_path1 = posixpath.join(test_loc, 'distribute_setup.py')
        file_path2 = posixpath.join(test_loc, 'date_test.py')

        err_msg1 = 'non-supported_date_format.ABOUT: Field about_resource: Path %s not found' % file_path1
        err_msg2 = 'supported_date_format.ABOUT: Field about_resource: Path %s not found' % file_path2
        expected_errors = [
            Error(INFO, 'non-supported_date_format.ABOUT: Field date is not a supported field and is ignored.'),
            Error(INFO, 'supported_date_format.ABOUT: Field date is not a supported field and is ignored.'),
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

    def test_collect_inventory_return_no_warnings_and_model_can_uuse_relative_paths(self):
        test_loc = get_test_loc('test_model/rel/allAboutInOneDir')
        errors, _abouts = model.collect_inventory(test_loc)
        expected_errors = []
        result = [(level, e) for level, e in errors if level > INFO]
        assert expected_errors == result

    def test_collect_inventory_populate_about_file_path(self):
        test_loc = get_test_loc('test_model/parse/complete')
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

    def test_collect_inventory_with_mapping(self):
        test_loc = get_test_loc('test_model/parse/name_mapping_test.ABOUT')
        mapping_file = DEFAULT_MAPPING
        errors, abouts = model.collect_inventory(test_loc, mapping_file)
        expected_msg1 = 'Field resource is a custom field'
        expected_msg2 = 'Field custom_mapping is not a supported field and is not defined in the mapping file. This field is ignored.'
        assert len(errors) == 2
        assert expected_msg1 in errors[0].message
        assert expected_msg2 in errors[1].message
        # The not supported 'resource' value is collected
        assert abouts[0].resource.value

    def test_collect_inventory_with_custom_mapping(self):
        test_loc = get_test_loc('test_model/parse/name_mapping_test.ABOUT')
        mapping_file = get_test_loc('test_model/custom_mapping/mapping.config')
        errors, abouts = model.collect_inventory(test_loc, mapping_file)
        expected_msg1 = 'Field resource is a custom field'
        expected_msg2 = 'Field custom_mapping is a custom field'
        assert len(errors) == 2
        assert expected_msg1 in errors[0].message
        assert expected_msg2 in errors[1].message
        # The not supported 'resource' value is collected
        assert abouts[0].resource.value
        assert abouts[0].custom_mapping.value

    def test_collect_inventory_without_mapping(self):
        test_loc = get_test_loc('test_model/parse/name_mapping_test.ABOUT')
        errors, _abouts = model.collect_inventory(test_loc)
        expected_msg1 = 'Field resource is not a supported field and is ignored.'
        expected_msg2 = 'Field custom_mapping is not a supported field and is ignored.'
        assert len(errors) == 2
        assert expected_msg1 in errors[0].message
        assert expected_msg2 in errors[1].message

    def test_saneyaml_load_license_expression(self):
        spec_char, returned_lic = model.parse_license_expression('mit or apache-2.0')
        expected_lic = ['mit', 'apache-2.0']
        expected_spec_char = []
        assert expected_lic == returned_lic
        assert expected_spec_char == spec_char

    def test_saneyaml_load_license_expression_with_special_chara(self):
        spec_char, returned_lic = model.parse_license_expression('mit, apache-2.0')
        expected_lic = []
        expected_spec_char = [',']
        assert expected_lic == returned_lic
        assert expected_spec_char == spec_char

    def test_collect_inventory_works_with_relative_paths(self):
        # FIXME: This test need to be run under src/attributecode/
        # or otherwise it will fail as the test depends on the launching
        # location
        test_loc = get_test_loc('test_model/parse/complete')
        # Use '.' as the indication of the current directory
        test_loc1 = test_loc + '/./'
        # Use '..' to go back to the parent directory
        test_loc2 = test_loc + '/../complete'
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

        expected = get_test_loc('test_model/inventory/no_about_resource_key/expected.csv')
        check_csv(expected, result)

    def test_collect_inventory_complex_from_directory(self):
        location = get_test_loc('test_model/inventory/complex')
        result = get_temp_file()
        errors, abouts = model.collect_inventory(location)

        model.write_output(abouts, result, format='csv')

        assert all(e.severity == INFO for e in errors)

        expected = get_test_loc('test_model/inventory/complex/expected.csv')
        check_csv(expected, result)


class FetchLicenseTest(unittest.TestCase):
    @mock.patch.object(model, 'urlopen')
    def test_valid_api_url(self, mock_data):
        mock_data.return_value = ''
        assert model.valid_api_url('non_valid_url') is False

    @mock.patch('attributecode.util.have_network_connection')
    @mock.patch('attributecode.model.valid_api_url')
    def test_pre_process_and_fetch_license_dict(self, have_network_connection, valid_api_url):
        have_network_connection.return_value = True

        valid_api_url.return_value = False
        error_msg = (
            'Network problem. Please check your Internet connection. '
            'License generation is skipped.')
        expected = ({}, [Error(ERROR, error_msg)])
        assert model.pre_process_and_fetch_license_dict([], '', '') == expected

        valid_api_url.return_value = True
        expected = ({}, [])
        assert model.pre_process_and_fetch_license_dict([], '', '') == expected
