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

import os
import unittest

from testing_utils import get_test_loc

from attributecode import attrib
from attributecode import model


class AttribTest(unittest.TestCase):

    def test_check_template_simple_valid_returns_None(self):
        expected = None
        assert expected == attrib.check_template('template_string')

    def test_check_template_complex_valid_returns_None(self):
        template = '''
        {% for about in abouts -%}
            {{ about.name.value }}: {{ about.version.value }}
            {% for res in about.about_resource.value -%}
                resource: {{ res }}
            {% endfor -%}
        {% endfor -%}'''
        expected = None
        assert expected == attrib.check_template(template)

    def test_check_template_complex_invalid_returns_error(self):
        template = '''
        {% for about in abouts -%}
            {{ about.name.value }}: {{ about.version.value }}
            {% for res in about.about_ressdsdsdsdsdsdource.value -%}
                resource: {{] res }}
            {% endfor -%}
        {% endfor -%}'''
        expected = (5, "unexpected ']'")
        assert expected == attrib.check_template(template)

    def test_check_template_invalid_return_error_lineno_and_message(self):
        expected = 1, "unexpected end of template, expected 'end of print statement'."
        assert expected == attrib.check_template('{{template_string')

    def test_check_template_all_builtin_templates_are_valid(self):
        builtin_templates_dir = os.path.dirname(attrib.default_template)
        for template in os.listdir(builtin_templates_dir):
            template = os.path.join(builtin_templates_dir, template)
            with open(template) as tmpl:
                template = tmpl.read()
            assert None == attrib.check_template(template)

    def test_generate(self):
        test_file = get_test_loc('attrib_gen/attrib.ABOUT')
        errors, abouts = model.collect_inventory(test_file)

        with open(get_test_loc('attrib_gen/test.template')) as tmpl:
            template = tmpl.read()

        assert not errors

                expected = (
            'Apache HTTP Server: 2.4.3\n'
            'resource: httpd-2.4.3.tar.gz\n')

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
