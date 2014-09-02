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

import string
from StringIO import StringIO
import tempfile
import unittest
from unittest.case import skip
import os
import stat
from os.path import abspath, dirname, join

from about_code_tool import about


TESTDATA_DIR = join(abspath(dirname(__file__)), 'testdata')


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


class CollectorTest(unittest.TestCase):
    def test_return_path_is_not_abspath_and_contains_subdirs_on_file(self):
        # Using a relative path for the purpose of this test
        test_file = ('about_code_tool/tests/testdata/thirdparty'
                    '/django_snippets_2413.ABOUT')
        output = get_temp_file()
        collector = about.Collector(test_file)
        collector.write_to_csv(output)
        expected = ('about_code_tool/tests/testdata/thirdparty'
                    '/django_snippets_2413.ABOUT')
        # FIXME: why [2]? what this test means?
        with open(output) as f:
            self.assertTrue(f.read().partition('\n')[2].startswith(expected))

    def test_return_path_is_not_abspath_and_contains_subdirs_on_dir(self):
        # Using a relative path for the purpose of this test
        test_file = 'about_code_tool/tests/testdata/basic'
        output = get_temp_file()
        collector = about.Collector(test_file)
        collector.write_to_csv(output)
        expected = 'about_code_tool/tests/testdata/basic'
        # FIXME: why [2]? what this test means?
        with open(output) as f:
            self.assertTrue(f.read().partition('\n')[2].startswith(expected))

    def test_header_row_in_csv_output(self):
        expected_header = ('about_file,name,version,about_resource,'
        'about_resource_path,spec_version,date,description,description_file,'
        'home_url,download_url,readme,readme_file,install,install_file,'
        'changelog,changelog_file,news,news_file,news_url,notes,notes_file,'
        'contact,owner,author,author_file,copyright,copyright_file,'
        'notice,notice_file,notice_url,license_text,license_text_file,'
        'license_url,license_spdx,redistribute,attribute,track_changes,'
        'vcs_tool,vcs_repository,vcs_path,vcs_tag,vcs_branch,vcs_revision,'
        'checksum_sha1,checksum_md5,checksum_sha256,dje_component,'
        'dje_license,dje_organization,dje_license_name,scm_branch,'
        'scm_repository,signature_gpg_file,redistribute_sources,about_format,'
        'usage,scm_tool,scm_path,scm_tag,scm_rev,organization,'
        'warnings,errors')

        test_file = 'about_code_tool/tests/testdata/basic'
        output = get_temp_file()
        collector = about.Collector(test_file)
        collector.write_to_csv(output)
        with open(output) as f:
            header_row = f.readline().replace('\n', '').replace('\r', '')
            self.assertEqual(expected_header, header_row)

    def test_collect_can_collect_a_directory_tree(self):
        test_dir = 'about_code_tool/tests/testdata/DateTest'
        expected = [('about_code_tool/tests/testdata/DateTest'
                     '/non-supported_date_format.ABOUT'),
                    ('about_code_tool/tests/testdata/DateTest'
                     '/supported_date_format.ABOUT')]
        result = about.Collector.collect(test_dir)
        self.assertEqual(sorted(expected), sorted(result))

    def test_collect_can_collect_a_single_file(self):
        test_file = ('about_code_tool/tests/testdata/thirdparty'
                      '/django_snippets_2413.ABOUT')
        expected = ['about_code_tool/tests/testdata/thirdparty'
                    '/django_snippets_2413.ABOUT']
        result = about.Collector.collect(test_file)
        self.assertEqual(expected, result)

    def test_collector_errors_encapsulation(self):
        test_file = 'about_code_tool/tests/testdata/DateTest'
        collector = about.Collector(test_file)
        self.assertEqual(2, len(collector.errors))

    def test_collector_warnings_encapsulation(self):
        test_file = 'about_code_tool/tests/testdata/allAboutInOneDir'
        collector = about.Collector(test_file)
        # self.assertEqual(4, len(collector.warnings))
        # No warning is thrown as all fields from ABOUT files are accepted.
        self.assertEqual(0, len(collector.warnings))

