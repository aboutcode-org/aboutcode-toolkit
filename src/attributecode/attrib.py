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

from attributecode import CRITICAL
from attributecode import Error
from attributecode.licenses import COMMON_LICENSES


# FIXME: the template dir should be outside the code tree
DEFAULT_TEMPLATE_FILE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'templates', 'default_html.template')


def generate_attribution_doc(abouts, output_location,
                            template_loc=DEFAULT_TEMPLATE_FILE, variables=None):
    """
    Generate and save an attribution doc at `output_location` using an `abouts`
    list of About objects, a `template_loc` template file location and a
    `variables` optional dict of extra variables.
    Return a list of Error objects if any.
    """
    errors = []

    with io.open(template_loc, encoding='utf-8') as inp:
        template_text = inp.read()

    rendering_errors, rendered = create_attribution_text(
        abouts, template_text=template_text, variables=variables)

    errors.extend(rendering_errors)

    if rendered:
        with io.open(output_location, 'w', encoding='utf-8') as of:
            of.write(rendered)

    return errors


def create_attribution_text(abouts, template_text, variables=None):
    """
    Generate an attribution text from an `abouts` list of About objects, a
    `template_text` template text and a `variables` optional dict of extra
    variables.

    Return a list of errors and the attribution text (or None).
    """
    rendered = None
    errors = []

    template = jinja2.Template(template_text)

    licenses_by_key = {}
    for about in abouts:
        for license in about.licenses:  # NOQA
            licenses_by_key[license.key] = license

    # a sorted common licenses list in use for reporting
    common_licenses_in_use = sorted(
        lic for key, lic in licenses_by_key.items() if key in COMMON_LICENSES)

    try:
        # Get the current UTC time
        utcnow = datetime.datetime.utcnow()
        rendered = template.render(
            utcnow=utcnow,
            variables=variables,
            # legacy for compatibility
            vartext=variables,
            abouts=abouts,
            common_licenses=COMMON_LICENSES,
            common_licenses_in_use=common_licenses_in_use,
        )

    except Exception as e:
        err = str(e)
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
