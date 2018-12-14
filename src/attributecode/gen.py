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

from attributecode import Error
from attributecode import ERROR
from attributecode import CRITICAL
from attributecode import model
from attributecode import util
from attributecode.util import csv
from attributecode.util import unique


def check_duplicated_about_file_path(inventory_dict):
    """
    Return a list of errors for duplicated about_file_path in a CSV file at location.
    """
    afp_list = []
    errors = []
    for component in inventory_dict:
        # Ignore all the empty path
        if component['about_file_path']:
            if component['about_file_path'] in afp_list:
                msg = ("The input has duplicated values in 'about_file_path' "
                       "field: " + component['about_file_path'])
                errors.append(Error(CRITICAL, msg))
            else:
                afp_list.append(component['about_file_path'])
    return errors



def load_inventory(location, base_dir=None):
    """
    Load the inventory file at `location` as About objects.
    Use the `base_dir` to resolve the ABOUT file location.
    Return a list of errors and a list of About objects.
    """
    errors = []
    abouts = []

    if location.endswith('.csv'):
        inventory = load_csv(location)
    elif location.endswith('.json'):
        inventory = load_json(location)
    else:
        raise Exception(
            'Unsupported inventory file type. '
            'Must be one of .csv or .json: {}'.format(location))
    inventory = list(inventory)

    # FIXME: this should not be done here.
    dup_about_paths_err = check_duplicated_about_file_path(inventory)
    if dup_about_paths_err:
        errors.extend(dup_about_paths_err)
        return errors, abouts

    if base_dir:
        base_dir = util.to_posix(base_dir)

    for entry in inventory:
        entry = dict(entry)

        about_file_path = entry.pop('about_file_path', None)
        if not about_file_path or not about_file_path.strip():
            msg = ('Empty or missing "about_file_path" for: "{}"'.format(about_file_path))
            errors.append(Error(ERROR, msg))
            continue
        about_file_path = util.to_posix(about_file_path)

        # Ensure there is no absolute directory path
        about_file_path = about_file_path.strip('/')

        segments = about_file_path.split('/')
        if any(seg != seg.strip() for seg in segments):
            msg = ('Invalid "about_file_path": must not end or start with a space for: "{}"'.format(about_file_path))
            errors.append(Error(ERROR, msg))
            continue

        try:
            about = model.About.from_dict(entry)
            if base_dir:
                about.location = os.path.join(base_dir, about_file_path)

            abouts.append(about)

        except Exception as e:
            msg = ('Cannot create .ABOUT file for: "{}".\n'.format(about_file_path) + str(e))
            errors.append(Error(ERROR, msg))
            continue

    return unique(errors), abouts


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
    with open(location) as json_file:
        results = json.load(json_file)

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

    Return a list errors and a list of About objects.
    """
    errors, abouts = load_inventory(inventory_location, base_dir=target_dir)

    notices_by_filename = {}
    licenses_by_key = {}

    if reference_dir:
        notices_by_filename, licenses_by_key = model.load_license_references(reference_dir)
        
    # TODO: validate inventory!!!!! to catch error before creating ABOUT files

    # update all licenses and notices
    for about in abouts:
        # Fix the location to ensure this is a proper .ABOUT file
        loc = about.location
        if not loc.endswith('.ABOUT'):
            loc = loc.rstrip('\\/').strip() + '.ABOUT'
        about.location = loc
        
        # used as a "prettier" display of .ABOUT file path
        about_path = loc.replace(target_dir, '').strip('/')

        # Update the License objects of this About using a mapping of reference licenses as {key: License}
        for license in about.licenses:  # NOQA
            ref_lic = licenses_by_key.get(license.key)
            if not ref_lic:
                msg = (
                    'Cannot generate valid .ABOUT file for: "{}". '
                    'Reference license is missing: {}'.format(about_path, license.key))
                errors.append(Error(ERROR, msg))
                continue

            license.update(ref_lic)
            
        if about.notice_file:
            notice_text = notices_by_filename.get(about.notice_file)
            if not notice_text:
                msg = (
                    'Cannot generate valid .ABOUT file for: "{}". '
                    'Empty or missing notice_file: {}'.format(about_path, about.notice_file))
                errors.append(Error(ERROR, msg))
            else:
                about.notice_text = notice_text

        # create the files proper
        about.dump(location=about.location, with_files=True)

    return unique(errors), abouts