class ParserTest(unittest.TestCase):
    def test_valid_chars_in_field_name(self):
        name = string.digits + string.ascii_letters + '_'
        line = string.digits + string.ascii_letters + '_'
        result, _warn = about.check_invalid_chars(name, line)
        expected = []
        self.assertEqual(expected, result)

    def test_result_chars_in_field_name(self):
        name = '_$asafg:'
        line = '_$asafg: test'
        result, _warn = about.check_invalid_chars(name, line)
        expected = ['$', ':']
        self.assertEqual(expected, result)

    def test_result_space_in_field_name(self):
        name = '_ Hello'
        line = '_ Hello'
        result, _warn = about.check_invalid_chars(name, line)
        expected = [' ']
        self.assertEqual(expected, result)

    def test_valid_chars_in_file_name(self):
        about_obj = about.AboutFile()
        name = string.digits + string.ascii_letters + '_-.'
        result = about_obj.invalid_chars_in_about_file_name(name)
        expected = []
        self.assertEqual(expected, result)

    def test_result_chars_in_file_name(self):
        about_obj = about.AboutFile()
        result = about_obj.invalid_chars_in_about_file_name('_$as/afg:')
        expected = [':']
        self.assertEqual(expected, result)

    def test_result_chars_in_file_name_path(self):
        about_obj = about.AboutFile()
        name = '%6571351()275612$/_$asafg:/'
        result = about_obj.invalid_chars_in_about_file_name(name)
        expected = []
        self.assertEqual(expected, result)

    def test_result_chars_in_file_name_path2(self):
        about_obj = about.AboutFile()
        name = '%6571351()275612$_$asafg:'
        result = about_obj.invalid_chars_in_about_file_name(name)
        expected = ['%', '(', ')', '$', '$', ':']
        self.assertEqual(expected, result)

    def test_result_space_in_file_name(self):
        about_obj = about.AboutFile()
        result = about_obj.invalid_chars_in_about_file_name('_ Hello')
        expected = [' ']
        self.assertEqual(expected, result)

    def test_resource_name(self):
        expected = 'first'
        result = about.resource_name('some/things/first')
        self.assertEqual(expected, result)

    def test_resource_name1(self):
        expected = 'first'
        result = about.resource_name('some/things/first/')
        self.assertEqual(expected, result)

    def test_resource_name2(self):
        expected = r'things\first'
        result = about.resource_name(r'c:\some/things\first')
        self.assertEqual(expected, result)

    def test_resource_name3(self):
        expected = 'first'
        result = about.resource_name(r'some\thi ngs//first')
        self.assertEqual(expected, result)

    def test_resource_name4(self):
        expected = r'\\'
        result = about.resource_name(r'%6571351()275612$/_$asafg:/\\')
        self.assertEqual(expected, result)

    def test_resource_name5(self):
        expected = '_$asafg:'
        result = about.resource_name('%6571351()2/75612$/_$asafg:')
        self.assertEqual(expected, result)

    def test_resource_name_does_not_recurse_infinitely(self):
        expected = ''
        result = about.resource_name('/')
        self.assertEqual(expected, result)

    def test_resource_name_does_not_recurse_infinitely2(self):
        expected = ''
        result = about.resource_name('/  /  ')
        self.assertEqual(expected, result)

    def test_resource_name_does_not_recurse_infinitely3(self):
        expected = ''
        result = about.resource_name(' / ')
        self.assertEqual(expected, result)

    def test_pre_process_when_user_forgets_colon(self):
        text_input = '''
about_resource: jquery.js
name: jQuery
version: 1.2.3
notes this is the first line.
 this is the second.
 this is the third.
date: 2013-01-02
'''
        expected = '''about_resource: jquery.js
name: jQuery
version: 1.2.3
date: 2013-01-02
'''
        expected_warnings = [(about.IGNORED, 'notes this is the first line.\n'),
                             (about.IGNORED, ' this is the second.\n',),
                             (about.IGNORED, ' this is the third.\n',)]

        about_obj = about.AboutFile()
        result, warn = about.AboutFile.pre_process(about_obj, StringIO(text_input))
        self.assertEqual(expected, result.read())
        for i, w in enumerate(warn):
            self.assertEqual(expected_warnings[i][0], w.code)
            self.assertEqual(expected_warnings[i][1], w.field_value)

    def test_user_forget_space_for_continuation_line(self):
        text_input = '''
about_resource: jquery.js
name: jQuery
version: 1.2.3
notes: this is the first line.
this is the second.
 this is the third.
date: 2013-01-02
'''

        expected = '''about_resource: jquery.js
name: jQuery
version: 1.2.3
notes: this is the first line.
date: 2013-01-02
'''

        expected_warnings = [(about.IGNORED, 'this is the second.\n'),
                             (about.IGNORED, ' this is the third.\n')]
        about_obj = about.AboutFile()
        result, warn = about.AboutFile.pre_process(about_obj, StringIO(text_input))
        self.assertEqual(expected, result.read())
        for i, w in enumerate(warn):
            self.assertEqual(expected_warnings[i][0], w.code)
            self.assertEqual(expected_warnings[i][1], w.field_value)

    def test_pre_process_with_invalid_chars_in_field_name(self):
        text_input = '''
about_resource: jquery.js
name: jQuery
vers|ion: 1.2.3
'''
        expected = '''about_resource: jquery.js
name: jQuery
'''
        about_obj = about.AboutFile()
        result, warn = about.AboutFile.pre_process(about_obj, StringIO(text_input))
        self.assertEqual(about.IGNORED, warn[0].code)
        self.assertEqual('vers|ion', warn[0].field_name)
        self.assertEqual(expected, result.read())

    def test_pre_process_with_spaces_left_of_colon(self):
        text_input = '''
about_resource   : jquery.js
name: jQuery
version: 1.2.3
'''
        expected = '''about_resource: jquery.js
name: jQuery
version: 1.2.3
'''
        about_obj = about.AboutFile()
        result, _warn = about.AboutFile.pre_process(about_obj,
                                                    StringIO(text_input))
        self.assertEqual(expected, result.read())

    def test_handles_last_line_is_a_continuation_line(self):
        warnings = []
        warn = about.AboutFile.check_line_continuation(' Last line is a continuation line.', True)
        warnings.append(warn)
        self.assertEqual(warnings, [''])

    def test_handles_last_line_is_not_a_continuation_line(self):
        warnings = []
        warn = about.AboutFile.check_line_continuation(' Last line is NOT a continuation line.', False)
        warnings.append(warn)
        self.assertEqual(1, len(warnings))

    def test_normalize_dupe_field_names(self):
        about_file = about.AboutFile(join(TESTDATA_DIR, 'parser_tests/dupe_field_name.ABOUT'))
        expected_warnings = [about.IGNORED, 'Apache HTTP Server']
        self.assertEqual(1, len(about_file.warnings))
        for w in about_file.warnings:
            self.assertEqual(expected_warnings[0], w.code)
            self.assertEqual(expected_warnings[1], w.field_value)

    def test_normalize_lowercase(self):
        about_file = about.AboutFile(join(TESTDATA_DIR, 'parser_tests/upper_field_names.ABOUT'))
        expected = {'name': 'Apache HTTP Server\nthis is a continuation',
                    'home_url': 'http://httpd.apache.org',
                    'download_url': 'http://archive.apache.org/dist/httpd/httpd-2.4.3.tar.gz',
                    'version': '2.4.3',
                    'date': '2012-08-21',
                    'license_spdx': 'Apache-2.0',
                    'license_text_file': 'httpd.LICENSE',
                    'copyright':'Copyright 2012 The Apache Software Foundation.',
                    'notice_file':'httpd.NOTICE',
                    'about_resource': 'about_file_ref.c', }
        self.assertTrue(all(item in about_file.validated_fields.items() for item in expected.items()))

    def test_validate_about_ref_testing_the_about_resource_field_is_present(self):
        test_file = join(TESTDATA_DIR, 'parser_tests/about_resource_field_present.ABOUT')
        about_file = about.AboutFile(test_file)
        expected = 'about_resource.c'
        self.assertEqual(about_file.about_resource, expected)

    def test_validate_about_ref_no_about_ref_key(self):
        about_file = about.AboutFile(join(TESTDATA_DIR, 'parser_tests/.ABOUT'))
        # We do not need 'about_resource' now, so no error should be thrown.
        # expected_errors = [about.VALUE, 'about_resource']
        self.assertEqual(0, len(about_file.errors))
        '''for w in about_file.errors:
            self.assertEqual(expected_errors[0], w.code)
            self.assertEqual(expected_errors[1], w.field_name)'''

    def test_validate_about_resource_error_thrown_when_file_referenced_by_about_file_does_not_exist(self):
        about_file = about.AboutFile(join(TESTDATA_DIR, 'parser_tests/missing_about_ref.ABOUT'))
        expected_errors = [about.FILE, 'about_resource']
        self.assertEqual(1, len(about_file.errors))
        for w in about_file.errors:
            self.assertEqual(expected_errors[0], w.code)
            self.assertEqual(expected_errors[1], w.field_name)

    def test_validate_mand_fields_name_and_version_and_about_resource_present(self):
        about_file = about.AboutFile(join(TESTDATA_DIR, 'parser_tests/missing_mand.ABOUT'))
        expected_errors = [(about.VALUE, 'name'),
                           (about.VALUE, 'version'), ]
        self.assertEqual(2, len(about_file.errors))
        for i, w in enumerate(about_file.errors):
            self.assertEqual(expected_errors[i][0], w.code)
            self.assertEqual(expected_errors[i][1], w.field_name)

        about_file = about.AboutFile(join(TESTDATA_DIR, 'parser_tests/missing_mand_values.ABOUT'))
        expected_errors = [(about.VALUE, 'name'),
                             (about.VALUE, 'version')]
        self.assertEqual(2, len(about_file.errors))
        for i, w in enumerate(about_file.errors):
            self.assertEqual(expected_errors[i][0], w.code)
            self.assertEqual(expected_errors[i][1], w.field_name)

    def test_validate_optional_file_field_value(self):
        about_file = about.AboutFile(join(TESTDATA_DIR, 'parser_tests/about_file_ref.c.ABOUT'))
        expected_warnings = [about.VALUE, 'notice_file']
        self.assertEqual(1, len(about_file.warnings))
        for w in about_file.warnings:
            self.assertEqual(expected_warnings[0], w.code)
            self.assertEqual(expected_warnings[1], w.field_name)


