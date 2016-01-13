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

from __future__ import print_function

import os
import sys
import ntpath
import posixpath
import optparse
from os.path import dirname
from os.path import abspath
from os.path import join
import errno


"""
Utility functions
"""


on_windows = 'win32' in sys.platform


def is_about_file(path):
    """
    Return True if the path represents a valid ABOUT file name.
    """
    return path.lower().endswith('.about')


def path_exists(location):
    """
    Return True if the path exists.
    """
    return location and  os.path.exists(abspath(location))


def canonical_path(location):
    """
    Return a fully resolved absolute (possible UNC'ed) path for location.
    """
    # path need to be unicode on Windows to ensure proper operations
    if on_windows:
        location = unicode(location)

    location = os.path.expanduser(location)
    location = os.path.expandvars(location)
    location = add_unc(location)
    location = os.path.normpath(location)
    location = os.path.abspath(location)
    return location

def posix_path(path):
    """
    Return a path using POSIX path separators given a path that may
    contain POSIX or windows separators, converting \ to /.
    """
    return path.replace(ntpath.sep, posixpath.sep)


UNC_PREFIX = u'\\\\?\\'
UNC_PREFIX_POSIX = posix_path(UNC_PREFIX)
UNC_PREFIXES = (UNC_PREFIX_POSIX, UNC_PREFIX,)

def add_unc(location):
    """
    Convert a location to an absolute Window UNC path to support long paths on
    Windows. Return the location unchanged if not on Windows. See
    https://msdn.microsoft.com/en-us/library/aa365247.aspx
    """
    if on_windows and not location.startswith(UNC_PREFIXES):
        return UNC_PREFIX + os.path.abspath(location)
    return location


def remove_unc(location):
    """
    Return location with leading UNC prefix removed if present.
    """
    if on_windows and location.startswith(UNC_PREFIXES):
        return location[len(UNC_PREFIX):]
    return location


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


class ImprovedFormatter(optparse.IndentedHelpFormatter):
    """
    Improved formatter.
    """
    def _format_text(self, text):
        """
        Overridden to allow description to be printed without
        modification.
        """
        return text

    def format_option(self, option):
        """
        Overridden to allow options help text to be printed without
        modification.
        """
        result = []
        opts = self.option_strings[option]
        opt_width = self.help_position - self.current_indent - 2
        if len(opts) > opt_width:
            opts = '%*s%s\n' % (self.current_indent, '', opts)
            indent_first = self.help_position
        else:  # start help on same line as opts
            opts = '%*s%-*s  ' % (self.current_indent, '',
                                  opt_width, opts)
            indent_first = 0
        result.append(opts)
        if option.help:
            help_text = self.expand_default(option)
            help_lines = help_text.split('\n')
            # help_lines = textwrap.wrap(help_text, self.help_width)
            result.append('%*s%s\n' % (indent_first, '', help_lines[0]))
            result.extend(['%*s%s\n' % (self.help_position, '', line)
                           for line in help_lines[1:]])
        elif opts[-1] != '\n':
            result.append('\n')
        return ''.join(result)


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


def resource_name(resource_path):
    """
    Return a resource name based on a posix path (either the filename or
    directory name). Recurse to handle paths that ends with a path separator.
    """
    left, right = posixpath.split(resource_path)
    if right:
        return right.strip()
    elif left and left != '/':
        # recurse for directories that end up with a /
        return resource_name(left)
    else:
        return ''

