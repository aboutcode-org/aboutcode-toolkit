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

import mock

from attributecode import api
from attributecode import ERROR
from attributecode import Error
from testing_utils import FakeResponse


class ApiTest(unittest.TestCase):
    @mock.patch.object(api, 'request_license_data')
    def test_api_get_license_details_from_api(self, request_license_data):
        license_data = {
            'name': 'Apache License 2.0',
            'full_text': 'Apache License Version 2.0 ...',
            'key': 'apache-2.0',
        }
        errors = []
        request_license_data.return_value = license_data, errors

        expected = ('Apache License 2.0', 'apache-2.0', 'Apache License Version 2.0 ...', [])
        result = api.get_license_details_from_api('url', 'api_key', 'license_key')
        assert expected == result

    @mock.patch.object(api, 'urlopen')
    def test_api_request_license_data(self, mock_data):
        response_content = (
            b'{"count":1,"results":[{"name":"Apache 2.0","key":"apache-2.0","text":"Text"}]}'
        )
        mock_data.return_value = FakeResponse(response_content)
        license_data = api.request_license_data('http://fake.url/', 'api_key', 'apache-2.0')
        expected = ({'name': 'Apache 2.0', 'key': 'apache-2.0', 'text': 'Text'}, [])
        assert expected == license_data

        response_content = b'{"count":0,"results":[]}'
        mock_data.return_value = FakeResponse(response_content)
        license_data = api.request_license_data('http://fake.url/', 'api_key', 'apache-2.0')
        expected = ({}, [Error(ERROR, "Invalid 'license': apache-2.0")])
        assert expected == license_data
