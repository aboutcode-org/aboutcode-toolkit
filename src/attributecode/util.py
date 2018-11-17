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

import codecs
from collections import OrderedDict
import json
import ntpath
import os
import posixpath
import shutil
import string
import sys

from attributecode import CRITICAL
from attributecode import Error
from attributecode import DEFAULT_MAPPING


python2 = sys.version_info[0] < 3

if python2:  # pragma: nocover
    import backports.csv as csv  # NOQA
    from itertools import izip_longest as zip_longest  # NOQA
else:  # pragma: nocover
    import csv  # NOQA
    from itertools import zip_longest  # NOQA


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

valid_file_chars = string.digits + string.ascii_letters + '_-.' + ' '


def invalid_chars(path):
    """
    Return a list of invalid characters in the file name of `path`.
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


def check_duplicate_keys_about_file(about_text):
    """
    Return a list of duplicated keys given a ABOUT text string.
    """
    seen = set()
    duplicates = set()
    for line in about_text.splitlines():
        """
        Ignore all the continuation string, mapping/list dahs, string block and empty line.
        """
        if not line.strip() :
            continue
        if line.startswith((' ', '\t')):
            continue
        if line.strip().startswith('-'):
            continue
        if ':' not in line:
            continue
        # Get the key name
        key, _, _val = line.partition(':')
        if key in seen:
            duplicates.add(key)
        else:
            seen.add(key)
    return sorted(duplicates)


def wrap_boolean_value(context):
    bool_fields = ['redistribute', 'attribute', 'track_changes', 'modified']
    input = []  # NOQA
    for line in context.splitlines():
        key = line.partition(':')[0]
        if key in bool_fields:
            value = "'" + line.partition(':')[2].strip() + "'"
            updated_line = key + ': ' + value
            input.append(updated_line)
        else:
            input.append(line)
    updated_context = '\n'.join(input)
    return updated_context


# TODO: rename to normalize_path
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
    Return a list of locations of files given the `location` of a
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
    Return a list of locations of ABOUT files given the `location` of a
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
    if path:
        path = path.lower()
        return path.endswith('.about') and path != '.about'


def resource_name(path):
    """
    Return the file or directory name from a path.
    """
    path = path.strip()
    path = to_posix(path)
    path = path.rstrip(posixpath.sep)
    _left, right = posixpath.split(path)
    return right.strip()


if python2:
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
else:
    OrderedDictReader = csv.DictReader


# FIXME: we should use a proper YAML file for this instead
def load_mapping(location, lowercase=True):
    """
    Return a mapping loaded from a mapping configuration file at `location`.
    If `lowercase` is True, the keys are lowercased.
    Raise Exception on errors including empty of non existing location.
    Return an empty mapping if the location is empty or does not exists.
    """
    if not location:
        return {}
    mapping = OrderedDict()
    with open(location) as mapping_file:
        for line in mapping_file:
            line = line.strip()
            if not line or ':' not in line or line.startswith('#'):
                continue
            if lowercase:
                line = line.lower()

            about_key, _, user_key = line.partition(':')
            # FIXME: why do we allow spaces in ABOUT keys and converts these to _????
            # FIXME: this should be an error instead
            about_key = about_key.strip().replace(' ', '_')
            user_key = user_key.strip()
            mapping[about_key] = user_key
    return mapping


def get_mapping(location=DEFAULT_MAPPING, lowercase=True):
    """
    Return a mapping of user key names to About key names by reading the
    mapping.config file from `location` or the directory of this source file if
    location was not provided.
    """
    return load_mapping(location, lowercase)


def apply_mapping(abouts, mapping_file=None):
    """
    Given a list of About data dictionaries and a dictionary of
    mapping, return a new About data dictionaries list where the keys
    have been replaced by the About mapped_abouts key if present. Load
    the mapping from the default mnapping.config if an alternate
    mapping dict is not provided.
    """

    if not mapping_file:
        return abouts

    mapping = get_mapping(mapping_file)

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


def format_output(about_data, mapping_file=None):
    """
    Convert the about_data dictionary to an ordered dictionary for saneyaml.dump()
    The ordering should be:

    about_resource
    name
    version <-- if any
    and the rest is the order from the mapping.config file (if any); otherwise alphabetical order.
    """
    mapping_key_order = []
    if mapping_file:
        mapping_key_order = get_mapping(mapping_file).keys()

    priority_keys = ['about_resource', 'name', 'version']
    about_data_keys = []
    order_dict = OrderedDict()
    for key in about_data:
        about_data_keys.append(key)
    if 'about_resource' in about_data_keys:
        order_dict['about_resource'] = about_data['about_resource']

    if 'name' in about_data_keys:
        order_dict['name'] = about_data['name']

    if 'version' in about_data_keys:
        order_dict['version'] = about_data['version']

    if not mapping_key_order:
        for other_key in sorted(about_data_keys):
            if not other_key in priority_keys:
                order_dict[other_key] = about_data[other_key]
    else:
        for key in mapping_key_order:
            if not key in priority_keys and key in about_data_keys:
                order_dict[key] = about_data[key]
        for other_key in sorted(about_data_keys):
            if not other_key in priority_keys and not other_key in mapping_key_order:
                order_dict[other_key] = about_data[other_key]
    return order_dict

# FIXME: why is this used for
def get_about_file_path(location, mapping_file=None):
    """
    Read file at location, return a list of about_file_path.
    """
    afp_list = []
    if location.endswith('.csv'):
        about_data = load_csv(location, mapping_file=mapping_file)
    else:
        about_data = load_json(location)

    for about in about_data:
        afp_list.append(about['about_file_path'])
    return afp_list


def load_csv(location, mapping_file=None):
    """
    Read CSV at `location`, return a list of ordered dictionaries, one
    for each row.
    Use `mapping_file` if provided.
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
    if mapping_file:
        results = apply_mapping(results, mapping_file)
    return results


