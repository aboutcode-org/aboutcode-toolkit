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
import sys


# TODO: version number
__version__ = '0.8.1'


MANDATORY_FIELDS = ['about_resource', 'name', 'version']
SKIPPED_FIELDS = ['warnings', 'errors']

Warn = namedtuple('Warn', 'field_name message',)
Error = namedtuple('Error', 'field_name message',)


errors = []
warnings = []


def _exists(file_path):
    if file_path:
        return exists(abspath(file_path))


def read_input(input_file):
    csvfile = csv.DictReader(open(input_file, 'rb'))
    components_list = []
    for line in csvfile:
        file_list = []
        if not line['about_file']:
            missing_about_file = "'about_file' field value is missing. Generation is skipped."
            errors.append(Error(None, missing_about_file))
            continue
        if not line['about_resource']:
            missing_about_resource = "'about_resource' is missing. Generation is skipped."
            errors.append(Error(line['about_file'], missing_about_resource))
            continue
        file_list.append(line)
        components_list.append(file_list)
    return components_list


def pre_generation(gen_location, input_list, action_num):
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
            about_file_location = join(gen_location, file_location)
            dir = dirname(about_file_location)
            if not _exists(dir):
                makedirs(dir)
            if _exists(about_file_location):
                if action_num == '0':
                    about_exist = "ABOUT file already existed. Generation is skipped."
                    warnings.append(Warn(about_file_location, about_exist))
                    continue
                # Overwrites the current ABOUT field value if existed
                elif action_num == '1':
                    about_object = about.AboutFile(about_file_location)
                    for field_name, value in about_object.parsed.items():
                        field_name = field_name.lower()
                        if not field_name in line.keys() or not line[field_name]:
                            line[field_name] = value
                    os.remove(about_file_location)
                # Keep the current field value and only add the "new" field and field value
                elif action_num == '2':
                    about_object = about.AboutFile(about_file_location)
                    for field_name, value in about_object.parsed.items():
                        field_name = field_name.lower()
                        line[field_name] = value
                    os.remove(about_file_location)
                elif action_num == '3':
                    os.remove(about_file_location)
            component_list.append(about_file_location)
            component_list.append(line)
            output_list.append(component_list)
    return output_list


def format_output(input_list):
    """
    process the input and covert to the specific strings format
    """
    components_list = []
    for items in input_list:
        component = []
        about_file_location = items[0]
        about_dict_list = items[1]

        context = ''
        if about_dict_list['name']:
            name = about_dict_list['name']
        else:
            name = ''
        if about_dict_list['version']:
            version = about_dict_list['version']
        else:
            version = ''
        context = 'about_resource: ' + about_dict_list['about_resource'] + '\n' \
                    + 'name: ' + name + '\n' \
                    + 'version: ' + version + '\n\n'
        for item in sorted(about_dict_list.iterkeys()):
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


def write_output(output):
    for line in output:
        about_file_location = line[0]
        context = line[1]
        with open(about_file_location, 'wb') as output_file:
            output_file.write(context)


def warnings_errors_summary(gen_location, show_error_num):
    display_error = False
    display_warning = False
    if show_error_num == '1':
        display_error = True
    if show_error_num == '2':
        display_error = True
        display_warning = True
    if errors or warnings:
        error_location = gen_location + 'error.txt' if gen_location.endswith('/') else gen_location + '/error.txt'
        errors_num = len(errors)
        warnings_num = len(warnings)
        if _exists(error_location):
            print("error.txt existed and will be replaced.")
        with open(error_location, 'wb') as error_file:
            if warnings:
                for warning_msg in warnings:
                    if display_warning:
                        print(str(warning_msg))
                    error_file.write(str(warning_msg) + '\n')
            if errors:
                for error_msg in errors:
                    if display_error:
                        print(str(error_msg))
                    error_file.write(str(error_msg) + '\n')
            error_file.write('\n' + 'Warnings: %s' % warnings_num)
            error_file.write('\n' + 'Errors: %s' % errors_num)
        print('Warnings: %s' % warnings_num)
        print('Errors: %s' % errors_num)
        print("See %s for the error/warning log." % error_location)


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
""")


def main(args, opts):
    opt_arg_num = '0'
    verb_arg_num = '0'
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

    input_list = read_input(input_file)
    components_list = pre_generation(gen_location, input_list, opt_arg_num)
    formatted_output = format_output(components_list)
    write_output(formatted_output)
    warnings_errors_summary(gen_location, verb_arg_num)

if __name__ == "__main__":
    longopts = ['help', 'version', 'action=', 'verbosity=']
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hv', longopts)
    except Exception as e:
        print(repr(e))
        syntax()
        option_usage()
        sys.exit(errno.EINVAL)

    main(args, opts)
