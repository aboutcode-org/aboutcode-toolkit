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
from collections import OrderedDict
import os
import posixpath
import re
import urlparse

import unicodecsv

from about_tool import saneyaml

from about_tool import Error
from about_tool import CRITICAL
from about_tool import WARNING
from about_tool import ERROR
from about_tool import INFO
from about_tool import util


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
            else:
                # no error for not present non required fields
                # FIXME: should we add an info?
                pass
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
        if self.has_content:
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
        r = ('Field(name=%(name)r, value=%(value)r, required=%(required)r, '
             'present=%(present)r)')
        return r % locals()

    def __eq__(self, other):
        """
        Equality based on string content value, ignoring spaces
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
        return self.value if self.has_content else u''

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
        return u'\n'.join(self.value) if self.has_content else u''

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
        scheme, netloc, _path, _p, _q, _frg = urlparse.urlparse(url)
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

                if not os.path.exists(location):
                    msg = (u'Field %(name)s: Path %(path)s not found'
                           % locals())
                    errors.append(Error(CRITICAL, msg))
                    location = None
            else:
                location = None
                msg = (u'Field %(name)s: Unable to verify path: %(path)s:'
                       u' No base directory provided' % locals())
                errors.append(Error(ERROR, msg))

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
        if not about_file_path:
            # FIXME: should we return an info or warning?
            return
        # clear
        self.resolved_paths = []
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

    def create_fields(self):
        """
        Create fields in an ordered mapping to keep a standard ordering. We
        could use a metaclass to track ordering django-like but this approach
        is simpler.

        TODO: use schematics
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
            self.load2(location)

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
            else:
                if field.present:
                    if not field.has_content:
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
        Read, parse, hydrate and validate the ABOUT file at location.
        Return a list of errors and update self with errors.
        """
        self.location = location
        loc = util.to_posix(location)
        base_dir = posixpath.dirname(loc)
        errors = []
        try:
            lines = codecs.open(loc, encoding='utf-8').readlines()
            errs = self.load_lines(lines, base_dir)
            errors.extend(errs)
        except Exception, e:
            msg = 'Cannot load invalid ABOUT file: %(location)r: %(e)r'
            errors.append(Error(CRITICAL, msg % locals()))

        self.errors = errors
        return errors

    def load2(self, location):
        """
        Read, parse and process the ABOUT file at location.
        Return a list of errors and update self with errors.
        """
        self.location = location
        loc = util.to_posix(location)
        base_dir = posixpath.dirname(loc)
        errors = []
        try:
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
        loc = util.to_posix(location)
        parent = posixpath.dirname(loc)
        if not os.path.exists(parent):
            os.makedirs(parent)
        about_file_path = loc
        if not about_file_path.endswith('.ABOUT'):
            if about_file_path.endswith('/'):
                about_file_path = util.to_posix(os.path.join(parent, os.path.basename(parent)))
            about_file_path += '.ABOUT'
        with codecs.open(about_file_path, mode='wb', encoding='utf-8') as dumped:
            dumped.write(self.dumps(with_absent, with_empty))


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
    location = util.get_absolute(location)
    locations = list(util.get_about_locations(location))
    # FIXME: CY: why do we have 2 check_file_names here?
    duplicate_errors = util.check_file_names(locations)
    errors.extend(duplicate_errors)

    name_errors = util.check_file_names(locations)
    errors.extend(name_errors)
    abouts = []
    for loc in locations:
        about_file_path = util.get_relative_path(location, loc)
        about = About(loc, about_file_path)
        errors.extend(about.errors)
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


def to_csv(abouts, location, with_absent=False, with_empty=True):
    """
    Write a CSV file at location given a list of About objects.
    """
    fieldnames = field_names(abouts)
    with codecs.open(location, mode='wb', encoding='utf-8') as csvfile:
        writer = unicodecsv.DictWriter(csvfile, fieldnames)
        writer.writeheader()
        for a in abouts:
            ad = a.as_dict(with_paths=True,
                           with_absent=with_absent,
                           with_empty=with_empty)
            writer.writerow(ad)


def from_csv(location, base_dir):
    """
    Load a CSV file at location and return a list of About objects.
    """
    # TODO: use this instead of load inventory


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
