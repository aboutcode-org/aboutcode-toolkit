#!/usr/bin/env python
# -*- coding: utf8 -*-

# =============================================================================
#  Copyright (c) 2013 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#      http://www.apache.org/licenses/LICENSE-2.0
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# =============================================================================

from __future__ import print_function
from __future__ import with_statement

import os
import shutil
import string
from StringIO import StringIO
import tempfile
import unittest
from os.path import abspath, dirname, join

from about_code_tool import about

TESTDATA_PATH = join(abspath(dirname(__file__)), 'testdata')


class BasicTest(unittest.TestCase):
    def test_simple_about_command_line_can_run(self):
        testpath = tempfile.NamedTemporaryFile(suffix='.csv', delete=True)
        tst_fn = testpath.name
        testpath.close()
        shutil.rmtree(tst_fn , ignore_errors=True)
        assert about.main(['about.ABOUT', tst_fn], []) == None
        self.assertTrue(len(open(tst_fn).read()) > 10)
        shutil.rmtree(tst_fn, ignore_errors=True)

    def test_return_path_is_not_abspath_and_contains_subdirs_on_file(self):
        # Using a relative path for the purpose of this test
        test_input = "about_code_tool/tests/testdata/thirdparty/django_snippets_2413.ABOUT"
        test_output = join(TESTDATA_PATH, 'output/test_return_path_is_not_abspath_on_file.csv')
        try:
            os.remove(test_output)
        except OSError:
            pass
        collector = about.AboutCollector(test_input, test_output, '0')
        collector.extract_about_info()
        self.assertTrue(open(test_output).read().partition('\n')[2].startswith('about_code_tool/tests/testdata/thirdparty/django_snippets_2413.ABOUT'))
        os.remove(test_output)

    def test_return_path_is_not_abspath_and_contains_subdirs_on_dir(self):
        # Using a relative path for the purpose of this test
        test_input = "about_code_tool/tests/testdata/basic"
        test_output = join(TESTDATA_PATH, 'output/test_return_path_is_not_abspath_on_dir.csv')
        try:
            os.remove(test_output)
        except OSError:
            pass
        collector = about.AboutCollector(test_input, test_output, '0')
        collector.extract_about_info()
        self.assertTrue(open(test_output).read().partition('\n')[2].startswith('about_code_tool/tests/testdata/basic'))
        os.remove(test_output)

    def test_isvalid_about_file(self):
        self.assertTrue(about.isvalid_about_file("test.About"))
        self.assertTrue(about.isvalid_about_file("test2.aboUT"))
        self.assertFalse(about.isvalid_about_file("no_about_ext.something"))


class ParserTest(unittest.TestCase):
    def test_valid_chars_in_field_name(self):
        about_obj = about.AboutFile()
        invalid, warnings = about_obj.check_invalid_chars_in_field_name(string.digits + string.ascii_letters + '_', string.digits + string.ascii_letters + '_')
        self.assertEqual([], invalid)

    def test_invalid_chars_in_field_name(self):
        about_obj = about.AboutFile()
        invalid, warnings = about_obj.check_invalid_chars_in_field_name('_$asafg:', '_$asafg: test')
        self.assertEqual(['$', ':'], invalid)

    def test_invalid_space_in_field_name(self):
        about_obj = about.AboutFile()
        invalid, warnings = about_obj.check_invalid_chars_in_field_name('_ Hello', '_ Hello')
        self.assertEqual([' '], invalid)

    def test_valid_chars_in_file_name(self):
        about_obj = about.AboutFile()
        invalid = about_obj.invalid_chars_in_about_file_name(string.digits + string.ascii_letters + '_-.')
        self.assertEqual([], invalid)

    def test_invalid_chars_in_file_name(self):
        about_obj = about.AboutFile()
        invalid = about_obj.invalid_chars_in_about_file_name('_$as/afg\\:')
        self.assertEqual(['\\', ':'], invalid)

    def test_invalid_chars_in_file_name_path(self):
        about_obj = about.AboutFile()
        invalid = about_obj.invalid_chars_in_about_file_name('%6571351()275612$/_$asafg:/\\')
        self.assertEqual(['\\', ], invalid)

    def test_invalid_chars_in_file_name_path2(self):
        about_obj = about.AboutFile()
        invalid = about_obj.invalid_chars_in_about_file_name('%6571351()275612$_$asafg:\\')
        self.assertEqual(['%', '(', ')', '$', '$', ':', '\\', ], invalid)

    def test_invalid_space_in_file_name(self):
        about_obj = about.AboutFile()
        invalid = about_obj.invalid_chars_in_about_file_name('_ Hello')
        self.assertEqual([' '], invalid)

    def test_resource_name(self):
        self.assertEqual('first', about.resource_name('some/things/first'))

    def test_resource_name1(self):
        self.assertEqual('first', about.resource_name('some/things/first/'))

    def test_resource_name2(self):
        self.assertEqual(r'things\first', about.resource_name(r'c:\some/things\first'))

    def test_resource_name3(self):
        self.assertEqual('first', about.resource_name(r'some\thi ngs//first'))

    def test_resource_name4(self):
        self.assertEqual(r'\\', about.resource_name(r'%6571351()275612$/_$asafg:/\\'))

    def test_resource_name5(self):
        self.assertEqual('_$asafg:', about.resource_name('%6571351()2/75612$/_$asafg:'))

    def test_resource_name_does_not_recurse_infinitely(self):
        self.assertEqual('', about.resource_name('/'))

    def test_resource_name_does_not_recurse_infinitely2(self):
        self.assertEqual('', about.resource_name('/  /  '))

    def test_resource_name_does_not_recurse_infinitely3(self):
        self.assertEqual('', about.resource_name(' / '))

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
        expected = \
