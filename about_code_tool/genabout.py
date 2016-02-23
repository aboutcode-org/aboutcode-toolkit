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

"""
Generate ABOUT files based on CSV file. The input file contains data such as the
ABOUT file location, the origin and license of the software components etc.
"""

from __future__ import print_function

from about import AboutFile
from about import ERROR_WARN_FIELDS
from about import MANDATORY_FIELDS
from about import OPTIONAL_FIELDS
from about import check_network_connection
from collections import namedtuple
from help import MAPPING_HELP
from help import VERBOSITY_HELP
from help import __full_info__
from help import __version_info__
from os import makedirs
from os.path import abspath
from os.path import basename
from os.path import dirname
from os.path import exists
from os.path import expanduser
from os.path import isdir
from os.path import join
from os.path import normpath
from urlparse import urljoin, urlparse
from util import ImprovedFormatter
from util import add_unc
from util import apply_mappings
from util import get_mappings
from util import path_exists

import copy
import csv
import errno
import json
import logging
import optparse
import os
import shutil
import sys
import urllib
import urllib2


LOG_FILENAME = 'error.log'

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.CRITICAL)
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)
file_logger = logging.getLogger(__name__ + '_file')


ESSENTIAL_FIELDS = ('about_file',)

SUPPORTED_FIELDS = OPTIONAL_FIELDS + MANDATORY_FIELDS + ESSENTIAL_FIELDS


def repr_problem(obj):
    """
    Return a formatted representation of a given Warn or Error object
    suitable for reporting.
    """
    field_name = obj.field_name
    field_value = obj.field_value
    message = obj.message
    return ('Field: %(field_name)s, '
            'Value: %(field_value)s, '
            'Message: %(message)s' % locals())


Warn = namedtuple('Warn', 'code field_name field_value message',)
Warn.__repr__ = repr_problem


Error = namedtuple('Error', 'code field_name field_value message',)
Error.__repr__ = repr_problem

IGNORED = 'field or line ignored problem'
VALUE = 'missing or empty or multiple value problem'
FILE = 'file problem'
URL = 'URL problem'
VCS = 'Version control problem'
DATE = 'Date problem'
ASCII = 'ASCII problem'
SPDX = 'SPDX license problem'
UNKNOWN = 'Unknown problem'
GENATTRIB = 'Attribution generation problem'
NETWORK = 'Network problem'


# Handle different behaviors if ABOUT file already exists
ACTION_DO_NOTHING_IF_ABOUT_FILE_EXIST = 0
ACTION_OVERWRITES_THE_CURRENT_ABOUT_FIELD_VALUE_IF_EXIST = 1
ACTION_KEEP_CURRENT_FIELDS_UNCHANGED_AND_ONLY_ADD_NEW_FIELDS = 2
ACTION_REPLACE_THE_ABOUT_FILE_WITH_THE_CURRENT_GENERATED_FILE = 3


def load_data_from_csv(location):
    """
    Load data from CSV at location and return a list of About data dictionaries.
    Keys are converted to lowercase.
    """
    abouts = []
    with open(location, 'rU') as inp:
        csvfile = csv.DictReader(inp)
        for row in csvfile:
            row_dict = {}
            for key, value in row.items():
                row_dict[key.lower()] = value.strip()
            abouts.append(row_dict)
    return abouts


def get_unknown_fields(abouts, user_keys):
    """
    Return a list of the non-supported fields given a list of About data
    dictionaries and a list of user-defined keys in MAPPING.CONFIG.
    """
    first = abouts[0]
    return [field for field in first
            if not field in SUPPORTED_FIELDS and not field in user_keys]


def has_duplicate_about_file_paths(abouts):
    """
    Given a list of About data dictionaries, check if there are any
    duplicated about_file paths. Return True if this is the case.
    """
    seen = set()
    for about in abouts:
        about_file_path = about['about_file']
        if about_file_path in seen:
            return True
        seen.add(about_file_path)


