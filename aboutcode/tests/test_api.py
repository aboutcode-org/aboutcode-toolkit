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

import unittest

from aboutcode import api


class ApiTest(unittest.TestCase):

    def test_build_api_url(self):
        url ='http:/dejacode.org/'
        api_username='phi'
        api_key='ABCD'
        license_key='apache'
        expected = 'http:/dejacode.org/apache/?username=phi&api_key=ABCD&format=json'
        result = api.build_api_url(url, api_username, api_key, license_key)
        self.assertEqual(expected, result)
