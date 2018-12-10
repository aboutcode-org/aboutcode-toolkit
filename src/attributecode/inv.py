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

import io
import json
import os
# FIXME: why posixpath???
import posixpath

import attr

from attributecode import CRITICAL
from attributecode import Error
from attributecode import util
from attributecode.model import About
from attributecode.util import csv
from attributecode.util import get_absolute
from attributecode.util import python2
from attributecode.util import to_posix
from attributecode.util import unique


"""
Collect and validate inventories of ABOUT files
"""


def collect_inventory(location):
    """
    Collect any ABOUT files in the directory tree at `location` and return a
    list of errors and a list of About objects.
    """
    errors = []
    input_location = util.get_absolute(location)
    about_locations = list(get_about_locations(input_location))

    name_errors = util.check_file_names(about_locations)
    errors.extend(name_errors)

    abouts = []
    for about_file_loc in about_locations:
        about = About.load(about_file_loc)
        abouts.append(about)

        # this could be a dict keys by path to keep per-path things?
        errors.extend(about.errors)

#         # TODO: WHY???
#         # Insert about_file_path reference in every error
#         for severity, message in about.errors:
#             msg = (about_file_loc + ": " + message)
#             errors.append(Error(severity, msg))

    return sorted(unique(errors)), abouts


def is_about_file(path):
    """
    Return True if the path represents a valid ABOUT file name.
    """
    if path:
        path = path.lower()
        return path.endswith('.about') and path != '.about'


def get_locations(location):
    """
    Return a list of locations of files given the `location` of a
    a file or a directory tree containing ABOUT files.
    File locations are normalized using posix path separators.
    """
    location = get_absolute(location)
    assert os.path.exists(location)

    if os.path.isfile(location):
        yield location
    else:
        for base_dir, _, files in os.walk(location):
            for name in files:
                bd = to_posix(base_dir)
                yield posixpath.join(bd, name)


def get_about_locations(location):
    """
    Return a list of locations of ABOUT files given the `location` of a
    a file or a directory tree containing ABOUT files.
    File locations are normalized using posix path separators.
    """
    for loc in get_locations(location):
        if is_about_file(loc):
            yield loc


def get_field_names(abouts):
    """
    Given a list of About objects, return a list of any field names that exist
    in any object, including custom fields.
    """
    standard_seen = set()
    custom_seen = set()
    for a in abouts:
        standard, custom = a.fields()
        standard_seen.update(standard)
        custom_seen.update(custom)

    # resort standard fields in standard order
    # which is a tad complex as this is a predefined order
    standard_names = list(attr.fields_dict(About).keys())
    standard = []
    for name in standard_names:
        if name in standard_seen:
            standard.append(name)

    return standard + sorted(custom_seen)


def save_as_json(location, abouts):
    """
    Write a JSON file at `location` given a list of About objects.
    Return a list of Error objects.
    """

    serialized = [a.to_dict(with_location=True, with_licenses=True) for a in abouts]

    if python2:
        with io.open(location, 'wb') as out:
            out.write(json.dumps(serialized, indent=2))
    else:
        with io.open(location, 'w', encoding='utf-8') as out:
            out.write(json.dumps(serialized, indent=2))

    return []


def save_as_csv(location, abouts):
    """
    Write a CSV file at `location` given a list of About objects.
    Return a list of Error objects.
    LEGACY: the licenses list of objects CANNOT be serialized to CSV
    """
    serialized = [a.to_dict(with_location=True, with_licenses=False) for a in abouts]

    field_names = get_field_names(abouts)

    errors = []

    with io.open(location, mode='w', encoding='utf-8') as output_file:
        writer = csv.DictWriter(output_file, field_names)
        writer.writeheader()
        for row in serialized:
            # FIXME: we should just crash instead IMHO
            # See https://github.com/dejacode/about-code-tool/issues/167
            try:
                writer.writerow(row)
            except Exception as e:
                msg = 'Generation skipped for {}: '.format(row) + str(e)
                errors.append(Error(CRITICAL, msg))
    return errors
