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

"""
AboutCode is a tool to process ABOUT files. ABOUT files are small text files
that document the provenance (aka. the origin and license) of software
components as well as the essential obligation such as attribution/credits and
source code redistribution. See the ABOUT spec at http://dejacode.org.

AbouCode reads and validates ABOUT files and collect software components
inventories.
"""

from __future__ import absolute_import
from __future__ import print_function

import codecs
import json
import os
import posixpath
import re
import urllib2
import unicodecsv

from collections import OrderedDict
from posixpath import dirname
from urlparse import urljoin, urlparse

from attributecode import ERROR
from attributecode import CRITICAL
from attributecode import INFO
from attributecode import WARNING
from attributecode import Error
from attributecode import api
from attributecode import saneyaml
from attributecode import util
from attributecode.util import add_unc, UNC_PREFIX, on_windows


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
            """else:
                # no error for not present non required fields
                # FIXME: should we add an info?
                # CY: I don't think so.
                pass"""
        else:
            # present fields should have content ...
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
                except Exception, e:
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
                value = u''.join(value)
            serialized = u'%(name)s: %(value)s' % locals()
        else:
            serialized = u'%(name)s:' % locals()
        return serialized

    def serialized_value(self):
        """
        Return a unicode serialization of self in the ABOUT format.
        Does not include a white space for continuations.
        """
        return self._serialized_value() or u''

    @property
    def has_content(self):
        return self.original_value and self.original_value.strip()

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
        return u'\n'.join(self.value) if self.value else u''

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