class GenAbout(object):
    def __init__(self):
        self.warnings = []
        self.errors = []
        self.extract_license_api_error = False

    @staticmethod
    def get_duplicated_keys(input_file):
        # FIXME: why use a static and not a regular function?
        csv_context = csv.reader(open(input_file, 'rU'))
        keys_row = csv_context.next()
        lower_case_keys_row = [k.lower() for k in keys_row]
        return ([key for key in keys_row if lower_case_keys_row.count(key.lower()) > 1])

    def validate(self, input_list):
        if not self.validate_mandatory_fields(input_list):
            required_keys = MANDATORY_FIELDS + ('about_file',)
            print('ERROR: Required column/keys not found in the <input_path> CSV.')
            print(required_keys)
            print("Use the '--mapping' option to map the input keys and verify the mapping information are correct.")
            print("OR correct the column names in the <input_path> CSV.")
            sys.exit(errno.EINVAL)

        elif not self.validate_value_in_essential_fields(input_list):
            print("ERROR: Some of the essential column/fields value are missing in the <input_path> CSV.")
            print(ESSENTIAL_FIELDS)
            print("Please check the the <input_path> CSV.")
            print("No ABOUT file was generated.")
            sys.exit(errno.EINVAL)

        elif has_duplicate_about_file_paths(input_list):
            print("ERROR: The <input_path> CSV has duplicated 'about_file' values.")
            print("Duplication is not supported. Please correct the the <input_path> CSV and rerun the tool.")
            print("No ABOUT file was generated.")
            sys.exit(errno.EINVAL)

    @staticmethod
    def validate_mandatory_fields(abouts):
        """
        Given a list of About data dictionaries, validate the presence of
        mandatory fields. Return True if they are present.
        """
        # FIXME: why use a static and not a regular function?
        
        for about in abouts:
            for key in MANDATORY_FIELDS + ESSENTIAL_FIELDS:
                if not key in about:
                    return False
        return True

    @staticmethod
    def validate_value_in_essential_fields(abouts):
        """
        Given a list of About data dictionaries, validate the presence of
        essential fields. Return True if they are present.
        """
        # FIXME: why use a static and not a regular function?
        for about in abouts:
            for key in ESSENTIAL_FIELDS:
                if not about.get(key):
                    return False
        return True

    def get_only_supported_fields(self, input_list, ignored_keys):
        copied_list = copy.deepcopy(input_list)
        for copied_dict in copied_list:
            for key in copied_dict.keys():
                if key in ignored_keys:
                    copied_dict.pop(key, None)
        msg = 'Field(s) %r not supported and will be ignored.' % ignored_keys
        self.warnings.append(Warn(IGNORED, ignored_keys, '', msg))
        return copied_list


    def verify_files_existence(self, input_list, project_dir, file_in_project):
        """
        Verify the existence of a file pointed to by ' _file' suffixed fields
        such as 'license_text_file'.
        """
        files_list = []
        # Get all the dictionary keys
        column_keys = input_list[0].keys()

        # Get all the keys that ends with _file except for the 'about_file'
        file_keys = []
        for key in column_keys:
            if key.endswith('_file') and key != 'about_file':
                file_keys.append(key)

        # FIXME: this loop is too complex
        for line in input_list:
            for file_key in file_keys:
                if not line[file_key]:
                    continue

                file_path_list = []
                file_value = []
                file_location = line['about_file']
                if file_location.startswith('/'):
                    file_location = file_location.partition('/')[2]
                about_parent_dir = dirname(file_location)
                if file_in_project:
                    if '\n' in line[file_key]:
                        file_value = line[file_key].split('\n')
                    else:
                        file_value.append(line[file_key])
                    for value in file_value:
                        if file_location.endswith('/'):
                            about_parent_dir = normpath(dirname(join(file_location, value)))
                        file_path_list.append(join(project_dir, dirname(file_location), value))
                else:
                    if '\n' in line[file_key]:
                        file_value = line[file_key].split('\n')
                    else:
                        file_value.append(line[file_key])
                    for value in file_value:
                        file_path_list.append(join(project_dir, value))

                for path in file_path_list:
                    if path_exists(path):
                        files_list.append((path, about_parent_dir))
                    else:
                        self.warnings.append(Warn(FILE, file_key, path, 'File does not exist.'))
        return files_list

    def request_license_data(self, url, username, api_key, license_key):
        """
        Return a dictionary of license data. 

        Send a request to a given API URL to gather license data for
        license_key, authenticating through an api_key and username.
        """
        payload = {
            'username': username,
            'api_key': api_key,
            'format': 'json'
        }

        url = url.rstrip('/')
        encoded_payload = urllib.urlencode(payload)
        full_url = '%(url)s/%(license_key)s/?%(encoded_payload)s' % locals()
        # handle special characters in URL such as space etc.
        full_url = urllib.quote(full_url, safe="%/:=&?~#+!$,;'@()*[]")
        license_data = {}
        try:
            # The 'self.extract_license_api_error' is True if any of the
            # api_url/api_username/api_key/network status have problem.
            if not self.extract_license_api_error:
                request = urllib2.Request(full_url)
                response = urllib2.urlopen(request)
                response_content = response.read()
                license_data = json.loads(response_content)
        except urllib2.HTTPError, http_e:
            # some auth problem
            if http_e.code == 401:
                error_msg = ("Authorization denied. Invalid '--api_username' or '--api_key'. License generation is skipped.")
                print('\n%(error_msg)s\n' % locals())
                self.extract_license_api_error = True
                self.errors.append(Error(VALUE, 'username/api_key', username + '/' + api_key, error_msg))
            else:
                # Since no api_url/api_username/api_key/network status have
                # problem detected, it yields 'dje_license_key' is the cause of
                # this exception. 
                self.errors.append(Error(VALUE, 'dje_license_key', license_key, "Invalid 'dje_license_key'"))
        except ValueError as e:
            # FIXME: when does this happen?
            pass
        finally:
            return license_data

    @staticmethod
    def copy_files(gen_location, files_list):
        """
        Copy the files into the gen_location
        """
        # FIXME : why use a static and not a regular function?
        for file_path, component_path in files_list:
            output_file_path = join(gen_location, component_path)
            if not path_exists(output_file_path):
                makedirs(output_file_path)
            shutil.copy2(file_path, output_file_path)

    def write_licenses(self, license_context_list):
        for gen_license_path, license_context in license_context_list:
            try:
                if not path_exists(dirname(gen_license_path)):
                    makedirs(dirname(gen_license_path))
                with open(gen_license_path, 'wb') as output:
                    output.write(license_context)
            except Exception:
                err = Error(UNKNOWN, 'Unknown', gen_license_path,
                            'Something is wrong.')
                self.errors.append(err)

    def get_license_details_from_api(self, url, username, api_key, license_key):
        """
        Returns the license_text of a given license_key using an API request.
        Returns an empty string if the text is not available.
        """
        license_data = self.request_license_data(url, username, api_key, license_key)
        license_name = license_data.get('name', '')
        license_text = license_data.get('full_text', '')
        license_key = license_data.get('key', '')
        return license_name, license_key, license_text

    def get_dje_license_list(self, gen_location, input_list, gen_license, dje_license_dict):
        # FIXME : this is too complex
        license_output_list = []
        for line in input_list:
            try:
                # If there is value in 'license_text_file', the tool will not
                # update/overwrite the 'license_text_file' with
                # 'dje_license_key'
                if line['license_text_file']:
                    file_location = line['about_file']
                    about_parent_dir = dirname(file_location)
                    license_text_file = line['license_text_file']
                    license_file = normpath(gen_location.rpartition('/')[0] + join(about_parent_dir, license_text_file))
                    if not path_exists(license_file):
                        self.errors.append(Error(FILE, 'license_text_file', license_file, "The 'license_text_file' does not exist."))
                else:
                    if gen_license and not self.extract_license_api_error:
                        if line['dje_license_key']:
                            license_output_list.append(self.gen_license_list(line))
                            lic_name = line['dje_license_name']
                            line['license_text_file'] = dje_license_dict[lic_name][0] + '.LICENSE'
                        else:
                            self.warnings.append(Warn(VALUE, 'dje_license_key', '',
                                                      "Missing 'dje_license_key' for " + line['about_file']))
            # This except condition will force the tool to create the
            # 'license_text_file' key column from the self.gen_license_list(line)
            except Exception:
                # FIXME: this is too complex
                if gen_license:
                    if line['dje_license_key']:
                        license_output_list.append(self.gen_license_list(line))
                        lic_name = line['dje_license_name']
                        if lic_name:
                            line['license_text_file'] = dje_license_dict[lic_name][0] + '.LICENSE'
                    else:
                        self.warnings.append(Warn(VALUE, 'dje_license_key', '',
                                                  "Missing 'dje_license_key' for " + line['about_file']))
        return license_output_list

    def pre_process_and_dje_license_dict(self, input_list, api_url, api_username, api_key):
        """
        Modify a list of About data dictionaries by adding license information
        fetched from the DejaCode API.
        """
        dje_uri = urlparse(api_url)
        domain = '{uri.scheme}://{uri.netloc}/'.format(uri=dje_uri)
        dje_lic_urn = urljoin(domain, 'urn/?urn=urn:dje:license:')
        key_text_dict = {}
        license_dict = {}
        if check_network_connection():
            if not self.valid_api_url(api_url):
                error_msg = "URL not reachable. Invalid '--api_url'. License generation is skipped."
                print('\n%(error_msg)s\n' % locals())
                self.extract_license_api_error = True
                self.errors.append(Error(VALUE, '--api_url', api_url, error_msg))
        else:
            error_msg = "Network problem. Please check your Internet connection. License generation is skipped."
            print('\n%(error_msg)s\n' % locals())
            self.extract_license_api_error = True
            self.errors.append(Error(NETWORK, 'Network', '', error_msg))
        for line in input_list:
            try:
                if line['dje_license_key']:
                    if '\n' in line['dje_license_key']:
                        line['dje_license_name'] = ""
                        self.errors.append(Error(VALUE, 'dje_license_key', line['dje_license_key'], "No multiple licenses or newline character are accepted."))
                        continue
                    lic = line['dje_license_key']
                    if not lic in license_dict:
                        detail_list = []
                        license_name, license_key, license_text = self.get_license_details_from_api(api_url, api_username, api_key, lic)
                        line['dje_license_key'] = license_key
                        license_dict[license_key] = license_name
                        line['dje_license_name'] = license_name
                        line['dje_license_url'] = dje_lic_urn + license_key
                        detail_list.append(license_key)
                        detail_list.append(license_text)
                        key_text_dict[license_name] = detail_list
                    else:
                        line['dje_license_name'] = license_dict[lic]
                        line['dje_license_url'] = dje_lic_urn + lic
            except Exception as e:
                err = Warn(VALUE, 'dje_license_key', '', 'Missing "dje_license_key" for ' + line['about_file'])
                self.warnings.append(err)
        return key_text_dict

    def valid_api_url(self, api_url):
        try:
            request = urllib2.Request(api_url)
            # This will always goes to exception as no username/key are provided.
            # The purpose of this code is to validate the provided api_url is correct
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, http_e:
            # The 405 error code is refer to "Method not allowed".
            # This is correct as no username and key are provided.
            if http_e.code == 405:
                return True
        except:
            # All other exceptions yield to invalid api_url
            pass
        return False

    def process_dje_licenses(self, dje_license_list, dje_license_dict, output_path):
        license_list_context = []
        for gen_path, license_name in dje_license_list:
            lic = license_name
            if gen_path.startswith('/'):
                gen_path = gen_path.partition('/')[2]
            if lic:
                license_key = dje_license_dict[lic][0]
                gen_license_path = join(output_path, gen_path, license_key) + '.LICENSE'
                if not path_exists(gen_license_path) and not self.extract_license_api_error:
                    context = dje_license_dict[lic][1]
                    if context:
                        gen_path_context = []
                        gen_path_context.append(gen_license_path)
                        gen_path_context.append(context.encode('utf8'))
                        license_list_context.append(gen_path_context)
        return license_list_context

    def pre_generation(self, gen_location, input_list, action_num):
        """
        Perform some pre-generation.
        TODO: document me
        """
        output_list = []
        for line in input_list:
            component_list = []
            file_location = line['about_file']
            # TODO: The following few line of code seems to change the value
            # without checking the action num which is incorrect.
            # Get the filename from the file_location and put it as the
            # value for 'about_resource'

            if file_location.startswith('/'):
                file_location = file_location.partition('/')[2]
            if not file_location.endswith('.ABOUT'):
                if file_location.endswith('/'):
                    file_location = dirname(file_location)
                    file_location = join(file_location, basename(file_location))
                file_location += '.ABOUT'
            # The following code is to check if there is any directory ends with spaces
            split_path = file_location.split('/')
            dir_endswith_space = False
            for segment in split_path:
                if segment.endswith(' '):
                    msg = 'File path contains directory name ends with spaces which is not allowed. Generation skipped.'
                    self.errors.append(Error(VALUE, 'about_file_path',
                                             file_location, msg))
                    dir_endswith_space = True
                    break
            if dir_endswith_space:
                continue

            about_file_location = join(gen_location, file_location)
            about_file_dir = dirname(about_file_location)
            if not os.path.exists(about_file_dir):
                # Check for invalid file path
                try:
                    makedirs(about_file_dir)
                except:
                    msg = 'Invalid ABOUT file path.'
                    self.errors.append(Error(VALUE, 'about_file_path',
                                             about_file_dir, msg))
                    continue
            about_file_exist = path_exists(about_file_location)
            if about_file_exist:
                if action_num == ACTION_DO_NOTHING_IF_ABOUT_FILE_EXIST:
                    msg = 'ABOUT file already existed. Generation is skipped.'
                    self.warnings.append(Warn(IGNORED, 'about_file',
                                              about_file_location, msg))
                    continue
                # Overwrites the current ABOUT field value if it existed
                elif action_num == ACTION_OVERWRITES_THE_CURRENT_ABOUT_FIELD_VALUE_IF_EXIST:
                    about_object = AboutFile(about_file_location)
                    for field_name, value in about_object.parsed.items():
                        field_name = field_name.lower()
                        if not field_name in line.keys() or not line[field_name]:
                            line[field_name] = value
                # Keep the current field value and only add the "new" field
                # and field value
                elif action_num == ACTION_KEEP_CURRENT_FIELDS_UNCHANGED_AND_ONLY_ADD_NEW_FIELDS:
                    about_object = AboutFile(about_file_location)
                    for field_name, value in about_object.parsed.items():
                        field_name = field_name.lower()
                        line[field_name] = value
                # We do not need to do anything if action_num is 3 as the
                # original ABOUT file will be replaced in the write_output()
                elif action_num == ACTION_REPLACE_THE_ABOUT_FILE_WITH_THE_CURRENT_GENERATED_FILE:
                    pass

            # The following is to ensure about_resource is present.
            # If they exist already, the code will not changes these.
            self.update_about_resource(line, about_file_exist)

            component_list.append(about_file_location)
            component_list.append(line)
            output_list.append(component_list)
        return output_list

    def update_about_resource(self, line, about_file_exist):
        # Check if 'about_resource' exist
        try:
            if line['about_resource']:
                if not about_file_exist:
                    about_resource = line['about_file']
                    if about_resource.endswith('/'):
                        line['about_resource'] = '.'
            else:  # 'about_resource' key present with no value
                about_resource = line['about_file']
                if about_resource.endswith('/'):
                    line['about_resource'] = '.'
                else:
                    line['about_resource'] = basename(about_resource)
        except:
            # Add the 'about_resource' field
            about_resource = line['about_file']
            if about_resource.endswith('/'):
                line['about_resource'] = '.'
            else:
                line['about_resource'] = basename(about_resource)

    @staticmethod
    def gen_license_list(line):
        dje_license_name = line['dje_license_name']
        file_location = line['about_file']
        """if file_location.endswith('/'):
            file_location = file_location.rpartition('/')[0]"""
        about_parent_dir = dirname(file_location)
        return (about_parent_dir, dje_license_name)

    @staticmethod
    def format_output(input_list):
        """
        Process the input and convert to the specific strings format.
        """
        components_list = []
        for about_file_location, about_dict_list in input_list:
            component = []
            component_name = about_dict_list.get('name', '')
            component_version = about_dict_list.get('version', '')
            context = 'about_resource: %s\nname: %s\nversion: %s\n\n' % (
                about_dict_list['about_resource'], component_name, component_version)

            for item in sorted(about_dict_list.iterkeys()):
                if item == 'about_file':
                    continue
                if not item in MANDATORY_FIELDS:
                    # The purpose of the replace('\n', '\n ') is used to
                    # format the continuation strings
                    value = about_dict_list[item].replace('\n', '\n ')
                    if (value or item in MANDATORY_FIELDS) and not item in ERROR_WARN_FIELDS and not item == 'about_resource':
                        # It will cause error if value has different coding
                        try:
                            value = unicode(value, errors='ignore')
                        except:
                            pass
                        context += item + ': ' + value + '\n'

            component.append(about_file_location)
            component.append(context)
            components_list.append(component)
        return components_list

    @staticmethod
    def write_output(output):
        for about_file_location, context in output:
            about_file_location = add_unc(about_file_location)
            if path_exists(about_file_location):
                os.remove(about_file_location)
            with open(about_file_location, 'wb') as output_file:
                output_file.write(context)

    def warnings_errors_summary(self):
        if self.errors:
            for error_msg in self.errors:
                logger.error(error_msg)
                file_logger.error(error_msg)

        if self.warnings:
            for warning_msg in self.warnings:
                logger.warning(warning_msg)
                file_logger.warning(warning_msg)


