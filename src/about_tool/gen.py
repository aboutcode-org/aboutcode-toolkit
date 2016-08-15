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

from __future__ import absolute_import
from __future__ import print_function

import ConfigParser as configparser
import codecs
import errno
import logging
import optparse
import os
import posixpath
import sys
import unicodecsv

from collections import OrderedDict
from posixpath import basename

from about_tool import ERROR
from about_tool import CRITICAL
from about_tool import Error
from about_tool import __about_spec_version__
from about_tool import __version__
from about_tool import model
from about_tool import util
from about_tool.model import verify_license_files_in_location
from about_tool.model import check_file_field_exist
from about_tool.util import copy_files, add_unc
from about_tool.util import to_posix


LOG_FILENAME = 'error.log'

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.CRITICAL)
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)
file_logger = logging.getLogger(__name__ + '_file')


# Handle different behaviors if ABOUT file already exists
ACTION_DO_NOTHING_IF_ABOUT_FILE_EXIST = 0
ACTION_OVERWRITES_THE_CURRENT_ABOUT_FIELD_VALUE_IF_EXIST = 1
ACTION_KEEP_CURRENT_FIELDS_UNCHANGED_AND_ONLY_ADD_NEW_FIELDS = 2
ACTION_REPLACE_THE_ABOUT_FILE_WITH_THE_CURRENT_GENERATED_FILE = 3


def check_duplicated_columns(location):
    """
    Return a list of errors for duplicated column names in a CSV file at location.
    """
    location = add_unc(location)
    with codecs.open(location, 'rb', encoding='utf-8', errors='ignore') as csvfile:
        reader = unicodecsv.UnicodeReader(csvfile)
        columns = reader.next()
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
    afp_list = []
    errors = []
    for component in inventory_dict:
        # Ignore all the empty path
        if component['about_file_path']:
            if component['about_file_path'] in afp_list:
                msg = ('The input has duplicated values in \'about_file_path\' field: ' +
                       component['about_file_path'])
                errors.append(Error(CRITICAL, msg))
            else:
                afp_list.append(component['about_file_path'])
    return errors


def load_inventory(mapping, location, base_dir):
    """
    Load the inventory file at location. Return a list of errors and a
    list of About objects validated against the base_dir.
    """
    errors = []
    abouts = []
    base_dir = util.to_posix(base_dir)
    if location.endswith('.csv'):
        dup_cols_err = check_duplicated_columns(location)
        if dup_cols_err:
            errors.extend(dup_cols_err)
            return errors, abouts
        inventory = util.load_csv(mapping, location)
    else:
        inventory = util.load_json(mapping, location)

    try:
        dup_about_paths_err = check_duplicated_about_file_path(inventory)
        if dup_about_paths_err:
            errors.extend(dup_about_paths_err)
            return errors, abouts
    except:
        msg = ('The essential field \'about_file_path\' is not found.')
        errors.append(Error(CRITICAL, msg))
        return errors, abouts

    for i, fields in enumerate(inventory):
        # check does the input contains the required fields
        requied_fileds = model.About.required_fields

        for f in requied_fileds:
            if f not in fields:
                msg = ('Required column: %(f)r not found.\n' % locals() +
                       'Use the \'--mapping\' option to map the input keys and verify the mapping information are correct.\n' +
                       'OR correct the column names in the <input>.')
                errors.append(Error(ERROR, msg))
                return errors, abouts
        afp = fields.get(model.About.about_file_path_attr)

        if not afp or not afp.strip():
            msg = ('Empty column: %(afp)r. '
                   'Cannot generate ABOUT file.' % locals())
            errors.append(Error(ERROR, msg))
            continue
        else:
            afp = util.to_posix(afp)
            loc = posixpath.join(base_dir, afp)
        about = model.About(about_file_path=afp)
        about.location = loc
        ld_errors = about.load_dict(fields, base_dir, with_empty=False)
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


