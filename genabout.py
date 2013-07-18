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
from os import makedirs
from os.path import exists, dirname, join, abspath, isdir
import csv
import errno
import string
import sys

# TODO: version number
__version__ = ''


MANDATORY_FIELDS = ['about_resource', 'name', 'version']
SKIPPED_FIELDS = ['warnings', 'errors']

def _exists(file_path):
    """
    Return True if path exists.
    """
    if file_path:
        return exists(abspath(file_path))

# This function will read the input csv file, get the information and write
# the information into the .ABOUT file.
# The current design is to assume the .ABOUT file doesn't exist and do nothing
# if it does.
def read_input_and_generate_output(input_file, gen_location):
    csvfile = csv.DictReader(open(input_file, 'rb'))
    for line in csvfile:
        try:
            file_location = line['about_file']
        except Exception, e:
            print(repr(e))
            sys.exit(errno.EINVAL)
        location = join(gen_location, file_location)
        about_file_location =''
        if location.lower().endswith('.about'):
            about_file_location = location
        else:
            if location[-1] == '/':
                about_file_location = location.rpartition('/')[0] + '.ABOUT'
            else:
                about_file_location = location + '.ABOUT'
        dir = dirname(about_file_location)
        if not _exists(dir):
            makedirs(dir)
        if _exists(about_file_location):
            print("About file already existed.")
        else:
            with open(about_file_location, 'wb') as output_file:
                context = ""
                for item in sorted(line.iterkeys()):
                    # The purpose of the replace('\n', '\n ') is used to
                    # format the continuation strings
                    value = line[item].replace('\n', '\n ')
                    if (value or item in MANDATORY_FIELDS) and not item in SKIPPED_FIELDS:
                        context += item + ': ' + value + '\n'
                output_file.write(context)

def main():
    # The length is 3 as
    # 1. the python script itself, genabout.py
    # 2. input file
    # 3. location for generation
    if not len(sys.argv) == 3:
        print(sys.argv[0] + " needs exactly 2 arguments. \n\n \t genabout.py <input_file> <generated_location>")
        sys.exit(0)

    input_file = sys.argv[1]
    gen_location = sys.argv[2]

    if not _exists(input_file):
        print(input_file, ': Input file does not exist.')
        sys.exit(0)
    if not _exists(gen_location):
        print(gen_location, ': Generated location does not exist.')
        sys.exit(0)

    read_input_and_generate_output(input_file, gen_location)

if __name__ == "__main__":
    main()