#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2014 nexB Inc. http://www.nexb.com/ - All rights reserved.
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
This is a tool to generate ABOUT files based on the input file.
The input file should be a csv format which contains information about the
file location, origin and license of the software components etc.
"""

from __future__ import print_function

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

from collections import namedtuple
from os import makedirs
from os.path import exists, dirname, join, abspath, isdir, normpath, basename

import about

__version__ = '0.9.0'

__copyright__ = """
Copyright (c) 2013-2014 nexB Inc. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

LOG_FILENAME = 'error.log'

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.CRITICAL)
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)
file_logger = logging.getLogger(__name__ + '_file')

ESSENTIAL_FIELDS = ('about_file',)

# The 'dje_license_key' will be removed and will use the 'dje_license' instead.
SUPPORTED_FIELDS = about.OPTIONAL_FIELDS + about.MANDATORY_FIELDS + ('about_file',)

Warn = namedtuple('Warn', 'field_name field_value message',)
Error = namedtuple('Error', 'field_name field_value message',)

# Handle different behaviors if ABOUT files already existed
ACTION_DO_NOTHING_IF_ABOUT_FILE_EXIST = 0
ACTION_OVERWRITES_THE_CURRENT_ABOUT_FIELD_VALUE_IF_EXIST = 1
ACTION_KEEP_CURRENT_FIELDS_UNCHANGED_AND_ONLY_ADD_NEW_FIELDS = 2
ACTION_REPLACE_THE_ABOUT_FILE_WITH_THE_CURRENT_GENERATED_FILE = 3



