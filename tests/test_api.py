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

import unittest

from mock import patch

import attributecode
from attributecode import api
from attributecode.api import LicenseInfo


class ApiTest(unittest.TestCase):

    def test_build_api_url(self):
        url = 'http:/dejacode.org/'
        api_username = 'phi'
        api_key = 'ABCD'
        license_key = 'apache'
        expected = 'http:/dejacode.org/apache/?username=phi&api_key=ABCD&format=json'
        result = api.build_api_url(url, api_username, api_key, license_key)
        assert expected == result

    @patch.object(attributecode.api, 'get_license_data')
    def test_get_license_info(self, mock_data):
        mock_data.return_value = [], {'key': 'test', 'name': 'test_name', 'full_text': 'test_full_text' }
        result = api.get_license_info(self, '', '', '', '')
        assert result == ([], LicenseInfo(key='test', name='test_name', text='test_full_text'))

    @patch.object(attributecode.api, 'request_license_data')
    def test_get_license_details_from_api(self, mock_data):
        mock_data.return_value = {'name': 'test_name', 'full_text': 'test_full_text', 'key': 'test'}, []
        result = api.get_license_details_from_api('', '', '')
        assert result == ('test_name', 'test', 'test_full_text', [])