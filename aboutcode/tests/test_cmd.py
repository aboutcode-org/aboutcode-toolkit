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
import codecs

import unicodecsv

from aboutcode.tests import get_test_loc
from aboutcode.tests import get_temp_file

from aboutcode import cmd
from aboutcode import model
from collections import OrderedDict


class OrderedDictReader(unicodecsv.DictReader):
    """
    A DictReader that return OrderedDicts
    """
    def next(self):
        row_dict = unicodecsv.DictReader.next(self)
        result = OrderedDict()
        # reorder based on fieldnames order
        for name in self.fieldnames:
            result[name] = row_dict[name]
        return result


def load_csv(location):
    """
    Read CSV at location, yield a list of ordered mappings, one for each row.
    """
    results = []
    with codecs.open(location, mode='rb', encoding='utf-8') as csvfile:
        for row in OrderedDictReader(csvfile):
            results.append(row)
    return results



class CmdTest(unittest.TestCase):

    def check_csv(self, expected, result):
        """
        Compare two CSV files at locations as lists of ordered items.
        """
        self.maxDiff = None
        def as_items(csvfile):
            return [i.items() for i in load_csv(csvfile)]

        expected = as_items(expected)
        result = as_items(result)
        self.assertEqual(expected, result)

    def test_to_cmd_basic_from_directory(self):
        location = get_test_loc('cmd-inventory/basic/about')
        result = get_temp_file()
        errors, abouts = model.collect_inventory(location)

        cmd.to_csv(abouts, result)

        expected_errors = []
        self.assertEqual(expected_errors, errors)

        expected = get_test_loc('cmd-inventory/basic/expected.csv')
        self.check_csv(expected, result)
