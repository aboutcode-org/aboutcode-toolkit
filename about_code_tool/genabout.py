#!/usr/bin/env python
# -*- coding: utf8 -*-

# =============================================================================
#  Copyright (c) 2013 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#      http://www.apache.org/licenses/LICENSE-2.0
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# =============================================================================

"""
This is a tool to generate ABOUT files based on the input file.
The input file should be a csv format which contains information about the
file location, origin and license of the software components etc.
"""

from __future__ import print_function
from collections import namedtuple
from os import makedirs
from os.path import exists, dirname, join, abspath, isdir
import about
import csv
import copy
import errno
import json
import getopt
import os
import shutil
import sys
import urllib
import urllib2


__version__ = '0.9.0'

MANDATORY_FIELDS = ['about_resource', 'name', 'version']
SKIPPED_FIELDS = ['warnings', 'errors']

SUPPORTED_FIELDS = about.OPTIONAL_FIELDS + about.MANDATORY_FIELDS \
                    + ('about_file', 'dje_license_key',)

Warn = namedtuple('Warn', 'field_name field_value message',)
Error = namedtuple('Error', 'field_name field_value message',)

self_path = abspath(dirname(__file__))


def request_license_data(url, username, api_key, license_key):
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

    try:
        request = urllib2.Request(full_url)
        response = urllib2.urlopen(request)
        response_content = response.read()
        data = json.loads(response_content)
    except urllib2.HTTPError as http_e:
        # the code 401 represents authorization problem
        if http_e.code == 401:
            return 'authorization denied'
        else:
            return {}
    except urllib2.URLError as url_e:
        if about.check_network_connection():
            return 'URL not reachable'
        return 'No network'
    except ValueError as value_e:
        return {}
    else:
        return data


