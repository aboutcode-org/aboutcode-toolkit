#!/usr/bin/env python
# -*- coding: utf8 -*-
# ============================================================================
#  Copyright (c) 2013-2017 nexB Inc. http://www.nexb.com/ - All rights reserved.
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
import codecs
import errno
import json
import ntpath
import os
from os.path import abspath
from os.path import dirname
from os.path import join
import posixpath
import shutil
import socket
import string
import sys

if sys.version_info[0] < 3:
    # Python 2
    import backports.csv as csv
else:
    # Python 3
    import csv

try:
    # Python 2
    import httplib
except ImportError:
    # Python 3
    import http.client as httplib

from attributecode import CRITICAL
from attributecode import Error


on_windows = 'win32' in sys.platform


def to_posix(path):
    """
    Return a path using the posix path separator given a path that may contain
    posix or windows separators, converting \ to /. NB: this path will still
    be valid in the windows explorer (except if UNC or share name). It will be
    a valid path everywhere in Python. It will not be valid for windows
    command line operations.
    """
    return path.replace(ntpath.sep, posixpath.sep)


UNC_PREFIX = u'\\\\?\\'
UNC_PREFIX_POSIX = to_posix(UNC_PREFIX)
UNC_PREFIXES = (UNC_PREFIX_POSIX, UNC_PREFIX,)

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


def get_locations(location):
    """
    Return a list of locations of files given the location of a
    a file or a directory tree containing ABOUT files.
    File locations are normalized using posix path separators.
    """
    location = add_unc(location)
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
    The first segment of the different between full_loc and base_loc will become
    the first segment of the returned path.
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
        # We don't want to keep the first segment of the root of the returned path.
        # See https://github.com/nexB/attributecode/issues/276
        # relative = posixpath.join(base_name, relative)
    return relative


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


# Python 3
OrderedDictReader = csv.DictReader

if sys.version_info[0] < 3:
    # Python 2
    class OrderedDictReader(csv.DictReader):
        """
        A DictReader that return OrderedDicts
        Copied from csv.DictReader itself backported from Python 3
        license: python
        """
        def __next__(self):
            if self.line_num == 0:
                # Used only for its side effect.
                self.fieldnames
            row = next(self.reader)
            self.line_num = self.reader.line_num
    
            # unlike the basic reader, we prefer not to return blanks,
            # because we will typically wind up with a dict full of None
            # values
            while row == []:
                row = next(self.reader)
            d = OrderedDict(zip(self.fieldnames, row))
            lf = len(self.fieldnames)
            lr = len(row)
            if lf < lr:
                d[self.restkey] = row[lf:]
            elif lf > lr:
                for key in self.fieldnames[lr:]:
                    d[key] = self.restval
            return d

        next = __next__


def get_mapping(location=None):
    """
    Return a mapping of user key names to About key names by reading the
    mapping.config file from location or the directory of this source file if
    location was not provided.
    """
    if not location:
        location = join(abspath(dirname(__file__)), 'mapping.config')
    if not os.path.exists(location):
        return {}

    mapping = {}
    try:
        with open(location) as mapping_file:
            for line in mapping_file:
                if not line or not line.strip() or line.strip().startswith('#'):
                    continue

                if ':' in line:
                    line = line.lower()
                    key, sep, value = line.partition(':')
                    about_key = key.strip().replace(' ', '_')
                    user_key = value.strip()
                    mapping[about_key] = user_key

    except Exception as e:
        print(repr(e))
        print('Cannot open or process mapping.config file at %(location)r.' % locals())
        # FIXME: this is rather brutal
        sys.exit(errno.EACCES)
    return mapping


def apply_mapping(abouts, alternate_mapping=None):
    """
    Given a list of About data dictionaries and a dictionary of
    mapping, return a new About data dictionaries list where the keys
    have been replaced by the About mapped_abouts key if present. Load
    the mapping from the default mnapping.config if an alternate
    mapping dict is not provided.
    """
    if alternate_mapping:
        mapping = alternate_mapping
    else:
        mapping = get_mapping()

    if not mapping:
        return abouts

    mapped_abouts = []
    for about in abouts:
        mapped_about = OrderedDict()
        for key in about:
            mapped = []
            for mapping_keys, input_keys in mapping.items():
                if key == input_keys:
                    mapped.append(mapping_keys)
            if not mapped:
                mapped.append(key)
            for mapped_key in mapped:
                mapped_about[mapped_key] = about[key]
        mapped_abouts.append(mapped_about)
    return mapped_abouts


