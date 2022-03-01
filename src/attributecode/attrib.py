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
from attributecode.model import parse_license_expression
from attributecode.model import License, StringField
from attributecode.util import add_unc
from attributecode.attrib_util import multi_sort

DEFAULT_TEMPLATE_FILE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '../../templates', 'default_html.template')

DEFAULT_TEMPLATE_SCANCODE_FILE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '../../templates', 'scancode_html.template')

DEFAULT_LICENSE_SCORE = 100

def generate(abouts, is_about_input, license_dict, scancode, min_license_score, template=None, vartext=None):
    """
    Generate an attribution text from an `abouts` list of About objects, a
    `template` template text and a `vartext` optional dict of extra
    variables.

    Return a tuple of (error, attribution text) where error is an Error object
    or None and attribution text is the generated text or None.
    """
    rendered = None
    errors = []
    template_error = check_template(template)
    if template_error:
        lineno, message = template_error
        error = Error(
            CRITICAL,
            'Template validation error at line: {lineno}: "{message}"'.format(**locals())
        )
        errors.append(error)
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
                if about.license_key.value:
                    key = about.license_key.value[index]
                else:
                    key = lic_name
                captured = False
                for lic in licenses_list:
                    if key in lic.key:
                        captured = True
                        break
                if not captured or not licenses_list:
                    name = lic_name
                    if about.license_file.value.keys():
                        filename = list(about.license_file.value.keys())[index]
                        text = list(about.license_file.value.values())[index]
                    else:
                        error = Error(CRITICAL, 'No license file found for ' + name)
                        errors.append(error)
                        break
                    if  about.license_url.value:
                        url = about.license_url.value[index]
                    else:
                        url = ''
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


    # We need special treatment for scancode input.
    # Each about_object may have duplicated license key and same/different license score
    # We will only keep the unique license key with the highest license score.
    # The process will update the license_key, license_name and license_score.
    if scancode:
        meet_score_licenses_list = []
        for about in abouts:
            # We will use a dictionary to keep the unique license key
            # which the dictionary key is the license key and the dictionary value
            # is (lic_score, lic_name)
            if about.license_key.value:
                updated_dict = {}
                lic_key = about.license_key.value
                lic_name = about.license_name.value
                lic_score = about.license_score.value
                assert len(lic_key) == len(lic_name)
                assert len(lic_key) == len(lic_score)
                if lic_key:
                    index = 0
                    for key in lic_key:
                        if key in updated_dict:
                            previous_score, _name = updated_dict[key]
                            current_score = lic_score[index]
                            if current_score > previous_score:
                                updated_dict[key] = (lic_score[index], lic_name[index])
                        else:
                            updated_dict[key] = (lic_score[index], lic_name[index])
                        index = index + 1
                updated_lic_key = []
                updated_lic_name = []
                updated_lic_score = []
                for lic in updated_dict:
                    score, name = updated_dict[lic]
                    if score >= min_license_score:
                        updated_lic_key.append(lic)
                        updated_lic_score.append(score)
                        updated_lic_name.append(name)
                        if not lic in meet_score_licenses_list:
                            meet_score_licenses_list.append(lic)
                about.license_key.value = updated_lic_key
                about.license_name.value = updated_lic_name
                about.license_score.value = updated_lic_score

        for lic in licenses_list:
            if not lic.key in meet_score_licenses_list:
                licenses_list.remove(lic)

    for about in abouts:
        # Create a license expression with license name
        lic_name_expression = ''
        lic_name_expression_list = []
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

            # Add the license name expression string into the about object as a custom field
            custom_field = StringField(name=name, value=lic_name_expression, present=True)
            setattr(about, 'license_name_expression', custom_field)

    # Sort the about objects by name
    abouts = sorted(abouts, key=lambda x: x.name.value.lower())

    # Sort the license object by key
    licenses_list = sorted(licenses_list, key=lambda x: x.key)

    rendered = template.render(
        abouts=abouts,
        common_licenses=COMMON_LICENSES,
        licenses_list=licenses_list,
        utcnow=utcnow,
        tkversion=__version__,
        vartext=vartext
    )

    return errors, rendered

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


def generate_from_file(abouts, is_about_input, license_dict, scancode, min_license_score, template_loc=None, vartext=None):
    """
    Generate an attribution text from an `abouts` list of About objects, a
    `template_loc` template file location and a `vartext` optional
    dict of extra variables.

    Return a tuple of (error, attribution text) where error is an Error object
    or None and attribution text is the generated text or None.
    """
    if not template_loc:
        if scancode:
            template_loc = add_unc(DEFAULT_TEMPLATE_SCANCODE_FILE)
        else:
            template_loc = add_unc(DEFAULT_TEMPLATE_FILE)
    else:
        template_loc = add_unc(template_loc)
    with io.open(template_loc, encoding='utf-8', errors='replace') as tplf:
        tpls = tplf.read()
    return generate(abouts, is_about_input, license_dict, scancode, min_license_score, template=tpls, vartext=vartext)


def generate_and_save(abouts, is_about_input, license_dict, output_location, scancode=False, min_license_score=0, template_loc=None, vartext=None):
    """
    Generate an attribution text from an `abouts` list of About objects, a
    `template_loc` template file location and a `vartext` optional
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
        scancode=scancode,
        min_license_score=min_license_score,
        template_loc=template_loc,
        vartext=vartext,
    )

    if rendering_error:
        errors.extend(rendering_error)

    if rendered:
        output_location = add_unc(output_location)
        with io.open(output_location, 'w', encoding='utf-8', errors='replace') as of:
            of.write(rendered)

    return errors, rendered
