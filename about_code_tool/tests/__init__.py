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

from __future__ import print_function

import os
import stat
import tempfile
import unittest
import logging
import codecs
import posixpath
import sys
import string
import ntpath

from about_code_tool.util import to_posix, to_native

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


TESTDATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'testdata')

on_windows = 'win32' in sys.platform
on_posix = not on_windows



def get_test_loc(path):
    """
    Return the location of a test file or directory given a path relative to
    the testdata directory.
    """
    base = to_posix(TESTDATA_DIR)
    path = to_posix(path)
    path = posixpath.join(base, path)
    #path = to_native(path)
    return path

def get_unicode_content(location):
    """
    Read file at location and return a unicode.
    """
    with codecs.open(location, 'rb', encoding='utf-8') as doc:
        return doc.read()


def get_test_lines(path):
    """
    Return a list of text lines loaded from the location of a test file or
    directory given a path relative to the testdata directory.
    """
    return get_unicode_content(get_test_loc(path)).splitlines(True)


def create_dir(location):
    """
    Create directory or directory tree at location, ensuring it is readable
    and writeable.
    """
    if not os.path.exists(location):
        os.makedirs(location)
        os.chmod(location, stat.S_IRWXU | stat.S_IRWXG
                 | stat.S_IROTH | stat.S_IXOTH)


def build_temp_dir(prefix='test-about-code-'):
    """
    Create and return a new unique empty directory created in base_dir.
    """
    location = tempfile.mkdtemp(prefix=prefix)
    create_dir(location)
    return location


def get_temp_file(file_name='test-about-code-tempfile'):
    """
    Return a unique new temporary file location to a non-existing
    temporary file that can safely be created without a risk of name
    collision.
    """
    temp_dir = get_temp_dir()
    location = os.path.join(temp_dir, file_name)
    return location


def get_temp_dir(sub_dir_path=None):
    """
    Create a unique new temporary directory location. Create directories
    identified by sub_dir_path if provided in this temporary directory.
    Return the location for this unique directory joined with the
    sub_dir_path if any.
    """
    new_temp_dir = build_temp_dir()

    if sub_dir_path:
        # create a sub directory hierarchy if requested
        new_temp_dir = os.path.join(new_temp_dir, sub_dir_path)
        create_dir(new_temp_dir)
    return new_temp_dir