def load_conf(location):
    """
    Load the about configuration file at location.
    Return a dictionary of dictionary.
    """
    location = add_unc(location)
    with codecs.open(location, mode='rb', encoding='utf-8') as conf_file:
        config = configparser.ConfigParser()
        config.read_file(conf_file)
        return config


def get_column_mappings(location_or_config):
    """
    Given the location of a config file or configuration object, return a dict 
    of mapping from an ABOUT field to a CSV inventory column.
    """
    if isinstance(location_or_config, basestring):
        config = load_conf(location_or_config)
    return config['mappings']


#FIXME: This function is too huge
def generate(mapping, license_text_location, extract_license, location, base_dir, policy=None, conf_location=None,
             with_empty=False, with_absent=False):
    """
    Load ABOUT data from an inventory at csv_location. Write ABOUT files to
    base_dir using policy flags and configuration file at conf_location.
    Policy defines which action to take for merging or overwriting fields and
    files. Return errors and about objects.
    """
    api_url = ''
    api_key = ''
    gen_license = False
    # Check if the extract_license contains valid argument
    if extract_license:
        # Strip the ' and " for api_url, and api_key from input
        api_url = extract_license[0].strip("'").strip("\"")
        api_key = extract_license[1].strip("'").strip("\"")
        gen_license = True

    bdir = to_posix(base_dir)
    errors, abouts = load_inventory(mapping, location, bdir)

    if gen_license:
        dje_license_dict, err = model.pre_process_and_dje_license_dict(abouts, api_url, api_key)
        if err:
            for e in err:
                # Avoid having same error multiple times
                if not e in errors:
                    errors.append(e)

    for about in abouts:
        # TODO: check the paths overlap ...???
        # For some reasons, the join does not work, using the '+' for now
        # dump_loc = posixpath.join(bdir, about.about_file_path)
        dump_loc = bdir + about.about_file_path

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
            continue

        try:
            # Generate value for 'about_resource' if it does not exist
            if not about.about_resource.value:
                about.about_resource.value = OrderedDict()
                if about.about_file_path.endswith('/'):
                    about.about_resource.value[u'.'] = None
                    about.about_resource.original_value = u'.'
                else:
                    about.about_resource.value[basename(about.about_file_path)] = None
                    about.about_resource.original_value = basename(about.about_file_path)
                about.about_resource.present = True

            if license_text_location:
                lic_loc_dict, lic_file_err = verify_license_files_in_location(about, license_text_location)
                if lic_loc_dict:
                    copy_files(lic_loc_dict, base_dir)
                if lic_file_err:
                    for file_err in lic_file_err:
                        errors.append(file_err)

            if gen_license:
                # Write generated LICENSE file
                lic_name, lic_context, lic_url = about.dump_lic(dump_loc, dje_license_dict)
                if lic_name:
                    if not about.license_name.present:
                        about.license_name.value = lic_name
                        about.license_name.present = True
                    if not about.license_file.present:
                        about.license_file.value = [about.dje_license_key.value + u'.LICENSE']
                        about.license_file.present = True
                        # The only time the tool fills in the license URL is
                        # when no license file present
                        if not about.license_url.present:
                            about.license_url.value = [lic_url]
                            about.license_url.present = True


            # Write the ABOUT file and check does the referenced file exist
            not_exist_errors = about.dump(dump_loc,
                                   with_empty=with_empty,
                                   with_absent=with_absent)
            file_field_not_exist_errors = check_file_field_exist(about, dump_loc)

            for e in not_exist_errors:
                errors.append(Error(ERROR, e))
            for e in file_field_not_exist_errors:
                errors.append(Error(ERROR, e))

        except Exception, e:
            # only keep the first 100 char of the exception
            emsg = repr(e)[:100]
            msg = (u'Failed to write ABOUT file at : '
                   u'%(dump_loc)s '
                   u'with error: %(emsg)s' % locals())
            errors.append(Error(ERROR, msg))
    dedup_errors = model.list_dedup(errors)
    return dedup_errors, abouts

def fetch_texts(abouts):
    """
    Given a list of About object, fetch updated data from the DejaCode API.
    """