class UrlCheckTest(unittest.TestCase):
    @skip('# FIXME: we should use a mock HTTP server AND NEVER do live HTTP requests')
    def test_check_url__with_network(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url('http://www.google.com', True))
        self.assertTrue(about_file.check_url('http://www.google.co.uk/', True))

    @skip('# FIXME: we should use a mock HTTP server AND NEVER do live HTTP requests')
    def test_check_url__with_network__not_starting_with_www(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url('https://nexb.com', True))
        self.assertTrue(about_file.check_url('http://archive.apache.org/dist/httpcomponents/commons-httpclient/2.0/source/commons-httpclient-2.0-alpha2-src.tar.gz', True))
        if about.check_network_connection():
            self.assertFalse(about_file.check_url('http://nothing_here.com', True))

    @skip('# FIXME: we should use a mock HTTP server AND NEVER do live HTTP requests')
    def test_check_url__with_network__not_starting_with_www_and_spaces(self):
        # TODO: this does work yet as we do not have a solution for now (URL with spaces)
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url(u'http://de.wikipedia.org/wiki/Elf (Begriffsklärung)', True))

    @skip('# FIXME: we should use a mock HTTP server AND NEVER do live HTTP requests')
    def test_check_url__with_network__no_schemes(self):
        about_file = about.AboutFile()
        self.assertFalse(about_file.check_url('google.com', True))
        self.assertFalse(about_file.check_url('www.google.com', True))
        self.assertFalse(about_file.check_url('', True))

    @skip('# FIXME: we should use a mock HTTP server AND NEVER do live HTTP requests')
    def test_check_url__with_network__not_reachable(self):
        about_file = about.AboutFile()
        if about.check_network_connection():
            self.assertFalse(about_file.check_url('http://www.google', True))

    @skip('# FIXME: we should use a mock HTTP server AND NEVER do live HTTP requests')
    def test_check_url__with_network__empty_URL(self):
        about_file = about.AboutFile()
        self.assertFalse(about_file.check_url('http:', True))

    def test_check_url__without_network(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url('http://www.google.com', False))

    def test_check_url__without_network__not_starting_with_www(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url('https://nexb.com', False))
        self.assertTrue(about_file.check_url('http://archive.apache.org/dist/httpcomponents/commons-httpclient/2.0/source/commons-httpclient-2.0-alpha2-src.tar.gz', False))
        self.assertTrue(about_file.check_url('http://de.wikipedia.org/wiki/Elf (Begriffsklärung)', False))
        self.assertTrue(about_file.check_url('http://nothing_here.com', False))

    def test_check_url__without_network__no_schemes(self):
        about_file = about.AboutFile()
        self.assertFalse(about_file.check_url('google.com', False))
        self.assertFalse(about_file.check_url('www.google.com', False))
        self.assertFalse(about_file.check_url('', False))

    def test_check_url__without_network__not_ends_with_com(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url('http://www.google', False))

    def test_check_url__without_network__ends_with_slash(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url('http://www.google.co.uk/', False))

    def test_check_url__without_network__empty_URL(self):
        about_file = about.AboutFile()
        self.assertFalse(about_file.check_url('http:', False))