'''about_resource: jquery.js
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

        expected = \
'''about_resource: jquery.js
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
        expected = \
'''about_resource: jquery.js
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
        expected = \
'''about_resource: jquery.js
name: jQuery
version: 1.2.3
'''
        about_obj = about.AboutFile()
        result, warn = about.AboutFile.pre_process(about_obj, StringIO(text_input))
        self.assertEqual(expected, result.read())

    def test_handles_last_line_is_a_continuation_line(self):
        warnings = []
        warn = about.AboutFile.check_line_continuation(" Last line is a continuation line.", True)
        warnings.append(warn)
        self.assertTrue(warnings == [""], "This should not throw any warning.")

    def test_handles_last_line_is_not_a_continuation_line(self):
        warnings = []
        warn = about.AboutFile.check_line_continuation(" Last line is NOT a continuation line.", False)
        warnings.append(warn)
        self.assertTrue(len(warnings) == 1, "This should throw ONLY 1 warning.")

    def test_normalize_dupe_field_names(self):
        about_file = about.AboutFile(join(TESTDATA_PATH, 'parser_tests/dupe_field_name.ABOUT'))
        expected_warnings = [about.IGNORED, 'Apache HTTP Server']
        self.assertTrue(len(about_file.warnings) == 1, "This should throw one warning")
        for w in about_file.warnings:
            self.assertEqual(expected_warnings[0], w.code)
            self.assertEqual(expected_warnings[1], w.field_value)

    def test_normalize_lowercase(self):
        about_file = about.AboutFile(join(TESTDATA_PATH, 'parser_tests/upper_field_names.ABOUT'))
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
        about_file = about.AboutFile(join(TESTDATA_PATH, 'parser_tests/about_resource_field_present.ABOUT'))
        self.assertEquals(about_file.about_resource_path, 'about_resource.c', 'the about_resource was not detected')

    def test_validate_about_ref_no_about_ref_key(self):
        about_file = about.AboutFile(join(TESTDATA_PATH, 'parser_tests/.ABOUT'))
        expected_errors = [about.VALUE, 'about_resource']
        self.assertTrue(len(about_file.errors) == 1, "This should throw 1 error")
        for w in about_file.errors:
            self.assertEqual(expected_errors[0], w.code)
            self.assertEqual(expected_errors[1], w.field_name)

    def test_validate_about_resource_error_thrown_when_file_referenced_by_about_file_does_not_exist(self):
        about_file = about.AboutFile(join(TESTDATA_PATH, 'parser_tests/missing_about_ref.ABOUT'))
        expected_errors = [about.FILE, 'about_resource']
        self.assertTrue(len(about_file.errors) == 1, "This should throw 1 error")
        for w in about_file.errors:
            self.assertEqual(expected_errors[0], w.code)
            self.assertEqual(expected_errors[1], w.field_name)

    def test_validate_mand_fields_name_and_version_and_about_resource_present(self):
        about_file = about.AboutFile(join(TESTDATA_PATH, 'parser_tests/missing_mand.ABOUT'))
        expected_errors = [(about.VALUE, 'about_resource'),
                           (about.VALUE, 'name'),
                           (about.VALUE, 'version'), ]
        self.assertTrue(len(about_file.errors) == 3, "This should throw 3 errors")
        for i, w in enumerate(about_file.errors):
            self.assertEqual(expected_errors[i][0], w.code)
            self.assertEqual(expected_errors[i][1], w.field_name)

        about_file = about.AboutFile(join(TESTDATA_PATH, 'parser_tests/missing_mand_values.ABOUT'))
        expected_errors = [(about.VALUE, 'name'),
                             (about.VALUE, 'version'),
                             (about.VALUE, 'about_resource')]
        self.assertTrue(len(about_file.errors) == 3, "This should throw 3 errors")
        for i, w in enumerate(about_file.errors):
            self.assertEqual(expected_errors[i][0], w.code)
            self.assertEqual(expected_errors[i][1], w.field_name)

    def test_validate_optional_file_field_value(self):
        about_file = about.AboutFile(join(TESTDATA_PATH, 'parser_tests/about_file_ref.c.ABOUT'))
        expected_warnings = [about.VALUE, 'notice_file']
        self.assertTrue(len(about_file.warnings) == 1, "This should throw one warning")
        for w in about_file.warnings:
            self.assertEqual(expected_warnings[0], w.code)
            self.assertEqual(expected_warnings[1], w.field_name)


class UrlCheckTest(unittest.TestCase):
    def test_check_url__with_network(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url("http://www.google.com", True))
        self.assertTrue(about_file.check_url("http://www.google.co.uk/", True))

    def test_check_url__with_network__not_starting_with_www(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url("https://nexb.com", True))
        self.assertTrue(about_file.check_url("http://archive.apache.org/dist/httpcomponents/commons-httpclient/2.0/source/commons-httpclient-2.0-alpha2-src.tar.gz", True))
        if about_file.check_network_connection():
            self.assertFalse(about_file.check_url("http://nothing_here.com", True))

    def FAILING_test_check_url__with_network__not_starting_with_www_and_spaces(self):
        # TODO: this does work yet as we do not have a solution for now (URL with spaces)
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url(u"http://de.wikipedia.org/wiki/Elf (Begriffsklärung)", True))

    def test_check_url__with_network__no_schemes(self):
        about_file = about.AboutFile()
        self.assertFalse(about_file.check_url("google.com", True))
        self.assertFalse(about_file.check_url("www.google.com", True))
        self.assertFalse(about_file.check_url("", True))

    def test_check_url__with_network__not_reachable(self):
        about_file = about.AboutFile()
        if about_file.check_network_connection():
            self.assertFalse(about_file.check_url("http://www.google", True))

    def test_check_url__with_network__empty_URL(self):
        about_file = about.AboutFile()
        self.assertFalse(about_file.check_url("http:", True))

    def test_check_url__without_network(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url("http://www.google.com", False))

    def test_check_url__without_network__not_starting_with_www(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url("https://nexb.com", False))
        self.assertTrue(about_file.check_url("http://archive.apache.org/dist/httpcomponents/commons-httpclient/2.0/source/commons-httpclient-2.0-alpha2-src.tar.gz", False))
        self.assertTrue(about_file.check_url("http://de.wikipedia.org/wiki/Elf (Begriffsklärung)", False))
        self.assertTrue(about_file.check_url("http://nothing_here.com", False))

    def test_check_url__without_network__no_schemes(self):
        about_file = about.AboutFile()
        self.assertFalse(about_file.check_url("google.com", False))
        self.assertFalse(about_file.check_url("www.google.com", False))
        self.assertFalse(about_file.check_url("", False))

    def test_check_url__without_network__not_ends_with_com(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url("http://www.google", False))

    def test_check_url__without_network__ends_with_slash(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_url("http://www.google.co.uk/", False))

    def test_check_url__without_network__empty_URL(self):
        about_file = about.AboutFile()
        self.assertFalse(about_file.check_url("http:", False))


class ValidateTest(unittest.TestCase):
    def test_validate_is_ascii_key(self):
        about_file = about.AboutFile()
        self.assertTrue(about_file.check_is_ascii('abc'))
        self.assertTrue(about_file.check_is_ascii('123'))
        self.assertTrue(about_file.check_is_ascii('!!!'))
        self.assertFalse(about_file.check_is_ascii(u'測試'))

    def test_validate_is_ascii_value(self):
        about_file = about.AboutFile(join(TESTDATA_PATH, 'filesfields/non_ascii_field.about'))
        expected_errors = [about.ASCII]
        self.assertTrue(len(about_file.errors) == 1, "This should throw 1 error")
        self.assertEqual(about_file.errors[0].code, expected_errors[0])

    def test_validate_spdx_licenses(self):
        about_file = about.AboutFile(join(TESTDATA_PATH, 'spdx_licenses/incorrect_spdx.about'))
        expected_errors = [about.SPDX]
        self.assertTrue(len(about_file.errors) == 1, "This should throw 1 error")
        for w in about_file.errors:
            self.assertEqual(expected_errors[0], w.code)

    def test_validate_spdx_licenses1(self):
        about_file = about.AboutFile(join(TESTDATA_PATH, 'spdx_licenses/invalid_multi_format_spdx.ABOUT'))
        expected_errors = [about.SPDX]
        self.assertTrue(len(about_file.errors) == 1, "This should throw 1 error")
        for w in about_file.errors:
            self.assertEqual(expected_errors[0], w.code)

    def test_validate_spdx_licenses2(self):
        about_file = about.AboutFile(join(TESTDATA_PATH, 'spdx_licenses/invalid_multi_name.ABOUT'))
        expected_errors = [about.SPDX]
        # The test case is: license_spdx: Something and SomeOtherThings
        # Thus, it should throw 2 errors: 'Something', 'SomeOtherThings'
        self.assertTrue(len(about_file.errors) == 2, "This should throw 2 errors")
        for w in about_file.errors:
            self.assertEqual(expected_errors[0], w.code)

    def test_validate_spdx_licenses3(self):
        about_file = about.AboutFile(join(TESTDATA_PATH, 'spdx_licenses/lower_case_spdx.ABOUT'))
        expected_warnings = [about.SPDX]
        self.assertTrue(len(about_file.warnings) == 1, "This should throw one warning")
        for w in about_file.warnings:
            self.assertEqual(expected_warnings[0], w.code)

    def test_validate_not_supported_date_format(self):
        about_file = about.AboutFile(join(TESTDATA_PATH, 'DateTest/non-supported_date_format.ABOUT'))
        expected_warnings = [about.DATE]
        self.assertTrue(len(about_file.warnings) == 1, "This should throw one warning")
        for w in about_file.warnings:
            self.assertEqual(expected_warnings[0], w.code)

    def test_validate_supported_date_format(self):
        about_file = about.AboutFile(join(TESTDATA_PATH, 'DateTest/supported_date_format.ABOUT'))
        self.assertTrue(len(about_file.warnings) == 0, "This should not throw warning.")

    def test_remove_blank_lines_and_field_spaces(self):
        text_input = '''
