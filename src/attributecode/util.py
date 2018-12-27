#!/usr/bin/env python
# -*- coding: utf8 -*-
# ============================================================================
#  Copyright (c) 2013-2018 nexB Inc. http://www.nexb.com/ - All rights reserved.
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
from __future__ import unicode_literals

from collections import OrderedDict
import os
import posixpath
import string
import sys

from attributecode import CRITICAL
from attributecode import Error


python2 = sys.version_info[0] < 3

if python2:  # pragma: nocover
    from backports import csv  # NOQA
    # monkey patch backports.csv until bug is fixed
    # https://github.com/ryanhiebert/backports.csv/issues/30
    csv.dict = OrderedDict
else:  # pragma: nocover
    import csv  # NOQA


on_windows = 'win32' in sys.platform


def to_posix(path):
    """
    Return a path using the posix path separator given a path that may contain
    posix or windows separators, converting "\\" to "/".
    NB: this path will still be valid in the windows explorer. It will be a
    valid path everywhere in Python. It may not lways be valid for windows
    command line operations.
    """
    return path.replace('\\', '/')


def to_native(path):
    """
    Return a path using the current OS path separator given a path that may
    contain posix or windows separators, converting "/" to "\\" on windows
    and "\\" to "/" on posix OSes.
    """
    return path.replace('\\', os.path.sep).replace('/', os.path.sep)


valid_file_chars = string.digits + string.ascii_letters + '_-.' + ' '


def invalid_chars(path):
    """
    Return a list of invalid characters in the file name of `path`.
    """
    path = to_posix(path)
    rname = resource_name(path)
    name = rname.lower()
    return [c for c in name if c not in valid_file_chars]

# FIXME: do not checl for invalida characters
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
    # FIXME: this should be a defaultdicts that accumulates all duplicated paths
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


def normalize(location):
    """
    Return an absolute normalized location.
    """
    location = os.path.expanduser(location)
    location = os.path.expandvars(location)
    location = os.path.normpath(location)
    location = os.path.abspath(location)
    return location


def get_relative_path(base_loc, full_loc):
    """
    Return a posix path for a given full_loc location relative to a base_loc
    location.
    """
    def norm(p):
        p = to_posix(p)
        p = p.strip('/')
        return posixpath.normpath(p)

    base = norm(base_loc)
    full = norm(full_loc)

    assert full.startswith(base), (
        'Cannot compute relative path: %(full_loc)r does not starts with %(base_loc)r' % locals())

    assert full != base, (
        'Cannot compute relative path: %(full_loc)r is the same as: %(base_loc)r' % locals())
    relative = full[len(base) + 1:]

    # We don't want to keep the first segment of the root of the returned path.
    # See https://github.com/nexB/attributecode/issues/276
    # relative = posixpath.join(base_name, relative)
    return relative


def resource_name(path):
    """
    Return the file or directory name from a path.
    """
    path = path.strip()
    path = to_posix(path)
    path = path.rstrip('/')
    _left, right = posixpath.split(path)
    return right.strip()


def extract_zip(location):
    """
    Extract a zip file at location in a temp directory and return the temporary
    directory where the archive was extracted.
    """
    import zipfile
    import tempfile

    if not zipfile.is_zipfile(location):
        raise Exception('Incorrect zip file %(location)r' % locals())

    archive_base_name = os.path.basename(location).replace('.zip', '')
    base_dir = tempfile.mkdtemp(prefix='aboutcode-toolkit-extract-')
    target_dir = os.path.join(base_dir, archive_base_name)

    os.makedirs(target_dir)

    if target_dir.endswith(('\\', '/')):
        target_dir = target_dir[:-1]

    with zipfile.ZipFile(location) as zipf:
        for info in zipf.infolist():
            name = info.filename
            content = zipf.read(name)
            target = os.path.join(target_dir, name)
            is_dir = target.endswith(('\\', '/'))
            if is_dir:
                target = target[:-1]
            parent = os.path.dirname(target)
            if on_windows:
                target = target.replace('/', '\\')
                parent = parent.replace('/', '\\')
            if not os.path.exists(parent):
                os.makedirs(parent)
            if not content and is_dir:
                if not os.path.exists(target):
                    os.makedirs(target)
            if not os.path.exists(target):
                with open(target, 'wb') as f:
                    f.write(content)
    return target_dir


def unique(sequence):
    """
    Return a list of unique items found in sequence. Preserve the original
    sequence order.
    For example:
    >>> unique([1, 5, 3, 5])
    [1, 5, 3]
    """
    deduped = []
    for item in sequence:
        if item not in deduped:
            deduped.append(item)
    return deduped
