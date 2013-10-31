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
import errno
import getopt
import os
import shutil
import sys
import urllib2

__version__ = '0.9.0'


MANDATORY_FIELDS = ['about_resource', 'name', 'version']
SKIPPED_FIELDS = ['warnings', 'errors']

Warn = namedtuple('Warn', 'field_name field_value message',)
Error = namedtuple('Error', 'field_name field_value message',)

self_path = abspath(dirname(__file__))


class GenAbout(object):
    def __init__(self):
        self.warnings = []
        self.errors = []

    def read_input(self, input_file, mapping):
        about_resource, about_file, name, version = self.config_mapping(mapping)
        csvfile = csv.DictReader(open(input_file, 'rU'))
        components_list = []
        for line in csvfile:
            file_list = []
            try:
                try:
                    line['about_file'] = line[about_file]
                    line['about_resource'] = line[about_resource]
                    line['name'] = line[name]
                    line['version'] = line[version]
                except Exception as e:
                    print(repr(e))
                    print("Please use the '--mapping' option to map the input keys and verify the mapping information are correct.")
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
                    missing_about_file = "'about_file' field value is missing. Generation is skipped."
                    self.errors.append(Error('about_file', None, missing_about_file))
                    continue
            except Exception as e:
                print(repr(e))
                print("The input does not have the 'about_file' key which is required.")
                sys.exit(errno.EINVAL)
            try:
                if not line['about_resource']:
                    missing_about_resource = "'about_resource' is missing. Generation is skipped."
                    self.errors.append(Error('about_resource', line['about_file'], missing_about_resource))
                    continue
            except Exception as e:
                print(repr(e))
                print("The input does not have the 'about_resource' key which is required.")
                sys.exit(errno.EINVAL)
            file_list.append(line)
            components_list.append(file_list)
        return components_list

    @staticmethod
    def config_mapping(mapping):
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
        output_list = []
        for component in input_list:
            for line in component:
                try:
                    if line['license_text_file']:
                        license_files_list = []
                        is_dir = False
                        if line['about_file'].endswith('/'):
                            is_dir = True
                        license_file = line['license_text_file']
                        file_location = line['about_file']
                        if '/' in file_location:
                            file_location = file_location.partition('/')[2]
                        about_parent_dir = os.path.dirname(file_location)
                        project_parent_dir = os.path.dirname(project_path)

                        license_file_path = join(project_parent_dir, about_parent_dir, license_file)
                        if _exists(license_file_path):
                            license_files_list.append(license_file_path)
                            output_list.append(license_files_list)
                        else:
                            self.warnings.append(Warn('license_text_file', license_file_path, "License doesn't exist."))
                except Exception as e:
                    print(repr(e))
                    print("The input does not have the 'license_text_file' key which is required.")
                    sys.exit(errno.EINVAL)
        return output_list

    def copy_license_files(self, gen_location, license_list):
        """
        copy the 'license_text_file' into the gen_location
        """
        for items in license_list:
            license_path = items[0]
            if not gen_location.endswith('/'):
                gen_location += '/'
            output_license_path = gen_location + license_path
            license_parent_dir = os.path.dirname(output_license_path)
            if not _exists(license_parent_dir):
                makedirs(license_parent_dir)
            shutil.copy2(license_path, output_license_path)

    #def extract_license_from_url(self):
    #    # This function needs discussion
    #    test = urllib2.urlopen("https://enterprise.dejacode.com/license_library/Demo/gpl-1.0/#license-text")
    #    with open('testdata/test_file.txt', 'wb') as output_file:
    #        output_file.write(test.read())

    def pre_generation(self, gen_location, input_list, action_num, all_in_one):
        """
        check the existence of the output location and handle differently
        according to the action_num.
        """
        output_list = []
        for component in input_list:
            for line in component:
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
        return output_list

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

    def write_output(self, output):
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
""")


def main(args, opts):
    opt_arg_num = '0'
    verb_arg_num = '0'
    all_in_one = False
    project_path = ''
    mapping_config = False

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

        if invalid_opt:
            assert False, 'Unsupported option.'

    if not len(args) == 2:
        print('Input file and generated location parameters are mandatory.')
        syntax()
        option_usage()
        sys.exit(errno.EINVAL)

    input_file = args[0]
    gen_location = args[1]

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

    #gen.extract_licesen_from_url()

    input_list = gen.read_input(input_file, mapping_config)
    if project_path:
        license_list = gen.verify_license_files(input_list, project_path)
        gen.copy_license_files(gen_location, license_list)

    components_list = gen.pre_generation(gen_location, input_list, opt_arg_num, all_in_one)
    formatted_output = gen.format_output(components_list)
    gen.write_output(formatted_output)
    gen.warnings_errors_summary(gen_location, verb_arg_num)

if __name__ == "__main__":
    longopts = ['help', 'version', 'action=', 'verbosity=', 'all-in-one=', 'copy_license=', 'mapping']
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hv', longopts)
    except Exception as e:
        print(repr(e))
        syntax()
        option_usage()
        sys.exit(errno.EINVAL)

    main(args, opts)