name: test space
version: 0.7.0
about_resource: about.py
field with spaces: This is a test case for field with spaces
'''
        expected = \
'''name: test space
version: 0.7.0
about_resource: about.py
'''

        expected_warnings = [(about.IGNORED, 'field with spaces: This is a test case for field with spaces\n')]
        about_obj = about.AboutFile()
        result, warn = about.AboutFile.pre_process(about_obj, StringIO(text_input))
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
        expected = \
'''name: no colon test
version: 0.7.0
about_resource: about.py
'''

        expected_warnings = [(about.IGNORED, 'test\n'),
                             (about.IGNORED, 'test with no colon\n')]
        about_obj = about.AboutFile()
        result, warn = about.AboutFile.pre_process(about_obj, StringIO(text_input))
        self.assertEqual(expected, result.read())
        for i, w in enumerate(warn):
            self.assertEqual(expected_warnings[i][0], w.code)
            self.assertEqual(expected_warnings[i][1], w.field_value)

    def test_generate_attribution(self):
        expected = u'version:2.4.3about_resource:httpd-2.4.3.tar.gzname:Apache HTTP Server'
        about_collector = about.AboutCollector(join(TESTDATA_PATH, 'attrib/attrib.ABOUT'), None, 0)
        result = about_collector.generate_attribution(join(TESTDATA_PATH, 'attrib/test.template'))
        self.assertEqual(result, expected)

    def test_license_text_extracted_from_license_text_file(self):
        expected ='''Tester holds the copyright for test component. Tester relinquishes copyright of
