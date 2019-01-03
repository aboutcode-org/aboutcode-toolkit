#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2018 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

from jinja2 import Environment
from jinja2.filters import environmentfilter
from jinja2.filters import make_attrgetter
from jinja2.filters import ignore_case
from jinja2.filters import FilterArgumentError


"""
Extra JINJA2 custom filters and other template utilities.
"""


def get_template(template_text):
    """
    Return a template built from a text string.
    Register custom templates as needed.
    """
    env = Environment(autoescape=True)
    # register our custom filters
    env.filters.update(dict(
        unique_together=unique_together,
        multi_sort=multi_sort))
    return env.from_string(template_text)


@environmentfilter
def multi_sort(environment, value, reverse=False, case_sensitive=False,
               attributes=None):
    """
    Sort an iterable using an "attributes" list of attribute names available on
    each iterable item. Sort ascending unless reverse is "true". Ignore the case
    of strings unless "case_sensitive" is "true".

    .. sourcecode:: jinja

        {% for item in iterable|multi_sort(attributes=['date', 'name']) %}
            ...
        {% endfor %}
    """
    if not attributes:
        raise FilterArgumentError(
            'The multi_sort filter requires a list of attributes as argument, '
            'such as in: '
            "for item in iterable|multi_sort(attributes=['date', 'name'])")

    # build a list of attribute getters, one for each attribute
    do_ignore_case = ignore_case if not case_sensitive else None
    attribute_getters = []
    for attribute in attributes:
        ag = make_attrgetter(environment, attribute, postprocess=do_ignore_case)
        attribute_getters.append(ag)

    # build a key function that has runs all attribute getters
    def key(v):
        return [a(v) for a in attribute_getters]

    return sorted(value, key=key, reverse=reverse)


@environmentfilter
def unique_together(environment, value, case_sensitive=False, attributes=None):
    """
    Return a list of unique items from an iterable. Unicity is checked when
    considering together all the values of an "attributes" list of attribute
    names available on each iterable item.. The items order is preserved. Ignore
    the case of strings unless "case_sensitive" is "true".
    .. sourcecode:: jinja

        {% for item in iterable|unique_together(attributes=['date', 'name']) %}
            ...
        {% endfor %}

    """
    if not attributes:
        raise FilterArgumentError(
            'The unique_together filter requires a list of attributes as argument, '
            'such as in: '
            "{% for item in iterable|unique_together(attributes=['date', 'name']) %} ")

    # build a list of attribute getters, one for each attribute
    do_ignore_case = ignore_case if not case_sensitive else None
    attribute_getters = []
    for attribute in attributes:
        ag = make_attrgetter(environment, attribute, postprocess=do_ignore_case)
        attribute_getters.append(ag)

    # build a unique_key function that has runs all attribute getters
    # and returns a hashable tuple
    def unique_key(v):
        return tuple(repr(a(v)) for a in attribute_getters)

    unique = []
    seen = set()
    for item in value:
        key = unique_key(item)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique
