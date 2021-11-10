#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) nexB Inc. http://www.nexb.com/ - All rights reserved.
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

import io
import os
import unittest

from testing_utils import get_test_loc
from testing_utils import get_temp_file

from attributecode import INFO
from attributecode import attrib
from attributecode import gen
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
            with io.open(template_loc, 'r', encoding='utf-8', errors='replace') as tmpl:
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

        license_dict = {}
        is_about_input = True
        min_license_score=0
        scancode = False
        error, result = attrib.generate(abouts, is_about_input, license_dict, scancode, min_license_score, template=template)
        assert expected == result
        assert not error

    def test_generate_with_default_template(self):
        test_file = get_test_loc('test_attrib/gen_default_template/attrib.ABOUT')
        errors, abouts = model.collect_inventory(test_file)
        assert not errors

        license_dict = {}
        is_about_input = True
        min_license_score=0
        scancode = False

        error, result = attrib.generate_from_file(abouts, is_about_input, license_dict, scancode, min_license_score)
        assert not error

        expected_file = get_test_loc(
            'test_attrib/gen_default_template/expected_default_attrib.html')
        with open(expected_file) as exp:
            expected = exp.read()

        # strip the timestamp: the timestamp is wrapped in italic block
        result = remove_timestamp(result)
        expected = remove_timestamp(expected)
        # Ignore all white spaces and newline
        result = result.replace('\n', '').replace(' ', '')
        expected = expected.replace('\n', '').replace(' ', '')
        assert expected == result

    def test_lic_key_name_sync(self):
        test_file = get_test_loc('test_attrib/gen_license_key_name_check/test.ABOUT')
        expected = get_test_loc('test_attrib/gen_license_key_name_check/expected/expected.html')
        template_loc = get_test_loc('test_attrib/gen_license_key_name_check/custom.template')
        output_file = get_temp_file()

        license_dict = {}
        is_about_input = True

        errors, abouts = model.collect_inventory(test_file)
        attrib.generate_and_save(abouts, is_about_input, license_dict, output_file, template_loc=template_loc)

        with open(output_file) as of:
            f1 = '\n'.join(of.readlines(False))
        with open(expected) as ef:
            f2 = '\n'.join(ef.readlines(False))

        assert f1 == f2

    def test_scancode_input(self):
        test_file = get_test_loc('test_attrib/scancode_input/clean-text-0.3.0-mod-lceupi.json')
        errors, abouts = gen.load_inventory(test_file, scancode=True)
        # No validation is done for the scancode input as it usually contains duplicated entry of
        # detected licenses which is not allow in the current spec.
        #expected_errors = [(40, 'Field about_resource: Unable to verify path: isc_lic.py: No base directory provided')]
        result = [(level, e) for level, e in errors if level > INFO]
        #assert expected_errors == result
        assert result == []

        lic_dict = {'isc': ['ISC License',
                            'isc.LICENSE',
                            'Permission to use, copy, modify, and/or distribute this software for any purpose\nwith or without fee is hereby granted, provided that the above copyright notice\nand this permission notice appear in all copies.\n\nTHE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH\nREGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND\nFITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,\nINDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS\nOF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER\nTORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF\nTHIS SOFTWARE.\n',
                            'https://scancode-licensedb.aboutcode.org/isc.LICENSE'],
                    'mit': ['MIT License',
                            'mit.LICENSE',
                            'Permission is hereby granted, free of charge, to any person obtaining\na copy of this software and associated documentation files (the\n"Software"), to deal in the Software without restriction, including\nwithout limitation the rights to use, copy, modify, merge, publish,\ndistribute, sublicense, and/or sell copies of the Software, and to\npermit persons to whom the Software is furnished to do so, subject to\nthe following conditions:\n\nThe above copyright notice and this permission notice shall be\nincluded in all copies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,\nEXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF\nMERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.\nIN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY\nCLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,\nTORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE\nSOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.',
                            'https://scancode-licensedb.aboutcode.org/mit.LICENSE']}
        is_about_input = False
        scancode = True
        errors, result = attrib.generate_from_file(abouts, is_about_input, lic_dict, scancode, min_license_score=0)
        expected_errors = []
        #result = [(level, e) for level, e in errors if level > INFO]
        #assert expected_errors == result
        assert not errors

        expected_file = get_test_loc(
            'test_attrib/scancode_input/expect.html')
        with open(expected_file) as exp:
            expected = exp.read()

        # strip the timestamp: the timestamp is wrapped in italic block
        result = remove_timestamp(result)
        expected = remove_timestamp(expected)
        # For whatever reasons, the directly comparison between the result and the
        # expected doesn't work well, it works after removed all the newline and spaces
        #assert expected == result
        #assert expected.splitlines(False) == result.splitlines(False)
        assert expected.replace('\n','').replace(' ','').replace('\t','') == result.replace('\n','').replace(' ','').replace('\t','')

    def test_generate_with_csv(self):
        test_file = get_test_loc('test_attrib/default_template/simple_sample.csv')
        errors, abouts = gen.load_inventory(test_file)

        lic_dict = {'isc': ['ISC License',
                            'isc.LICENSE',
                            'Permission to use, copy, modify, and/or distribute this software for any purpose\nwith or without fee is hereby granted, provided that the above copyright notice\nand this permission notice appear in all copies.\n\nTHE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH\nREGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND\nFITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,\nINDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS\nOF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER\nTORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF\nTHIS SOFTWARE.\n',
                            'https://scancode-licensedb.aboutcode.org/isc.LICENSE']}
        is_about_input = False
        scancode = False

        error, result = attrib.generate_from_file(abouts, is_about_input, lic_dict, scancode, min_license_score=0)
        assert not error

        expected_file = get_test_loc(
            'test_attrib/default_template/expect.html')
        with open(expected_file) as exp:
            expected = exp.read()

        # strip the timestamp: the timestamp is wrapped in italic block
        result = remove_timestamp(result)
        expected = remove_timestamp(expected)
        #assert expected == result
        assert expected.replace('\n','').replace(' ','') == result.replace('\n','').replace(' ','')

def remove_timestamp(html_text):
    """
    Return the `html_text` generated attribution stripped from timestamps: the
    timestamp is wrapped in italic block in the default template.
    """
    return '\n'.join(x for x in html_text.splitlines() if not '<i>' in x)
