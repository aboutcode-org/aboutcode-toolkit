#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2018 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

import datetime
import io
import os

import jinja2

from aboutcode import CRITICAL
from aboutcode import Error
from aboutcode.licenses import COMMON_LICENSES


# FIXME: the template dir should be outside the code tree
DEFAULT_TEMPLATE_FILE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'templates', 'default_html.template')


def generate_attribution_doc(packages, output_location,
                            template_loc=DEFAULT_TEMPLATE_FILE, variables=None):
    """
    Generate and save an attribution doc at `output_location` using an `packages`
    list of Package objects, a `template_loc` template file location and a
    `variables` optional dict of extra variables.
    Return a list of Error objects if any.
    """
    errors = []

    with io.open(template_loc, encoding='utf-8') as inp:
        template_text = inp.read()

    rendering_errors, rendered = create_attribution_text(
        packages, template_text=template_text, variables=variables)

    errors.extend(rendering_errors)

    if rendered:
        with io.open(output_location, 'w', encoding='utf-8') as of:
            of.write(rendered)

    return errors


def create_attribution_text(packages, template_text, variables=None):
    """
    Generate an attribution text from an `packages` list of Package objects, a
    `template_text` template text and a `variables` optional dict of extra
    variables.

    Return a list of errors and the attribution text (or None).

    TODO: document data available to the template.
    """
    rendered = None
    errors = []

    template = jinja2.Template(template_text, autoescape=True)

    licenses_by_key = {}
    for package in packages:
        for license in package.licenses:  # NOQA
            licenses_by_key[license.key] = license

    # a sorted common licenses list in use for reporting
    common_licenses_in_use = sorted(
        lic for key, lic in licenses_by_key.items() if key in COMMON_LICENSES)

    # compute unique Package objects
    unique_packages = sorted({package.hashable(): package for package in packages}.values())

    packages = sorted(packages)

    try:
        rendered = template.render(
            # the current UTC time
            utcnow=datetime.datetime.utcnow(),
            # variables from CLI vartext option
            variables=variables,
            # a list of all packages objects

            packages=packages,

            # a list of unique packages
            unique_packages=unique_packages,

            # sorted list of unique license objects
            unique_licenses=sorted(licenses_by_key.values()),

            # list of common licenses keys
            common_licenses=COMMON_LICENSES,
            # sorted list of common License object actually used across all packages
            common_licenses_in_use=common_licenses_in_use,

            ####################################################################
            # legacy data for backward compatibility
            ####################################################################
            # prefer using variables
            vartext_dict=variables,
            # a list of all package objects: use packages instead
            abouts=packages,
        )

    except Exception as e:
        import traceback
        err = str(e) + '\n' + traceback.format_exc()
        error = Error(CRITICAL, 'Template processing error: {}'.format(err))
        errors.append(error)

    return errors, rendered


def check_template(template_text):
    """
    Check the syntax of a template. Return an error tuple (line number,
    message) if the template is invalid or None if it is valid.
    """
    try:
        jinja2.Template(template_text)
    except (jinja2.TemplateSyntaxError, jinja2.TemplateAssertionError) as e:
        return e.lineno, e.message
