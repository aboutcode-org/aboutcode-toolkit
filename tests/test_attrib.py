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

import io
import os
import unittest

from aboutcode import attrib
from aboutcode import inv

from testing_utils import get_test_loc


class TemplateTest(unittest.TestCase):

    def test_check_template_with_simple_valid_template_returns_None(self):
        expected = None
        assert expected == attrib.check_template('template_string')

    def test_check_template_with_complex_valid_template_returns_None(self):
        template = '''
        {% for about in abouts -%}
            {{ about.name.value }}: {{ about.version.value }}
            {% for res in about.about_resource.value -%}
                resource: {{ res }}
            {% endfor -%}
        {% endfor -%}'''
        expected = None
        assert expected == attrib.check_template(template)

    def test_check_template_with_complex_invalid_template_returns_error(self):
        template = '''
        {% for about in abouts -%}
            {{ about.name.value }}: {{ about.version.value }}
            {% for res in about.about_ressdsdsdsdsdsdource.value -%}
                resource: {{] res }}
            {% endfor -%}
        {% endfor -%}'''
        expected = (5, "unexpected ']'")
        assert expected == attrib.check_template(template)

    def test_check_template_with_invalid_template_return_error_lineno_and_message(self):
        expected = 1, "unexpected end of template, expected 'end of print statement'."
        assert expected == attrib.check_template('{{template_string')

    def test_check_template_all_builtin_templates_are_valid(self):
        builtin_templates_dir = os.path.dirname(attrib.DEFAULT_TEMPLATE_FILE)
        for template in os.listdir(builtin_templates_dir):
            template_loc = os.path.join(builtin_templates_dir, template)
            with io.open(template_loc, 'r', encoding='utf-8') as tmpl:
                template = tmpl.read()
            assert None == attrib.check_template(template)


class GenerateTest(unittest.TestCase):

    def test_generate_from_collected_inventory_wih_custom_template(self):
        test_file = get_test_loc('test_attrib/gen_simple/attrib.ABOUT')
        errors, abouts = inv.collect_inventory(test_file)
        assert not errors

        test_template = get_test_loc('test_attrib/gen_simple/test.template')
        with open(test_template) as tmpl:
            template_text = tmpl.read()

        expected = (
            'Apache HTTP Server: 2.4.3\n'
            'resource: httpd-2.4.3.tar.gz\n')

        error, result = attrib.create_attribution_text(abouts, template_text)
        assert expected == result
        assert not error

    def test_generate_with_default_template(self, regen=False):
        test_file = get_test_loc('test_attrib/gen_default_template')
        errors, abouts = inv.collect_inventory(test_file)
        assert not errors

        test_template = attrib.DEFAULT_TEMPLATE_FILE
        with open(test_template) as tmpl:
            template_text = tmpl.read()

        error, result = attrib.create_attribution_text(abouts, template_text)
        assert not error

        expected_file = get_test_loc(
            'test_attrib/gen_default_template/expected_default_attrib.html')
        if regen:
            with io.open(expected_file, 'w') as out:
                out.write(result)

        with open(expected_file) as exp:
            expected = exp.read()

        # strip the timestamp: the timestamp is wrapped in italic block
        result = remove_timestamp(result)
        expected = remove_timestamp(expected)
        assert expected == result


def remove_timestamp(html_text):
    """
    Return the `html_text` generated attribution stripped from timestamps: the
    timestamp is wrapped in italic block in the default template.
    """
    return '\n'.join(x for x in html_text.splitlines() if not '<i>' in x)