class GenAbout(object):
    def __init__(self):
        self.warnings = []
        self.errors = []

    def read_input(self, input_file, mapping):
        about_resource, about_file, name, version = self.config_mapping(mapping)
        csvfile = csv.DictReader(open(input_file, 'rU'))
        components_list = []
        check_duplication = []
        ignored_fields_list = self.check_non_supported_fields(input_file)
        if ignored_fields_list:
            self.warnings.append(Warn(ignored_fields_list, '' ,\
                                      'The field(s) "%s"' % ignored_fields_list\
                                      + ' is/are not supported and will be ignored'))
        for line in csvfile:
            file_list = {}
            try:
                line['about_file'] = line[about_file]
                line['about_resource'] = line[about_resource]
                line['name'] = line[name]
                line['version'] = line[version]
                component = line['about_file'] + line['about_resource']
                if component in check_duplication:
                    print("The input has duplicated 'about_file' and 'about_resource'.")
                    print("Duplication is not supported. Please correct the input and rerun the tool.")
                    print("No ABOUT file is created.")
                    sys.exit(errno.EINVAL)
                check_duplication.append(component)
            except Exception as e:
                print(repr(e))
                print("The required keys not found.")
                print("Please use the '--mapping' option to map the input keys and verify the mapping information are correct.")
                print("OR, correct the header keys from the input CSV.")
                sys.exit(errno.EINVAL)
            if not about_file == 'about_file':
                del line[about_file]
            if not about_resource == 'about_resource':
                del line[about_resource]
            if not name == 'name':
                del line[name]
            if not version == 'version':
                del line[version]
            if not line['about_file']:
                # This code is to handle blank line
                for key in line.keys():
                    if line[key]:
                        missing_about_file = "'about_file' field value is missing. Generation is skipped."
                        self.errors.append(Error('about_file', None, missing_about_file))
                        break
                continue
            # We don't need to use the try/except here as the existence of 
            # line['about_resource'] has already been checked above. 
            if not line['about_resource']:
                # This code is to handle blank line
                for key in line.keys():
                    if line[key]:
                        missing_about_resource = "'about_resource' is missing. Generation is skipped."
                        self.errors.append(Error('about_resource', line['about_file'], missing_about_resource))
                        break
                continue
            for key in line.keys():
                if key in SUPPORTED_FIELDS:
                    file_list[key] = line[key]
            components_list.append(file_list)
        return components_list

    @staticmethod
    def check_non_supported_fields(input_file):
        csvfile = csv.DictReader(open(input_file, 'rU'))
        non_supported_fields_list = []
        for line in csvfile:
            for key in line.keys():
                if not key in SUPPORTED_FIELDS:
                    non_supported_fields_list.append(key)
            break
        return non_supported_fields_list

    @staticmethod
    def config_mapping(mapping):
        """
        Read the MAPPING.CONFIG and do the key mapping.
        """
        about_resource = 'about_resource'
        about_file = 'about_file'
        name = 'name'
        version = 'version'
        if mapping:
            try:
                with open(join(self_path, 'MAPPING.CONFIG'), "rU") as file_in:
                    for line in file_in.readlines():
                        if not line.startswith('#'):
                            if line.partition(':')[0] == 'about_resource':
                                new_value = line.partition(':')[2].strip()
                                if new_value:
                                    about_resource = new_value
                            elif line.partition(':')[0] == 'about_file':
                                new_value = line.partition(':')[2].strip()
                                if new_value:
                                    about_file = new_value
                            elif line.partition(':')[0] == 'name':
                                new_value = line.partition(':')[2].strip()
                                if new_value:
                                    name = new_value
                            elif line.partition(':')[0] == 'version':
                                new_value = line.partition(':')[2].strip()
                                if new_value:
                                    version = new_value
                    return about_resource, about_file, name, version
            except Exception as e:
                print(repr(e))
                print("The 'MAPPING.CONFIG' cannot be opened.")
                sys.exit(errno.EACCES)
        else:
            return about_resource, about_file, name, version

    def verify_license_files(self, input_list, project_path):
        """
        Verify the existence of the 'license text file'
        """
        license_files_list = []
        for component in input_list:
            for line in component:
                try:
                    if line['license_text_file']:
                        is_dir = False
                        if line['about_file'].endswith('/'):
                            is_dir = True
                        license_file = line['license_text_file']
                        file_location = line['about_file']
                        if file_location.startswith('/'):
                            file_location = file_location.partition('/')[2]
                        if file_location.endswith('/'):
                            file_location = file_location.rpartition('/')[0]
                        about_parent_dir = os.path.dirname(file_location)
                        project_parent_dir = os.path.dirname(project_path)
                        license_file_path = join(project_parent_dir, about_parent_dir, license_file)
                        if _exists(license_file_path):
                            license_files_list.append(license_file_path)
                        else:
                            self.warnings.append(Warn('license_text_file', license_file_path, "License doesn't exist."))
                except Exception as e:
                    print(repr(e))
                    print("The input does not have the 'license_text_file' key which is required.")
                    sys.exit(errno.EINVAL)
        return license_files_list, project_parent_dir

    @staticmethod
    def copy_license_files(gen_location, license_list, project_dir):
        """
        Copy the 'license_text_file' into the gen_location
        """
        for license_path in license_list:
            if gen_location.endswith('/'):
                gen_location = gen_location.rpartition('/')[0]
            output_license_path = gen_location + license_path.partition(project_dir)[2]
            license_parent_dir = os.path.dirname(output_license_path)
            if not _exists(license_parent_dir):
                makedirs(license_parent_dir)
            shutil.copy2(license_path, output_license_path)

    def extract_dje_license(self, project_path, license_list, url, username, key):
        """
        Extract license text from DJE
        """
        license_context_list = []
        for items in license_list:
            gen_path = items[0]
            license_key = items[1]
            if gen_path.startswith('/'):
                gen_path = gen_path.partition('/')[2]
            gen_license_path = join(project_path, gen_path, license_key) + '.LICENSE'
            if not _exists(gen_license_path):
                context = self.get_license_text_from_api(url, username, key, license_key)
                if context == 'authorization denied':
                    print("Authorization denied. Invalid '--api_username' or '--api_key'.")
                    print("LICENSE generation is skipped.")
                    sys.exit(errno.EINVAL)
                if context == 'URL not reachable':
                    print("URL not reachable. Invalid '--api_url'.")
                    print("LICENSE generation is skipped.")
                    sys.exit(errno.EINVAL)
                if context == 'No network':
                    print("Network problem. Please check the Internet connection.")
                    print("LICENSE generation is skipped.")
                    sys.exit(errno.EINVAL)
                if not context:
                    self.errors.append(Error('dje_license_key', license_key,
                                             "Invalid 'dje_license_key'"))
                else:
                    gen_path_context = []
                    gen_path_context.append(gen_license_path)
                    gen_path_context.append(context.encode('utf8'))
                    license_context_list.append(gen_path_context)
        return license_context_list

    def write_licenses(self, license_context_list):
        for license in license_context_list:
            gen_license_path = license[0]
            license_context = license[1]
            try:
                with open(gen_license_path, 'wb') as output:
                    output.write(license_context)
            except Exception as e:
                self.errors.append(Error('Unknown', gen_license_path,
                                     "Something is wrong."))

    @staticmethod
    def get_license_text_from_api(url, username, api_key, license_key):
        """
        Returns the license_text of a given license_key using an API request.
        Returns an empty string if the text is not available.
        """
        data = request_license_data(url, username, api_key, license_key)
        if data == 'authorization denied' or data == 'URL not reachable' or data == 'No network':
            return data
        license_text = data.get('full_text', '')
        return license_text

    def pre_generation(self, gen_location, input_list, action_num, all_in_one, gen_license):
        """
        check the existence of the output location and handle differently
        according to the action_num.
        """
        output_list = []
        license_output_list = []
        # The input_list needs to be copied and be used below.
        # Otherwise, the value in the input_list may be changed based on the 
        # action number below
        copied_list = copy.deepcopy(input_list)
        #for component in copied_list:
        for line in copied_list:
            # ToDo: The following code is used to validate the existence
            # of the 'license_text_file' if there is any.
            # All the validation calls should be re-factored along with the about.py
            try:
                # We do not need to check for the gen_license option
                # as the value of the 'license_text_file' will not be changed
                # regardless the gen_license is set or not.
                if line['license_text_file']:
                    file_location = line['about_file']
                    if file_location.endswith('/'):
                        file_location = file_location.rpartition('/')[0]
                    about_parent_dir = os.path.dirname(file_location)
                    license_file = gen_location.rpartition('/')[0] + join(about_parent_dir, line['license_text_file'])
                    if not _exists(license_file):
                        self.errors.append(Error('license_text_file', license_file, 
                                                 "The 'license_text_file' doesn't exist."))
                else:
                    if gen_license:
                        try:
                            if line['dje_license_key']:
                                license_output_list.append(self.gen_license_list(line))
                            else:
                                self.warnings.append(Warn('dje_license_key', '',
                                                          "Missing 'dje_license_key' for " + line['about_file']))
                        except Exception as e:
                            print(repr(e))
                            print("The input does not have the 'dje_license_key' key which is required.")
                            sys.exit(errno.EINVAL)
            # This except condition will force the tool to create the 
            # 'license_text_file' key column
            except Exception as e:
                if gen_license:
                    try:
                        if line['dje_license_key']:
                            license_output_list.append(self.gen_license_list(line))
                        else:
                            self.warnings.append(Warn('dje_license_key', '',
                                                      "Missing 'dje_license_key' for " + line['about_file']))
                    except Exception as e:
                        print(repr(e))
                        print("The input does not have the 'dje_license_key' key which is required.")
                        sys.exit(errno.EINVAL)

            component_list = []
            file_location = line['about_file']
            if file_location.startswith('/'):
                file_location = file_location.partition('/')[2]
            if not file_location.endswith('.ABOUT'):
                if file_location.endswith('/'):
                    file_location = file_location.rpartition('/')[0]
                file_location += '.ABOUT'
            if all_in_one:
                # This is to get the filename instead of the file path
                file_location = file_location.rpartition('/')[2]
            about_file_location = join(gen_location, file_location)
            dir = dirname(about_file_location)
            if not _exists(dir):
                makedirs(dir)
            if _exists(about_file_location):
                if action_num == '0':
                    about_exist = "ABOUT file already existed. Generation is skipped."
                    self.warnings.append(Warn('about_file', about_file_location, about_exist))
                    continue
                # Overwrites the current ABOUT field value if existed
                elif action_num == '1':
                    about_object = about.AboutFile(about_file_location)
                    for field_name, value in about_object.parsed.items():
                        field_name = field_name.lower()
                        if not field_name in line.keys() or not line[field_name]:
                            line[field_name] = value
                # Keep the current field value and only add the "new" field and field value
                elif action_num == '2':
                    about_object = about.AboutFile(about_file_location)
                    for field_name, value in about_object.parsed.items():
                        field_name = field_name.lower()
                        line[field_name] = value
                # We don't need to do anything for the action_num = 3 as
                # the original ABOUT file will be replaced in the write_output()
            component_list.append(about_file_location)
            component_list.append(line)
            output_list.append(component_list)
        return output_list, license_output_list

    @staticmethod
    def gen_license_list(line):
        dje_license_key_list = []
        dje_key = line['dje_license_key']
        file_location = line['about_file']
        if file_location.endswith('/'):
            file_location = file_location.rpartition('/')[0]
        about_parent_dir = os.path.dirname(file_location)
        dje_license_key_list.append(about_parent_dir)
        dje_license_key_list.append(dje_key)
        line['license_text_file'] = dje_key +'.LICENSE'
        return dje_license_key_list


    @staticmethod
    def format_output(input_list):
        """
        Process the input and convert to the specific strings format.
        """
        components_list = []
        for entry in input_list:
            about_file_location = entry[0]
            about_dict_list = entry[1]

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
                    if (value or item in MANDATORY_FIELDS) and not item in SKIPPED_FIELDS:
                        context += item + ': ' + value + '\n'

            component.append(about_file_location)
            component.append(context)
            components_list.append(component)
        return components_list

    @staticmethod
    def write_output(output):
        for line in output:
            about_file_location = line[0]
            context = line[1]
            if _exists(about_file_location):
                os.remove(about_file_location)
            with open(about_file_location, 'wb') as output_file:
                output_file.write(context)

    def warnings_errors_summary(self, gen_location, show_error_num):
        display_error = False
        display_warning = False
        if show_error_num == '1':
            display_error = True
        if show_error_num == '2':
            display_error = True
            display_warning = True
        if self.errors or self.warnings:
            error_location = gen_location + 'error.txt' if gen_location.endswith('/') else gen_location + '/error.txt'
            errors_num = len(self.errors)
            warnings_num = len(self.warnings)
            if _exists(error_location):
                print("error.txt existed and will be replaced.")
            with open(error_location, 'wb') as error_file:
                if self.warnings:
                    for warning_msg in self.warnings:
                        if display_warning:
                            print(str(warning_msg))
                        error_file.write(str(warning_msg) + '\n')
                if self.errors:
                    for error_msg in self.errors:
                        if display_error:
                            print(str(error_msg))
                        error_file.write(str(error_msg) + '\n')
                error_file.write('\n' + 'Warnings: %s' % warnings_num)
                error_file.write('\n' + 'Errors: %s' % errors_num)
            print('Warnings: %s' % warnings_num)
            print('Errors: %s' % errors_num)
            print("See %s for the error/warning log." % error_location)


