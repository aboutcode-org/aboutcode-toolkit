#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2014-2019 nexB Inc. http://www.nexb.com/ - All rights reserved.
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
import unittest

from testing_utils import get_temp_dir
from testing_utils import get_test_loc

from attributecode import ERROR
from attributecode import INFO
from attributecode import CRITICAL
from attributecode import Error
from attributecode import gen
from attributecode.transform import read_csv_rows
from attributecode.transform import transform_data
from attributecode.transform import Transformer


class TransformTest(unittest.TestCase):
    def test_transform_data(self):
        test_file = get_test_loc('test_transform/input.csv')
        configuration = get_test_loc('test_transform/configuration')
        rows = read_csv_rows(test_file)
        transformer = Transformer.from_file(configuration)
        col_name, data, err = transform_data(rows, transformer)
        expect = [u'about_resource', u'name']
        assert col_name == expect