def filter_dicts_of_empty_values(abouts):
    """
    Return a list of About data dictionaries filtering dictionaries composed
    entirely of empty values.
    """
    filtered = []
    for about in abouts:
        if any(v and v.strip() for v in about.values()):
            filtered.append(dict(about))
    return filtered



USAGE_SYNTAX = """\
    <input_path> must be a file with a .csv extension containing an inventory of ABOUT data.
    <output_path> must be a directory where ABOUT files should be generated.
"""

ACTION_HELP = """\
Handle different behaviors if ABOUT files already exist:
0 - Do nothing if an ABOUT file exists (default).
1 - Merge and overwrite existing ABOUT files field values with new generated field/value.
2 - Merge and keep existing ABOUT files field value. Add new generated field/value.
3 - Overwrite existing ABOUT files with generated files.
"""

COPY_FILES_HELP = """\
Copy the '*_file' from the COPY_FILES directory to the generated location.
"""

LICENSE_TEXT_LOCATION_HELP = """\
Copy the 'license_text_file' from the LICENSE_TEXT_LOCATION directory to the generated location.
"""

EXTRACT_LICENSE_HELP = """\
Fetch and save license texts in <license_key>.LICENSE files side-by-side with the
.ABOUT files using the DejaCode License Library API.
api_url - URL to the DejaCode License Library.
api_username - The DejaCode username.
api_key - Key attached to your username and used to authenticate
          yourself in the API. Contact us to get an API key.

Example syntax:
genabout.py --extract_license --api_url='api_url' --api_username='api_username' --api_key='api_key'
"""


