#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2015 nexB Inc. http://www.nexb.com/ - All rights reserved.
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
Tool to generate component attribution based on a set of .ABOUTfiles. 

Optionally accepts a list (i.e. a subset) of ABOUT file paths to limit the
generated attribution to this subset.
"""

from __future__ import print_function

from about import Collector
from help import MAPPING_HELP
from help import VERBOSITY_HELP
from help import __full_info__
from help import __version_info__
from os.path import abspath
from os.path import basename
from os.path import dirname
from os.path import exists
from os.path import expanduser
from os.path import isdir
from os.path import join
from os.path import normpath
from util import ImprovedFormatter
from util import apply_mappings
from util import extract_zip

import csv
import errno
import logging
import optparse
import os
import posixpath
import sys


LOG_FILENAME = 'error.log'

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.CRITICAL)
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)
file_logger = logging.getLogger(__name__ + '_file')

def get_about_file_paths(abouts):
    """
    Return a list of about_file paths given a list of About data dictionaries.
    """
    return [row['about_file'] for row in abouts if 'about_file' in row]


def as_about_paths(paths):
    """
    Given a list of paths, return a list of paths that point all to .ABOUT files.
    """
    normalized_paths = []
    for path in paths:
        if path.endswith('.ABOUT'):
            normalized_paths.append(path)
        else:
            if path.endswith('/'):
                path += basename(dirname(path))
            normalized_paths.append(path + '.ABOUT')
    return normalized_paths


def lower_keys(dicts):
    """
    Return a new a list of 'dicts' dictionaries such that all the keys are
    lowercased.
    """
    lowered_dicts = []
    for dct in dicts:
        lowered = {}
        for key, value in dct.items():
            lowered[key.lower()] = value
        lowered_dicts.append(lowered)
    return lowered_dicts


def has_about_file_keys(abouts):
    """
    Return True if all dicts in a list of About dictionaries have an about_file key.
    """
    return all(about.get('about_file') for about in abouts)


def normalize_about_file_paths(abouts):
    """
    Update a list of About data dictionaries such that all 'about_file' paths are
    absolute POSIX paths (i.e. prefixed with a POSIX / "slash").
    """
    for about in abouts:
        about_file_path = about.get('about_file')
        if about_file_path and not about_file_path.startswith(posixpath.sep):
            about['about_file'] = '/' + about_file_path
    return abouts


USAGE_SYNTAX = """\
    <input_path> can be a file or directory containing ABOUT files.
    <output_path> is a file path to save the rendered attribution (e.g. .html).
    <component_list> is an optional .csv file with at least an "about_file" column to limit attribution generation to that list.
"""


TEMPLATE_LOCATION_HELP = """\
Optional path to a custom template to use for the generating the attribution.
Default to 'about_code_tool/templates/default.html'
"""

VERIFICATION_HELP = """\
Optional path to a verification CSV file created from the generated attribution.
"""

def main(parser, options, args):
    overwrite = options.overwrite
    verbosity = options.verbosity
    mapping_config = options.mapping
    template_location = options.template_location
    verification_location = options.verification_location

    if options.version:
        print(__full_info__)
        sys.exit(0)

    if verbosity == 1:
        handler.setLevel(logging.ERROR)
    elif verbosity >= 2:
        handler.setLevel(logging.WARNING)

    if mapping_config:
        if not exists('MAPPING.CONFIG'):
            print("ERROR: The 'MAPPING.CONFIG' file does not exist.")
            sys.exit(errno.EINVAL)

    if template_location:
        template_location = abspath(expanduser(template_location))
        if not exists(template_location):
            print('ERROR: The TEMPLATE_LOCATION file does not exist.')
            parser.print_help()
            sys.exit(errno.EINVAL)

    if verification_location:
        verification_location = abspath(expanduser(verification_location))
        if not verification_location.endswith('.csv'):
            print('ERROR: The VERIFICATION_LOCATION file path must end with ".csv".')
            parser.print_help()
            sys.exit(errno.EINVAL)
        if not exists(dirname(verification_location)):
            print('ERROR: The VERIFICATION_LOCATION file parent directory does not exist.')
            parser.print_help()
            sys.exit(errno.EINVAL)

    if not len(args) >= 2 or not len(args) < 4:
        print('ERROR: The number of arguments is incorrect.')
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
        print('ERROR: <input_path> does not exist.')
        parser.print_help()
        sys.exit(errno.EEXIST)

    if input_path.lower().endswith('.zip'):
        # accept zipped ABOUT files as input
        input_path = extract_zip(input_path)

    if isdir(output_path):
        print('ERROR: <output_path> cannot be a directory')
        parser.print_help()
        sys.exit(errno.EISDIR)

    """
    # We only support HTML currently
    if not output_path.endswith('.html'):
        print('ERROR: <output_path> must be an HTML file.')
        parser.print_help()
        sys.exit(errno.EINVAL)
    """

    if exists(output_path) and not overwrite:
        print('ERROR: A file at <output_path> already exists. Select a different file name or use the --overwrite option.')
        parser.print_help()
        sys.exit(errno.EEXIST)

    if component_subset_path and not exists(component_subset_path):
        print('ERROR: the <component_list> CSV file does not exist.')
        parser.print_help()
        sys.exit(errno.EEXIST)

    if not exists(output_path) or (exists(output_path) and overwrite):
        collector = Collector(input_path)
        outlist = None
        if not component_subset_path:
            sublist = None

        else:
            with open(component_subset_path, 'rU') as inp:
                reader = csv.DictReader(inp)
                abouts = [data for data in reader]

            abouts = lower_keys(abouts)

            if mapping_config:
                abouts = apply_mappings(abouts)

            if not has_about_file_keys(abouts):
                print('ERROR: The required column key "about_file" was not found in the <component_list> CSV file.')
                print('Please use the "--mapping" option to map the input keys and verify the mapping information are correct.')
                print('OR, correct the header keys from the component list.')
                parser.print_help()
                sys.exit(errno.EISDIR)

            abouts = normalize_about_file_paths(abouts)

            sublist = get_about_file_paths(abouts)
            outlist = as_about_paths(sublist)

        attrib_str = collector.generate_attribution(template_path=template_location, limit_to=outlist, verification=verification_location)
        errors = collector.get_genattrib_errors()

        if attrib_str:
            try:
                with open(output_path, 'w') as f:
                    f.write(attrib_str)
            except Exception as e:
                print('An error occurred. Attribution was not generated.')
                print(e)

        print('Completed.')
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
            print('%d errors detected.' % len(errors))

    else:
        # we should never reach this
        assert False, 'Unsupported option(s).'


def get_parser():
    """
    Return a command line options parser.
    """
    parser = optparse.OptionParser(
        usage='%prog [options] input_path output_path [component_list]',
        description=USAGE_SYNTAX,
        add_help_option=False,
        formatter=ImprovedFormatter(),
    )
    parser.add_option('-h', '--help', action='help', help='Print this help message and exit.')
    parser.add_option('--version', action='store_true', help='Print the current version and copyright notice and exit')
    parser.add_option('--overwrite', action='store_true', help='Overwrites the <output_path> file if it exists.')
    parser.add_option('--verbosity', type=int, help=VERBOSITY_HELP)
    parser.add_option('--template_location', type='string', help=TEMPLATE_LOCATION_HELP)
    parser.add_option('--mapping', action='store_true', help=MAPPING_HELP)
    parser.add_option('--verification_location', type='string', help=VERIFICATION_HELP)
    return parser


if __name__ == '__main__':
    print(__version_info__)
    parser = get_parser()
    options, args = parser.parse_args()
    main(parser, options, args)