def _exists(file_path):
    if file_path:
        return exists(abspath(file_path))


def syntax():
    print("""
Syntax:
    genabout.py [Options] [Input File] [Generated Location]
    Input File         - The input CSV file
    Generated Location - the output location where the ABOUT files should be generated
""")


def version():
    print("""
ABOUT CODE: Version: %s
Copyright (c) 2013 nexB Inc. All rights reserved.
http://dejacode.org
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations
under the License.""" % __version__)


def option_usage():
    print("""
Options:
    -v,--version         Display current version, license notice, and copyright notice
    -h,--help            Display help
    --action  <arg>      Handle different behaviors if ABOUT files already existed
        <arg>
            0 - Do nothing if ABOUT file existed (default)
            1 - Overwrites the current ABOUT field value if existed
            2 - Keep the current field value and only add the "new" field and field value
            3 - Replace the ABOUT file with the current generation
    --verbosity  <arg>   Print more or less verbose messages while processing ABOUT files
        <arg>
            0 - Do not print any warning or error messages, just a total count (default)
            1 - Print error messages
            2 - Print error and warning messages
    --all-in-one <bool>   Behavior of generating ABOUT files
        <bool>
            False - Generate ABOUT files in a project-like structure based on the about_file location (default)
            True  - Generate all the ABOUT files in the [Generated Location] regardless of the about_file location
    --copy_license <path>    Copy the 'license_text_file'
                                This option is for users who want to generate ABOUT files separate
                                from the original codebase and want to copy the licenses into the
                                output location.
        <path>
            Project path
    --mapping    Activate the MAPPING.CONFIG
    --extract_license <3 args required>    Extract License text and create <license_key>.LICENSE 
                                            side-by-side with the .ABOUT from DJE License Library
        <--api_url='URL'> - URL to the DJE License Library
        <--api_username='user_api'> - The regular DJE username
        <--api_key='user_api_key'> - Hash attached to your username which is used 
                                     to authenticate yourself in the API. Contact
                                     us to get the hash key. 
        Example syntax:
            genabout.py --extract_license --api_url='https://enterprise.dejacode.com/api/v1/license_text/' --api_username='<user_api>' --api_key='<user_api_key>'
""")


