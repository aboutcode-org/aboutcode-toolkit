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

import collections
import datetime
import io
import os

import jinja2

from attributecode import __version__
from attributecode import CRITICAL
from attributecode import ERROR
from attributecode import Error
from attributecode.licenses import COMMON_LICENSES
from attributecode.model import detect_special_char
from attributecode.model import parse_license_expression
from attributecode.model import License
from attributecode.util import add_unc
from attributecode.util import convert_object_to_dict
from attributecode.attrib_util import multi_sort

DEFAULT_TEMPLATE_FILE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '../../templates', 'default_html.template')

DEFAULT_LICENSE_SCORE = 100

def generate(abouts, is_about_input, license_dict, min_license_score, template=None, variables=None):
    """
    Generate an attribution text from an `abouts` list of About objects, a
    `template` template text and a `variables` optional dict of extra
    variables.

    Return a tuple of (error, attribution text) where error is an Error object
    or None and attribution text is the generated text or None.
    """
    rendered = None
    error = None
    template_error = check_template(template)
    if template_error:
        lineno, message = template_error
        error = Error(
            CRITICAL,
            'Template validation error at line: {lineno}: "{message}"'.format(**locals())
        )
        return error, None

    template = jinja2.Template(template)
    # Get the current UTC time
    utcnow = datetime.datetime.utcnow()

    licenses_list = []
    lic_name_expression_list = []
    if is_about_input:
        for about in abouts:
            # about.license_file.value is a OrderDict with license_file_name as
            # the key and the license text as the value
            index = 0
            for lic_name in about.license_name.value:
                key = about.license_key.value[index]
                captured = False
                for lic in licenses_list:
                    if key in lic.key:
                        captured = True
                if not captured or not licenses_list:
                    name = lic_name
                    filename = list(about.license_file.value.keys())[index]
                    if  about.license_url.value:
                        url = about.license_url.value[index]
                    else:
                        url = ''
                    text = list(about.license_file.value.values())[index]
                    license_object = License(key, name, filename, url, text)
                    licenses_list.append(license_object) 
                index = index + 1
    else:
        for key in license_dict:
            name = license_dict[key][0]
            filename = license_dict[key][1]
            text = license_dict[key][2]
            url = license_dict[key][3]
            license_object = License(key, name, filename, url, text)
            licenses_list.append(license_object)

    for about in abouts:
        # Create a license expression with license name
        if about.license_expression.value:
            for segment in about.license_expression.value.split():
                not_lic = True
                for lic in licenses_list:
                    if segment == lic.key:
                        lic_name_expression_list.append(lic.name)
                        not_lic = False
                        break
                if not_lic:
                    lic_name_expression_list.append(segment)
            # Join the license name expression into a single string
            lic_name_expression = ' '.join(lic_name_expression_list)
        
            # Add the license name expression string into the about object as a list
            about.license_name_expression = lic_name_expression

    rendered = template.render(
        abouts=abouts, 
        common_licenses=COMMON_LICENSES,
        licenses_list=licenses_list,
        min_license_score=min_license_score,
        utcnow=utcnow,
        tkversion=__version__,
        variables=variables
    )
    return error, rendered


def get_license_file_key(license_text_name):
    if license_text_name.endswith('.LICENSE'):
        # See https://github.com/nexB/aboutcode-toolkit/issues/439
        # for why using split instead of strip
        return license_text_name.rsplit('.', 1)[0]
    else:
        return license_text_name


def check_template(template_string):
    """
    Check the syntax of a template. Return an error tuple (line number,
    message) if the template is invalid or None if it is valid.
    """
    try:
        jinja2.filters.FILTERS['multi_sort'] = multi_sort
        jinja2.Template(template_string)
    except (jinja2.TemplateSyntaxError, jinja2.TemplateAssertionError) as e:
        return e.lineno, e.message


def generate_from_file(abouts, is_about_input, license_dict, min_license_score, template_loc=DEFAULT_TEMPLATE_FILE, variables=None):
    """
    Generate an attribution text from an `abouts` list of About objects, a
    `template_loc` template file location and a `variables` optional
    dict of extra variables.

    Return a tuple of (error, attribution text) where error is an Error object
    or None and attribution text is the generated text or None.
    """
    template_loc = add_unc(template_loc)
    with io.open(template_loc, encoding='utf-8') as tplf:
        tpls = tplf.read()
    return generate(abouts, is_about_input, license_dict, min_license_score, template=tpls, variables=variables)


def generate_and_save(abouts, is_about_input, license_dict, output_location, min_license_score=0, template_loc=None, variables=None):
    """
    Generate an attribution text from an `abouts` list of About objects, a
    `template_loc` template file location and a `variables` optional
    dict of extra variables. Save the generated attribution text in the
    `output_location` file.
    Return a list of Error objects if any.
    """
    errors = []
    # Parse license_expression and save to the license list
    for about in abouts:
        if not about.license_expression.value:
            continue
        special_char_in_expression, lic_list = parse_license_expression(about.license_expression.value)
        if special_char_in_expression:
            msg = (u"The following character(s) cannot be in the license_expression: " +
                   str(special_char_in_expression))
            errors.append(Error(ERROR, msg))
    rendering_error, rendered = generate_from_file(
        abouts,
        is_about_input,
        license_dict,
        min_license_score=min_license_score,
        template_loc=template_loc,
        variables=variables,
    )

    if rendering_error:
        errors.append(rendering_error)

    if rendered:
        output_location = add_unc(output_location)
        with io.open(output_location, 'w', encoding='utf-8') as of:
            of.write(rendered)

    return errors, rendered
