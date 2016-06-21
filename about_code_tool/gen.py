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

import codecs
from collections import OrderedDict
import ConfigParser as configparser
import errno
import logging
import optparse
import os
from os.path import exists, dirname, abspath, isdir
import posixpath
import sys

import unicodecsv

from about_code_tool import __version__
from about_code_tool import __about_spec_version__

from about_code_tool import Error
from about_code_tool import ERROR

from about_code_tool import util
from about_code_tool import model
from about_code_tool.util import to_posix


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
        msg = 'Duplicated column name(s): %(dup_msg)s' % locals()
        errors.append(Error(ERROR, msg))
    return errors


def load_inventory(location, base_dir):
    """
    Load the inventory CSV file at location. Return a list of errors and a
    list of About objects validated against the base_dir.
    """
    errors = []
    abouts = []
    errors.extend(check_duplicated_columns(location))
    base_dir = util.to_posix(base_dir)
    inventory = util.load_csv(location)
    for i, fields in enumerate(inventory):
        # get then remove the about file path
        afpa = model.About.about_file_path_attr
        if afpa not in fields:
            msg = ('Missing column: %(afpa)r. '
                   'Cannot generate ABOUT file.' % locals())
            errors.append(Error(ERROR, msg))
            continue
        else:
            afp = fields.get(afpa)

        if not afp or not afp.strip():
            msg = ('Empty column: %(afpa)r. '
                   'Cannot generate ABOUT file.' % locals())
            errors.append(Error(ERROR, msg))
            continue
        else:
            afp = util.to_posix(afp)
            loc = posixpath.join(base_dir, afp)
        about = model.About(about_file_path=afp)
        about.location = loc
        ld_errors = about.load_dict(fields, base_dir, with_empty=False)
        errors.extend(ld_errors)
        abouts.append(about)
    return errors, abouts


def load_conf(location):
    """
    Load the about configuration file at location.
    Return a dictionary of dictionary.
    """
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


# FIXME: are mappings really needed and useful? is this too complex?
def apply_mapping(inventory, config):
    """
    Given a config object, applies mapping if present to the inventory.
    Return the updated inventory.
    """
    mappings = config.get('mappings')
    if not mappings:
        return inventory
    else:
        # iterate over the inventory
        # rename fields
        pass


# FIXME: are policies really needed?

policies = ('skip',  # DO_NOTHING_IF_ABOUT_FILE_EXIST
            'overwrite',  # OVERWRITE_ABOUT_FIELDS_OR FILE
            'new',  # KEEP_FIELDS_UNCHANGED_AND_ONLY_ADD_NEW_FIELDS
            )


def generate(location, base_dir, policy=None, conf_location=None,
             with_empty=False, with_absent=False):
    """
    Load ABOUT data from an inventory at csv_location. Write ABOUT files to
    base_dir using policy flags and configuration file at conf_location.
    Policy defines which action to take for merging or overwriting fields and
    files. Return errors and about objects.
    """
    bdir = to_posix(base_dir)
    errors, abouts = load_inventory(location, bdir)
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
            # Write the ABOUT file
            about.dump(dump_loc,
                       with_empty=with_empty,
                       with_absent=with_absent)
        except Exception, e:
            # only keep the first 100 char of the exception
            emsg = repr(e)[:100]
            msg = (u'Failed to write ABOUT file at : '
                   u'%(dump_loc)s '
                   u'with error: %(emsg)s' % locals())
            errors.append(Error(ERROR, msg))
    return errors, abouts


def fetch_texts(abouts):
    """
    Given a list of About object, fetch updated data from the DejaCode API.
    """


USAGE_SYNTAX = '''
    INPUT is an inventory file in CSV format
    OUTPUT is the directory where to generate ABOUT files
'''


