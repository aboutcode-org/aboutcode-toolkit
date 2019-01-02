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

from collections import OrderedDict
import io
import json
import os

from aboutcode import Error
from aboutcode import ERROR
from aboutcode import CRITICAL
from aboutcode import model
from aboutcode import util
from aboutcode.util import csv
from aboutcode.util import unique
from aboutcode.util import resource_name


def load_inventory(location, base_dir=None):
    """
    Load the inventory file at `location` as Package objects.
    Use the `base_dir` to resolve the ABOUT file location.
    Return a list of errors and a list of Package objects.
    """
    packages = []

    if location.endswith('.csv'):
        inventory = load_csv(location)
    elif location.endswith('.json'):
        inventory = load_json(location)
    else:
        err = Error(
            CRITICAL,
            'Unsupported inventory file type. Must be one of .csv or .json')
        return [err], []

    inventory = list(inventory)

    if not inventory:
        err = Error(CRITICAL, 'Empty inventory.')
        return [err], []

    # various check prior to generation

    # validate field names using the first row fields as a sample
    sample = dict(inventory[0])
    standard_fields, custom_fields = model.split_fields(sample)
    fields_err = model.validate_field_names(
        standard_fields.keys(), custom_fields.keys())
    if fields_err:
        return fields_err, packages

    if base_dir:
        base_dir = util.to_posix(base_dir)

    errors = []

    for entry in inventory:
        entry = dict(entry)
        abr = entry['about_resource']
        about_resource = util.to_posix(abr)

        if abr != about_resource:
            msg = ('Invalid "about_resource". Path must be a POSIX path '
                   'using "/" (slash) as separator: "{}"'.format(abr))
            errors.append(Error(ERROR, msg))
            continue


        abfp = entry.get('about_file_path', '')
        if abfp and abfp != util.to_posix(abfp):
            msg = ('Invalid "about_file_path". Path must be a POSIX path '
                   'using "/" (slash) as separator: "{}"'.format(abr))
            errors.append(Error(ERROR, msg))
            continue

        if not abfp:
            abfp = about_resource

        # Ensure there is no absolute directory path
        about_file_path = util.to_posix(abfp).strip('/')

        # Skip paths with lead and trailing spaces in directories or files segments
        if has_spaces(about_file_path):
            msg = ('Invalid path to create an ABOUT file: a path segment '
                   'cannot start or end with a space: "{}"'.format(about_file_path))
            errors.append(Error(ERROR, msg))
            continue

        # always use the file name as the about_resource to make this relative
        # to the ABOUT file location
        file_name = resource_name(about_resource)
        entry['about_resource'] = file_name

        if not about_file_path.endswith('.ABOUT'):
            about_file_path += '.ABOUT'

        entry['about_file_path'] = about_file_path
        if base_dir:
            entry['about_file_location'] = os.path.join(base_dir, about_file_path)

        try:
            packages.append(model.Package.from_dict(entry))

        except Exception as e:
            if len(e.args) == 1 and isinstance(e.args[0], Error):
                err = e.args[0]
                msg = 'Cannot create .ABOUT file for: "{}".\n{}'.format(
                    about_file_path, err.message)
                err = Error(CRITICAL, msg)
            else:
                import traceback
                msg = 'Cannot create .ABOUT file for: "{}".\n{}\n{}'.format(
                    about_file_path, str(e) , traceback.format_exc())
                err = Error(CRITICAL, msg)
            errors.append(err)
            continue

    return unique(errors), packages


def has_spaces(path):
    """
    Return True if any segments of the `path` string contains a leading or
    trailing space.
    """
    path = util.to_posix(path).strip('/')
    return any(seg != seg.strip() for seg in path.split('/') if seg)


def load_csv(location):
    """
    Read CSV at `location` and yield an ordered mapping for each row.
    """
    with io.open(location, encoding='utf-8') as csvfile:
        for row in csv.DictReader(csvfile):
            yield row


