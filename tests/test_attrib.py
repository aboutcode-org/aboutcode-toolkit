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

from testing_utils import get_test_loc

from attributecode import attrib
from attributecode import model


class AttribTest(unittest.TestCase):

    def test_check_template(self):
        assert attrib.check_template('template_string') == None
        assert attrib.check_template('{{template_string') == (1,
          "unexpected end of template, expected 'end of print statement'.",)
        with open(get_test_loc('attrib_gen/test.template')) as tmpl:
            template = tmpl.read()
        assert attrib.check_template(template) == None

    def test_check_template_default_is_valid(self):
        with open(attrib.default_template) as tmpl:
            template = tmpl.read()
        assert attrib.check_template(template) == None

    def test_generate(self):
        expected = (u'Apache HTTP Server: 2.4.3\n'
                    u'resource: httpd-2.4.3.tar.gz\n')
        test_file = get_test_loc('attrib_gen/attrib.ABOUT')
        with open(get_test_loc('attrib_gen/test.template')) as tmpl:
            template = tmpl.read()
        _errors, abouts = model.collect_inventory(test_file)
        result = attrib.generate(abouts, template)
        self.assertEqual(expected, result)

    def test_generate_from_file_with_default_template(self):
        test_file = get_test_loc('attrib_gen/attrib.ABOUT')
        _errors, abouts = model.collect_inventory(test_file)
        result = attrib.generate_from_file(abouts)
        with open(get_test_loc('attrib_gen/expected_default_attrib.html')) as exp:
            expected = exp.read()
        # strip the timestamp: the timestamp is wrapped in italic block
        self.assertEqual([x.rstrip() for x in expected.splitlines()],
                         [x.rstrip() for x in result.splitlines() if not '<i>' in x])
