#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2017 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

import codecs
from collections import OrderedDict
import logging
import posixpath
import sys

if sys.version_info[0] < 3:
    # Python 2
    import backports.csv as csv
else:
    # Python 3
    import csv

from attributecode import ERROR
from attributecode import CRITICAL
from attributecode import Error
from attributecode import model
from attributecode.model import check_file_field_exist
from attributecode import util
from attributecode.util import add_unc
from attributecode.util import to_posix


LOG_FILENAME = 'error.log'

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.CRITICAL)
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)
file_logger = logging.getLogger(__name__ + '_file')


def check_duplicated_columns(location):
    """
    Return a list of errors for duplicated column names in a CSV file
    at location.
    """
    location = add_unc(location)
    # FIXME: why ignore errors?
    with codecs.open(location, 'rb', encoding='utf-8', errors='ignore') as csvfile:
        reader = csv.reader(csvfile)
        columns = next(reader)
        columns = [col for col in columns]

    seen = set()
    dupes = OrderedDict()
    for col in columns:
        c = col.lower()
        if c in seen:
            if c in dupes:
                dupes[c].append(col)
            else:
                dupes[c] = [col]
        seen.add(c.lower())

    errors = []
    if dupes:
        dup_msg = []
        for name, names in dupes.items():
            names = u', '.join(names)
            msg = '%(name)s with %(names)s' % locals()
            dup_msg.append(msg)
        dup_msg = u', '.join(dup_msg)
        msg = ('Duplicated column name(s): %(dup_msg)s\n' % locals() +
               'Please correct the input and re-run.')
        errors.append(Error(ERROR, msg))
    return errors


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
                msg = ("The input has duplicated values in 'about_file_path' field: " + component['about_file_path'])
                errors.append(Error(CRITICAL, msg))
            else:
                afp_list.append(component['about_file_path'])
    return errors


def load_inventory(location, base_dir, license_notice_text_location=None,
                   use_mapping=False):
    """
    Load the inventory file at `location` for ABOUT and LICENSE files
    stored in the `base_dir`. Return a list of errors and a list of
    About objects validated against the base_dir.
    Optionally use `license_notice_text_location` as the location of
    license and notice texts.
    Optionally use mappings for field names if `use_mapping` is True.
    """
    errors = []
    abouts = []
    base_dir = util.to_posix(base_dir)
    if location.endswith('.csv'):
        dup_cols_err = check_duplicated_columns(location)
        if dup_cols_err:
            errors.extend(dup_cols_err)
            return errors, abouts
        inventory = util.load_csv(location, use_mapping)
    else:
        inventory = util.load_json(location, use_mapping)

    try:
        dup_about_paths_err = check_duplicated_about_file_path(inventory)
        if dup_about_paths_err:
            errors.extend(dup_about_paths_err)
            return errors, abouts
    except:
        msg = "The essential field 'about_file_path' is not found."
        errors.append(Error(CRITICAL, msg))
        return errors, abouts

    for i, fields in enumerate(inventory):
        # check does the input contains the required fields
        required_fields = model.About.required_fields

        for f in required_fields:
            if f not in fields:
                msg = (
                    "Required column: %(f)r not found.\n"
                    "Use the --mapping option to map the input keys and verify the "
                    "mapping information are correct.\n"
                    "OR correct the column names in the <input>"
                ) % locals()

                errors.append(Error(ERROR, msg))
                return errors, abouts
        afp = fields.get(model.About.about_file_path_attr)

        if not afp or not afp.strip():
            msg = 'Empty column: %(afp)r. Cannot generate .ABOUT file.' % locals()
            errors.append(Error(ERROR, msg))
            continue
        else:
            afp = util.to_posix(afp)
            loc = posixpath.join(base_dir, afp)
        about = model.About(about_file_path=afp)
        about.location = loc
        running_inventory = False
        ld_errors = about.load_dict(fields, base_dir, running_inventory, license_notice_text_location, with_empty=False)
        # 'about_resource' field will be generated during the process.
        # No error need to be raise for the missing 'about_resource'.
        for e in ld_errors:
            if e.message == 'Field about_resource is required':
                ld_errors.remove(e)
        for e in ld_errors:
            if not e in errors:
                errors.extend(ld_errors)
        abouts.append(about)
    return errors, abouts


