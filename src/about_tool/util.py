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
import ntpath
import os
import posixpath
import string
import sys

import unicodecsv

from about_tool import CRITICAL
from about_tool import Error


on_windows = 'win32' in sys.platform
UNC_PREFIX = u'\\\\?\\'

valid_file_chars = string.digits + string.ascii_letters + '_-.'


def invalid_chars(path):
    """
    Return a list of invalid characters in the file name of path
    """
    path = to_posix(path)
    rname = resource_name(path)
    name = rname.lower()
    return [c for c in name if c not in valid_file_chars]


def check_file_names(paths):
    """
    Given a sequence of file paths, check that file names are valid and that
    there are no case-insensitive duplicates in any given directories.
    Return a list of errors.

    From spec :
        A file name can contain only these US-ASCII characters:
        - digits from 0 to 9
        - uppercase and lowercase letters from A to Z
        - the _ underscore, - dash and . period signs.
    From spec:
     The case of a file name is not significant. On case-sensitive file
     systems (such as Linux), a tool must raise an error if two ABOUT files
     stored in the same directory have the same lowercase file name.
    """
    seen = {}
    errors = []
    for orig_path in paths:
        path = orig_path
        invalid = invalid_chars(path)
        if invalid:
            invalid = ''.join(invalid)
            msg = ('Invalid characters %(invalid)r in file name at: '
                   '%(path)r' % locals())
            errors.append(Error(CRITICAL, msg))

        path = to_posix(orig_path)
        name = resource_name(path).lower()
        parent = posixpath.dirname(path)
        path = posixpath.join(parent, name)
        path = posixpath.normpath(path)
        path = posixpath.abspath(path)
        existing = seen.get(path)
        if existing:
            msg = ('Duplicate files: %(orig_path)r and %(existing)r '
                   'have the same case-insensitive file name' % locals())
            errors.append(Error(CRITICAL, msg))
        else:
            seen[path] = orig_path
    return errors


def get_absolute(location):
    """
    Return an absolute normalized location.
    """
    location = os.path.expanduser(location)
    location = os.path.expandvars(location)
    location = os.path.normpath(location)
    location = os.path.abspath(location)
    return location


def as_unc(location):
    """
    Convert a location to an absolute Window UNC path to support long paths
    on Windows. Return the location unchanged if not on Windows.
    See https://msdn.microsoft.com/en-us/library/aa365247.aspx
    """
    if not on_windows or (on_windows and location.startswith(UNC_PREFIX)):
        return location
    return UNC_PREFIX + os.path.abspath(location)


def get_locations(location):
    """
    Return a list of locations of files given the location of a
    a file or a directory tree containing ABOUT files.
    File locations are normalized using posix path separators.
    """
    # See https://bugs.python.org/issue4071
    if on_windows:
        location = unicode(location)
    location = as_unc(location)
    location = get_absolute(location)
    assert os.path.exists(location)

    if os.path.isfile(location):
        yield location
    else:
        for base_dir, _, files in os.walk(location):
            for name in files:
                bd = to_posix(base_dir)
                yield posixpath.join(bd, name)


def get_about_locations(location):
    """
    Return a list of locations of ABOUT files given the location of a
    a file or a directory tree containing ABOUT files.
    File locations are normalized using posix path separators.
    """
    for loc in get_locations(location):
        if is_about_file(loc):
            yield loc


def get_relative_path(base_loc, full_loc):
    """
    Return a posix path for a given full location relative to a base location.
    The last segment of the base_loc will become the first segment of the
    returned path.
    """
    def norm(p):
        if p.startswith(UNC_PREFIX) or p.startswith(to_posix(UNC_PREFIX)):
            p = p.strip(UNC_PREFIX).strip(to_posix(UNC_PREFIX))
        p = to_posix(p)
        p = p.strip(posixpath.sep)
        p = posixpath.normpath(p)
        return p

    base = norm(base_loc)
    path = norm(full_loc)

    assert path.startswith(base), ('Cannot compute relative path: '
                                   '%(path)r does not start with %(base)r'
                                   % locals())
    base_name = resource_name(base)
    no_dir = base == base_name
    same_loc = base == path
    if same_loc:
        # this is the case of a single file or single dir
        if no_dir:
            # we have no dir: the full path is the same as the resource name
            relative = base_name
        else:
            # we have at least one dir
            parent_dir = posixpath.dirname(base)
            parent_dir = resource_name(parent_dir)
            relative = posixpath.join(parent_dir, base_name)
    else:
        relative = path[len(base) + 1:]
        relative = posixpath.join(base_name, relative)

    return relative


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


def is_about_file(path):
    """
    Return True if the path represents a valid ABOUT file name.
    """
    return path and path.lower().endswith('.about')


def resource_name(path):
    """
    Return the file or directory name from a path.
    """
    path = path.strip()
    path = to_posix(path)
    path = path.rstrip(posixpath.sep)
    _left, right = posixpath.split(path)
    return right.strip()


class OrderedDictReader(unicodecsv.DictReader):
    """
    A DictReader that return OrderedDicts
    """
    def next(self):
        row_dict = unicodecsv.DictReader.next(self)
        result = OrderedDict()
        # reorder based on fieldnames order
        for name in self.fieldnames:
            result[name] = row_dict[name]
        return result


def load_csv(location):
    """
    Read CSV at location, return a list of ordered mappings, one for each row.
    """
    results = []
    with codecs.open(location, mode='rb', encoding='utf-8', errors='ignore') as csvfile:
        for row in OrderedDictReader(csvfile):
            results.append(row)
    return results
