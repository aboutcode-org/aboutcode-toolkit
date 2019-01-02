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
import traceback

import attr

from aboutcode import CRITICAL
from aboutcode import Error
from aboutcode import util
from aboutcode.model import Package
from aboutcode.util import csv
from aboutcode.util import normalize
from aboutcode.util import python2
from aboutcode.util import to_posix
from aboutcode.util import unique
from aboutcode.util import get_relative_path
from aboutcode.util import resource_name


"""
Collect and validate inventories of ABOUT files
"""


def collect_inventory(location, check_files=False):
    """
    Collect any ABOUT files in the directory tree at `location` and return a
    list of errors and a list of Package objects.

    If `check_files` is True, also check that files referenced in an ABOUT file
    exist (about_resource, license and notice files, etc.)
    """
    errors = []
    input_location = normalize(location)
    about_locations = []
    try:
        about_locations.extend(get_about_locations(input_location))
    except Exception as e:
        errors.append(Error(CRITICAL, str(e) + '\n' + traceback.format_exc()))

    name_errors = util.check_file_names(about_locations)
    errors.extend(name_errors)

    packages = []

    if errors:
        return sorted(unique(errors)), packages


    is_file = os.path.isfile(input_location)

    for about_file_loc in about_locations :
        package = None
        try:
            if is_file:
                about_file_path = resource_name(input_location)
            else:
                about_file_path = get_relative_path(input_location, about_file_loc)

            package = Package.load(about_file_loc)
            package.about_file_path = about_file_path
            packages.append(package)

            if check_files:
                package.check_files()

            # this could be a dict keys by path to keep per-path things?
            errors.extend(package.errors)

        except Exception as exce:
            if all(isinstance(e, Error) for e in exce.args):
                for err in exce.args:
                    if not err.path:
                        err.path = about_file_path
                    errors.append(err)
            else:
                errors.append(Error(
                    CRITICAL,
                    str(exce) + '\n' + traceback.format_exc(),
                    path=about_file_path
                ))

        if package:
            # Insert path reference in every Package error
            for err in package.errors:
                if not err.path:
                    err.path = about_file_path

    return sorted(unique(errors)), packages


def is_about_file(path):
    """
    Return True if the path represents a valid ABOUT file name.
    """
    if path:
        path = path.lower()
        return path.endswith('.about') and path != '.about'


def get_locations(location):
    """
    Yield posix locations of files given the `location` of a
    a file or a directory tree containing ABOUT files.
    File locations are normalized using posix path separators.
    """
    assert os.path.exists(location)
    location = normalize(location)
    location = to_posix(location)

    if os.path.isfile(location):
        yield location
    else:
        for name in os.listdir(location):
            path = posixpath.join(location , name)
            for f in get_locations(path):
                yield f


def get_about_locations(location):
    """
    Return a list of locations of ABOUT files given the `location` of a
    a file or a directory tree containing ABOUT files.
    File locations are normalized using posix path separators.
    """
    for loc in get_locations(location):
        if is_about_file(loc):
            yield loc


def get_field_names(packages):
    """
    Given a list of Package objects, return a list of any field names that exist
    in any object, including custom fields.
    """
    standard_seen = set()
    custom_seen = set()
    for a in packages:
        standard, custom = a.fields()
        standard_seen.update(standard)
        custom_seen.update(custom)

    # resort standard fields in standard order
    # which is a tad complex as this is a predefined order
    standard_names = list(attr.fields_dict(Package).keys())
    standard = []
    for name in standard_names:
        if name in standard_seen:
            standard.append(name)

    return standard + sorted(custom_seen)


def save_as_json(location, packages):
    """
    Write a JSON file at `location` given a list of Package objects.
    Return a list of Error objects.
    """

    serialized = [a.to_dict(with_path=True, with_licenses=True) for a in packages]

    if python2:
        with io.open(location, 'wb') as out:
            out.write(json.dumps(serialized, indent=2))
    else:
        with io.open(location, 'w', encoding='utf-8') as out:
            out.write(json.dumps(serialized, indent=2))

    return []


def save_as_csv(location, packages):
    """
    Write a CSV file at `location` given a list of Package objects.
    Return a list of Error objects.
    LEGACY: the licenses list of objects CANNOT be serialized to CSV
    """
    serialized = [a.to_dict(with_path=True, with_licenses=False) for a in packages]

    field_names = get_field_names(packages)

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
