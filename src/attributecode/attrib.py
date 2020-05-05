#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2020 nexB Inc. http://www.nexb.com/ - All rights reserved.
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
from attributecode.model import parse_license_expression
from attributecode.util import add_unc
from attributecode.attrib_util import multi_sort


DEFAULT_TEMPLATE_FILE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '../../templates', 'default_html.template')


def generate(abouts, template=None, variables=None):
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

    try:
        captured_license = []
        license_key_and_context = {}
        sorted_license_key_and_context = {}
        license_file_name_and_key = {}
        license_key_to_license_name = {}
        license_name_to_license_key = {}
        # FIXME: This need to be simplified
        for about in abouts:
            # about.license_file.value is a OrderDict with license_text_name as
            # the key and the license text as the value
            if about.license_file:
                # We want to create a dictionary which have the license short name as
                # the key and license text as the value
                for license_text_name in about.license_file.value:
                    if not license_text_name in captured_license:
                        captured_license.append(license_text_name)
                        if license_text_name.endswith('.LICENSE'):
                            license_key = license_text_name.strip('.LICENSE')
                        else:
                            license_key = license_text_name
                        license_key_and_context[license_key] = about.license_file.value[license_text_name]
                        sorted_license_key_and_context = collections.OrderedDict(sorted(license_key_and_context.items()))
                        license_file_name_and_key[license_text_name] = license_key

            # Convert/map the key in license expression to license name
            if about.license_expression.value and about.license_name.value:
                special_char_in_expression, lic_list = parse_license_expression(about.license_expression.value)
                lic_name_list = about.license_name.value
                lic_name_expression_list = []

                # The order of the license_name and key should be the same
                # The length for both list should be the same
                assert len(lic_name_list) == len(lic_list)

                # Map the license key to license name
                index_for_license_name_list = 0
                for key in lic_list:
                    license_key_to_license_name[key] = lic_name_list[index_for_license_name_list]
                    license_name_to_license_key[lic_name_list[index_for_license_name_list]] = key
                    index_for_license_name_list = index_for_license_name_list + 1

                # Create a license expression with license name instead of key
                for segment in about.license_expression.value.split():
                    if segment in license_key_to_license_name:
                        lic_name_expression_list.append(license_key_to_license_name[segment])
                    else:
                        lic_name_expression_list.append(segment)

                # Join the license name expression into a single string
                lic_name_expression = ' '.join(lic_name_expression_list)

                # Add the license name expression string into the about object
                about.license_name_expression = lic_name_expression

        # Get the current UTC time
        utcnow = datetime.datetime.utcnow()
        rendered = template.render(
            abouts=abouts, common_licenses=COMMON_LICENSES,
            license_key_and_context=sorted_license_key_and_context,
            license_file_name_and_key=license_file_name_and_key,
            license_key_to_license_name=license_key_to_license_name,
            license_name_to_license_key=license_name_to_license_key,
            utcnow=utcnow,
            tkversion=__version__,
            variables=variables
        )
    except Exception as e:
        lineno = getattr(e, 'lineno', '') or ''
        if lineno:
            lineno = ' at line: {}'.format(lineno)
        err = getattr(e, 'message', '') or ''
        error = Error(
            CRITICAL,
            'Template processing error {lineno}: {err}'.format(**locals()),
        )
    return error, rendered


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


def generate_from_file(abouts, template_loc=DEFAULT_TEMPLATE_FILE, variables=None):
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
    return generate(abouts, template=tpls, variables=variables)


def generate_and_save(abouts, output_location, template_loc=None, variables=None):
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
        template_loc=template_loc,
        variables=variables
    )

    if rendering_error:
        errors.append(rendering_error)

    if rendered:
        output_location = add_unc(output_location)
        with io.open(output_location, 'w', encoding='utf-8') as of:
            of.write(rendered)

    return errors