def main(parser, options, args):
    """
    Main commnand line entry point.
    """
    verbosity = options.verbosity
    action = options.action
    copy_files_path = options.copy_files
    license_text_path = options.license_text_location
    mapping_config = options.mapping
    extract_license = options.extract_license

    action_num = 0
    api_url = ''
    api_username = ''
    api_key = ''
    gen_license = False
    dje_license_dict = {}

    if options.version:
        print(__full_info__)
        sys.exit(0)

    if verbosity == 1:
        handler.setLevel(logging.ERROR)
    elif verbosity >= 2:
        handler.setLevel(logging.WARNING)

    valid_actions = 0, 1, 2, 3
    if action:
        if action in valid_actions:
            action_num = action
        else:
            print('ERROR: Invalid action: must be one of: 0, 1, 2 or 3')
            sys.exit(errno.EINVAL)

    if copy_files_path:
        # code to handle tilde character
        copy_files_path = os.path.abspath(expanduser(copy_files_path))
        if not path_exists(copy_files_path):
            print("ERROR: The COPY_FILES path does not exist.")
            sys.exit(errno.EINVAL)

    if license_text_path:
        # code to handle tilde character
        license_text_path = os.path.abspath(expanduser(license_text_path))
        if not path_exists(license_text_path):
            print("ERROR: LICENSE_TEXT_LOCATION path does not exist.")
            sys.exit(errno.EINVAL)

    if mapping_config and not path_exists('MAPPING.CONFIG'):
            print("ERROR: The file 'MAPPING.CONFIG' does not exist.")
            sys.exit(errno.EINVAL)

    if extract_license:
        api_url = extract_license[0].partition('--api_url=')[2]
        api_username = extract_license[1].partition('--api_username=')[2]
        api_key = extract_license[2].partition('--api_key=')[2]
        gen_license = True

    if not len(args) == 2:
        print('ERROR: <input_path> and <utput_path> are required.')
        print()
        parser.print_help()
        sys.exit(errno.EEXIST)

    input_path, output_path = args
    output_path = abspath(output_path)

    if not output_path.endswith('/'):
        output_path += '/'

    if not exists(input_path):
        print('ERROR: <input_path> file does not exist.')
        print()
        parser.print_help()
        sys.exit(errno.EEXIST)

    if not exists(output_path):
        print('ERROR: <output_path> directory does not exist.')
        print()
        parser.print_help()
        sys.exit(errno.EEXIST)

    if not isdir(output_path):
        print('ERROR: <output_path> must be a directory, not a file.')
        print()
        parser.print_help()
        sys.exit(errno.EISDIR)

    if not input_path.endswith('.csv'):
        print("ERROR: <input_path> file must be a CSV file ends with '.csv'")
        print()
        parser.print_help()
        sys.exit(errno.EINVAL)

    gen = GenAbout()

    dup_keys = gen.get_duplicated_keys(input_path)
    if dup_keys:
        print('ERROR: The <input_path> CSV file contains duplicated column keys. '
              'Duplicated column keys are not allowed.')
        print(dup_keys)
        print()
        print('Please fix the input file and re-run the tool.')
        sys.exit(errno.EINVAL)

    # Remove the previous log file if exist
    log_path = join(output_path, LOG_FILENAME)
    if exists(log_path):
        os.remove(log_path)

    file_handler = logging.FileHandler(log_path)
    file_logger.addHandler(file_handler)

    input_data = load_data_from_csv(input_path)
    input_data = filter_dicts_of_empty_values(input_data)

    user_keys = []
    if mapping_config:
        mappings = get_mappings(location=None)
        input_data = apply_mappings(input_data, mappings)
        user_keys = mappings.keys()

    gen.validate(input_data)

    ignored_fields_list = get_unknown_fields(input_data, user_keys)
    if ignored_fields_list:
        input_list = gen.get_only_supported_fields(input_data, ignored_fields_list)
    else:
        input_list = input_data

    if copy_files_path:
        if not isdir(copy_files_path):
            print("WARNING: The COPY_FILES path must be a directory.")
            print("'--copy_files' option ignored.")
        else:
            licenses_in_project = True
            license_list = gen.verify_files_existence(input_list,
                                                      copy_files_path,
                                                      licenses_in_project)
            if not license_list:
                print("WARNING: No file found. '--copy_files' is ignored.")
            else:
                gen.copy_files(output_path, license_list)

    if license_text_path:
        if not isdir(license_text_path):
            print("WARNING: The LICENSE_TEXT_LOCATION  path must be a directory.")
            print("'--license_text_location' option ignored.")
        else:
            licenses_in_project = False
            license_list = gen.verify_files_existence(input_list,
                                                      license_text_path,
                                                      licenses_in_project)
            if not license_list:
                print("WARNING: No file found. '--copy_files' option ignored.")
            else:
                gen.copy_files(output_path, license_list)

    if extract_license:
        if not api_url or not api_username or not api_key:
            print("ERROR: Missing argument for --extract_license")
            sys.exit(errno.EINVAL)
        for line in input_list:
            try:
                if line['dje_license_key']:
                    break
            except Exception as e:
                print(repr(e))
                print("ERROR: The <input_path> CSV does not contain the required column 'dje_license_key' ")
                sys.exit(errno.EINVAL)

    if gen_license:
        # Strip the ' and " for api_url, api_username and api_key from input
        api_url = api_url.strip("'").strip("\"")
        api_username = api_username.strip("'").strip("\"")
        api_key = api_key.strip("'").strip("\"")
        dje_license_dict = gen.pre_process_and_dje_license_dict(input_list, api_url, api_username, api_key)

    dje_license_list = gen.get_dje_license_list(output_path, input_list, gen_license, dje_license_dict)
    components_list = gen.pre_generation(output_path, input_list, action_num)
    formatted_output = gen.format_output(components_list)
    gen.write_output(formatted_output)

    if dje_license_list:
        license_list_context = gen.process_dje_licenses(dje_license_list, dje_license_dict, output_path)
        gen.write_licenses(license_list_context)

    print('Completed.')
    gen.warnings_errors_summary()
    print('Warnings: %s' % len(gen.warnings))
    print('Errors: %s' % len(gen.errors))


def get_parser():
    """
    Return a command line options parser.
    """
    parser = optparse.OptionParser(
        usage='%prog [options] input_path output_path',
        description=USAGE_SYNTAX,
        add_help_option=False,
        formatter=ImprovedFormatter(),
    )
    parser.add_option('-h', '--help', action='help', help='Print this help message and exit.')
    parser.add_option('--version', action='store_true', help='Print the current version and copyright notice and exit.')
    parser.add_option('--verbosity', type=int, help=VERBOSITY_HELP)
    parser.add_option('--action', type=int, help=ACTION_HELP)
    parser.add_option('--copy_files', type='string', help=COPY_FILES_HELP)
    parser.add_option('--license_text_location', type='string', help=LICENSE_TEXT_LOCATION_HELP)
    parser.add_option('--mapping', action='store_true', help=MAPPING_HELP)
    parser.add_option('--extract_license', type='string', nargs=3, help=EXTRACT_LICENSE_HELP)
    return parser


if __name__ == '__main__':
    print(__version_info__)
    parser = get_parser()
    options, args = parser.parse_args()
    main(parser, options, args)
