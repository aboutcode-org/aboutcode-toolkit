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
import errno
import httplib
import json
import ntpath
import os
import posixpath
import shutil
import socket
import string
import sys
import unicodecsv

from collections import OrderedDict
from os.path import abspath
from os.path import dirname
from os.path import join

from about_tool import CRITICAL, ERROR, Error


on_windows = 'win32' in sys.platform


def posix_path(path):
    """
    Return a path using POSIX path separators given a path that may
    contain POSIX or windows separators, converting \ to /.
    """
    return path.replace(ntpath.sep, posixpath.sep)


UNC_PREFIX = u'\\\\?\\'
UNC_PREFIX_POSIX = posix_path(UNC_PREFIX)
UNC_PREFIXES = (UNC_PREFIX_POSIX, UNC_PREFIX,)

valid_file_chars = string.digits + string.ascii_letters + '_-.'

have_mapping = False


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

def get_mappings(location=None):
    """
    Return a mapping of user key names to About key names by reading the
    MAPPING.CONFIG file from location or the directory of this source file if
    location was not provided.
    """
    if not location:
        location = abspath(dirname(__file__))
    mappings = {}
    try:
        with open(join(location, 'MAPPING.CONFIG'), 'rU') as mapping_file:
            for line in mapping_file:
                if not line or not line.strip() or line.strip().startswith('#'):
                    continue

                if ':' in line:
                    line = line.lower()
                    key, sep, value = line.partition(':')
                    about_key = key.strip().replace(' ', '_')
                    user_key = value.strip()
                    #mappings[user_key] = about_key
                    mappings[about_key] = user_key

    except Exception as e:
        print(repr(e))
        print('Cannot open or process MAPPING.CONFIG file at %(location)r.' %locals())
        # this is rather brutal
        sys.exit(errno.EACCES)
    return mappings


def apply_mappings(abouts, mappings=None):
    """
    Given a list of About data dictionaries and a dictionary of mappings,
    return a new About data dictionaries list where the keys have been
    replaced by the About mapped_abouts key if present.
    """
    mappings = mappings or get_mappings()
    mapped_abouts = []
    for about in abouts:
        mapped_about = {}
        for key in about:
            mapped = []
            for mapping_keys, input_keys in mappings.items():
                if key == input_keys:
                    mapped.append(mapping_keys)
            if not mapped:
                mapped.append(key)
            for mapped_key in mapped:
                mapped_about[mapped_key] = about[key]
        mapped_abouts.append(mapped_about)
    return mapped_abouts


def get_about_file_path(mapping, location):
    """
    Read file at location, return a list of about_file_path.
    """
    afp_list = []
    if location.endswith('.csv'):
        about_data = load_csv(mapping, location)
    else:
        about_data = load_json(mapping, location)

    for about in about_data:
        afp_list.append(about['about_file_path'])
    return afp_list


def load_csv(mapping, location):
    """
    Read CSV at location, return a list of ordered mappings, one for each row.
    """
    global have_mapping
    have_mapping = mapping

    results = []
    with codecs.open(location, mode='rb', encoding='utf-8', errors='ignore') as csvfile:
        for row in OrderedDictReader(csvfile):
            input_row = {}
            # convert all the column keys to lower case as the same behavior as
            # when user use the --mapping
            for key in row.keys():
                input_row[key.lower()] = row[key]
            results.append(input_row)
    # user has the mapping option set
    if mapping:
        results = apply_mappings(results)
    return results


def load_json(mapping, location):
    """
    Read JSON at location, return a list of ordered mappings, one for each entry.
    """
    global have_mapping
    have_mapping = mapping

    with open(location) as json_file:    
        results = json.load(json_file)
    if mapping:
        results = apply_mappings(results)
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
                os.makedirs(parent)
            if not content and is_dir:
                if not os.path.exists(target):
                    os.makedirs(target)
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
    if on_windows and not location.startswith(UNC_PREFIXES):
        return UNC_PREFIX + os.path.abspath(location)
    return location


# FIXME: This should be part of the model
def verify_license_files(abouts, lic_location):
    lic_loc_dict = {}
    errors = []

    for about in abouts:
        """
        The license_file field is filled if the input has dje_license_key and 
        the 'extract_license' option is used. This function only wants to check
        the existence of the license file provided in the license_field from the
        license_text_location.
        """
        if about.license_file.value and not about.dje_license_key.value:
            for lic in about.license_file.value:
                lic_path = posix_path(posixpath.join(lic_location, lic))
                if posixpath.exists(lic_path):
                    copy_to = posixpath.dirname(about.about_file_path)
                    lic_loc_dict[copy_to] = lic_path
                else:
                    msg = ('The file, ' + lic + ' in \'license_file\' field does not exist')
                    errors.append(Error(ERROR, msg))
    return lic_loc_dict, errors


def copy_files(license_location_dict, gen_location):
    """
    Copy the files into the gen_location
    """
    for loc in license_location_dict:
        location = loc
        if loc.startswith('/'):
            location = loc.strip('/')
        copy_to = posixpath.join(posix_path(gen_location), location)
        shutil.copy2(license_location_dict[loc], copy_to)