def generate(location, base_dir, license_notice_text_location=None,
             fetch_license=False, policy=None, conf_location=None,
             with_empty=False, with_absent=False, use_mapping=False):
    """
    Load ABOUT data from a CSV inventory at `location`. Write ABOUT files to
    base_dir using policy flags and configuration file at conf_location.
    Policy defines which action to take for merging or overwriting fields and
    files. Return errors and about objects.
    """
    api_url = ''
    api_key = ''
    gen_license = False
    # Check if the fetch_license contains valid argument
    if fetch_license:
        # Strip the ' and " for api_url, and api_key from input
        api_url = fetch_license[0].strip("'").strip('"')
        api_key = fetch_license[1].strip("'").strip('"')
        gen_license = True

    bdir = to_posix(base_dir)
    errors, abouts = load_inventory(
        location=location,
        base_dir=bdir,
        license_notice_text_location=license_notice_text_location,
        use_mapping=use_mapping)

    if gen_license:
        license_dict, err = model.pre_process_and_fetch_license_dict(abouts, api_url, api_key)
        if err:
            for e in err:
                # Avoid having same error multiple times
                if not e in errors:
                    errors.append(e)

    for about in abouts:
        if about.about_file_path.startswith('/'):
            about.about_file_path = about.about_file_path.lstrip('/')
        dump_loc = posixpath.join(bdir, about.about_file_path.lstrip('/'))

        # The following code is to check if there is any directory ends with spaces
        split_path = about.about_file_path.split('/')
        dir_endswith_space = False
        for segment in split_path:
            if segment.endswith(' '):
                msg = (u'File path : '
                       u'%(dump_loc)s '
                       u'contains directory name ends with spaces which is not '
                       u'allowed. Generation skipped.' % locals())
                errors.append(Error(ERROR, msg))
                dir_endswith_space = True
                break
        if dir_endswith_space:
            # Continue to work on the next about object
            continue

        try:
            # Generate value for 'about_resource' if it does not exist
            if not about.about_resource.value:
                about.about_resource.value = OrderedDict()
                if about.about_file_path.endswith('/'):
                    about.about_resource.value[u'.'] = None
                    about.about_resource.original_value = u'.'
                else:
                    about.about_resource.value[posixpath.basename(about.about_file_path)] = None
                    about.about_resource.original_value = posixpath.basename(about.about_file_path)
                about.about_resource.present = True

            # Generate value for 'about_resource_path' if it does not exist
            # Basically, this should be the same as the 'about_resource'
            if not about.about_resource_path.value:
                about.about_resource_path.value = OrderedDict()
                about.about_resource_path.value = about.about_resource.value
                about.about_resource_path.present = True

            if gen_license:
                about.license_file.value = OrderedDict()
                # Write generated LICENSE file
                license_key_name_context_url_list = about.dump_lic(dump_loc, license_dict)
                if license_key_name_context_url_list:
                    # Do not help user to fill in the license name
                    # if not about.license_name.present:
                    #    about.license_name.value = lic_name
                    #    about.license_name.present = True
                    if not about.license_file.present:
                        for lic_key, lic_name, lic_context, lic_url in license_key_name_context_url_list:
                            gen_license_name = lic_key + u'.LICENSE'
                            about.license_file.value[gen_license_name] = lic_context
                            about.license_file.present = True
                            if not about.license_name.present:
                                about.license_name.value.append(lic_name)
                            if not about.license_url.present:
                                about.license_url.value.append(lic_url)
                        if about.license_url.value:
                            about.license_url.present = True
                        if about.license_name.value:
                            about.license_name.present = True

            # Write the ABOUT file and check does the referenced file exist
            # This function is not purposed to throw error. However, since I've commented
            # out the error throwing in FileTextField (See model.py), I have add error handling
            # in this function. This error handling should be removed once the fetch-license option
            # is treated as a subcommand.
            not_exist_errors = about.dump(dump_loc,
                                   with_empty=with_empty,
                                   with_absent=with_absent)
            file_field_not_exist_errors = check_file_field_exist(about, dump_loc)

            for e in not_exist_errors:
                errors.append(Error(ERROR, e))
            for e in file_field_not_exist_errors:
                errors.append(Error(ERROR, e))

        except Exception as e:
            # only keep the first 100 char of the exception
            emsg = repr(e)[:100]
            msg = (u'Failed to write .ABOUT file at : '
                   u'%(dump_loc)s '
                   u'with error: %(emsg)s' % locals())
            errors.append(Error(ERROR, msg))
    dedup_errors = deduplicate(errors)
    return dedup_errors, abouts


def deduplicate(sequence):
    """
    Return a list of unique items found in sequence. Preserve the original
    sequence order.
    """
    deduped = []
    for item in sequence:
        if item not in deduped:
            deduped.append(item)
    return deduped
