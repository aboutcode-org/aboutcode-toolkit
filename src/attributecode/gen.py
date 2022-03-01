#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) nexB Inc. http://www.nexb.com/ - All rights reserved.
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

import codecs

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
from attributecode.util import invalid_chars
from attributecode.util import to_posix
from attributecode.util import UNC_PREFIX_POSIX
from attributecode.util import unique
from attributecode.util import load_scancode_json, load_csv, load_json, load_excel


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
    dupes = dict()
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
        err = Error(ERROR, msg)
        if not err in errors:
            errors.append(err)
    return errors


def check_duplicated_about_resource(arp, arp_list):
    """
    Return error for duplicated about_resource.
    """
    if arp in arp_list:
        msg = ("The input has duplicated values in 'about_resource' "
               "field: " + arp)
        return Error(CRITICAL, msg)
    return ''


def check_newline_in_file_field(component):
    """
    Return a list of errors for newline characters detected in *_file fields.
    """
    errors = []
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


def check_about_resource_filename(arp):
    """
    Return error for invalid/non-support about_resource's filename or
    empty string if no error is found.
    """
    if invalid_chars(arp):
        msg = ("Invalid characters present in 'about_resource' "
                   "field: " + arp)
        return (Error(ERROR, msg))
    return ''


def load_inventory(location, from_attrib=False, base_dir=None, scancode=False, reference_dir=None):
    """
    Load the inventory file at `location` for ABOUT and LICENSE files stored in
    the `base_dir`. Return a list of errors and a list of About objects
    validated against the `base_dir`.

    Optionally use `reference_dir` as the directory location of extra reference
    license and notice files to reuse.
    """
    errors = []
    abouts = []

    if base_dir:
        base_dir = util.to_posix(base_dir)
    if scancode:
        inventory = load_scancode_json(location)
    else:
        if location.endswith('.csv'):
            dup_cols_err = check_duplicated_columns(location)
            if dup_cols_err:
                errors.extend(dup_cols_err)
                return errors, abouts
            inventory = load_csv(location)
        elif location.endswith('.xlsx'):
            dup_cols_err, inventory = load_excel(location)
            if dup_cols_err:
                errors.extend(dup_cols_err)
                return errors, abouts
        else:
            inventory = load_json(location)

    try:
        arp_list = []
        errors = []
        for component in inventory:
            if not from_attrib:
                arp = component['about_resource']
                dup_err = check_duplicated_about_resource(arp, arp_list)
                if dup_err:
                    if not dup_err in errors:
                        errors.append(dup_err)
                else:
                    arp_list.append(arp)

                invalid_about_filename = check_about_resource_filename(arp)
                if invalid_about_filename and not invalid_about_filename in errors:
                    errors.append(invalid_about_filename)

            newline_in_file_err = check_newline_in_file_field(component)
            if newline_in_file_err:
                errors.extend(newline_in_file_err)
        if errors:
            return errors, abouts
    except Exception as e:
        # TODO: why catch ALL Exception
        msg = "The essential field 'about_resource' is not found in the <input>"
        errors.append(Error(CRITICAL, msg))
        return errors, abouts

    custom_fields_list = []
    for fields in inventory:
        # check does the input contains the required fields
        required_fields = model.About.required_fields

        for f in required_fields:
            if f not in fields:
                if from_attrib and f == 'about_resource':
                    continue
                else:
                    msg = "Required field: %(f)r not found in the <input>" % locals()
                    errors.append(Error(CRITICAL, msg))
                    return errors, abouts
        # Set about file path to '' if no 'about_resource' is provided from
        # the input for `attrib`
        if not 'about_resource' in fields:
            afp = ''
        else:
            afp = fields.get(model.About.ABOUT_RESOURCE_ATTR)

        """
        # FIXME: this should not be a failure condition
        if not afp or not afp.strip():
            msg = 'Empty column: %(afp)r. Cannot generate .ABOUT file.' % locals()
            errors.append(Error(ERROR, msg))
            continue
        else:
        """
        afp = util.to_posix(afp)
        if base_dir:
            loc = join(base_dir, afp)
        else:
            loc = afp
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

        # Set 'about_resource' to '.' if no 'about_resource' is provided from
        # the input for `attrib`
        elif not 'about_resource' in fields and from_attrib:
            fields['about_resource'] = u'.'

        ld_errors = about.load_dict(
            fields,
            base_dir,
            scancode=scancode,
            from_attrib=from_attrib,
            running_inventory=False,
            reference_dir=reference_dir,
        )

        for severity, message in ld_errors:
            if 'Custom Field' in message:
                field_name = message.replace('Custom Field: ', '').strip()
                if not field_name in custom_fields_list:
                    custom_fields_list.append(field_name)
            else:
                errors.append(Error(severity, message))

        abouts.append(about)
    if custom_fields_list:
        custom_fields_err_msg = 'Field ' + str(custom_fields_list) + ' is a custom field.'
        errors.append(Error(INFO, custom_fields_err_msg))
    # Covert the license_score value from string to list of int
    # The licesne_score is not in the spec but is specify in the scancode license scan.
    # This key will be treated as a custom string field. Therefore, we need to
    # convert back to the list with float type for score.
    if scancode:
        for about in abouts:
            try:
                score_list = list(map(float, about.license_score.value.replace('[', '').replace(']', '').split(',')))
                about.license_score.value = score_list
            except:
                pass

    return errors, abouts


def update_about_resource(self):
    pass


def generate(location, base_dir, android=None, reference_dir=None, fetch_license=False, fetch_license_djc=False):
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
    if fetch_license_djc:
        # Strip the ' and " for api_url, and api_key from input
        api_url = fetch_license_djc[0].strip("'").strip('"')
        api_key = fetch_license_djc[1].strip("'").strip('"')
        gen_license = True

    if fetch_license:
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
        # Strip trailing spaces
        about.about_file_path = about.about_file_path.strip()
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
                about.about_resource.value = dict()
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
                errors.append(Error(INFO, msg))

            licenses_dict = {}
            if gen_license:
                # Write generated LICENSE file
                license_key_name_context_url_list = about.dump_lic(dump_loc, license_dict)
                if license_key_name_context_url_list:
                    for lic_key, lic_name, lic_filename, lic_context, lic_url, spdx_lic_key in license_key_name_context_url_list:
                        licenses_dict[lic_key] = [lic_name, lic_filename, lic_context, lic_url, spdx_lic_key]
                        if not lic_name in about.license_name.value:
                            about.license_name.value.append(lic_name)
                        about.license_file.value[lic_filename] = lic_filename
                        if not lic_url in about.license_url.value:
                            about.license_url.value.append(lic_url)
                        if not spdx_lic_key in about.spdx_license_key.value:
                            about.spdx_license_key.value.append(spdx_lic_key)
                        if about.license_name.value:
                            about.license_name.present = True
                        if about.license_file.value:
                            about.license_file.present = True
                        if about.license_url.value:
                            about.license_url.present = True
                        if about.spdx_license_key.value:
                            about.spdx_license_key.present = True

            about.dump(dump_loc, licenses_dict)

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
    return errors, abouts
