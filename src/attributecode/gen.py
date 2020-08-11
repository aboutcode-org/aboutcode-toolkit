#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2020 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

# FIXME: why posipath???
from posixpath import basename
from posixpath import dirname
from posixpath import exists
from posixpath import join
from posixpath import normpath

from attributecode import ERROR
from attributecode import CRITICAL
from attributecode import INFO
from attributecode import Error
from attributecode import model
from attributecode import util
from attributecode.util import add_unc
from attributecode.util import csv
from attributecode.util import file_fields
from attributecode.util import to_posix
from attributecode.util import UNC_PREFIX_POSIX
from attributecode.util import unique


def check_duplicated_columns(location):
    """
    Return a list of errors for duplicated column names in a CSV file
    at location.
    """
    location = add_unc(location)
    with codecs.open(location, 'rb', encoding='utf-8-sig', errors='replace') as csvfile:
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
    return unique(errors)


def check_duplicated_about_resource(inventory_dict):
    """
    Return a list of errors for duplicated about_resource in a CSV file at location.
    """
    arp_list = []
    errors = []
    for component in inventory_dict:
        # Ignore all the empty path
        if component['about_resource']:
            if component['about_resource'] in arp_list:
                msg = ("The input has duplicated values in 'about_resource' "
                       "field: " + component['about_resource'])
                errors.append(Error(CRITICAL, msg))
            else:
                arp_list.append(component['about_resource'])
    return errors


def check_newline_in_file_field(inventory_dict):
    """
    Return a list of errors for newline characters detected in *_file fields.
    """
    errors = []
    for component in inventory_dict:
        for k in component.keys():
            if k in file_fields:
                try:
                    if '\n' in component[k]:
                        msg = ("New line character detected in '%s' for '%s' which is not supported."
                                "\nPlease use ',' to declare multiple files.") % (k, component['about_resource'])
                        errors.append(Error(CRITICAL, msg))
                except:
                    pass
    return errors


# TODO: this should be either the CSV or the ABOUT files but not both???
def load_inventory(location, base_dir, reference_dir=None):
    """
    Load the inventory file at `location` for ABOUT and LICENSE files stored in
    the `base_dir`. Return a list of errors and a list of About objects
    validated against the `base_dir`.

    Optionally use `reference_dir` as the directory location of extra reference
    license and notice files to reuse.
    """
    errors = []
    abouts = []
    base_dir = util.to_posix(base_dir)
    # FIXME: do not mix up CSV and JSON
    if location.endswith('.csv'):
        # FIXME: this should not be done here.
        dup_cols_err = check_duplicated_columns(location)
        if dup_cols_err:
            errors.extend(dup_cols_err)
            return errors, abouts
        inventory = util.load_csv(location)
    else:
        inventory = util.load_json(location)

    try:
        # FIXME: this should not be done here.
        dup_about_resource_err = check_duplicated_about_resource(inventory)
        if dup_about_resource_err:
            errors.extend(dup_about_resource_err)
            return errors, abouts
        newline_in_file = check_newline_in_file_field(inventory)
        if newline_in_file:
            errors.extend(newline_in_file)
            return errors, abouts
    except Exception as e:
        # TODO: why catch ALL Exception
        msg = "The essential field 'about_resource' is not found in the <input>"
        errors.append(Error(CRITICAL, msg))
        return errors, abouts

    for i, fields in enumerate(inventory):
        # check does the input contains the required fields
        required_fields = model.About.required_fields

        for f in required_fields:
            if f not in fields:
                msg = "Required field: %(f)r not found in the <input>" % locals()
                errors.append(Error(ERROR, msg))
                return errors, abouts
        afp = fields.get(model.About.ABOUT_RESOURCE_ATTR)

        # FIXME: this should not be a failure condition
        if not afp or not afp.strip():
            msg = 'Empty column: %(afp)r. Cannot generate .ABOUT file.' % locals()
            errors.append(Error(ERROR, msg))
            continue
        else:
            afp = util.to_posix(afp)
            loc = join(base_dir, afp)
        about = model.About(about_file_path=afp)
        about.location = loc

        # Update value for 'about_resource'
        # keep only the filename or '.' if it's a directory
        if 'about_resource' in fields:
            updated_resource_value = u''
            resource_path = fields['about_resource']
            if resource_path.endswith(u'/'):
                updated_resource_value = u'.'
            else:
                updated_resource_value = basename(resource_path)
            fields['about_resource'] = updated_resource_value

        ld_errors = about.load_dict(
            fields,
            base_dir,
            running_inventory=False,
            reference_dir=reference_dir,
        )
        """
        # 'about_resource' field will be generated during the process.
        # No error need to be raise for the missing 'about_resource'.
        for e in ld_errors:
            if e.message == 'Field about_resource is required':
                ld_errors.remove(e)
        """
        for e in ld_errors:
            if not e in errors:
                errors.extend(ld_errors)
        abouts.append(about)

    return unique(errors), abouts

