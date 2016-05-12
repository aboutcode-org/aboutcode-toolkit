#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2016 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

import codecs
import csv
import os

import jinja2
from licenses import COMMON_LICENSES
from posixpath import basename, dirname


def generate(abouts, template_string=None):
    """
    Generate and return attribution text from a list of ABOUT objects and a
    template string.
    The returned rendered text may contain template processing error messages.
    """
    syntax_error = check_template(template_string)
    if syntax_error:
        return 'Template validation error at line: %r: %r' % (syntax_error)
    template = jinja2.Template(template_string)

    try:
        lic_dict = {}
        lic_name_dict = {}
        lic_data = {}
        for about in abouts:
            lic_name = about.license_name.value
            if about.license_file.value and lic_name:
                for lic_key in about.license_file.value.keys():
                    if not lic_key in lic_dict:
                        lic_dict[lic_key] = about.license_file.value[lic_key]
                        lic_name_dict[lic_key] = lic_name

        for key in sorted(lic_dict):
            lic_data[lic_name_dict[key]] = lic_dict[key]

        rendered = template.render(abouts=abouts, common_licenses=COMMON_LICENSES, lic_data=lic_data)
    except Exception, e:
        line = getattr(e, 'lineno', None)
        ln_msg = ' at line: %r' % line if line else ''
        err = getattr(e, 'message', '')
        return 'Template processing error%(ln_msg)s: %(err)r' % locals()
    return rendered


def check_template(template_string):
    """
    Check the syntax of a template. Return an error tuple (line number,
    message) if the template is invalid or None if it is valid.
    """
    try:
        jinja2.Template(template_string)
        return
    except (jinja2.TemplateSyntaxError, jinja2.TemplateAssertionError,), e:
        return e.lineno, e.message


# FIXME: the template dir should be outside the code tree
# FIXME: use posix paths
default_template = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                'templates', 'default3.html')

def generate_from_file(abouts, template_loc=None):
    """
    Generate and return attribution string from a list of ABOUT objects and a
    template location.
    """
    if not template_loc:
        template_loc = default_template
    with codecs.open(template_loc, 'rb', encoding='utf-8') as tplf:
        tpls = tplf.read()
    return generate(abouts, template_string=tpls)


def generate_and_save(abouts, output_location, template_loc=None,
                      inventory_location=None):
    """
    Generate attribution using template and save at output_location.
    Filter the list of about object based on the inventory CSV at 
    inventory_location.
    """
    updated_abouts = []
    filter_afp = []
    if inventory_location:
        with open(inventory_location, 'rU') as inp:
            reader = csv.DictReader(inp)
            about_data = [data for data in reader]
            for data in about_data:
                afp = data['about_file_path']
                if afp.startswith('/'):
                    afp = afp.partition('/')[2]
                filter_afp.append(afp)
        list = as_about_paths(filter_afp)

        for about in abouts:
            for fp in list:
                if about.about_file_path == fp:
                    updated_abouts.append(about)
    else:
        updated_abouts = abouts
    rendered = generate_from_file(updated_abouts, template_loc=template_loc)

    if rendered:
        with codecs.open(output_location, 'wb', encoding='utf-8') as of:
            of.write(rendered)
    

def as_about_paths(paths):
    """
    Given a list of paths, return a list of paths that point all to .ABOUT files.
    """
    normalized_paths = []
    for path in paths:
        if path.endswith('.ABOUT'):
            normalized_paths.append(path)
        else:
            if path.endswith('/'):
                path += basename(dirname(path))
            normalized_paths.append(path + '.ABOUT')
    return normalized_paths