def load_json(location):
    """
    Read JSON file at `location` and return a list of ordered dicts, one for
    each entry.
    """
    # FIXME: IMHO we should know where the JSON is from and its shape
    # FIXME use: object_pairs_hook=OrderedDict
    with io.open(location, 'rb') as json_file:
        results = json.load(json_file, object_pairs_hook=OrderedDict)

    # If the loaded JSON is not a list,
    # - JSON output from AboutCode Manager:
    # look for the "components" field as it is the field
    # that contain everything the tool needs and ignore other fields.
    # For instance,
    # {
    #    "aboutcode_manager_notice":"xyz",
    #    "aboutcode_manager_version":"xxx",
    #    "components":
    #    [{
    #        "license_expression":"apache-2.0",
    #        "copyright":"Copyright (c) 2017 nexB Inc.",
    #        "path":"ScanCode",
    #        ...
    #    }]
    # }
    #
    # - JSON output from ScanCode:
    # look for the "files" field as it is the field
    # that contain everything the tool needs and ignore other fields:
    # For instance,
    # {
    #    "scancode_notice":"xyz",
    #    "scancode_version":"xxx",
    #    "files":
    #    [{
    #        "path": "test",
    #        "type": "directory",
    #        "name": "test",
    #        ...
    #    }]
    # }
    #
    # - JSON file that is not produced by scancode or aboutcode toolkit
    # For instance,
    # {
    #    "path": "test",
    #    "type": "directory",
    #    "name": "test",
    #    ...
    # }
    # FIXME: this is too clever and complex... IMHO we should not try to guess the format.
    # instead a command line option should be provided explictly to say what is the format
    if isinstance(results, list):
        results = sorted(results)
    else:
        if u'aboutcode_manager_notice' in results:
            results = results['components']
        elif u'scancode_notice' in results:
            results = results['files']
        else:
            results = [results]
    return results


def generate_about_files(inventory_location, target_dir, reference_dir=None):
    """
    Load ABOUT data from a CSV or JSON inventory at `inventory_location`.
    Write .ABOUT files in the `target_dir` directory.

    If `reference_dir` is provided reuse and copy license and notice files
    referenced in the inventory.

    Return a list errors and a list of Package objects.
    """
    errors, packages = load_inventory(inventory_location, base_dir=target_dir)
    notices_by_filename = {}
    licenses_by_key = {}

    if reference_dir:
        notices_by_filename, licenses_by_key = model.get_reference_licenses(reference_dir)

    # TODO: validate inventory!!!!! to catch error before creating ABOUT files

    # update all licenses and notices
    for package in packages:
        # Fix the location to ensure this is a proper .ABOUT file
        afl = package.about_file_location
        if not afl:
            pass

        if not afl.endswith('.ABOUT'):
            afl = afl.rstrip('\\/').strip() + '.ABOUT'

        package.about_file_location = afl

        # used as a "prettier" display of .ABOUT file path
        about_path = afl.replace(target_dir, '').strip('/')

        # Update the License objects of this Package using a mapping of reference licenses as {key: License}
        for license in package.licenses:  # NOQA
            ref_lic = licenses_by_key.get(license.key)
            if not ref_lic:
                msg = (
                    'Cannot generate valid .ABOUT file for: "{}". '
                    'Reference license is missing: {}'.format(about_path, license.key))
                errors.append(Error(ERROR, msg))
                continue

            license.update(ref_lic)

        if package.notice_file:
            notice_text = notices_by_filename.get(package.notice_file)
            if not notice_text:
                msg = (
                    'Cannot generate valid .ABOUT file for: "{}". '
                    'Empty or missing notice_file: {}'.format(about_path, package.notice_file))
                errors.append(Error(ERROR, msg))
            else:
                package.notice_text = notice_text

        # create the files proper
        package.dump(location=afl, with_files=True)

    return unique(errors), packages