def main(args, opts):
    opt_arg_num = '0'
    verb_arg_num = '0'
    all_in_one = False
    project_path = ''
    mapping_config = False
    gen_license = False
    api_url = ''
    api_username = ''
    api_key = ''

    for opt, opt_arg in opts:
        invalid_opt = True
        if opt in ('-h', '--help'):
            syntax()
            option_usage()
            sys.exit(0)

        if opt in ('-v', '--version'):
            version()
            sys.exit(0)

        if opt in ('--action'):
            invalid_opt = False
            valid_opt_args = ['0', '1', '2', '3']
            if not opt_arg or not opt_arg in valid_opt_args:
                print("Invalid option argument.")
                option_usage()
                sys.exit(errno.EINVAL)
            else:
                opt_arg_num = opt_arg

        if opt in ('--verbosity'):
            invalid_opt = False
            valid_opt_args = ['0', '1', '2']
            if not opt_arg or not opt_arg in valid_opt_args:
                print("Invalid option argument.")
                option_usage()
                sys.exit(errno.EINVAL)
            else:
                verb_arg_num = opt_arg

        if opt in ('--all-in-one'):
            invalid_opt = False
            valid_opt_args = ['true', 'false']
            if not opt_arg or not opt_arg.lower() in valid_opt_args:
                print("Invalid option argument.")
                option_usage()
                sys.exit(errno.EINVAL)
            else:
                if opt_arg.lower() == 'true':
                    all_in_one = True

        if opt in ('--copy_license'):
            invalid_opt = False
            project_path = opt_arg
            if not _exists(project_path):
                print("The project path doesn't exist.")
                option_usage()
                sys.exit(errno.EINVAL)

        if opt in ('--mapping'):
            invalid_opt = False
            if not _exists('MAPPING.CONFIG'):
                print("The file 'MAPPING.CONFIG' doesn't exist.")
                option_usage()
                sys.exit(errno.EINVAL)
            else:
                mapping_config = True

        if opt in ('--extract_license'):
            invalid_opt = False
            gen_license = True


        if opt in ('--api_url'):
            invalid_opt = False
            if not opt_arg or not 'http' in opt_arg.lower():
                print("Invalid option argument.")
                option_usage()
                sys.exit(errno.EINVAL)
            else:
                api_url = opt_arg

        if opt in ('--api_username'):
            invalid_opt = False
            if not opt_arg or '/' in opt_arg or '\\' in opt_arg:
                print("Invalid option argument.")
                option_usage()
                sys.exit(errno.EINVAL)
            else:
                api_username = opt_arg

        if opt in ('--api_key'):
            invalid_opt = False
            if not opt_arg or '/' in opt_arg or '\\' in opt_arg:
                print("Invalid option argument.")
                option_usage()
                sys.exit(errno.EINVAL)
            else:
                api_key = opt_arg

        if invalid_opt:
            assert False, 'Unsupported option.'
        
    if not len(args) == 2:
        print('Input file and generated location parameters are mandatory.')
        syntax()
        option_usage()
        sys.exit(errno.EINVAL)

    input_file = args[0]
    gen_location = args[1]
    
    if not gen_location.endswith('/'):
        gen_location += '/'

    if isdir(input_file):
        print(input_file, ": Input is not a CSV file.")
        sys.exit(errno.EIO)
    if not _exists(input_file):
        print(input_file, ': Input file does not exist.')
        sys.exit(errno.EIO)
    if not _exists(gen_location):
        print(gen_location, ': Generated location does not exist.')
        sys.exit(errno.EIO)

    gen = GenAbout()

    input_list = gen.read_input(input_file, mapping_config)
    if project_path:
        license_list, project_dir = gen.verify_license_files(input_list, project_path)
        gen.copy_license_files(gen_location, license_list, project_dir)

    if gen_license:
        if not api_url or not api_username or not api_key:
            print("Missing argument for --extract_license")
            option_usage()
            sys.exit(errno.EINVAL)

    components_list, dje_license_list = gen.pre_generation(gen_location, input_list, opt_arg_num, all_in_one, gen_license)
    formatted_output = gen.format_output(components_list)
    gen.write_output(formatted_output)

    if dje_license_list:
        license_list_context = gen.extract_dje_license(gen_location, dje_license_list, api_url, api_username, api_key)
        gen.write_licenses(license_list_context)

    gen.warnings_errors_summary(gen_location, verb_arg_num)

if __name__ == "__main__":
    longopts = ['help', 'version', 'action=', 'verbosity=', 'all-in-one=', 'copy_license=', 'mapping', 'extract_license', 'api_url='
                , 'api_username=', 'api_key=']
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hv', longopts)
    except Exception as e:
        print(repr(e))
        syntax()
        option_usage()
        sys.exit(errno.EINVAL)

    main(args, opts)