def get_about_file_path(location, use_mapping=False):
    """
    Read file at location, return a list of about_file_path.
    """
    afp_list = []
    if location.endswith('.csv'):
        about_data = load_csv(location, use_mapping=use_mapping)
    else:
        about_data = load_json(location, use_mapping=use_mapping)

    for about in about_data:
        afp_list.append(about['about_file_path'])
    return afp_list


def load_csv(location, use_mapping=False):
    """
    Read CSV at location, return a list of ordered dictionaries, one
    for each row.
    """
    results = []
    # FIXME: why ignore encoding errors here?
    with codecs.open(location, mode='rb', encoding='utf-8',
                     errors='ignore') as csvfile:
        for row in OrderedDictReader(csvfile):
            # convert all the column keys to lower case as the same
            # behavior as when user use the --mapping
            updated_row = OrderedDict(
                [(key.lower(), value) for key, value in row.items()]
            )
            results.append(updated_row)
    if use_mapping:
        results = apply_mapping(results)
    return results


def load_json(location, use_mapping=False):
    """
    Read JSON at location, return a list of ordered mappings, one for each entry.
    """
    with open(location) as json_file:
        results = json.load(json_file)
    if use_mapping:
        results = apply_mapping(results)
    return results


def have_network_connection():
    """
    Return True if an HTTP connection to some public web site is possible.
    """
    http_connection = httplib.HTTPConnection('dejacode.org', timeout=10)
    try:
        http_connection.connect()
    except socket.error:
        return False
    else:
        return True

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
    base_dir = tempfile.mkdtemp()
    target_dir = os.path.join(base_dir, archive_base_name)
    target_dir = add_unc(target_dir)
    os.makedirs(target_dir)

    if target_dir.endswith((ntpath.sep, posixpath.sep)):
        target_dir = target_dir[:-1]

    with zipfile.ZipFile(location) as zipf:
        for info in zipf.infolist():
            name = info.filename
            content = zipf.read(name)
            target = os.path.join(target_dir, name)
            is_dir = target.endswith((ntpath.sep, posixpath.sep))
            if is_dir:
                target = target[:-1]
            parent = os.path.dirname(target)
            if on_windows:
                target = target.replace(posixpath.sep, ntpath.sep)
                parent = parent.replace(posixpath.sep, ntpath.sep)
            if not os.path.exists(parent):
                os.makedirs(add_unc(parent))
            if not content and is_dir:
                if not os.path.exists(target):
                    os.makedirs(add_unc(target))
            if not os.path.exists(target):
                with open(target, 'wb') as f:
                    f.write(content)
    return target_dir


def add_unc(location):
    """
    Convert a location to an absolute Window UNC path to support long paths on
    Windows. Return the location unchanged if not on Windows. See
    https://msdn.microsoft.com/en-us/library/aa365247.aspx
    """
    if on_windows and not location.startswith(UNC_PREFIX):
        if location.startswith(UNC_PREFIX_POSIX):
            return UNC_PREFIX + os.path.abspath(location.strip(UNC_PREFIX_POSIX))
        return UNC_PREFIX + os.path.abspath(location)
    return location


def copy_license_notice_files(fields, base_dir, license_notice_text_location, afp):
    lic_name = u''
    for key, value in fields:
        if key == u'license_file' or key == u'notice_file':
            lic_name = value

            from_lic_path = posixpath.join(to_posix(license_notice_text_location), lic_name)
            about_file_dir = dirname(to_posix(afp)).lstrip('/')
            to_lic_path = posixpath.join(to_posix(base_dir), about_file_dir)

            if on_windows:
                from_lic_path = add_unc(from_lic_path)
                to_lic_path = add_unc(to_lic_path)

            # Errors will be captured when doing the validation
            if not posixpath.exists(from_lic_path):
                continue

            if not posixpath.exists(to_lic_path):
                os.makedirs(to_lic_path)
            shutil.copy2(from_lic_path, to_lic_path)
