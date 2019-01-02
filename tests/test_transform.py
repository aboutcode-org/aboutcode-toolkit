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

from aboutcode import CRITICAL
from aboutcode import Error
from aboutcode import transform

from testing_utils import get_test_loc


class TransformTest(unittest.TestCase):

    def test_read_csv_rows_can_read_invalid_utf8(self):
        test_file = get_test_loc('test_transform/mojibake.csv')
        list(transform.read_csv_rows(test_file))

    def test_get_duplicate_columns(self):
        column_names = 'a', 'b', 'a'
        result = transform.get_duplicate_columns(column_names)
        assert ['a'] == result

    def test_check_required_columns_always_include_defaults(self):
        test_data = [
            dict(about_resource='' ,
                name='Utilities' ,
                version='0.11.0' ,
                foo='bar',
                baz='val'),
            dict(
                about_resource='tarball.tgz',
                name='Core',
                version='1',
                foo='',
                baz='')
        ]

        required_columns = ['name', 'version', 'foo', 'required']
        transformer = transform.Transformer(required_columns=required_columns)
        errors = transformer.check_required_columns(test_data)
        expected = [
            Error(CRITICAL, 'Row 1 is missing required values for columns: required, about_resource'),
            Error(CRITICAL, 'Row 2 is missing required values for columns: required, foo')]

        assert expected == errors
