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

from attributecode import api


class ApiTest(unittest.TestCase):
    @patch.object(api, 'request_license_data')
    def test_get_license_details_from_api(self, mock_data):
        license_data = {
            'name': 'Apache License 2.0',
            'full_text': 'Apache License Version 2.0 ...',
            'key': 'apache-2.0',
        }
        errors = []
        mock_data.return_value = license_data, errors

        expected = ('Apache License 2.0', 'apache-2.0', 'Apache License Version 2.0 ...', [])
        result = api.get_license_details_from_api('url', 'api_key', 'license_key')
        assert expected == result