ACTION_HELP = """\
Handle different behaviors if ABOUT files already existed
0 - Do nothing if ABOUT file existed (default)
1 - Overwrites the current ABOUT field value if existed
2 - Keep the current field value and only add the "new" field and field value
3 - Replace the ABOUT file with the current generation
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
        msg = 'AboutCode %(__version__)s\n%(__copyright__)s'.format(globals())
        print(msg)
        sys.exit(0)

    if verbosity == 1:
        handler.setLevel(logging.ERROR)
    elif verbosity >= 2:
        handler.setLevel(logging.WARNING)

    valid_actions = 0, 1, 2, 3
    if action and action in valid_actions:
        action_num = action
    else:
        print('Invalid action: should be 0,1,2 or 3')
        sys.exit(errno.EINVAL)

    if copy_files_path and not os.path.exists(copy_files_path):
            print("The project path does not exist.")
            sys.exit(errno.EINVAL)

    if license_text_path and not os.path.exists(license_text_path):
            print("The license text path does not exist.")
            sys.exit(errno.EINVAL)

    if mapping_config and not os.path.exists('MAPPING.CONFIG'):
            print("The file 'MAPPING.CONFIG' does not exist.")
            sys.exit(errno.EINVAL)

    if extract_license:
        api_url = extract_license[0].partition('--api_url=')[2]
        api_username = extract_license[1].partition('--api_username=')[2]
        api_key = extract_license[2].partition('--api_key=')[2]
        gen_license = True

    if not len(args) == 2:
        print('Input and Output paths are required.')
        print()
        parser.print_help()
        sys.exit(errno.EEXIST)

    input_path, output_path = args
    output_path = abspath(output_path)

    if not output_path.endswith('/'):
        output_path += '/'

    if not exists(input_path):
        print('Input path does not exist.')
        print()
        parser.print_help()
        sys.exit(errno.EEXIST)

    if not exists(output_path):
        print('Output path does not exist.')
        print()
        parser.print_help()
        sys.exit(errno.EEXIST)

    if not isdir(output_path):
        print('Output must be a directory, not a file.')
        print()
        parser.print_help()
        sys.exit(errno.EISDIR)

    if not input_path.endswith('.csv'):
        print("Input file name must be a CSV file ends with '.csv'")
        print()
        parser.print_help()
        sys.exit(errno.EINVAL)

    gen = None  # GenAbout()

    dup_keys = gen.get_duplicated_keys(input_path)
    if dup_keys:
        print('The input file contains duplicated keys. '
              'Duplicated keys are not allowed.')
        print(dup_keys)
        print()
        print('Please fix the input file and re-run the tool.')
        sys.exit(errno.EINVAL)

    # Clear the log file
    # FIXME: we should just delete the file, not override it
    # or we should append to it...
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

    ignored_fields_list = gen.get_non_supported_fields(input_list,
                                                       mapping_keys)
    if ignored_fields_list:
        input_list = gen.get_only_supported_fields(input_list,
                                                   ignored_fields_list)

    if copy_files_path:
        if not isdir(copy_files_path):
            print("The '--copy_files' <project_path> must be a directory.")
            print("'--copy_files' is skipped.")
        else:
            # if not copy_files_path.endswith('/'):
            #   copy_files_path += '/'
            project_parent_dir = dirname(copy_files_path)
            licenses_in_project = True
            license_list = gen.verify_files_existence(input_list,
                                                      project_parent_dir,
                                                      licenses_in_project)
            if not license_list:
                print("None of the file is found. '--copy_files' is ignored.")
            else:
                gen.copy_files(output_path, license_list)

    if license_text_path:
        if not isdir(license_text_path):
            print("The '--license_text_location' <license_path> "
                  "must be a directory.")
            print("'--license_text_location' is skipped.")
        else:
            # if not license_text_path.endswith('/'):
            #    license_text_path += '/'
            license_dir = dirname(license_text_path)
            licenses_in_project = False
            license_list = gen.verify_files_existence(input_list,
                                                      license_dir,
                                                      licenses_in_project)
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
                print("The input does not have the 'dje_license' "
                      "key which is required.")
                sys.exit(errno.EINVAL)

    if gen_license:
        dje_license_dict = gen.pre_process_and_dje_license_dict(input_list,
                                                                api_url,
                                                                api_username,
                                                                api_key)

    dje_license_list = gen.get_dje_license_list(output_path,
                                                input_list,
                                                gen_license,
                                                dje_license_dict)
    components_list = gen.pre_generation(output_path,
                                         input_list,
                                         action_num,
                                         all_in_one)
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
                opts = '%*s%s\n' % (self.current_indent, '', opts)
                indent_first = self.help_position
            else:  # start help on same line as opts
                opts = '%*s%-*s  ' % (self.current_indent, '', opt_width, opts)
                indent_first = 0
            result.append(opts)
            if option.help:
                help_text = self.expand_default(option)
                help_lines = help_text.split('\n')
                # help_lines = textwrap.wrap(help_text, self.help_width)
                result.append('%*s%s\n' % (indent_first, '', help_lines[0]))
                result.extend(['%*s%s\n' % (self.help_position, '', line)
                               for line in help_lines[1:]])
            elif opts[-1] != '\n':
                result.append('\n')
            return ''.join(result)

    parser = optparse.OptionParser(
        usage='%prog [options] input_path output_path',
        description=USAGE_SYNTAX,
        add_help_option=False,
        formatter=MyFormatter(),
    )
    parser.add_option('--action', type=int,
                      help=ACTION_HELP)
    parser.add_option('--copy_files', type='string',
                      help=COPY_FILES_HELP)
    parser.add_option('--license_text_location', type='string',
                      help=LICENSE_TEXT_LOCATION_HELP)
    parser.add_option('--mapping', action='store_true',
                      help=MAPPING_HELP)
    parser.add_option('--extract_license', type='string', nargs=3,
                      help=EXTRACT_LICENSE_HELP)
    return parser


if __name__ == '__main__':
    parser = get_parser()
    options, args = parser.parse_args()
    main(parser, options, args)