class UrlField(ListField):
    """
    A URL field. The validated value is a list of URLs.
    """
    def _validate(self, *args, **kwargs):
        """
        Check that URLs are valid. Return a list of errors.
        """
        errors = super(UrlField, self)._validate(*args, ** kwargs)
        for url in self.value:
            if not self.is_valid_url(url):
                name = self.name
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
        self.base_dir = kwargs.get('base_dir')
        if self.base_dir:
            self.base_dir = util.to_posix(self.base_dir)

        name = self.name
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

            if self.base_dir:
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
                    errors.append(Error(CRITICAL, msg))
                    location = None
            else:
                msg = (u'Field %(name)s: Unable to verify path: %(path)s:'
                       u' No base directory provided' % locals())
                errors.append(Error(ERROR, msg))
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

        # FIXME
        # The value in the 'license_file' field does not only represent there should
        # be license side by side with the ABOUT file, but this can also be used for
        # copying the license from the provided 'license_text_location'. In another
        # word, the license file in the 'license_file' field may not always located
        # side by side with the ABOUT file. However, our code will check the
        # existence of the file by joining the 'base_dir' and the value in the
        # 'license_file' field when the about object is created which will yield error.
        # I am commenting out the errors for now.
        # I am checking the existence of the 'license_file' in the dump()

        # One solution is to extract out the fetch-license option to a subcommand.
        # Users need to run the fetch-license command first to generate/copy all
        # the licenses first and then generate the ABOUT files afterward so that
        # this code can check the existense of the license_file.

        # errors = super(FileTextField, self)._validate(*args, ** kwargs)
        super(FileTextField, self)._validate(*args, ** kwargs)
        errors = []

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
                text = codecs.open(location, encoding='utf-8').read()
                self.value[path] = text
            except Exception, e:
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

    flags = {'yes': True, 'y': True, 'no': False, 'n': False, }

    flag_values = ', '.join(flags)

    def _validate(self, *args, **kwargs):
        """
        Check that flag are valid. Convert flags to booleans. Default flag to
        False. Return a list of errors.
        """
        errors = super(BooleanField, self)._validate(*args, ** kwargs)

        flag = self.get_flag(self.original_value)
        if flag is False:
            name = self.name
            val = self.original_value
            flag_values = self.flag_values
            msg = (u'Field %(name)s: Invalid flag value: %(val)r is not '
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
            self.value = self.flags.get(flag)
        return errors

    def get_flag(self, value):
        """
        Return a normalized existing flag value if found in the list of
        possible values or None if empty or False if not found.
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
                    # of of yes, no, true, etc.
                    return value
                else:
                    return False
            else:
                return False

    @property
    def has_content(self):
        # Special for flags: None means False AND content not defined
        flag = self.get_flag(self.original_value)
        if flag:
            return True
        else:
            return flag

    def _serialized_value(self):
        # default normalized values for serialization
        if self.value is True:
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


def validate_fields(fields, base_dir):
    """
    Validate a sequence of Field objects. Return a list of errors.
    Validation may update the Field objects as needed as a side effect.
    """
    errors = []
    for f in fields:
        val_err = f.validate(base_dir=base_dir)
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
            ('about_resource', AboutResourceField(required=True)),
            ('name', SingleLineField(required=True)),

            ('version', SingleLineField()),
            ('download_url', UrlField()),
            ('description', StringField()),
            ('home_url', UrlField()),
            ('notes', StringField()),

            ('license', ListField()),
            ('license_name', StringField()),
            ('license_file', FileTextField()),
            ('license_url', UrlField()),
            ('copyright', StringField()),
            ('notice_file', FileTextField()),
            ('notice_url', UrlField()),

            ('redistribute', BooleanField()),
            ('attribute', BooleanField()),
            ('track_change', BooleanField()),
            ('modified', BooleanField()),

            ('changelog_file', FileTextField()),

            ('owner', ListField()),
            ('owner_url', UrlField()),
            ('contact', ListField()),
            ('author', ListField()),

            ('vcs_tool', SingleLineField()),
            ('vcs_repository', SingleLineField()),
            ('vcs_path', SingleLineField()),
            ('vcs_tag', SingleLineField()),
            ('vcs_branch', SingleLineField()),
            ('vcs_revision', SingleLineField()),

            ('checksum', ListField()),
            ('spec_version', SingleLineField()),
        ])

        for name, field in self.fields.items():
            # we could have a hack to get the actual field name
            # but setting an attribute is explicit and cleaner
            field.name = name
            setattr(self, name, field)

    def __init__(self, location=None, about_file_path=None):
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
            self.load(location)

    def __repr__(self):
        return repr(self.all_fields())

    def __eq__(self, other):
        """
        Equality based on fields and custom_fields., i.e. content.
        """
        return (isinstance(other, self.__class__)
                and self.fields == other.fields
                and self.custom_fields == other.custom_fields)

    def attribution_fields(self, fields):
        """
        Return attrib-only fields
        """
        attrib_fields = ['name',
                         'version',
                         'license',
                         'license_name',
                         'license_file',
                         'license_url',
                         'copyright',
                         'notice_file',
                         'notice_url',
                         'redistribute',
                         'attribute',
                         'track_change',
                         'modified',
                         'changelog_file',
                         'owner',
                         'author']

        return OrderedDict([(n, o,) for n, o in fields.items()
                                if n in attrib_fields])

    def same_attribution(self, other):
        """
        Equality based on attribution-related fields.
        """
        return (isinstance(other, self.__class__)
                and self.attribution_fields(self.fields)
                    == self.attribution_fields(other.fields))

    def resolved_resources_paths(self):
        """
        Return a serialized string of resolved resource paths, one per line.
        """
        abrf = self.about_resource
        abrf.resolve(self.about_file_path)
        return u'\n'.join(abrf.resolved_paths)

    def all_fields(self, with_absent=True, with_empty=True):
        """
        Return the list of all Field objects.
        If with_absent, include absent (not present) fields.
        If with_empty, include empty fields.
        """
        all_fields = []
        for field in self.fields.values() + self.custom_fields.values():
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
            arpa = self.about_resource_path_attr
            as_dict[afpa] = self.about_file_path
            as_dict[arpa] = self.resolved_resources_paths()

        for field in self.all_fields(with_absent=with_absent,
                                     with_empty=with_empty):
            as_dict[field.name] = field.serialized_value()
        return as_dict

    def hydrate(self, fields):
        """
        Process an iterable of field (name, value) tuples. Update or create
        Fields attributes and the fields and custom fields dictionaries.
        Return a list of errors.
        """
        errors = []
        seen_fields = OrderedDict()
        if util.have_mapping:
            mapping = util.get_mappings(None)
        for name, value in fields:
            # normalize to lower case
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
            else:
                if util.have_mapping:
                    if name in mapping.keys():
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
                        else:
                            if name in dir(self):
                                msg = (u'Field %(orig_name)s has an '
                                       u'illegal reserved name')
                                errors.append(Error(ERROR, msg % locals()))
                            else:
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
                    else:
                        msg = (u'Field %(orig_name)s is not a supported field and is not ' +
                               u'defined in the mapping file. This field is ignored.')
                        errors.append(Error(INFO, msg % locals()))
                else:
                    if not name == self.about_file_path_attr:
                        msg = (u'Field %(orig_name)s is not a supported field and is ignored.')
                        errors.append(Error(INFO, msg % locals()))
        return errors

    def process(self, fields, base_dir=None):
        """
        Hydrate and validate a sequence of field name/value tuples from an
        ABOUT file. Return a list of errors.
        """
        self.base_dir = base_dir
        errors = []
        hydratation_errors = self.hydrate(fields)
        errors.extend(hydratation_errors)

        # we validate all fields, not only these hydrated
        all_fields = self.all_fields()
        validation_errors = validate_fields(all_fields, self.base_dir)
        errors.extend(validation_errors)

        # do not forget to resolve about resource paths
        self.about_resource.resolve(self.about_file_path)
        return errors

    def load(self, location):
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
            input_text = codecs.open(loc, encoding='utf-8').read()
            errs = self.load_dict(saneyaml.load(input_text), base_dir)
            errors.extend(errs)
        except Exception, e:
            msg = 'Cannot load invalid ABOUT file: %(location)r: %(e)r'
            errors.append(Error(CRITICAL, msg % locals()))

        self.errors = errors
        return errors

    def loads(self, string, base_dir):
        """
        Load the ABOUT file from string. Return a list of errors.
        """
        lines = string.splitlines(True)
        errors = self.load_lines(lines, base_dir)
        self.errors = errors
        return errors

    def load_lines(self, lines, base_dir):
        """
        Load the ABOUT file from a lines list. Return a list of errors.
        """
        errors = []
        parse_errors, fields = parse(lines)
        errors.extend(parse_errors)
        process_errors = self.process(fields, base_dir)
        errors.extend(process_errors)
        self.errors = errors
        return errors

    def load_dict(self, fields_dict, base_dir, with_empty=True):
        """
        Load the ABOUT file from a fields name/value mapping.
        If with_empty, create fields with no value for empty fields.
        Return a list of
        errors.
        """
        fields = fields_dict.items()
        if not with_empty:
            fields = [(n, v) for n, v in fields_dict.items() if v]
        errors = self.process(fields, base_dir)
        self.errors = errors
        return errors

    def dumps(self, with_absent=False, with_empty=True):
        """
        Return self as a formatted ABOUT string.
        If with_absent, include absent (not present) fields.
        If with_empty, include empty fields.
        """
        serialized = []
        for field in self.all_fields(with_absent, with_empty):
            serialized.append(field.serialize())
        # always end with a new line
        return u'\n'.join(serialized) + u'\n'

    def dump(self, location, with_absent=False, with_empty=True):
        """
        Write formatted ABOUT representation of self to location.
        If with_absent, include absent (not present) fields.
        If with_empty, include empty fields.
        """
        errors = []
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
            dumped.write(self.dumps(with_absent, with_empty))
            for about_resource_value in self.about_resource.value:
                path = posixpath.join(dirname(util.to_posix(about_file_path)), about_resource_value)
                if not posixpath.exists(path):
                    msg = (u'The reference file : '
                           u'%(path)s '
                           u'does not exist' % locals())
                    errors.append(msg)
        return errors


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

        if self.license.present and not self.license_file.present:
            for lic_key in self.license.value:
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
    + field_name +
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


def collect_inventory(location):
    """
    Collect ABOUT files at location and return a list of errors and a list of
    About objects.
    """
    errors = []
    input_location = util.get_absolute(location)
    about_locations = list(util.get_about_locations(input_location))

    name_errors = util.check_file_names(about_locations)
    errors.extend(name_errors)
    abouts = []
    for about_loc in about_locations:
        about_file_path = util.get_relative_path(input_location, about_loc)
        about = About(about_loc, about_file_path)
        # Avoid logging duplicated/same errors multiple times
        for about_error in about.errors:
            if not about_error in errors:
                errors.append(about_error)
        abouts.append(about)
    return errors, abouts


def field_names(abouts, with_paths=True, with_absent=True, with_empty=True):
    """
    Given a list of About objects, return a list of any field names that exist
    in any object, including custom fields.
    """
    fields = []
    if with_paths:
        fields.append(About.about_file_path_attr)
        fields.append(About.about_resource_path_attr)

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
        if 'about_resource_path' in ad.keys():
            arp = ad['about_resource_path']
            arp = '/' + arp if not arp.startswith('/') else arp
            ad['about_resource_path'] = arp
        # Make the 'about_resource_path' endswith '/' if the 'about_resource'
        # reference the current directory
        if 'about_resource' in ad.keys() and ad['about_resource'] == '.':
            if not ad['about_resource_path'].endswith('/'):
                ad['about_resource_path'] += '/'
        abouts_dictionary_list.append(ad)
    return abouts_dictionary_list


def write_output(abouts, location, format, with_absent=False, with_empty=True):
    """
    Write a CSV/JSON file at location given a list of About objects
    """
    errors = []
    about_dictionary_list = about_object_to_list_of_dictionary(abouts, with_absent, with_empty)
    location = add_unc(location)
    with codecs.open(location, mode='wb', encoding='utf-8') as output_file:
        if format == 'csv':
            fieldnames = field_names(abouts)
            writer = unicodecsv.DictWriter(output_file, fieldnames)
            writer.writeheader()
            for row in about_dictionary_list:
                # See https://github.com/dejacode/about-code-tool/issues/167
                try:
                    writer.writerow(row)
                except Exception as e:
                    msg = u'Generation skipped for ' + row['about_file_path'] + u' : ' + str(e)
                    errors.append(Error(CRITICAL, msg))
        else:
            output_file.write(json.dumps(about_dictionary_list, indent=2))
    return errors


def by_license(abouts):
    """
    Return an ordered dict sorted by key of About objects grouped by license
    """
    grouped = {}
    grouped[''] = []
    no_license = grouped['']
    for about in abouts:
        if about.license.value:
            for lic in about.license.value:
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
        if about.license.value:
            for lic in about.license.value:
                if lic in grouped:
                    grouped[lic].append(about)
                else:
                    grouped[lic] = [about]
        else:
            no_license.append(about)
    return OrderedDict(sorted(grouped.items()))


def common_licenses(abouts):
    """
    Return a ordered dictionary of repeated licenses sorted by key and update
    the list of about objects with license references for repeated licenses.
    """
    pass

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
        # No need to go thru all the about objects for license extraction if we detected
        # invalid '--api_key'
        auth_error = Error(ERROR, u"Authorization denied. Invalid '--api_key'. License generation is skipped.")
        if auth_error in errors:
            break
        if about.license.present:
            for lic_key in about.license.value:
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


def valid_api_url(api_url):
    try:
        request = urllib2.Request(api_url)
        # This will always goes to exception as no key are provided.
        # The purpose of this code is to validate the provided api_url is correct
        response = urllib2.urlopen(request)
    except urllib2.HTTPError, http_e:
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


def check_file_field_exist(about, location):
    """
    Return a list of errors for non-existence file in file fields
    """
    errors = []
    loc = util.to_posix(location)
    parent = posixpath.dirname(loc)

    about_file_path = util.to_posix(os.path.join(parent, os.path.basename(parent)))
    if on_windows:
        about_file_path = add_unc(about_file_path)

    # The model only has the following as FileTextField
    license_files = about.license_file.value
    notice_files = about.notice_file.value
    changelog_files = about.changelog_file.value

    if license_files:
        for lic in license_files:
            lic_path = posixpath.join(dirname(util.to_posix(about_file_path)), lic)
            if not posixpath.exists(lic_path):
                msg = (u'Field license_file: Path '
                   u'%(lic_path)s '
                   u'not found' % locals())
                errors.append(msg)

    if notice_files:
        for notice in notice_files:
            notice_path = posixpath.join(dirname(util.to_posix(about_file_path)), notice)
            if not posixpath.exists(notice_path):
                msg = (u'Field notice_file: Path '
                   u'%(notice_path)s '
                   u'not found' % locals())
                errors.append(msg)

    if changelog_files:
        for changelog in changelog_files:
            changelog_path = posixpath.join(dirname(util.to_posix(about_file_path)), changelog)
            if not posixpath.exists(changelog_path):
                msg = (u'Field changelog_file: Path '
                   u'%(changelog_path)s '
                   u'not found' % locals())
                errors.append(msg)
    return errors