def update_about_resource(self):
    pass

def generate(location, base_dir, android=None, reference_dir=None, fetch_license=False):
    """
    Load ABOUT data from a CSV inventory at `location`. Write ABOUT files to
    base_dir. Return errors and about objects.
    """
    not_exist_errors = []
    notice_dict = {}
    api_url = ''
    api_key = ''
    gen_license = False
    # FIXME: use two different arguments: key and url
    # Check if the fetch_license contains valid argument
    if fetch_license:
        # Strip the ' and " for api_url, and api_key from input
        api_url = fetch_license[0].strip("'").strip('"')
        api_key = fetch_license[1].strip("'").strip('"')
        gen_license = True

    # TODO: WHY use posix??
    bdir = to_posix(base_dir)

    errors, abouts = load_inventory(
        location=location,
        base_dir=bdir,
        reference_dir=reference_dir
    )

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
        dump_loc = join(bdir, about.about_file_path.lstrip('/'))

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
                about_resource_value = ''
                if about.about_file_path.endswith('/'):
                    about_resource_value = u'.'
                else:
                    about_resource_value = basename(about.about_file_path)
                about.about_resource.value[about_resource_value] = None
                about.about_resource.present = True
                # Check for the existence of the 'about_resource'
                # If the input already have the 'about_resource' field, it will
                # be validated when creating the about object
                loc = util.to_posix(dump_loc)
                about_file_loc = loc
                path = join(dirname(util.to_posix(about_file_loc)), about_resource_value)
                if not exists(path):
                    path = util.to_posix(path.strip(UNC_PREFIX_POSIX))
                    path = normpath(path)
                    msg = (u'Field about_resource: '
                           u'%(path)s '
                           u'does not exist' % locals())
                    not_exist_errors.append(msg)

            if gen_license:
                # Write generated LICENSE file
                license_key_name_context_url_list = about.dump_lic(dump_loc, license_dict)
                if license_key_name_context_url_list:
                    # use value not "presence"
                    if not about.license_file.present:
                        about.license_file.value = OrderedDict()
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

            about.dump(dump_loc)

            if android:
                """
                Create MODULE_LICENSE_XXX and get context to create NOTICE file
                follow the standard from Android Open Source Project
                """
                import os
                parent_path = os.path.dirname(util.to_posix(dump_loc))

                about.android_module_license(parent_path)
                notice_path, notice_context = about.android_notice(parent_path)
                if notice_path in notice_dict.keys():
                    notice_dict[notice_path] += '\n\n' + notice_context
                else:
                    notice_dict[notice_path] = notice_context

            for e in not_exist_errors:
                errors.append(Error(INFO, e))

        except Exception as e:
            # only keep the first 100 char of the exception
            # TODO: truncated errors are likely making diagnotics harder
            emsg = repr(e)[:100]
            msg = (u'Failed to write .ABOUT file at : '
                   u'%(dump_loc)s '
                   u'with error: %(emsg)s' % locals())
            errors.append(Error(ERROR, msg))

    if android:
        # Check if there is already a NOTICE file present
        for path in notice_dict.keys():
            if os.path.exists(path):
                msg = (u'NOTICE file already exist at: %s' % path)
                errors.append(Error(ERROR, msg))
            else:
                about.dump_android_notice(path, notice_dict[path])

    return unique(errors), abouts
