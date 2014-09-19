#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2014 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

from __future__ import print_function

import os
import codecs

import jinja2


def generate_and_save(abouts, output_location, template=None,
                      inventory_location=None):
    rendered = generate(abouts, template=None, inventory_location=None)
    if rendered:
        with codecs.open(output_location, 'wb', encoding='utf-8') as of:
            of.write(rendered)


def generate(abouts, template=None, inventory_location=None):
    """
    Generate an attribution file from the current list of ABOUT objects.
    The optional `limit_to` parameter allows to restrict the generated
    attribution to a specific list of component names.
    """

    if not template:
        template = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'templates/default2.html')

    # FIXME: the template dir should be outside the code tree
    template_dir = os.path.dirname(template)
    template_file_name = os.path.basename(template)
    loader = jinja2.FileSystemLoader(template_dir)
    jinja_env = jinja2.Environment(loader=loader)

    try:
        template = jinja_env.get_template(template_file_name)
    except jinja2.TemplateNotFound:
        return
    if inventory_location:
        pass

    rendered = template.render(abouts=abouts)
    return rendered