class GenAbout(object):
    def __init__(self):
        self.warnings = []
        self.errors = []
        self.extract_dje_license_error = False

    @staticmethod
    def get_duplicated_keys(input_file):
        csv_context = csv.reader(open(input_file, 'rU'))
        keys_row = csv_context.next()
        lower_case_keys_row = [k.lower() for k in keys_row]
        return ([key for key in keys_row if lower_case_keys_row.count(key.lower()) > 1])

    @staticmethod
    def get_input_list(input_file):
        csvfile = csv.DictReader(open(input_file, 'rU'))
        input_list = []
        for row in csvfile:
            row_dict = {}
            for key in row:
                row_dict[key.lower()] = row[key]
            input_list.append(row_dict)
        return input_list
        # return [{k.lower(): v for k, v in r.iteritems()} for r in csvfile]

    @staticmethod
    def get_non_empty_rows_list(input_list):
        copied_list = copy.deepcopy(input_list)
        new_list = []
        for line in copied_list:
            for key in line.keys():
                if line[key]:
                    new_list.append(line)
                    break
        return new_list

    @staticmethod
    def get_mapping_list():
        """
        Read the MAPPING.CONFIG
        """
        self_path = abspath(dirname(__file__))
        mapping_list = {}
        try:
            with open(join(self_path, 'MAPPING.CONFIG'), 'rU') as file_in:
                for line in file_in.readlines():
                    if not line.startswith('#') and ':' in line:
                        about_spec_key = line.partition(':')[0]
                        user_spec_key = line.partition(':')[2].strip()
                        # Handle cases which keys contain spaces
                        if about_spec_key.endswith(' '):
                            about_spec_key = about_spec_key.strip()
                        about_spec_key = about_spec_key.replace(' ', '_')
                        mapping_list[about_spec_key.lower()] = user_spec_key.lower()
        except Exception as e:
            print(repr(e))
            print('The "MAPPING.CONFIG" file cannot be opened.')
            sys.exit(errno.EACCES)
        return mapping_list

    @staticmethod
    def convert_input_list(input_list, mapping_list):
        """
        Perform the key mapping
        """
        copied_list = copy.deepcopy(input_list)
        for copied_dict in copied_list:
            for about_spec_key in mapping_list:
                if mapping_list[about_spec_key] in copied_dict.keys():
                    copied_dict[about_spec_key] = copied_dict.pop(mapping_list[about_spec_key])
        return copied_list

    def validate(self, input_list):
        if not self.validate_mandatory_fields(input_list):
            required_keys = about.MANDATORY_FIELDS + ('about_file',)
            print("The required keys not found.")
            print(required_keys)
            print("Please use the '--mapping' option to map the input keys and verify the mapping information are correct.")
            print("OR, correct the header keys from the input CSV.")
            sys.exit(errno.EINVAL)
        if not self.validate_value_in_essential_fields(input_list):
            print("Some of the essential fields value are missing.")
            print(ESSENTIAL_FIELDS)
            print("Please check the input CSV.")
            print("No ABOUT file is created.")
            sys.exit(errno.EINVAL)
        if self.validate_duplication(input_list):
            print("The input has duplicated 'about_file' and 'about_resource'.")
            print("Duplication is not supported. Please correct the input and rerun the tool.")
            print("No ABOUT file is created.")
            sys.exit(errno.EINVAL)

    @staticmethod
    def validate_mandatory_fields(input_list):
        for line in input_list:
            for key in about.MANDATORY_FIELDS + ('about_file',):
                if not key in line.keys():
                    return False
        return True

    @staticmethod
    def validate_value_in_essential_fields(input_list):
        for line in input_list:
            for key in ESSENTIAL_FIELDS:
                if not line[key]:
                    return False
        return True

    @staticmethod
    def validate_duplication(input_list):
        check_duplication = []
        for line in input_list:
            component = line['about_file']
            if component in check_duplication:
                return True
            check_duplication.append(component)
        return False

    def get_only_supported_fields(self, input_list, ignored_keys_list):
        copied_list = copy.deepcopy(input_list)
        for copied_dict in copied_list:
            for key in copied_dict.keys():
                if key in ignored_keys_list:
                    copied_dict.pop(key, None)
        msg = 'The field(s) "%s" is/are not supported and will be ignored.' % ignored_keys_list
        self.warnings.append(Warn(ignored_keys_list, '', msg))
        return copied_list

    @staticmethod
    def get_non_supported_fields(input_list, mapping_keys):
        """
        Returns a list of the non-supported fields in a given line.
        """
        first_line = input_list[0]
        return [field for field in first_line.keys() if not field in SUPPORTED_FIELDS and not field in mapping_keys]

    def verify_files_existence(self, input_list, project_dir, file_in_project):
        """
        Verify the existence of the 'license text file'
        """
        files_list = []
        # Get all the dictionary keys
        column_keys = input_list[0].keys()

        # Get all the keys that ending with _file except for the 'about_file
        file_keys = []
        for key in column_keys:
            if '_file' in key and key != 'about_file':
                file_keys.append(key)

        for line in input_list:
            for file_key in file_keys:
                if line[file_key]:
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
                        if _exists(path):
                            files_list.append((path, about_parent_dir))
                        else:
                            self.warnings.append(Warn(file_key, path, "File does not exist."))
        return files_list

    def request_license_data(self, url, username, api_key, license_key):
        """
        Send a request to a given API URL to gather license data.
        Authentication through an Api Key and a username.
        Returns a python dictionary of results returned by the API.
        """
        payload = {
            'username': username,
            'api_key': api_key,
            'format': 'json'
        }

        full_url = '{0}{1}/?{2}'.format(
            url if url.endswith('/') else url + '/',
            license_key, urllib.urlencode(payload))
        # The following is to handle special characters in URL such as space etc.
        full_url = urllib.quote(full_url, safe="%/:=&?~#+!$,;'@()*[]")

        try:
            request = urllib2.Request(full_url)
            response = urllib2.urlopen(request)
            response_content = response.read()
            data = json.loads(response_content)
        except urllib2.HTTPError as http_e:
            # the code 401 represents authorization problem
            if http_e.code == 401:
                error_msg = ("Authorization denied. Invalid '--api_username' or '--api_key'."
                            " LICENSE generation is skipped.")
                print("\n" + error_msg + "\n")
                self.extract_dje_license_error = True
                self.errors.append(Error('username/key', username + '/' + api_key, error_msg))
            else:
                self.errors.append(Error('dje_license', license_key,
                                         "Invalid 'dje_license_key'"))
            return {}
        except urllib2.URLError:
            if about.check_network_connection():
                error_msg = ("URL not reachable. Invalid '--api_url'."
                             " LICENSE generation is skipped.")
                print("\n" + error_msg + "\n")
                self.extract_dje_license_error = True
                self.errors.append(Error('--api_url', url, error_msg))
            else:
                error_msg = "Network problem. Please check the Internet connection. LICENSE generation is skipped."
                print("\n" + error_msg + "\n")
                self.extract_dje_license_error = True
                self.errors.append(Error('Network', '', error_msg))
            return {}
        except ValueError:
            return {}
        else:
            return data

    @staticmethod
    def copy_files(gen_location, files_list):
        """
        Copy the files into the gen_location
        """
        for file_path, component_path in files_list:
            output_file_path = join(gen_location, component_path)
            if not _exists(output_file_path):
                makedirs(output_file_path)
            shutil.copy2(file_path, output_file_path)

    def write_licenses(self, license_context_list):
        for gen_license_path, license_context in license_context_list:
            try:
                if not _exists(dirname(gen_license_path)):
                    makedirs(dirname(gen_license_path))
                with open(gen_license_path, 'wb') as output:
                    output.write(license_context)
            except Exception:
                err = Error('Unknown', gen_license_path,
                            'Something is wrong.')
                self.errors.append(err)

    def get_license_details_from_api(self, url, username, api_key, license_key):
        """
        Returns the license_text of a given license_key using an API request.
        Returns an empty string if the text is not available.
        """
        data = self.request_license_data(url, username, api_key, license_key)
        license_name = data.get('name', '')
        license_text = data.get('full_text', '')
        license_key = data.get('key', '')
        return [license_name, license_key, license_text]

    def get_dje_license_list(self, gen_location, input_list, gen_license, dje_license_dict):
        # FIXME : this is too complex
        license_output_list = []
        for line in input_list:
            try:
                # If there is value in 'license_text_file', the tool will not
                # update/overwrite the 'license_text_file' with 'dje_license_key'
                if line['license_text_file']:
                    file_value = []
                    license_file_list = []
                    file_location = line['about_file']
                    about_parent_dir = dirname(file_location)
                    if '\n' in line['license_text_file']:
                        file_value = line['license_text_file'].split('\n')
                    else:
                        file_value = [line['license_text_file']]
                    for license_text_file in file_value:
                        license_file_list.append(normpath(gen_location.rpartition('/')[0] + join(about_parent_dir, license_text_file)))
                    for license_file in license_file_list:
                        if not _exists(license_file):
                            self.errors.append(Error('license_text_file', license_file, "The 'license_text_file' does not exist."))
                else:
                    if gen_license:
                        if line['dje_license']:
                            license_output_list.append(self.gen_license_list(line))
                            license_names = []
                            if '\n' in line['dje_license_name']:
                                license_names = line['dje_license_name'].split('\n ')
                            else:
                                license_names = [line['dje_license_name']]
                            for lic_name in license_names:
                                try:
                                    if line['license_text_file']:
                                        line['license_text_file'] += '\n '
                                    line['license_text_file'] += dje_license_dict[lic_name][0] + '.LICENSE'
                                except:
                                    line['license_text_file'] = dje_license_dict[lic_name][0] + '.LICENSE'
                        else:
                            self.warnings.append(Warn('dje_license', '',
                                                      "Missing 'dje_license' for " + line['about_file']))
            # This except condition will force the tool to create the
            # 'license_text_file' key column from the self.gen_license_list(line)
            except Exception:
                # FIXME: this is too complex
                if gen_license:
                    if line['dje_license']:
                        license_output_list.append(self.gen_license_list(line))
                        license_names = []
                        if '\n' in line['dje_license_name']:
                            license_names = line['dje_license_name'].split('\n ')
                        else:
                            license_names = [line['dje_license_name']]

                        for lic_name in license_names:
                            if 'license_text_file' in line:
                                line['license_text_file'] += '\n '
                            license_name = dje_license_dict[lic_name][0]
                            license_text_file = license_name + '.LICENSE'
                            line['license_text_file'] = license_text_file
                    else:
                        self.warnings.append(Warn('dje_license', '',
                                                  "Missing 'dje_license' for " + line['about_file']))
        return license_output_list

    def pre_process_and_dje_license_dict(self, input_list, api_url, api_username, api_key):
        key_text_dict = {}
        license_dict = {}
        for line in input_list:
            try:
                if line['dje_license']:
                    license_list = []
                    if '\n' in line['dje_license']:
                        license_list = line['dje_license'].split('\n')
                    else:
                        license_list = [line['dje_license']]
                    for lic in license_list:
                        if not lic in license_dict:
                            detail_list = []
                            detail = self.get_license_details_from_api(api_url, api_username, api_key, lic)
                            license_dict[lic] = detail[0]
                            try:
                                if line['dje_license_name']:
                                    line['dje_license_name'] += "\n " + detail[0]
                            except:
                                line['dje_license_name'] = detail[0]
                            dje_key = detail[1]
                            license_context = detail [2]
                            detail_list.append(dje_key)
                            detail_list.append(license_context)
                            key_text_dict[detail[0]] = detail_list
                        else:
                            line['dje_license_name'] = license_dict[lic]
            except Exception:
                err = Warn('dje_license', '',
                           'Missing "dje_license" for ' + line['about_file'])
                self.warnings.append(err)
        return key_text_dict

    def process_dje_licenses(self, dje_license_list, dje_license_dict, output_path):
        license_list_context = []
        for gen_path, license_name in dje_license_list:
            licenses = []
            if '\n' in license_name:
                licenses = license_name.split('\n ')
            else:
                licenses = [license_name]
            if gen_path.startswith('/'):
                gen_path = gen_path.partition('/')[2]
            for lic in licenses:
                license_key = dje_license_dict[lic][0]
                gen_license_path = join(output_path, gen_path, license_key) + '.LICENSE'
                if not _exists(gen_license_path) and not self.extract_dje_license_error:
                    context = dje_license_dict[lic][1]
                    if context:
                        gen_path_context = []
                        gen_path_context.append(gen_license_path)
                        gen_path_context.append(context.encode('utf8'))
                        license_list_context.append(gen_path_context)
        return license_list_context

    def pre_generation(self, gen_location, input_list, action_num, all_in_one):
        """
        Perfom some pre-generation.
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

            """line['about_resource'] = basename(file_location)
            if not file_location.startswith('/'):
                line['about_resource_path'] = '/' + file_location
            else:
                line['about_resource_path'] = file_location
                # Strip the first '/' for the later 'join'
                file_location = file_location.partition('/')[2]
            if not file_location.endswith('.ABOUT'):
                if file_location.endswith('/'):
                    file_location = dirname(file_location)
                    file_location = join(file_location, basename(file_location))
                    # Since this is referencing everything in the current directory,
                    # we will use a '.' period to reference it.
                    line['about_resource'] = '.'
                file_location += '.ABOUT'"""
            if all_in_one:
                # This is to get the filename instead of the file path
                file_location = file_location.rpartition('/')[2]
            about_file_location = join(gen_location, file_location)
            about_file_dir = dirname(about_file_location)
            if not os.path.exists(about_file_dir):
                makedirs(about_file_dir)
            about_file_exist = _exists(about_file_location)
            if about_file_exist:
                if action_num == ACTION_DO_NOTHING_IF_ABOUT_FILE_EXIST:
                    msg = 'ABOUT file already existed. Generation is skipped.'
                    self.warnings.append(Warn('about_file',
                                              about_file_location, msg))
                    continue
                # Overwrites the current ABOUT field value if it existed
                elif action_num == ACTION_OVERWRITES_THE_CURRENT_ABOUT_FIELD_VALUE_IF_EXIST:
                    about_object = about.AboutFile(about_file_location)
                    for field_name, value in about_object.parsed.items():
                        field_name = field_name.lower()
                        if not field_name in line.keys() or not line[field_name]:
                            line[field_name] = value
                # Keep the current field value and only add the "new" field
                # and field value
                elif action_num == ACTION_KEEP_CURRENT_FIELDS_UNCHANGED_AND_ONLY_ADD_NEW_FIELDS:
                    about_object = about.AboutFile(about_file_location)
                    for field_name, value in about_object.parsed.items():
                        field_name = field_name.lower()
                        line[field_name] = value
                # We do not need to do anything if action_num is 3 as the
                # original ABOUT file will be replaced in the write_output()
                elif action_num == ACTION_REPLACE_THE_ABOUT_FILE_WITH_THE_CURRENT_GENERATED_FILE:
                    pass

            # The following is to ensure about_resource and
            # about_resource_path fields are present. If they exist already,
            # the code will not changes these.
            self.update_about_resource(line, about_file_exist)
            self.update_about_resource_path(line, about_file_exist)

            component_list.append(about_file_location)
            component_list.append(line)
            output_list.append(component_list)
        return output_list

    def update_about_resource(self, line, about_file_exist):
        # Check is 'about_resource' exist
        try:
            if line['about_resource']:
                if not about_file_exist:
                    about_resource = line['about_file']
                    if about_resource.endswith('/'):
                        line['about_resource'] = '.'
        except:
            # Add the 'about_resource' field
            about_resource = line['about_file']
            if about_resource.endswith('/'):
                line['about_resource'] = '.'
            else:
                line['about_resource'] = basename(about_resource)

    def update_about_resource_path(self, line, about_file_exist):
        # Check is 'about_resource_path' exist
        try:
            if line['about_resoure_path']:
                if not about_file_exist:
                    file_path = line['about_file']
                    if not file_path.startswith('/'):
                        line['about_resource_path'] = '/' + file_path
                    else:
                        line['about_resource_path'] = file_path
        except:
            file_path = line['about_file']
            if not file_path.startswith('/'):
                line['about_resource_path'] = '/' + file_path
            else:
                line['about_resource_path'] = file_path

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
                if not item in about.MANDATORY_FIELDS:
                    # The purpose of the replace('\n', '\n ') is used to
                    # format the continuation strings
                    value = about_dict_list[item].replace('\n', '\n ')
                    if (value or item in about.MANDATORY_FIELDS) and not item\
                        in about.ERROR_WARN_FIELDS and not item == 'about_resource':
                        context += item + ': ' + value + '\n'

            component.append(about_file_location)
            component.append(context)
            components_list.append(component)
        return components_list

    @staticmethod
    def write_output(output):
        for about_file_location, context in output:
            if _exists(about_file_location):
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


def _exists(location):
    # FIXME: duplicated code with about.py
    return location and  exists(abspath(location))


USAGE_SYNTAX = """\
    Input must be a CSV file
    Output must be a directory location where the ABOUT files should be generated