def load_json(location):
    """
    Read JSON file at `location` and return a list of ordered mappings, one for
    each entry.
    """
    # FIXME: IMHO we should know where the JSON is from and its shape
    # FIXME use: object_pairs_hook=OrderedDict
    with open(location) as json_file:
        results = json.load(json_file)

    # If the loaded JSON is not a list,
    # - JSON output from AboutCode Manager:
    # look for the "components" field as it is the field
    # that contain everything the tool needs and ignore other fields.
    # For instance,
    # {
    #    "aboutcode_manager_notice":"xyz",
    #    "aboutcode_manager_version":"xxx",
    #    "components":
    #    [{
    #        "license_expression":"apache-2.0",
    #        "copyright":"Copyright (c) 2017 nexB Inc.",
    #        "path":"ScanCode",
    #        ...
    #    }]
    # }
    #
    # - JSON output from ScanCode:
    # look for the "files" field as it is the field
    # that contain everything the tool needs and ignore other fields:
    # For instance,
    # {
    #    "scancode_notice":"xyz",
    #    "scancode_version":"xxx",
    #    "files":
    #    [{
    #        "path": "test",
    #        "type": "directory",
    #        "name": "test",
    #        ...
    #    }]
    # }
    #
    # - JSON file that is not produced by scancode or aboutcode toolkit
    # For instance,
    # {
    #    "path": "test",
    #    "type": "directory",
    #    "name": "test",
    #    ...
    # }
    # FIXME: this is too clever and complex... IMHO we should not try to guess the format.
    # instead a command line option should be provided explictly to say what is the format
    if isinstance(results, list):
        results = sorted(results)
    else:
        if u'aboutcode_manager_notice' in results:
            results = results['components']
        elif u'scancode_notice' in results:
            results = results['files']
        else:
            results = [results]
    return results


