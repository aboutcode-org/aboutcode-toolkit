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

"""
AboutCode toolkit is a tool to process ABOUT files. ABOUT files are
small text files that document the provenance (aka. the origin and
license) of software components as well as the essential obligation
such as attribution/credits and source code redistribution. See the
ABOUT spec at http://dejacode.org.

AboutCode toolkit reads and validates ABOUT files and collect software
components inventories.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
import codecs
import json
import os
import posixpath
from posixpath import dirname

import yaml
import re
import sys

if sys.version_info[0] < 3:  # Python 2
    import backports.csv as csv  # NOQA
    from itertools import izip_longest as zip_longest  # NOQA
    from urlparse import urljoin, urlparse  # NOQA
    from urllib2 import urlopen, Request, HTTPError  # NOQA
else:  # Python 3
    basestring = str  # NOQA
    import csv  # NOQA
    from itertools import zip_longest  # NOQA
    from urllib.parse import urljoin, urlparse  # NOQA
    from urllib.request import urlopen, Request  # NOQA
    from urllib.error import HTTPError  # NOQA

from license_expression import Licensing

from attributecode import CRITICAL
from attributecode import ERROR
from attributecode import INFO
from attributecode import WARNING
from attributecode import api
from attributecode import Error
from attributecode import saneyaml
from attributecode import util
from attributecode.util import add_unc
from attributecode.util import copy_license_notice_files
from attributecode.util import on_windows
from attributecode.util import ungroup_licenses
from attributecode.util import UNC_PREFIX


class Field(object):
    """
    An ABOUT file field. The initial value is a string. Subclasses can and
    will alter the value type as needed.
    """

    def __init__(self, name=None, value=None, required=False, present=False):
        # normalized names are lowercased per specification
        self.name = name
        # save this and do not mutate it afterwards
        if isinstance(value, basestring):
            self.original_value = value
        elif value:
            self.original_value = repr(value)
        else:
            self.original_value = value

        # can become a string, list or OrderedDict() after validation
        self.value = value or self.default_value()

        self.required = required
        # True if the field is present in an About object
        self.present = present

        self.errors = []

    def default_value(self):
        return ''

    def validate(self, *args, **kwargs):
        """
        Validate and normalize thyself. Return a list of errors.
        """
        errors = []
        name = self.name
        self.value = self.default_value()
        if not self.present:
            # required fields must be present
            if self.required:
                msg = u'Field %(name)s is required'
                errors.append(Error(CRITICAL, msg % locals()))
                return errors
        else:
            # present fields should have content ...
            # The boolean value can be True, False and None
            # The value True or False is the content of boolean fields
            if not self.has_content:
                # ... especially if required
                if self.required:
                    msg = u'Field %(name)s is required and empty'
                    severity = CRITICAL
                else:
                    severity = WARNING
                    msg = u'Field %(name)s is present but empty'
                errors.append(Error(severity, msg % locals()))
            else:
                # present fields with content go through validation...
                # first trim any trailing spaces on each line
                if isinstance(self.original_value, basestring):
                    value = '\n'.join(s.rstrip() for s
                                      in self.original_value.splitlines(False))
                    # then strip leading and trailing spaces
                    value = value.strip()
                else:
                    value = self.original_value
                self.value = value
                try:
                    validation_errors = self._validate(*args, **kwargs)
                    errors.extend(validation_errors)
                except Exception as e:
                    emsg = repr(e)
                    msg = u'Error validating field %(name)s: %(value)r: %(emsg)r'
                    errors.append(Error(CRITICAL, msg % locals()))
                    raise

        # set or reset self
        self.errors = errors
        return errors

    def _validate(self, *args, **kwargs):
        """
        Validate and normalize thyself. Return a list of errors.
        Subclasses should override as needed.
        """
        return []

    def serialize(self):
        """
        Return a unicode serialization of self in the ABOUT format.
        """
        name = self.name
        value = self.serialized_value() or u''
        if self.has_content or self.value:
            value = value.splitlines(True)
            # multi-line
            if len(value) > 1:
                # This code is used to read the YAML's multi-line format in
                # ABOUT files
                # (Test: test_loads_dumps_is_idempotent)
                if value[0].strip() == u'|' or value[0].strip() == u'>':
                    value = u' '.join(value)
                else:
                    # Insert '|' as the indicator for multi-line follow by a
                    # newline character
                    value.insert(0, u'|\n')
                    # insert 4 spaces for newline values
                    value = u'    '.join(value)
            else:
                # See https://github.com/nexB/aboutcode-toolkit/issues/323
                # The yaml.load() will throw error if the parsed value
                # contains ': ' character. A work around is to put a pipe, '|'
                # to indicate the whole value as a string
                if value and ': ' in value[0]:
                    value.insert(0, u'|\n')
                    # insert 4 spaces for newline values
                    value = u'    '.join(value)
                else:
                    value = u''.join(value)

        serialized = u'%(name)s:' % locals()
        if value:
            serialized += ' ' + '%(value)s' % locals()
        return serialized

    def serialized_value(self):
        """
        Return a unicode serialization of self in the ABOUT format.
        Does not include a white space for continuations.
        """
        return self._serialized_value() or u''

    @property
    def has_content(self):
        return self.original_value

    def __repr__(self):
        name = self.name
        value = self.value
        required = self.required
        has_content = self.has_content
        present = self.present
        r = ('Field(name=%(name)r, value=%(value)r, required=%(required)r, present=%(present)r)')
        return r % locals()

    def __eq__(self, other):
        """
        Equality based on string content value, ignoring spaces.
        """
        return (isinstance(other, self.__class__)
                and self.name == other.name
                and self.value == other.value)


class StringField(Field):
    """
    A field containing a string value possibly on multiple lines.
    The validated value is a string.
    """
    def _validate(self, *args, **kwargs):
        errors = super(StringField, self)._validate(*args, ** kwargs)
        return errors

    def _serialized_value(self):
        return self.value if self.value else u''

    def __eq__(self, other):
        """
        Equality based on string content value, ignoring spaces
        """
        if not (isinstance(other, self.__class__)
                and self.name == other.name):
            return False

        if self.value == other.value:
            return True

        # compare values stripped from spaces. Empty and None are equal
        if self.value:
            sval = u''.join(self.value.split())
        if not sval:
            sval = None

        if other.value:
            oval = u''.join(other.value.split())
        if not oval:
            oval = None

        if sval == oval:
            return True


class SingleLineField(StringField):
    """
    A field containing a string value on a single line. The validated value is
    a string.
    """
    def _validate(self, *args, **kwargs):
        errors = super(SingleLineField, self)._validate(*args, ** kwargs)
        if self.value and isinstance(self.value, basestring) and '\n' in self.value:
            name = self.name
            value = self.original_value
            msg = (u'Field %(name)s: Cannot span multiple lines: %(value)s'
                   % locals())
            errors.append(Error(ERROR, msg))
        return errors


class ListField(StringField):
    """
    A field containing a list of string values, one per line. The validated
    value is a list.
    """
    def default_value(self):
        return []

    def _validate(self, *args, **kwargs):
        errors = super(ListField, self)._validate(*args, ** kwargs)

        # reset
        self.value = []

        if isinstance(self.original_value, basestring):
            values = self.original_value.splitlines(False)
        elif isinstance(self.original_value, list):
            values = self.original_value
        else:
            values = [repr(self.original_value)]

        for val in values:
            if isinstance(val, basestring):
                val = val.strip()
            if not val:
                name = self.name
                msg = (u'Field %(name)s: ignored empty list value'
                       % locals())
                errors.append(Error(INFO, msg))
                continue
            # keep only unique and report error for duplicates
            if val not in self.value:
                self.value.append(val)
            else:
                name = self.name
                msg = (u'Field %(name)s: ignored duplicated list value: '
                       '%(val)r' % locals())
                errors.append(Error(WARNING, msg))
        return errors

    def _serialized_value(self):
        return self.value if self.value else u''

    def __eq__(self, other):
        """
        Equality based on sort-insensitive values
        """

        if not (isinstance(other, self.__class__)
                and self.name == other.name):
            return False

        if self.value == other.value:
            return True

        # compare values stripped from spaces.
        sval = []
        if self.value and isinstance(self.value, list):
            sval = sorted(self.value)

        oval = []
        if other.value and isinstance(other.value, list):
            oval = sorted(other.value)

        if sval == oval:
            return True

class UrlListField(ListField):
    """
    A URL field. The validated value is a list of URLs.
    """
    def _validate(self, *args, **kwargs):
        """
        Check that URLs are valid. Return a list of errors.
        """
        errors = super(UrlListField, self)._validate(*args, ** kwargs)
        name = self.name
        val = self.value
        for url in val:
            if not self.is_valid_url(url):
                msg = (u'Field %(name)s: Invalid URL: %(val)s' % locals())
                errors.append(Error(WARNING, msg))
        return errors

    @staticmethod
    def is_valid_url(url):
        """
        Return True if a URL is valid.
        """
        scheme, netloc, _path, _p, _q, _frg = urlparse(url)
        valid = scheme in ('http', 'https', 'ftp') and netloc
        return valid


class UrlField(StringField):
    """
    A URL field. The validated value is a URL.
    """
    def _validate(self, *args, **kwargs):
        """
        Check that URL is valid. Return a list of errors.
        """
        errors = super(UrlField, self)._validate(*args, ** kwargs)
        name = self.name
        val = self.value
        if not self.is_valid_url(val):
            msg = (u'Field %(name)s: Invalid URL: %(val)s' % locals())
            errors.append(Error(WARNING, msg))
        return errors

    @staticmethod
    def is_valid_url(url):
        """
        Return True if a URL is valid.
        """
        scheme, netloc, _path, _p, _q, _frg = urlparse(url)
        valid = scheme in ('http', 'https', 'ftp') and netloc
        return valid


class PathField(ListField):
    """
    A field pointing to one or more paths relative to the ABOUT file location.
    The validated value is an ordered mapping of path->location or None.
    The paths can also be resolved
    """
    def default_value(self):
        return {}

    def _validate(self, *args, **kwargs):
        """
        Ensure that paths point to existing resources. Normalize to posix
        paths. Return a list of errors.

        base_dir is the directory location of the ABOUT file used to resolve
        relative paths to actual file locations.
        """
        errors = super(PathField, self)._validate(*args, ** kwargs)
        self.about_file_path = kwargs.get('about_file_path')
        self.running_inventory = kwargs.get('running_inventory')
        self.base_dir = kwargs.get('base_dir')
        self.license_notice_text_location = kwargs.get('license_notice_text_location')

        if self.base_dir:
            self.base_dir = util.to_posix(self.base_dir)

        name = self.name

        # FIXME: Why is the PathField an ordered dict?
        # mapping of normalized paths to a location or None
        paths = OrderedDict()

        for path in self.value:
            path = path.strip()
            path = util.to_posix(path)

            # normalize eventual / to .
            # and a succession of one or more ////// to . too
            if path.strip() and not path.strip(posixpath.sep):
                path = '.'

            # removing leading and trailing path separator
            # path are always relative
            path = path.strip(posixpath.sep)

            # the license files, if need to be copied, are located under the path
            # set from the 'license-text-location' option, so the tool should check
            # at the 'license-text-location' instead of the 'base_dir'
            if not (self.base_dir or self.license_notice_text_location):
                msg = (u'Field %(name)s: Unable to verify path: %(path)s:'
                       u' No base directory provided' % locals())
                errors.append(Error(ERROR, msg))
                location = None
                paths[path] = location
                continue

            if self.license_notice_text_location:
                location = posixpath.join(self.license_notice_text_location, path)
            else:
                # The 'about_resource' should be a joined path with
                # the 'about_file_path' and the 'base_dir
                if not self.running_inventory and self.about_file_path:
                    # Get the parent directory of the 'about_file_path'
                    afp_parent = posixpath.dirname(self.about_file_path)

                    # Create a relative 'about_resource' path by joining the
                    # parent of the 'about_file_path' with the value of the
                    # 'about_resource'
                    arp = posixpath.join(afp_parent, path)
                    normalized_arp = posixpath.normpath(arp).strip(posixpath.sep)
                    location = posixpath.join(self.base_dir, normalized_arp)
                else:
                    location = posixpath.join(self.base_dir, path)

            location = util.to_native(location)
            location = os.path.abspath(os.path.normpath(location))
            location = util.to_posix(location)
            location = add_unc(location)

            if not os.path.exists(location):
                # We don't want to show the UNC_PREFIX in the error message
                location = util.to_posix(location.strip(UNC_PREFIX))
                msg = (u'Field %(name)s: Path %(location)s not found'
                       % locals())
                # We want to show INFO error for 'about_resource'
                if name == u'about_resource':
                    errors.append(Error(INFO, msg))
                else:
                    errors.append(Error(CRITICAL, msg))
                location = None

            paths[path] = location

        self.value = paths
        return errors


class AboutResourceField(PathField):
    """
    Special field for about_resource. self.resolved_paths contains a list of
    the paths resolved relative to the about file path.
    """
    def __init__(self, *args, ** kwargs):
        super(AboutResourceField, self).__init__(*args, ** kwargs)
        self.resolved_paths = []

    def _validate(self, *args, **kwargs):
        errors = super(AboutResourceField, self)._validate(*args, ** kwargs)
        return errors

    def resolve(self, about_file_path):
        """
        Resolve resource paths relative to an ABOUT file path.
        Set a list attribute on self called resolved_paths
        """
        self.resolved_paths = []
        if not about_file_path:
            # FIXME: should we return an info or warning?
            # The existence of about_file_path has been checked in the load_inventory()
            return
        base_dir = posixpath.dirname(about_file_path).strip(posixpath.sep)
        for path in self.value.keys():
            resolved = posixpath.join(base_dir, path)
            resolved = posixpath.normpath(resolved)
            self.resolved_paths.append(resolved)


class FileTextField(PathField):
    """
    A path field pointing to one or more text files such as license files.
    The validated value is an ordered mapping of path->Text or None if no
    location or text could not be loaded.
    """
    def _validate(self, *args, **kwargs):
        """
        Load and validate the texts referenced by paths fields. Return a list
        of errors. base_dir is the directory used to resolve a file location
        from a path.
        """

        errors = super(FileTextField, self)._validate(*args, ** kwargs)
        super(FileTextField, self)._validate(*args, ** kwargs)

        # a FileTextField is a PathField
        # self.value is a paths to location ordered mapping
        # we will replace the location with the text content
        name = self.name
        for path, location in self.value.items():
            if not location:
                # do not try to load if no location
                # errors about non existing locations are PathField errors
                # already collected.
                continue
            try:
                # TODO: we have lots the location by replacing it with a text
                location = add_unc(location)
                with codecs.open(location, encoding='utf-8', errors='ignore') as txt:
                    text = txt.read()
                self.value[path] = text
            except Exception as e:
                # only keep the first 100 char of the exception
                emsg = repr(e)[:100]
                msg = (u'Field %(name)s: Failed to load text at path: '
                       u'%(path)s '
                       u'with error: %(emsg)s' % locals())
                errors.append(Error(ERROR, msg))
        # set or reset self
        self.errors = errors
        return errors


class BooleanField(SingleLineField):
    """
    An flag field with a boolean value. Validated value is False, True or None.
    """
    def default_value(self):
        return None

    true_flags = ('yes', 'y', 'true', 'x')
    false_flags = ('no', 'n', 'false')
    flag_values = true_flags + false_flags

    def _validate(self, *args, **kwargs):
        """
        Check that flag are valid. Convert flags to booleans. Default flag to
        False. Return a list of errors.
        """
        errors = super(BooleanField, self)._validate(*args, ** kwargs)
        self.about_file_path = kwargs.get('about_file_path')
        flag = self.get_flag(self.original_value)
        if flag is False:
            name = self.name
            val = self.original_value
            about_file_path = self.about_file_path
            flag_values = self.flag_values
            msg = (u'Path: %(about_file_path)s - Field %(name)s: Invalid flag value: %(val)r is not '
                   u'one of: %(flag_values)s' % locals())
            errors.append(Error(ERROR, msg))
            self.value = None
        elif flag is None:
            name = self.name
            msg = (u'Field %(name)s: field is empty. '
                   u'Defaulting flag to no.' % locals())
            errors.append(Error(INFO, msg))
            self.value = None
        else:
            if flag == u'yes' or flag is True:
                self.value = True
            else:
                self.value = False
        return errors

    def get_flag(self, value):
        """
        Return a normalized existing flag value if found in the list of
        possible values or None if empty or False if not found or original value
        if it is not a boolean value
        """
        if value is None or value == '':
            return None

        if isinstance(value, bool):
            return value
        else:
            if isinstance(value, basestring):
                value = value.strip()
                if not value:
                    return None

                value = value.lower()
                if value in self.flag_values:
                    if value in self.true_flags:
                        return u'yes'
                    else:
                        return u'no'
                else:
                    return False
            else:
                return False

    @property
    def has_content(self):
        """
        Return true if it has content regardless of what value, False otherwise
        """
        if self.original_value:
            return True
        return False

    def _serialized_value(self):
        # default normalized values for serialization
        if self.value:
            return u'yes'
        elif self.value is False:
            return u'no'
        else:
            # self.value is None
            # TODO: should we serialize to No for None???
            return u''

    def __eq__(self, other):
        """
        Boolean equality
        """
        return (isinstance(other, self.__class__)
                and self.name == other.name
                and self.value == other.value)


def validate_fields(fields, about_file_path, running_inventory, base_dir,
                    license_notice_text_location=None):
    """
    Validate a sequence of Field objects. Return a list of errors.
    Validation may update the Field objects as needed as a side effect.
    """
    errors = []
    for f in fields:
        val_err = f.validate(
            base_dir=base_dir,
            about_file_path=about_file_path,
            running_inventory=running_inventory,
            license_notice_text_location=license_notice_text_location,
        )
        errors.extend(val_err)
    return errors


class About(object):
    """
    Represent an ABOUT file and functions to parse and validate a file.
    """
    # special names, used only when serializing lists of ABOUT files to CSV or
    # similar

    # name of the attribute containing the relative ABOUT file path
    about_file_path_attr = 'about_file_path'

    # name of the attribute containing the resolved relative Resources paths
    about_resource_path_attr = 'about_resource_path'

    # Required fields
    required_fields = [about_file_path_attr, 'name']

    def create_fields(self):
        """
        Create fields in an ordered mapping to keep a standard ordering. We
        could use a metaclass to track ordering django-like but this approach
        is simpler.
        """
        self.fields = OrderedDict([
            # ('about_resource', ListField(required=True)),
            # ('about_resource', AboutResourceField(required=True)),
            ('about_resource', AboutResourceField(required=True)),
            ('name', SingleLineField(required=True)),

            ('version', SingleLineField()),
            ('download_url', UrlField()),
            ('description', StringField()),
            ('homepage_url', UrlField()),
            ('notes', StringField()),

            ('license_expression', StringField()),
            ('license_key', ListField()),
            ('license_name', ListField()),
            ('license_file', FileTextField()),
            ('license_url', UrlListField()),
            ('copyright', StringField()),
            ('notice_file', FileTextField()),
            ('notice_url', UrlField()),

            ('redistribute', BooleanField()),
            ('attribute', BooleanField()),
            ('track_changes', BooleanField()),
            ('modified', BooleanField()),
            ('internal_use_only', BooleanField()),

            ('changelog_file', FileTextField()),

            ('owner', StringField()),
            ('owner_url', UrlField()),
            ('contact', StringField()),
            ('author', ListField()),
            ('author_file', FileTextField()),

            ('vcs_tool', SingleLineField()),
            ('vcs_repository', SingleLineField()),
            ('vcs_path', SingleLineField()),
            ('vcs_tag', SingleLineField()),
            ('vcs_branch', SingleLineField()),
            ('vcs_revision', SingleLineField()),

            ('checksum_md5', SingleLineField()),
            ('checksum_sha1', SingleLineField()),
            ('checksum_sha256', SingleLineField()),
            ('spec_version', SingleLineField()),
        ])

        for name, field in self.fields.items():
            # we could have a hack to get the actual field name
            # but setting an attribute is explicit and cleaner
            field.name = name
            setattr(self, name, field)

    def __init__(self, location=None, about_file_path=None, use_mapping=False, mapping_file=None):
        self.create_fields()
        self.custom_fields = OrderedDict()

        self.errors = []
        # about file path relative to the root of an inventory using posix
        # path separators
        self.about_file_path = about_file_path

        # os native absolute location, using posix path separators
        self.location = location
        self.base_dir = None
        if self.location:
            self.base_dir = os.path.dirname(location)
            self.load(location, use_mapping, mapping_file)

    def __repr__(self):
        return repr(self.all_fields())

    def __eq__(self, other):
        """
        Equality based on fields and custom_fields., i.e. content.
        """
        return (isinstance(other, self.__class__)
                and self.fields == other.fields
                and self.custom_fields == other.custom_fields)

    @staticmethod
    def attribution_fields(fields):
        """
        Return attrib-only fields
        """
        attrib_fields = ['name',
                         'version',
                         'license_key',
                         'license_name',
                         'license_file',
                         'license_url',
                         'copyright',
                         'notice_file',
                         'notice_url',
                         'redistribute',
                         'attribute',
                         'track_changes',
                         'modified',
                         'changelog_file',
                         'owner',
                         'author']

        return OrderedDict([(n, o) for n, o in fields.items()
                            if n in attrib_fields])

    def same_attribution(self, other):
        """
        Equality based on attribution-related fields.
        """
        return (isinstance(other, self.__class__)
                and self.attribution_fields(self.fields) == self.attribution_fields(other.fields))

    def resolved_resources_paths(self):
        """
        Return a serialized string of resolved resource paths, one per line.
        """
        abrf = self.about_resource_path
        abrf.resolve(self.about_file_path)
        return u'\n'.join(abrf.resolved_paths)

    def all_fields(self, with_absent=True, with_empty=True):
        """
        Return the list of all Field objects.
        If with_absent, include absent (not present) fields.
        If with_empty, include empty fields.
        """
        all_fields = []
        bool_fields = ['redistribute', 'attribute', 'track_changes', 'modified']
        for field in list(self.fields.values()) + list(self.custom_fields.values()):
            if field.required:
                all_fields.append(field)
            # TODO: The following code need refactor
            else:
                if with_absent:
                    all_fields.append(field)
                elif field.present:
                    if with_empty:
                        all_fields.append(field)
                    elif field.present and field.value:
                        all_fields.append(field)
                    elif field.name in bool_fields:
                        # Check is the value valid
                        if not field.value == None:
                            all_fields.append(field)
                else:
                    if field.present:
                        if not field.value:
                            if with_empty:
                                all_fields.append(field)
                        else:
                            all_fields.append(field)
                    else:
                        if with_absent:
                            all_fields.append(field)
        return all_fields

    def as_dict(self, with_paths=False, with_absent=True, with_empty=True):
        """
        Return all the standard fields and customer-defined fields of this
        About object in an ordered mapping.
        If with_paths, include special paths attributes.
        If with_absent, include absent (not present) fields.
        If with_empty, include empty fields.
        """
        as_dict = OrderedDict()
        if with_paths:
            afpa = self.about_file_path_attr
            as_dict[afpa] = self.about_file_path

        for field in self.all_fields(with_absent=with_absent,
                                     with_empty=with_empty):
            as_dict[field.name] = field.serialized_value()
        return as_dict

    def hydrate(self, fields, use_mapping=False, mapping_file=None):
        """
        Process an iterable of field (name, value) tuples. Update or create
        Fields attributes and the fields and custom fields dictionaries.
        Return a list of errors.
        """
        errors = []
        seen_fields = OrderedDict()

        mapping = {}
        if use_mapping or mapping_file:
            mapping = util.get_mapping(mapping_file)
        for name, value in fields:
            orig_name = name
            name = name.lower()
            previous_value = seen_fields.get(name)
            if previous_value:
                if value != previous_value:
                    msg = (u'Field %(orig_name)s is a duplicate. '
                           u'Original value: "%(previous_value)s" '
                           u'replaced with: "%(value)s"')
                    errors.append(Error(WARNING, msg % locals()))
                else:
                    msg = (u'Field %(orig_name)s is a duplicate '
                           u'with the same value as before.')
                    errors.append(Error(INFO, msg % locals()))

            seen_fields[name] = value

            standard_field = self.fields.get(name)
            if standard_field:
                standard_field.original_value = value
                standard_field.value = value
                standard_field.present = True
                continue

            if not use_mapping and not mapping_file:
                if not name == self.about_file_path_attr:
                    msg = (u'Field %(orig_name)s is not a supported field and is ignored.')
                    errors.append(Error(INFO, msg % locals()))
                continue

            if name not in mapping.keys():
                msg = (u'Field %(orig_name)s is not a supported field and is not ' +
                       u'defined in the mapping file. This field is ignored.')
                errors.append(Error(INFO, msg % locals()))
                continue

            # this is a special attribute
            if name == self.about_file_path_attr:
                setattr(self, self.about_file_path_attr, value)
                continue

            # this is a special attribute, skip entirely
            if name == self.about_resource_path_attr:
                continue

            msg = (u'Field %(orig_name)s is a custom field')
            errors.append(Error(INFO, msg % locals()))
            custom_field = self.custom_fields.get(name)
            if custom_field:
                custom_field.original_value = value
                custom_field.value = value
                custom_field.present = True
                continue

            if name in dir(self):
                msg = (u'Field %(orig_name)s has an '
                       u'illegal reserved name')
                errors.append(Error(ERROR, msg % locals()))
                continue

            # custom fields are always handled as StringFields
            custom_field = StringField(name=name,
                                       value=value,
                                       present=True)
            self.custom_fields[name] = custom_field
            try:
                setattr(self, name, custom_field)
            except:
                # The intended captured error message should display
                # the line number of where the invalid line is,
                # but I am not able to get the line number from
                # the original code. By-passing the line number
                # for now.
                # msg = u'Invalid line: %(line)d: %(orig_name)r'
                msg = u'Invalid line: %(orig_name)r: ' % locals()
                msg += u'%s' % custom_field.value
                errors.append(Error(CRITICAL, msg))
        return errors

    def process(self, fields, about_file_path, running_inventory=False,
                base_dir=None, license_notice_text_location=None,
                use_mapping=False, mapping_file=None):
        """
        Hydrate and validate a sequence of field name/value tuples from an
        ABOUT file. Return a list of errors.
        """
        self.base_dir = base_dir
        self.license_notice_text_location = license_notice_text_location
        afp = self.about_file_path
        errors = []
        hydratation_errors = self.hydrate(fields, use_mapping=use_mapping, mapping_file=mapping_file)
        errors.extend(hydratation_errors)

        # We want to copy the license_files before the validation
        if license_notice_text_location:
            copy_license_notice_files(
                fields, base_dir, license_notice_text_location, afp)
        # we validate all fields, not only these hydrated
        all_fields = self.all_fields()
        validation_errors = validate_fields(
            all_fields, about_file_path, running_inventory,
            self.base_dir, self.license_notice_text_location)
        errors.extend(validation_errors)

        # do not forget to resolve about resource paths The
        # 'about_resource' field is now a ListField and those do not
        # need to resolve
        # self.about_resource.resolve(self.about_file_path)
        return errors

    def load(self, location, use_mapping=False, mapping_file=None):
        """
        Read, parse and process the ABOUT file at location.
        Return a list of errors and update self with errors.
        """
        self.location = location
        loc = util.to_posix(location)
        base_dir = posixpath.dirname(loc)
        errors = []
        try:
            loc = add_unc(loc)
            with codecs.open(loc, encoding='utf-8') as txt:
                input_text = txt.read()
            # Check for duplicated key
            yaml.load(input_text, Loader=util.NoDuplicateLoader)
            """
            The running_inventory defines if the current process is 'inventory' or not.
            This is used for the validation of the path of the 'about_resource'.
            In the 'inventory' command, the code will use the parent of the about_file_path
            location and join with the 'about_resource' for the validation.
            On the other hand, in the 'gen' command, the code will use the
            generated location (aka base_dir) along with the parent of the about_file_path
            and then join with the 'about_resource'
            """
            running_inventory = True
            # wrap the value of the boolean field in quote to avoid
            # automatically conversion from yaml.load
            input = util.wrap_boolean_value(input_text)  # NOQA
            errs = self.load_dict(saneyaml.load(input), base_dir, running_inventory, use_mapping, mapping_file)
            errors.extend(errs)
        except Exception as e:
            msg = 'Cannot load invalid ABOUT file: %(location)r: %(e)r\n' + str(e)
            errors.append(Error(CRITICAL, msg % locals()))

        self.errors = errors
        return errors

    def load_dict(self, fields_dict, base_dir, running_inventory=False,
                  use_mapping=False, mapping_file=None,
                  license_notice_text_location=None, with_empty=True):
        """
        Load the ABOUT file from a fields name/value mapping.
        If with_empty, create fields with no value for empty fields.
        Return a list of
        errors.
        """
        fields = list(fields_dict.items())
        about_file_path = self.about_file_path
        if not with_empty:
            fields = [(n, v) for n, v in fields_dict.items() if v]
        for key, value in fields:
            if key == u'licenses':
                lic_key, lic_name, lic_file, lic_url = ungroup_licenses(value)
                if lic_key:
                    fields.append(('license_key', lic_key))
                if lic_name:
                    fields.append(('license_name', lic_name))
                if lic_file:
                    fields.append(('license_file', lic_file))
                if lic_url:
                    fields.append(('license_url', lic_url))
                # The licenses field has been ungrouped and can be removed.
                # Otherwise, it will gives the following INFO level error
                # 'Field licenses is not a supported field and is ignored.'
                licenses_field = (key, value)
                fields.remove(licenses_field)
        errors = self.process(
            fields, about_file_path, running_inventory, base_dir,
            license_notice_text_location, use_mapping, mapping_file)
        self.errors = errors
        return errors


    def dumps(self, use_mapping=False, mapping_file=False, with_absent=False, with_empty=True):
        """
        Return self as a formatted ABOUT string.
        If with_absent, include absent (not present) fields.
        If with_empty, include empty fields.
        """
        about_data = {}
        # Group the same license information (name, url, file) together
        license_key = []
        license_name = []
        license_file = []
        license_url = []
        file_fields = ['about_resource', 'notice_file', 'changelog_file', 'author_file']
        bool_fields = ['redistribute', 'attribute', 'track_changes', 'modified']
        for field in self.all_fields(with_absent, with_empty):
            if field.name == 'license_key' and field.value:
                license_key = field.value
            elif field.name == 'license_name' and field.value:
                license_name = field.value
            elif field.name == 'license_file' and field.value:
                license_file = field.value.keys()
            elif field.name == 'license_url' and field.value:
                license_url = field.value
            # No multiple 'about_resource' reference supported.
            # Take the first element (should only be one) in the list for the
            # value of 'about_resource'
            elif field.name in file_fields and field.value:
                about_data[field.name] = list(field.value.keys())[0]
            else:
                if field.value or (field.name in bool_fields and not field.value == None):
                    about_data[field.name] = field.value

        # Group the same license information in a list
        license_group = list(zip_longest(license_key, license_name, license_file, license_url))
        for lic_group in license_group:
            lic_dict = {}
            if lic_group[0]:
                lic_dict['key'] = lic_group[0]
            if lic_group[1]:
                lic_dict['name'] = lic_group[1]
            if lic_group[2]:
                lic_dict['file'] = lic_group[2]
            if lic_group[3]:
                lic_dict['url'] = lic_group[3]
            about_data.setdefault('licenses', []).append(lic_dict)
        formatted_about_data = util.format_output(about_data, use_mapping, mapping_file)
        return saneyaml.dump(formatted_about_data)

    def dump(self, location, use_mapping=False, mapping_file=False, with_absent=False, with_empty=True):
        """
        Write formatted ABOUT representation of self to location.
        If with_absent, include absent (not present) fields.
        If with_empty, include empty fields.
        """
        loc = util.to_posix(location)
        parent = posixpath.dirname(loc)

        if not posixpath.exists(parent):
            os.makedirs(add_unc(parent))

        about_file_path = loc
        if not about_file_path.endswith('.ABOUT'):
            if about_file_path.endswith('/'):
                about_file_path = util.to_posix(os.path.join(parent, os.path.basename(parent)))
            about_file_path += '.ABOUT'
        if on_windows:
            about_file_path = add_unc(about_file_path)
        with codecs.open(about_file_path, mode='wb', encoding='utf-8') as dumped:
            dumped.write(self.dumps(use_mapping, mapping_file, with_absent, with_empty))

    def dump_lic(self, location, license_dict):
        """
        Write LICENSE files and return the a list of key, name, context and the url
        as these information are needed for the ABOUT file
        """
        license_name = license_context = license_url = ''
        loc = util.to_posix(location)
        parent = posixpath.dirname(loc)
        license_key_name_context_url = []

        if not posixpath.exists(parent):
            os.makedirs(add_unc(parent))

        if self.license_expression.present and not self.license_file.present:
            special_char_in_expression, lic_list = parse_license_expression(self.license_expression.value)
            self.license_key.value = lic_list
            self.license_key.present = True
            if not special_char_in_expression:
                for lic_key in lic_list:
                    try:
                        if license_dict[lic_key]:
                            license_path = posixpath.join(parent, lic_key)
                            license_path += u'.LICENSE'
                            license_path = add_unc(license_path)
                            license_name, license_context, license_url = license_dict[lic_key]
                            license_info = (lic_key, license_name, license_context, license_url)
                            license_key_name_context_url.append(license_info)
                            with codecs.open(license_path, mode='wb', encoding='utf-8') as lic:
                                lic.write(license_context)
                    except:
                        pass
        return license_key_name_context_url


# valid field name
field_name = r'(?P<name>[a-z][0-9a-z_]*)'

valid_field_name = re.compile(field_name, re.UNICODE | re.IGNORECASE).match

# line in the form of "name: value"
field_declaration = re.compile(
    r'^'
    +field_name +
    r'\s*:\s*'
    r'(?P<value>.*)'
    r'\s*$'
    , re.UNICODE | re.IGNORECASE
    ).match


# continuation line in the form of " value"
continuation = re.compile(
    r'^'
    r' '
    r'(?P<value>.*)'
    r'\s*$'
    , re.UNICODE | re.IGNORECASE
    ).match


def parse(lines):
    """
    Parse a list of unicode lines from an ABOUT file. Return a
    list of errors found during parsing and a list of tuples of (name,
    value) strings.
    """
    errors = []
    fields = []

    # track current name and value to accumulate possible continuations
    name = None
    value = []

    for num, line in enumerate(lines):
        has_content = line.strip()
        new_field = field_declaration(line)
        cont = continuation(line)

        if cont:
            if name:
                # name is set, so the continuation is for the field name
                # append the value
                value.append(cont.group('value'))
            else:
                # name is not set and the line is not empty
                if has_content:
                    msg = 'Invalid continuation line: %(num)d: %(line)r'
                    errors.append(Error(CRITICAL, msg % locals()))

        elif not line or not has_content:
            # an empty line: append current name/value if any and reset
            if name:
                fields.append((name, value,))
                # reset
                name = None

        elif new_field:
            # new field line: yield current name/value if any
            if name:
                fields.append((name, value,))
            # start new field
            name = new_field.group('name')
            # values are always stored in a list
            # even simple single string values
            value = [new_field.group('value')]

        else:
            # neither empty, nor new field nor continuation
            # this is an error
            msg = 'Invalid line: %(num)d: %(line)r'
            errors.append(Error(CRITICAL, msg % locals()))

    # append if any name/value was left over on last iteration
    if name:
        fields.append((name, value,))

    # rejoin eventual multi-line string values
    fields = [(name, u'\n'.join(value),) for name, value in fields]
    return errors, fields


def collect_inventory(location, use_mapping=False, mapping_file=None):
    """
    Collect ABOUT files at location and return a list of errors and a list of
    About objects.
    """
    errors = []
    dedup_errors = []
    input_location = util.get_absolute(location)
    about_locations = list(util.get_about_locations(input_location))

    name_errors = util.check_file_names(about_locations)
    errors.extend(name_errors)
    abouts = []
    for about_loc in about_locations:
        about_file_path = util.get_relative_path(input_location, about_loc)
        about = About(about_loc, about_file_path, use_mapping, mapping_file)
        # Insert about_file_path reference to the error
        for severity, message in about.errors:
            msg = (about_file_path + ": " + message)
            errors.append(Error(severity, msg))
        abouts.append(about)

    # Avoid logging duplicated/same errors multiple times
    for about_error in errors:
        if not about_error in dedup_errors:
            dedup_errors.append(about_error)
    return dedup_errors, abouts


def field_names(abouts, with_paths=True, with_absent=True, with_empty=True):
    """
    Given a list of About objects, return a list of any field names that exist
    in any object, including custom fields.
    """
    fields = []
    if with_paths:
        fields.append(About.about_file_path_attr)
        # fields.append(About.about_resource_path_attr)

    standard_fields = About().fields.keys()
    if with_absent:
        fields.extend(standard_fields)
    else:
        standards = []
        for a in abouts:
            for name, field in a.fields.items():
                if field.required:
                    if name not in standards:
                        standards.append(name)
                else:
                    if field.present:
                        if name not in standards:
                            standards.append(name)
        # resort standard fields in standard order
        # which is a tad complex as this is a predefined order
        sorted_std = []
        for fn in standard_fields:
            if fn in standards:
                sorted_std.append(fn)
        fields.extend(sorted_std)

    customs = []
    for a in abouts:
        for name, field in a.custom_fields.items():
            if field.has_content:
                if name not in customs:
                    customs.append(name)
            else:
                if with_empty:
                    if name not in customs:
                        customs.append(name)
    # always sort custom fields list by name
    customs.sort()
    fields.extend(customs)

    return fields


def about_object_to_list_of_dictionary(abouts, with_absent=False, with_empty=True):
    """
    Convert About objects to a list of dictionaries
    """
    abouts_dictionary_list = []
    for about in abouts:
        ad = about.as_dict(with_paths=True, with_absent=with_absent, with_empty=with_empty)
        if 'about_file_path' in ad.keys():
            afp = ad['about_file_path']
            afp = '/' + afp if not afp.startswith('/') else afp
            ad['about_file_path'] = afp
        abouts_dictionary_list.append(ad)
    return abouts_dictionary_list


def write_output(abouts, location, format, mapping_output=None, with_absent=False, with_empty=True):  # NOQA
    """
    Write a CSV/JSON file at location given a list of About objects
    """
    errors = []
    about_dictionary_list = about_object_to_list_of_dictionary(abouts, with_absent, with_empty)
    if mapping_output:
        updated_dictionary_list = util.update_about_dictionary_keys(about_dictionary_list, mapping_output)
    else:
        updated_dictionary_list = about_dictionary_list
    location = add_unc(location)
    with codecs.open(location, mode='wb', encoding='utf-8') as output_file:
        if format == 'csv':
            fieldnames = field_names(abouts)
            if mapping_output:
                updated_fieldnames = util.update_fieldnames(fieldnames, mapping_output)
            else:
                updated_fieldnames = fieldnames
            writer = csv.DictWriter(output_file, updated_fieldnames)
            writer.writeheader()
            csv_formatted_list = util.format_about_dict_for_csv_output(updated_dictionary_list)
            for row in csv_formatted_list:
                # See https://github.com/dejacode/about-code-tool/issues/167
                try:
                    writer.writerow(row)
                except Exception as e:
                    msg = u'Generation skipped for ' + row['about_file_path'] + u' : ' + str(e)
                    errors.append(Error(CRITICAL, msg))
        else:
            json_fomatted_list = util.format_about_dict_for_json_output(updated_dictionary_list)
            output_file.write(json.dumps(json_fomatted_list, indent=2))
    return errors


def by_license(abouts):
    """
    Return an ordered dict sorted by key of About objects grouped by license
    """
    grouped = {}
    grouped[''] = []
    no_license = grouped['']
    for about in abouts:
        if about.license_expression.value:
            special_char_in_expression, lic_list = parse_license_expression(about.license_expression.value)
            if not special_char_in_expression:
                for lic in lic_list:
                    if lic in grouped:
                        grouped[lic].append(about)
                    else:
                        grouped[lic] = [about]
        else:
            no_license.append(about)
    return OrderedDict(sorted(grouped.items()))


def by_name(abouts):
    """
    Return an ordered dict sorted by key of About objects grouped by component
    name.
    """
    grouped = {}
    grouped[''] = []
    no_name = grouped['']
    for about in abouts:
        name = about.name.value
        if name:
            if name in grouped:
                grouped[name].append(about)
            else:
                grouped[name] = [about]
        else:
            no_name.append(about)
    return OrderedDict(sorted(grouped.items()))


def unique(abouts):
    """
    Return a list of unique About objects.
    """
    uniques = []
    for about in abouts:
        if any(about == x for x in uniques):
            continue
        uniques.append(about)
    return uniques


def by_license_content(abouts):
    """
    Return an ordered dict sorted by key of About objects grouped by license
    content.
    """
    grouped = {}
    grouped[''] = []
    no_license = grouped['']
    for about in abouts:
        if about.license_key.value:
            special_char_in_expression, lic_list = parse_license_expression(about.license_key.value)
            if not special_char_in_expression:
                for lic in lic_list:
                    if lic in grouped:
                        grouped[lic].append(about)
                    else:
                        grouped[lic] = [about]
        else:
            no_license.append(about)
    return OrderedDict(sorted(grouped.items()))


def pre_process_and_fetch_license_dict(abouts, api_url, api_key):
    """
    Modify a list of About data dictionaries by adding license information
    fetched from the DejaCode API.
    """
    dje_uri = urlparse(api_url)
    domain = '{uri.scheme}://{uri.netloc}/'.format(uri=dje_uri)
    dje_lic_urn = urljoin(domain, 'urn/?urn=urn:dje:license:')
    key_text_dict = {}
    captured_license = []
    errors = []
    if util.have_network_connection():
        if not valid_api_url(api_url):
            msg = u"URL not reachable. Invalid '--api_url'. License generation is skipped."
            errors.append(Error(ERROR, msg))
    else:
        msg = u'Network problem. Please check your Internet connection. License generation is skipped.'
        errors.append(Error(ERROR, msg))
    for about in abouts:
        # No need to go through all the about objects for license extraction if we detected
        # invalid '--api_key'
        auth_error = Error(ERROR, u"Authorization denied. Invalid '--api_key'. License generation is skipped.")
        if auth_error in errors:
            break
        if about.license_expression.present:
            special_char_in_expression, lic_list = parse_license_expression(about.license_expression.value)
            if special_char_in_expression:
                msg = (u"The following character(s) cannot be in the licesne_expression: " +
                       str(special_char_in_expression))
                errors.append(Error(ERROR, msg))
            else:
                for lic_key in lic_list:
                    if not lic_key in captured_license:
                        detail_list = []
                        license_name, license_key, license_text, errs = api.get_license_details_from_api(api_url, api_key, lic_key)
                        for e in errs:
                            if e not in errors:
                                errors.append(e)
                        if license_key:
                            captured_license.append(lic_key)
                            dje_lic_url = dje_lic_urn + license_key
                            detail_list.append(license_name)
                            detail_list.append(license_text)
                            detail_list.append(dje_lic_url)
                            key_text_dict[license_key] = detail_list
    return key_text_dict, errors


def parse_license_expression(lic_expression):
    licensing = Licensing()
    lic_list = []
    special_char = special_char_in_license_expresion(lic_expression)
    if not special_char:
        # Parse the license expression and save it into a list
        lic_list = licensing.license_keys(lic_expression)
    return special_char, lic_list


def special_char_in_license_expresion(lic_expression):
    not_support_char = [
        '!', '@', '#', '$', '%', '^', '&', '*', '=', '{', '}',
        '|', '[', ']', '\\', ':', ';', '<', '>', '?', ',', '/']
    special_character = []
    for char in not_support_char:
        if char in lic_expression:
            special_character.append(char)
    return special_character


def valid_api_url(api_url):
    try:
        request = Request(api_url)
        # This will always goes to exception as no key are provided.
        # The purpose of this code is to validate the provided api_url is correct
        urlopen(request)
    except HTTPError as http_e:
        # The 403 error code is refer to "Authentication credentials were not provided.".
        # This is correct as no key are provided.
        if http_e.code == 403:
            return True
    except:
        # All other exceptions yield to invalid api_url
        pass
    return False


def verify_license_files_in_location(about, lic_location):
    """
    Check the existence of the license file provided in the license_field from the
    license_text_location.
    Return a dictionary of the path of where the license should be copied to as
    the key and the path of where the license should be copied from as the value.
    """
    license_location_dict = {}
    errors = []
    # The license_file field is filled if the input has license value and
    # the 'fetch_license' option is used.
    if about.license_file.value:
        for lic in about.license_file.value:
            lic_path = util.to_posix(posixpath.join(lic_location, lic))
            if posixpath.exists(lic_path):
                copy_to = dirname(about.about_file_path)
                license_location_dict[copy_to] = lic_path
            else:
                msg = (u'The license file : '
                       u'%(lic)s '
                       u'does not exist in '
                       u'%(lic_path)s and therefore cannot be copied' % locals())
                errors.append(Error(ERROR, msg))
    return license_location_dict, errors