"""

VERBOSITY_HELP = """\
Print more or fewer verbose messages while processing ABOUT files
0 - Do not print any warning or error messages, just a total count (default)
1 - Print error messages
2 - Print error and warning messages
"""

ACTION_HELP = """\
Handle different behaviors if ABOUT files already existed
0 - Do nothing if ABOUT file existed (default)
1 - Overwrites the current ABOUT field value if existed
2 - Keep the current field value and only add the "new" field and field value
3 - Replace the ABOUT file with the current generation
"""

ALL_IN_ONE_HELP = """\
Generate all the ABOUT files in the [output_path] without
any project structure
"""

COPY_FILES_HELP = """\
Copy the '*_file' from the project to the generated location
Project path - Project path
"""

LICENSE_TEXT_LOCATION_HELP = """\
Copy the 'license_text_file' from the directory to the generated location
License path - License text files path
"""

MAPPING_HELP = """\
Configure the mapping key from the MAPPING.CONFIG
"""

EXTRACT_LICENSE_HELP = """\
Extract License text and create <license_key>.LICENSE side-by-side
    with the .ABOUT from DJE License Library.
api_url - URL to the DJE License Library
api_username - The regular DJE username
api_key - Hash attached to your username which is used to authenticate
            yourself in the API. Contact us to get the hash key.

