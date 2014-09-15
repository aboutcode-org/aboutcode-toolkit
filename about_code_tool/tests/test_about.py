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


class ValidateTest(unittest.TestCase):
    def test_generate_attribution(self):
        expected = (u'notice_text:'
                    'version:2.4.3'
                    'about_resource:httpd-2.4.3.tar.gz'
                    'name:Apache HTTP Serverlicense_text:')
        test_file = join(TESTDATA_DIR, 'attrib/attrib.ABOUT')
        collector = about.Collector(test_file)
        template = join(TESTDATA_DIR, 'attrib/test.template')
        result = collector.generate_attribution(template)
        self.assertEqual(expected, result)

