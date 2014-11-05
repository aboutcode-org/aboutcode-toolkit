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
This tool is used to generate component attribution based on a set of .ABOUT
files. Optionally, one could pass a subset list of specific components for set
of .ABOUT files to generate attribution.
"""

from __future__ import print_function

import csv
import errno
import logging
import optparse
import os
import sys

from os.path import exists, dirname, join, abspath, isdir, basename, expanduser, normpath

from about import Collector
import genabout

LOG_FILENAME = 'error.log'

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.CRITICAL)
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)
file_logger = logging.getLogger(__name__ + '_file')

__version__ = '1.0.2'

__about_spec_version__ = '1.0.0'  # See http://dejacode.org

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


def component_subset_to_sublist(input_list):
    sublist = [row["about_file"] for row in input_list
                   if "about_file" in row.keys()]
    return sublist


def update_path_to_about(input_list):
    output_list = []
    for row in input_list:
        if not row.endswith('.ABOUT'):
            if row.endswith('/'):
                row += basename(dirname(row))
            output_list.append(row + '.ABOUT')
        else:
            output_list.append(row)
    return output_list


def convert_dict_key_to_lower_case(input_list):
    output_list = []
    for line in input_list:
        lower_dict = {}
        for key in line:
            lower_dict[key.lower()] = line[key]
        output_list.append(lower_dict)
    return output_list


def check_about_file_existence_and_format(input_list):
    try:
        for row in input_list:
            # Force the path to start with the '/' to map with the project
            # structure
            if not row['about_file'].startswith('/'):
                row['about_file'] = '/' + row['about_file']
        return input_list
    except Exception:
        return []


USAGE_SYNTAX = """\
    Input can be a file or directory.
    Output of rendered template must be a file (e.g. .html).
    Component List must be a .csv file which has at least an "about_file" column.
"""


VERBOSITY_HELP = """\
Print more or fewer verbose messages while processing ABOUT files
0 - Do not print any warning or error messages, just a total count (default)
1 - Print error messages
2 - Print error and warning messages
"""


TEMPLATE_LOCATION_HELP = """\
Use the custom template for the Attribution Generation
"""


MAPPING_HELP = """\
Configure the mapping key from the MAPPING.CONFIG
"""


def main(parser, options, args):
    overwrite = options.overwrite
    verbosity = options.verbosity
    mapping_config = options.mapping
    template_location = options.template_location

    if options.version:
        print('ABOUT tool {0}\n{1}'.format(__version__, __copyright__))
        sys.exit(0)

    if verbosity == 1:
        handler.setLevel(logging.ERROR)
    elif verbosity >= 2:
        handler.setLevel(logging.WARNING)

    if mapping_config:
        if not exists('MAPPING.CONFIG'):
            print("The file 'MAPPING.CONFIG' does not exist.")
            sys.exit(errno.EINVAL)

    if not len(args) >= 2 and not len(args) < 4:
        print('Path for input and output are required.\n')
        parser.print_help()
        sys.exit(errno.EEXIST)

    input_path = args[0]
    output_path = args[1]
    if len(args) == 3:
        component_subset_path = args[2]
    else:
        component_subset_path = ""

    # TODO: need more path normalization (normpath, expanduser)
    input_path = expanduser(normpath(input_path))
    output_path = expanduser(normpath(output_path))

    # Add the following to solve the
    # UnicodeEncodeError: 'ascii' codec can't encode character
    # FIXME: these two lines do not make sense
    reload(sys)
    sys.setdefaultencoding('utf-8')  # @UndefinedVariable

    if not exists(input_path):
        print('Input path does not exist.')
        parser.print_help()
        sys.exit(errno.EEXIST)

    if isdir(output_path):
        print('Output must be a HTML file.')
        parser.print_help()
        sys.exit(errno.EISDIR)

    # We only support HTML currently
    if not output_path.endswith('.html'):
        print('Output must be a HTML file.')
        parser.print_help()
        sys.exit(errno.EINVAL)

    if exists(output_path) and not overwrite:
        print('Output file already exists. Select a different file name '
              'or use the --overwrite option.')
        parser.print_help()
        sys.exit(errno.EEXIST)

    if template_location:
        template_location = abspath(expanduser(template_location))
        if not exists(expanduser(template_location)):
            print('The defined template location does not exist.')
            parser.print_help()
            sys.exit(errno.EINVAL)

    if component_subset_path and not exists(component_subset_path):
        print('Component Subset path does not exist.')
        parser.print_help()
        sys.exit(errno.EEXIST)

    if not exists(output_path) or (exists(output_path) and overwrite):
        collector = Collector(input_path)
        outlist = None
        if not component_subset_path:
            sublist = None
        else:
            input_list = []
            with open(component_subset_path, "rU") as f:
                input_dict = csv.DictReader(f)
                for row in input_dict:
                    input_list.append(row)
            updated_list = convert_dict_key_to_lower_case(input_list)
            if mapping_config:
                mapping_list = genabout.GenAbout().get_mapping_list()
                updated_list = genabout.GenAbout().convert_input_list(updated_list, mapping_list)
            if not check_about_file_existence_and_format(updated_list):
                print('The required key "about_file" was not found.')
                print('Please use the "--mapping" option to map the input '
                      'keys and verify the mapping information are correct.')
                print('OR, correct the header keys from the component list.')
                parser.print_help()
                sys.exit(errno.EISDIR)
            sublist = component_subset_to_sublist(updated_list)
            outlist = update_path_to_about(sublist)

        attrib_str = collector.generate_attribution(template_path=template_location, limit_to=outlist)
        errors = collector.get_genattrib_errors()

        if attrib_str:
            try:
                with open(output_path, "w") as f:
                    f.write(attrib_str)
            except Exception as e:
                print("Problem occurs. Attribution was not generated.")
                print(e)

        # Remove the previous log file if exist
        log_path = join(dirname(output_path), LOG_FILENAME)
        if exists(log_path):
            os.remove(log_path)

        file_handler = logging.FileHandler(log_path)
        file_logger.addHandler(file_handler)
        for error_msg in errors:
            logger.error(error_msg)
            file_logger.error(error_msg)
        if errors:
            print("%d errors detected." % len(errors))

    else:
        # we should never reach this
        assert False, "Unsupported option(s)."


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
                result.append("%*s%s\n" % (indent_first, "", help_lines[0]))
                result.extend(["%*s%s\n" % (self.help_position, "", line)
                               for line in help_lines[1:]])
            elif opts[-1] != "\n":
                result.append("\n")
            return "".join(result)

    parser = optparse.OptionParser(
        usage='%prog [options] input_path output_path component_list',
        description=USAGE_SYNTAX,
        add_help_option=False,
        formatter=MyFormatter(),
    )
    parser.add_option("-h", "--help", action="help", help="Display help")
    parser.add_option("-v", "--version", action="store_true",
        help='Display current version, license notice, and copyright notice')
    parser.add_option('--overwrite', action='store_true',
                      help='Overwrites the output file if it exists')
    parser.add_option('--verbosity', type=int,
                      help=VERBOSITY_HELP)
    parser.add_option('--template_location', type='string',
                      help=TEMPLATE_LOCATION_HELP)
    parser.add_option('--mapping', action='store_true',
                      help=MAPPING_HELP)
    return parser


if __name__ == "__main__":
    parser = get_parser()
    options, args = parser.parse_args()
    main(parser, options, args)
