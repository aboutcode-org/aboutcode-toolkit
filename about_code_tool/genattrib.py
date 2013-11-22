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
This is a tool to generate component attribution based on a set of .ABOUT files.
Optionally, one could pass a subset list of specific components for set of
.ABOUT files to generate attribution.
"""

from __future__ import print_function
from __future__ import with_statement
from about import AboutCollector

import codecs
import csv
import errno
import fnmatch
import getopt
import httplib
import posixpath
import socket
import string
import sys
import urlparse
from collections import namedtuple
from datetime import datetime
from email.parser import HeaderParser
from os import listdir, walk
from os.path import exists, dirname, join, abspath, isdir, basename, normpath
from StringIO import StringIO
__version__ = '0.9.0'

# see http://dejacode.org
__about_spec_version__ = '0.8.0'

def component_subset_to_sublist(input_path):
    sublist = []
    with open(input_path, "rU") as f:
        csv_dict = csv.DictReader(f)
        sublist = [row["about_resource"] for row in csv_dict
                   if "about_resource" in row.keys()]

    return sublist

def syntax():
    print("""
Syntax:
    genattrib.py [Options] [Input] [Output] [Component List]
    Input can be a file or directory.
    Output of rendered template must be a file (e.g. .html).
    Component List must be a .csv file which has at least an "about_resource" column.
""")


def option_usage():
    print("""
Options:
    --overwrite          Overwrites the output file if it exists
    -v,--version         Display current version, license notice, and copyright notice
    -h,--help            Display help
    --verbosity  <arg>   Print more or less verbose messages while processing ABOUT files
        <arg>
            0 - Do not print any warning or error messages, just a total count (default)
            1 - Print error messages
            2 - Print error and warning messages
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


def main(args, opts):
    overwrite = False
    opt_arg_num = '0'
    for opt, opt_arg in opts:
        invalid_opt = True
        if opt in ('-h', '--help'):
            syntax()
            option_usage()
            sys.exit(0)

        if opt in ('-v', '--version'):
            version()
            sys.exit(0)

        if opt in ('--verbosity'):
            invalid_opt = False
            valid_opt_args = ['0', '1', '2']
            if not opt_arg or not opt_arg in valid_opt_args:
                print("Invalid option argument.")
                option_usage()
                sys.exit(errno.EINVAL)
            else:
                opt_arg_num = opt_arg

        if opt in ('--overwrite'):
            invalid_opt = False
            overwrite = True

        if invalid_opt:
            assert False, 'Unsupported option.'

    if len(args) < 2:
        print('Input and output parameters are mandatory.')
        syntax()
        option_usage()
        sys.exit(errno.EINVAL)

    input_path = args[0]
    output_path = args[1]
    component_subset_path = None if len(args) < 3 else args[2]

    # TODO: need more path normalization (normpath, expanduser)
    # input_path = abspath(input_path)
    output_path = abspath(output_path)

    if not exists(input_path):
        print('Input path does not exist.')
        option_usage()
        sys.exit(errno.EEXIST)

    if isdir(output_path):
        print('Output must be a file, not a directory.')
        option_usage()
        sys.exit(errno.EISDIR)

    if exists(output_path) and not overwrite:
        print('Output file already exists. Select a different file name or use '
              'the --overwrite option.')
        option_usage()
        sys.exit(errno.EEXIST)

    if component_subset_path and not exists(component_subset_path):
        print('Component Subset path does not exist.')
        option_usage()
        sys.exit(errno.EEXIST)

    if not exists(output_path) or (exists(output_path) and overwrite):
        collector = AboutCollector(input_path, output_path, opt_arg_num)
        sublist = None if not component_subset_path else component_subset_to_sublist(component_subset_path)
        attrib_str = collector.generate_attribution( sublist = sublist )
        with open(output_path, "w") as f:
            f.write(attrib_str)

    else:
        # we should never reach this
        assert False, "Unsupported option(s)."


if __name__ == "__main__":
    longopts = ['help', 'version', 'overwrite', 'verbosity=']
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hv', longopts)
    except Exception as e:
        print(repr(e))
        syntax()
        option_usage()
        sys.exit(errno.EINVAL)

    main(args, opts)