class ValidateTest(unittest.TestCase):
    def test_is_valid_about_file(self):
        self.assertTrue(about.is_about_file('test.About'))
        self.assertTrue(about.is_about_file('test2.aboUT'))
        self.assertFalse(about.is_about_file('no_about_ext.something'))

    def test_validate_is_ascii_key(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_is_ascii('abc'))
        self.assertTrue(about_file.check_is_ascii('123'))
        self.assertTrue(about_file.check_is_ascii('!!!'))
        self.assertFalse(about_file.check_is_ascii(u'測試'))

    def test_validate_is_ascii_value(self):
        about_file = about.AboutFile(join(TESTDATA_DIR, 'filesfields/non_ascii_field.about'))
        expected_errors = [about.ASCII]
        self.assertEqual(1, len(about_file.errors))
        self.assertEqual(about_file.errors[0].code, expected_errors[0])

    def test_validate_spdx_licenses(self):
        test_file = join(TESTDATA_DIR, 'spdx_licenses/incorrect_spdx.about')
        about_file = about.AboutFile(test_file)
        expected_errors = [about.SPDX]
        self.assertEqual(1, len(about_file.errors))
        for w in about_file.errors:
            self.assertEqual(expected_errors[0], w.code)

    def test_validate_spdx_licenses1(self):
        test_file = join(TESTDATA_DIR,
                         'spdx_licenses/invalid_multi_format_spdx.ABOUT')
        about_file = about.AboutFile(test_file)
        expected_errors = [about.SPDX]
        self.assertEqual(1, len(about_file.errors))
        for w in about_file.errors:
            self.assertEqual(expected_errors[0], w.code)

    def test_validate_spdx_licenses2(self):
        test_file = join(TESTDATA_DIR,
                         'spdx_licenses/invalid_multi_name.ABOUT')
        about_file = about.AboutFile(test_file)
        expected_errors = [about.SPDX]
        # The test case is: license_spdx: Something and SomeOtherThings
        # Thus, it should throw 2 errors: 'Something', 'SomeOtherThings'
        self.assertEqual(2, len(about_file.errors))
        for w in about_file.errors:
            self.assertEqual(expected_errors[0], w.code)

    def test_validate_spdx_licenses3(self):
        test_file = join(TESTDATA_DIR, 'spdx_licenses/lower_case_spdx.ABOUT')
        about_file = about.AboutFile(test_file)
        expected_warnings = [about.SPDX]
        self.assertEqual(1, len(about_file.warnings))
        for w in about_file.warnings:
            self.assertEqual(expected_warnings[0], w.code)

    def test_validate_not_supported_date_format(self):
        test_file = join(TESTDATA_DIR,
                         'DateTest/non-supported_date_format.ABOUT')
        about_file = about.AboutFile(test_file)
        expected_warnings = [about.DATE]
        self.assertEqual(1, len(about_file.warnings))
        for w in about_file.warnings:
            self.assertEqual(expected_warnings[0], w.code)

    def test_validate_supported_date_format(self):
        test_file = join(TESTDATA_DIR, 'DateTest/supported_date_format.ABOUT')
        about_file = about.AboutFile(test_file)
        self.assertEqual(0, len(about_file.warnings))

    def test_remove_blank_lines_and_field_spaces(self):
        text_input = '''
name: test space
version: 0.7.0
about_resource: about.py
field with spaces: This is a test case for field with spaces
'''
        expected = '''name: test space
version: 0.7.0
about_resource: about.py
'''

        msg = 'field with spaces: This is a test case for field with spaces\n'
        expected_warnings = [(about.IGNORED, msg)]
        about_obj = about.AboutFile()
        result, warn = about.AboutFile.pre_process(about_obj,
                                                   StringIO(text_input))
        self.assertEqual(expected, result.read())
        for i, w in enumerate(warn):
            self.assertEqual(expected_warnings[i][0], w.code)
            self.assertEqual(expected_warnings[i][1], w.field_value)

    def test_remove_blank_lines_and_no_colon_fields(self):
        text_input = '''
name: no colon test
test
version: 0.7.0
about_resource: about.py
test with no colon
'''
        expected = '''name: no colon test
version: 0.7.0
about_resource: about.py
'''

        expected_warnings = [(about.IGNORED, 'test\n'),
                             (about.IGNORED, 'test with no colon\n')]
        about_obj = about.AboutFile()
        result, warn = about.AboutFile.pre_process(about_obj,
                                                   StringIO(text_input))

        self.assertEqual(expected, result.read())
        for i, w in enumerate(warn):
            self.assertEqual(expected_warnings[i][0], w.code)
            self.assertEqual(expected_warnings[i][1], w.field_value)

    def test_generate_attribution_with_custom_template(self):
        expected = (u'notice_text:'
                    'version:2.4.3'
                    'about_resource:httpd-2.4.3.tar.gz'
                    'name:Apache HTTP Serverlicense_text:')
        test_file = join(TESTDATA_DIR, 'attrib/attrib.ABOUT')
        collector = about.Collector(test_file)
        template = join(TESTDATA_DIR, 'attrib/test.template')
        result = collector.generate_attribution(template)
        self.assertEqual(expected, result)

    def test_license_text_extracted_from_license_text_file(self):
        expected = '''Tester holds the copyright for test component. Tester relinquishes copyright of
this software and releases the component to Public Domain.

* Email Test@tester.com for any questions'''

        test_file = join(TESTDATA_DIR, 'attrib/license_text.ABOUT')
        about_file = about.AboutFile(test_file)
        result = about_file.license_text()
        self.assertEqual(expected, result)

    def test_notice_text_extacted_from_notice_text_file(self):
        expected = '''Test component is released to Public Domain.'''
        test_file = join(TESTDATA_DIR, 'attrib/license_text.ABOUT')
        about_file = about.AboutFile(test_file)
        result = about_file.notice_text()
        self.assertEqual(result, expected)

    def test_license_text_returns_empty_string_when_no_field_present(self):
        expected = ''
        test_file = join(TESTDATA_DIR, 'attrib/no_text_file_field.ABOUT')
        about_file = about.AboutFile(test_file)
        result = about_file.license_text()
        self.assertEqual(result, expected)

    def test_notice_text_returns_empty_string_when_no_field_present(self):
        test_file = join(TESTDATA_DIR, 'attrib/no_text_file_field.ABOUT')
        about_file = about.AboutFile(test_file)
        result = about_file.notice_text()
        expected = ''
        self.assertEqual(result, expected)

    def test_license_text_returns_empty_string_when_ref_file_doesnt_exist(self):
        expected = ''
        test_file = join(TESTDATA_DIR,
                         'attrib/missing_notice_license_files.ABOUT')
        about_file = about.AboutFile(test_file)
        result = about_file.license_text()
        self.assertEqual(result, expected)

    def test_notice_text_returns_empty_string_when_ref_file_doesnt_exist(self):
        expected = ''
        test_file = join(TESTDATA_DIR,
                         'attrib/missing_notice_license_files.ABOUT')
        about_file = about.AboutFile(test_file)
        result = about_file.notice_text()
        self.assertEqual(result, expected)


class OtherTest(unittest.TestCase):
    def test_get_custom_field_keys(self):
        about_file = about.AboutFile(join(TESTDATA_DIR, 'basic/basic.about'))
        result = about_file.get_custom_field_keys()
        expected = ['scm_branch', 'scm_repository', 'signature_gpg_file',
                         'redistribute_sources', 'about_format', 'usage',
                         'scm_tool', 'scm_path', 'scm_tag', 'scm_rev',
                         'organization']
        self.assertEqual(result, expected)