this software and releases the component to Public Domain.

* Email Test@tester.com for any questions'''

        about_file = about.AboutFile(join(TESTDATA_PATH, 'attrib/license_text.ABOUT'))
        license_text = about_file.license_text()
        self.assertEqual(license_text, expected)

    def test_notice_text_extacted_from_notice_text_file(self):
        expected ='''Test component is released to Public Domain.'''
        about_file = about.AboutFile(join(TESTDATA_PATH, 'attrib/license_text.ABOUT'))
        notice_text = about_file.notice_text()
        self.assertEqual(notice_text, expected)

    def test_license_text_returns_empty_string_when_no_field_present(self):
        expected = ''
        about_file = about.AboutFile(join(TESTDATA_PATH, 'attrib/no_text_file_field.ABOUT'))
        license_text = about_file.license_text()
        self.assertEqual(license_text, expected)

    def test_notice_text_returns_empty_string_when_no_field_present(self):
        expected = ''
        about_file = about.AboutFile(join(TESTDATA_PATH, 'attrib/no_text_file_field.ABOUT'))
        notice_text = about_file.notice_text()
        self.assertEqual(notice_text, expected)

    def test_license_text_returns_empty_string_when_ref_file_doesnt_exist(self):
        expected = ''
        about_file = about.AboutFile(join(TESTDATA_PATH, 'attrib/missing_notice_license_files.ABOUT'))
        license_text = about_file.license_text()
        self.assertEqual(license_text, expected)

    def test_notice_text_returns_empty_string_when_ref_file_doesnt_exist(self):
        expected = ''
        about_file = about.AboutFile(join(TESTDATA_PATH, 'attrib/missing_notice_license_files.ABOUT'))
        notice_text = about_file.notice_text()
        self.assertEqual(notice_text, expected)
