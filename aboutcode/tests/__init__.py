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


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


TESTDATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'testdata')


on_windows = 'win' in sys.platform
on_posix = not on_windows


def to_posix(path):
    """
    Return a path using the posix path separator given a path that may contain
    posix or windows separators, converting \ to /. NB: this path will still
    be valid in the windows explorer (except if UNC or share name). It will be
    a valid path everywhere in Python. It will not be valid for windows
    command line operations.
    """
    return path.replace(ntpath.sep, posixpath.sep)


def to_native(path):
    """
    Return a path using the current OS path separator given a path that may
    contain posix or windows separators, converting / to \ on windows and \ to
    / on posix OSes.
    """
    path = path.replace(ntpath.sep, os.path.sep)
    path = path.replace(posixpath.sep, os.path.sep)
    return path


def get_test_loc(path):
    """
    Return the location of a test file or directory given a path relative to
    the testdata directory.
    """
    path = to_posix(path)
    path = to_native(path)
    return os.path.join(TESTDATA_DIR, path)


def get_test_lines(path):
    """
    Return a list of text lines loaded from the location of a test file or
    directory given a path relative to the testdata directory.
    """
    with codecs.open(get_test_loc(path), 'rb', encoding='utf-8') as doc:
        return doc.readlines(True)


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