# FIXME: rename to is_online: BUT do we really need this at all????
def have_network_connection():
    """
    Return True if an HTTP connection to some public web site is possible.
    """
    import socket
    if python2:
        import httplib  # NOQA
    else:
        import http.client as httplib  # NOQA

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
    base_dir = tempfile.mkdtemp(prefix='aboutcode-toolkit-extract-')
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
    Convert a `location` to an absolute Window UNC path to support long paths on
    Windows. Return the location unchanged if not on Windows. See
    https://msdn.microsoft.com/en-us/library/aa365247.aspx
    """
    if on_windows and not location.startswith(UNC_PREFIX):
        if location.startswith(UNC_PREFIX_POSIX):
            return UNC_PREFIX + os.path.abspath(location.strip(UNC_PREFIX_POSIX))
        return UNC_PREFIX + os.path.abspath(location)
    return location


# FIXME: add docstring
def copy_license_notice_files(fields, base_dir, license_notice_text_location, afp):
    lic_name = ''
    for key, value in fields:
        if key == 'license_file' or key == 'notice_file':
            lic_name = value

            from_lic_path = posixpath.join(to_posix(license_notice_text_location), lic_name)
            about_file_dir = os.path.dirname(to_posix(afp)).lstrip('/')
            to_lic_path = posixpath.join(to_posix(base_dir), about_file_dir)

            if on_windows:
                from_lic_path = add_unc(from_lic_path)
                to_lic_path = add_unc(to_lic_path)

            # Strip the white spaces
            from_lic_path = from_lic_path.strip()
            to_lic_path = to_lic_path.strip()

            # Errors will be captured when doing the validation
            if not posixpath.exists(from_lic_path):
                continue

            if not posixpath.exists(to_lic_path):
                os.makedirs(to_lic_path)
            try:
                shutil.copy2(from_lic_path, to_lic_path)
            except Exception as e:
                print(repr(e))
                print('Cannot copy file at %(from_lic_path)r.' % locals())


# FIXME: this is NOT a util but something to move with inventories or a method
# from About objects
def inventory_filter(abouts, filters):
    """
    Return a list of filtered About objects from an `abouts` list of About
    object using the `filters` mapping of:
        {field_name: [acceptable_values, ....]}

    ... such that only the About object that have a field_name with a value that
    matches one of the acceptable values is returned. Other About object are
    filtered out.
    """
    matching_abouts = []
    for about in abouts:
        for field_name, acceptable_values in filters.items():
            # Check if the about object has the filtered attribute and if the
            # attributed value is the same as the defined in the filter
            actual_value = getattr(about, field_name, None)
            if actual_value in acceptable_values and not about in matching_abouts:
                matching_abouts.append(about)
                # FIXME: if it matches once it matches always which is probably not right
                break

    return matching_abouts




# FIXME: we should use a license object instead
def ungroup_licenses(licenses):
    """
    Ungroup multiple licenses information
    """
    lic_key = []
    lic_name = []
    lic_file = []
    lic_url = []
    for lic in licenses:
        if 'key' in lic:
            lic_key.append(lic['key'])
        if 'name' in lic:
            lic_name.append(lic['name'])
        if 'file' in lic:
            lic_file.append(lic['file'])
        if 'url' in lic:
            lic_url.append(lic['url'])
    return lic_key, lic_name, lic_file, lic_url


# FIXME: add docstring
def format_about_dict_for_csv_output(about_dictionary_list):
    csv_formatted_list = []
    file_fields = ['license_file', 'notice_file', 'changelog_file', 'author_file']
    for element in about_dictionary_list:
        row_list = OrderedDict()
        for key in element:
            if element[key]:
                if isinstance(element[key], list):
                    row_list[key] = u'\n'.join((element[key]))
                elif key == u'about_resource' or key in file_fields:
                    row_list[key] = u'\n'.join((element[key].keys()))
                else:
                    row_list[key] = element[key]
        csv_formatted_list.append(row_list)
    return csv_formatted_list


# FIXME: add docstring
def format_about_dict_for_json_output(about_dictionary_list):
    licenses = ['license_key', 'license_name', 'license_file', 'license_url']
    file_fields = ['notice_file', 'changelog_file', 'author_file']
    json_formatted_list = []
    for element in about_dictionary_list:
        row_list = OrderedDict()
        # FIXME: aboid using parallel list... use an object instead
        license_key = []
        license_name = []
        license_file = []
        license_url = []

        for key in element:
            if element[key]:
                # The 'about_resource' is an ordered dict
                if key == 'about_resource':
                    row_list[key] = list(element[key].keys())[0]
                elif key in licenses:
                    if key == 'license_key':
                        license_key = element[key]
                    elif key == 'license_name':
                        license_name = element[key]
                    elif key == 'license_file':
                        license_file = element[key].keys()
                    elif key == 'license_url':
                        license_url = element[key]
                elif key in file_fields:
                    row_list[key] = element[key].keys()
                else:
                    row_list[key] = element[key]

        # Group the same license information in a list
        license_group = list(zip_longest(license_key, license_name, license_file, license_url))
        if license_group:
            licenses_list = []
            for lic_group in license_group:
                lic_dict = OrderedDict()
                if lic_group[0]:
                    lic_dict['key'] = lic_group[0]
                if lic_group[1]:
                    lic_dict['name'] = lic_group[1]
                if lic_group[2]:
                    lic_dict['file'] = lic_group[2]
                if lic_group[3]:
                    lic_dict['url'] = lic_group[3]
                licenses_list.append(lic_dict)
            row_list['licenses'] = licenses_list
        json_formatted_list.append(row_list)
    return json_formatted_list


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


# FIXME: remove and replace by saneyaml
from collections import Hashable

from yaml.reader import Reader
from yaml.scanner import Scanner
from yaml.parser import Parser
from yaml.composer import Composer
from yaml.constructor import Constructor, ConstructorError
from yaml.resolver import Resolver
from yaml.nodes import MappingNode

# FIXME: add docstring
class NoDuplicateConstructor(Constructor):
    def construct_mapping(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(
                None, None,
                "expected a mapping node, but found %s" % node.id,
                node.start_mark)
        mapping = {}
        for key_node, value_node in node.value:
            # keys can be list -> deep
            key = self.construct_object(key_node, deep=True)
            # lists are not hashable, but tuples are
            if not isinstance(key, Hashable):
                if isinstance(key, list):
                    key = tuple(key)

            if sys.version_info.major == 2:
                try:
                    hash(key)
                except TypeError as exc:
                    raise ConstructorError(
                        "while constructing a mapping", node.start_mark,
                        "found unacceptable key (%s)" %
                        exc, key_node.start_mark)
            else:
                if not isinstance(key, Hashable):
                    raise ConstructorError(
                        "while constructing a mapping", node.start_mark,
                        "found unhashable key", key_node.start_mark)

            value = self.construct_object(value_node, deep=deep)

            # Actually do the check.
            if key in mapping:
                raise KeyError("Got duplicate key: {!r}".format(key))

            mapping[key] = value
        return mapping


# FIXME: add docstring
class NoDuplicateLoader(Reader, Scanner, Parser, Composer, NoDuplicateConstructor, Resolver):
    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        NoDuplicateConstructor.__init__(self)
        Resolver.__init__(self)
