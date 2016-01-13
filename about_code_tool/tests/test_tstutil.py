#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2015 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

import unittest

from about_code_tool import util


class UtilTest(unittest.TestCase):

    def test_get_mappings(self):
        expected = {
            'name': 'component',
            'copyright': 'confirmed copyright',
            'confirmed_license': 'confirmed license',
            'version': 'confirmed version',
            'about_file': 'directory/filename'
        }

        result = util.get_mappings()
        self.assertEqual(expected, result)

    def test_apply_mappings(self):
        mappings = {
            'about_file': 'Directory/Filename',
            'version': 'Confirmed Version',
            'about_resource': 'file_name',
            'name': 'Component'
        }

        test_fields = [
            {
             'file_name': 'opensans',
             'ignore field': 'i',
             'Component': 'OpenSans Fonts',
             'Confirmed Version': '1',
             'Directory/Filename': '/extension/streamer/opensans/',
            }
        ]

        expected = [
            {
             'about_resource': 'opensans',
             'ignore field': 'i',
             'name': 'OpenSans Fonts',
             'version': '1',
             'about_file': '/extension/streamer/opensans/',
            }
        ]

        result = util.apply_mappings(test_fields, mappings)
        self.assertEqual(expected, result)

    def test_apply_mappings_same_name(self):
        mappings = {
            'about_file': 'Directory/Filename',
            'version': 'Confirmed Version',
            'about_resource': 'file_name',
            'name': 'Component',
            'component' : 'Component'
        }

        test_fields = [
            {
             'file_name': 'opensans',
             'ignore field': 'i',
             'Component': 'OpenSans Fonts',
             'Confirmed Version': '1',
             'Directory/Filename': '/extension/streamer/opensans/',
            }
        ]

        expected = [
            {
             'about_resource': 'opensans',
             'ignore field': 'i',
             'name': 'OpenSans Fonts',
             'version': '1',
             'about_file': '/extension/streamer/opensans/',
             'component': 'OpenSans Fonts',
            }
        ]

        result = util.apply_mappings(test_fields, mappings)
        self.assertEqual(expected, result)

    def test_util_resource_name(self):
        expected = 'first'
        result = util.resource_name('some/things/first')
        self.assertEqual(expected, result)

    def test_util_resource_name1(self):
        expected = 'first'
        result = util.resource_name('some/things/first/')
        self.assertEqual(expected, result)

    def test_util_resource_name2(self):
        expected = r'things\first'
        result = util.resource_name(r'c:\some/things\first')
        self.assertEqual(expected, result)

    def test_util_resource_name3(self):
        expected = 'first'
        result = util.resource_name(r'some\thi ngs//first')
        self.assertEqual(expected, result)

    def test_util_resource_name4(self):
        expected = r'\\'
        result = util.resource_name(r'%6571351()275612$/_$asafg:/\\')
        self.assertEqual(expected, result)

    def test_util_resource_name5(self):
        expected = '_$asafg:'
        result = util.resource_name('%6571351()2/75612$/_$asafg:')
        self.assertEqual(expected, result)

    def test_util_resource_name_does_not_recurse_infinitely(self):
        expected = ''
        result = util.resource_name('/')
        self.assertEqual(expected, result)

    def test_util_resource_name_does_not_recurse_infinitely2(self):
        expected = ''
        result = util.resource_name('/  /  ')
        self.assertEqual(expected, result)

    def test_util_resource_name_does_not_recurse_infinitely3(self):
        expected = ''
        result = util.resource_name(' / ')
        self.assertEqual(expected, result)
