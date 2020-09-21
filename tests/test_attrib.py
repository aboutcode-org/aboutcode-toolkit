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

import io
import os
import unittest

from testing_utils import get_test_loc
from testing_utils import get_temp_file

from attributecode import attrib
from attributecode import model

class TemplateTest(unittest.TestCase):

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
        builtin_templates_dir = os.path.dirname(attrib.DEFAULT_TEMPLATE_FILE)
        for template in os.listdir(builtin_templates_dir):
            template_loc = os.path.join(builtin_templates_dir, template)
            with io.open(template_loc, 'r', encoding='utf-8') as tmpl:
                template = tmpl.read()
            try:
                assert None == attrib.check_template(template)
            except:
                raise Exception(template_loc)


class GenerateTest(unittest.TestCase):

    def test_generate_from_collected_inventory_wih_custom_temaplte(self):
        test_file = get_test_loc('test_attrib/gen_simple/attrib.ABOUT')
        errors, abouts = model.collect_inventory(test_file)
        assert not errors

        test_template = get_test_loc('test_attrib/gen_simple/test.template')
        with open(test_template) as tmpl:
            template = tmpl.read()

        expected = (
            'Apache HTTP Server: 2.4.3\n'
            'resource: httpd-2.4.3.tar.gz\n')

        error, result = attrib.generate(abouts, template)
        assert expected == result
        assert not error

    def test_generate_with_default_template(self):
        test_file = get_test_loc('test_attrib/gen_default_template/attrib.ABOUT')
        errors, abouts = model.collect_inventory(test_file)
        assert not errors

        error, result = attrib.generate_from_file(abouts)
        assert not error

        expected_file = get_test_loc(
            'test_attrib/gen_default_template/expected_default_attrib.html')
        with open(expected_file) as exp:
            expected = exp.read()

        # strip the timestamp: the timestamp is wrapped in italic block
        result = remove_timestamp(result)
        expected = remove_timestamp(expected)
        assert expected == result

    def test_lic_key_name_sync(self):
        test_file = get_test_loc('test_attrib/gen_license_key_name_check/test.ABOUT')
        expected = get_test_loc('test_attrib/gen_license_key_name_check/expected/expected.html')
        template_loc = get_test_loc('test_attrib/gen_license_key_name_check/custom.template')
        output_file = get_temp_file()

        errors, abouts = model.collect_inventory(test_file)
        attrib.generate_and_save(abouts, output_file, template_loc)

        with open(output_file) as of:
            f1 = '\n'.join(of.readlines(False))
        with open(expected) as ef:
            f2 = '\n'.join(ef.readlines(False))

        assert f1 == f2

def remove_timestamp(html_text):
    """
    Return the `html_text` generated attribution stripped from timestamps: the
    timestamp is wrapped in italic block in the default template.
    """
    return '\n'.join(x for x in html_text.splitlines() if not '<i>' in x)
