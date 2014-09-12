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

from aboutcode.tests import get_test_loc
from aboutcode.tests import get_temp_file

from aboutcode import model
from aboutcode import util
from aboutcode import INFO
from aboutcode import CRITICAL
from aboutcode import Error
from aboutcode import ERROR
from aboutcode import WARNING
from aboutcode import DEBUG
from aboutcode import NOTSET
from aboutcode import cmd


class CmdTest(unittest.TestCase):

    def check_csv(self, expected, result):
        """
        Compare two CSV files at locations as lists of ordered items.
        """
        self.maxDiff = None
        def as_items(csvfile):
            return [i.items() for i in util.load_csv(csvfile)]

        expected = as_items(expected)
        result = as_items(result)
        self.assertEqual(expected, result)

    def test_collect_inventory_basic_from_directory(self):
        location = get_test_loc('inventory/basic/about')
        result = get_temp_file()
        errors, abouts = model.collect_inventory(location)

        model.to_csv(abouts, result)

        expected_errors = []
        self.assertEqual(expected_errors, errors)

        expected = get_test_loc('inventory/basic/expected.csv')
        self.check_csv(expected, result)


    def test_collect_inventory_complex_from_directory(self):
        self.maxDiff=None
        location = get_test_loc('inventory/complex/about')
        result = get_temp_file()
        errors, abouts = model.collect_inventory(location)

        model.to_csv(abouts, result)

        self.assertTrue(all(e.severity==INFO for e in errors))

        expected = get_test_loc('inventory/complex/expected.csv')
        self.check_csv(expected, result)


# NB: this test depends on py.test stdout/err capture capabilities
def test_log_errors(capsys):
    errors = [Error(CRITICAL, 'msg1'),
              Error(ERROR, 'msg2'),
              Error(INFO, 'msg3'),
              Error(WARNING, 'msg4'),
              Error(DEBUG, 'msg4'),
              Error(NOTSET, 'msg4'),
              ]
    cmd.log_errors(errors,level=NOTSET)
    out, err = capsys.readouterr()
    expected_out = '''CRITICAL: msg1
ERROR: msg2
INFO: msg3
WARNING: msg4
DEBUG: msg4
NOTSET: msg4
'''
    assert '' == err
    assert expected_out ==out