Example syntax:
genabout.py --extract_license --api_url='api_url' --api_username='api_username' --api_key='api_key'
"""

INVALID_OPTION_ARG = """\
    Invalid option argument.
"""

def main(parser, options, args):
    verbosity = options.verbosity
    action = options.action
    all_in_one = options.all_in_one
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
    mapping_keys = []

    if options.version:
        print('ABOUT tool {0}\n{1}'.format(__version__, __copyright__))
        sys.exit(0)

    if verbosity == 1:
        handler.setLevel(logging.ERROR)
    elif verbosity >= 2:
        handler.setLevel(logging.WARNING)

    if action:
        if not action in [0, 1, 2, 3]:
            print('--action' + INVALID_OPTION_ARG)
            sys.exit(errno.EINVAL)
        else:
            action_num = action

    if copy_files_path:
        if not _exists(copy_files_path):
            print("The project path does not exist.")
            sys.exit(errno.EINVAL)

    if license_text_path:
        if not _exists(license_text_path):
            print("The license text path does not exist.")
            sys.exit(errno.EINVAL)

    if mapping_config:
        if not _exists('MAPPING.CONFIG'):
            print("The file 'MAPPING.CONFIG' does not exist.")
            sys.exit(errno.EINVAL)

    if extract_license:
        api_url = extract_license[0].partition('--api_url=')[2]
        api_username = extract_license[1].partition('--api_username=')[2]
        api_key = extract_license[2].partition('--api_key=')[2]
        gen_license = True

    if not len(args) == 2:
        print('Input and Output paths are required.\n')
        parser.print_help()
        sys.exit(errno.EEXIST)

    input_path, output_path = args
    output_path = abspath(output_path)

    if not output_path.endswith('/'):
        output_path += '/'

    if not exists(input_path):
        print('Input path does not exist.\n')
        parser.print_help()
        sys.exit(errno.EEXIST)

    if not exists(output_path):
        print('Output path does not exist.\n')
        parser.print_help()
        sys.exit(errno.EEXIST)

    if not isdir(output_path):
        print('Output must be a directory, not a file.\n')
        parser.print_help()
        sys.exit(errno.EISDIR)

    if not input_path.endswith('.csv'):
        print("Input file name must be a CSV file ends with '.csv'\n")
        parser.print_help()
        sys.exit(errno.EINVAL)

    gen = GenAbout()

    dup_keys = gen.get_duplicated_keys(input_path)
    if dup_keys:
        print('The input file contains duplicated keys. Duplicated keys are not allowed.')
        print(dup_keys)
        print('\nPlease fix the input file and re-run the tool.')
        sys.exit(errno.EINVAL)

    # Clear the log file
    with open(output_path + LOG_FILENAME, 'w'):
        pass

    file_handler = logging.FileHandler(output_path + LOG_FILENAME)
    file_logger.addHandler(file_handler)

    input_list = gen.get_input_list(input_path)
    input_list = gen.get_non_empty_rows_list(input_list)

    if mapping_config:
        mapping_list = gen.get_mapping_list()
        input_list = gen.convert_input_list(input_list, mapping_list)
        mapping_keys = mapping_list.keys()

    gen.validate(input_list)

    ignored_fields_list = gen.get_non_supported_fields(input_list, mapping_keys)
    if ignored_fields_list:
        input_list = gen.get_only_supported_fields(input_list, ignored_fields_list)

    if copy_files_path:
        if not isdir(copy_files_path):
            print("The '--copy_files' <project_path> must be a directory.")
            print("'--copy_files' is skipped.")
        else:
            # if not copy_files_path.endswith('/'):
            #   copy_files_path += '/'
            project_parent_dir = dirname(copy_files_path)
            licenses_in_project = True
            license_list = gen.verify_files_existence(input_list, project_parent_dir, licenses_in_project)
            if not license_list:
                print("None of the file is found. '--copy_files' is ignored.")
            else:
                gen.copy_files(output_path, license_list)

    if license_text_path:
        if not isdir(license_text_path):
            print("The '--license_text_location' <license_path> must be a directory.")
            print("'--license_text_location' is skipped.")
        else:
            # if not license_text_path.endswith('/'):
            #    license_text_path += '/'
            license_dir = dirname(license_text_path)
            licenses_in_project = False
            license_list = gen.verify_files_existence(input_list, license_dir, licenses_in_project)
            if not license_list:
                print("None of the file is found. '--copy_files' is ignored.")
            else:
                gen.copy_files(output_path, license_list)

    if extract_license:
        if not api_url or not api_username or not api_key:
            print("Missing argument for --extract_license")
            sys.exit(errno.EINVAL)
        for line in input_list:
            try:
                if line['dje_license']:
                    break
            except Exception as e:
                print(repr(e))
                print("The input does not have the 'dje_license' key which is required.")
                sys.exit(errno.EINVAL)

    if gen_license:
        dje_license_dict = gen.pre_process_and_dje_license_dict(input_list,
                                                                    api_url,
                                                                    api_username,
                                                                    api_key)

    dje_license_list = gen.get_dje_license_list(output_path, input_list, gen_license, dje_license_dict)
    components_list = gen.pre_generation(output_path, input_list, action_num, all_in_one)
    formatted_output = gen.format_output(components_list)
    gen.write_output(formatted_output)

    if dje_license_list:
        license_list_context = gen.process_dje_licenses(dje_license_list,
                                                        dje_license_dict,
                                                        output_path)
        gen.write_licenses(license_list_context)

    gen.warnings_errors_summary()
    print('Warnings: %s' % len(gen.warnings))
    print('Errors: %s' % len(gen.errors))

def get_parser():
    class MyFormatter(optparse.IndentedHelpFormatter):
        def _format_text(self, text):
            """
            Overridden to allow description to be printed without
            modification
            """
            return text

        def format_option(self, option):
            """
            Overridden to allow options help text to be printed without
            modification
            """
            result = []
            opts = self.option_strings[option]
            opt_width = self.help_position - self.current_indent - 2
            if len(opts) > opt_width:
                opts = "%*s%s\n" % (self.current_indent, "", opts)
                indent_first = self.help_position
            else:  # start help on same line as opts
                opts = "%*s%-*s  " % (self.current_indent, "", opt_width, opts)
                indent_first = 0
            result.append(opts)
            if option.help:
                help_text = self.expand_default(option)
                help_lines = help_text.split('\n')
                # help_lines = textwrap.wrap(help_text, self.help_width)
                result.append("%*s%s\n" % (indent_first, "", help_lines[0]))
                result.extend(["%*s%s\n" % (self.help_position, "", line)
                               for line in help_lines[1:]])
            elif opts[-1] != "\n":
                result.append("\n")
            return "".join(result)

    parser = optparse.OptionParser(
        usage='%prog [options] input_path output_path',
        description=USAGE_SYNTAX,
        add_help_option=False,
        formatter=MyFormatter(),
    )
    parser.add_option('-h', '--help', action='help', help='Display help')
    parser.add_option(
        '--version', action='store_true',
        help='Display current version, license notice, and copyright notice')
    parser.add_option('--verbosity', type=int, help=VERBOSITY_HELP)
    parser.add_option('--action', type=int, help=ACTION_HELP)
    parser.add_option('--all_in_one', action='store_true', help=ALL_IN_ONE_HELP)
    parser.add_option('--copy_files', type='string', help=COPY_FILES_HELP)
    parser.add_option('--license_text_location', type='string', help=LICENSE_TEXT_LOCATION_HELP)
    parser.add_option('--mapping', action='store_true', help=MAPPING_HELP)
    parser.add_option(
        '--extract_license', type='string', nargs=3, help=EXTRACT_LICENSE_HELP)
    return parser


if __name__ == "__main__":
    parser = get_parser()
    options, args = parser.parse_args()
    main(parser, options, args)
