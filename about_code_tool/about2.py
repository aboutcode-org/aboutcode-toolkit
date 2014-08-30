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

"""
AboutCode is a tool to process ABOUT files. ABOUT files are small text files
that document the provenance (aka. the origin and license) of software
components as well as the essential obligation such as attribution/credits and
source code redistribution. See the ABOUT spec at http://dejacode.org.

AbouCode reads and validates ABOUT files and collect software components
inventories.
"""

from __future__ import print_function

import codecs
import os
import re
import urlparse
import string
import logging
import posixpath
import ntpath
from collections import namedtuple, OrderedDict


__version__ = '0.10.0'

__about_spec_version__ = 'simplification'

__copyright__ = """
Copyright (c) 2013-2014 nexB Inc. All rights reserved. http://dejacode.org
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.CRITICAL)
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)


Error = namedtuple('Error', ['severity', 'message'], verbose=True)

def error_repr(self):
    sev = severities[self.severity]
    msg = self.message
    return 'Error(%(sev)s, %(msg)r)' % locals()

Error.__repr__ = error_repr

# modeled after the logging levels
CRITICAL = 50
ERROR = 40
WARNING = 30
INFO = 20
DEBUG = 10
NOTSET = 0

severities = {
    CRITICAL : u'CRITICAL',
    ERROR : u'ERROR',
    WARNING : u'WARNING',
    INFO : u'INFO',
    DEBUG : u'DEBUG',
    NOTSET : u'NOTSET'
    }


class Field(object):
    """
    An ABOUT file field.
    """
    def __init__(self, name=None, value=None, required=False, present=False):
        # normalized names are lowercased per specification
        self.name = name
        self.value = value  # list or OrderedDict()
        self.required = required
        # True if the field is present in an About object
        self.present = present
        self.errors = []

    def validate(self, **kwargs):
        """
        Validate and normalize thyself. Return a list of errors.
        """
        name = self.name
        errors = []
        if name == 'about_resource':
            print('validate: name/value:', repr(self.name), repr(self.value))
            print(' ', repr(self))
        if self.present:
            if not self.has_content:
                # check empties
                if self.required:
                    msg = u'Field %(name)s is required and empty'
                    severity = CRITICAL
                else:
                    severity = WARNING
                    msg = u'Field %(name)s is present but empty'
                errors.append(Error(severity, msg % locals()))
            else:
                validation_errors = self._validate(kwargs)
                errors.extend(validation_errors)

        else:
            if self.required:
                msg = u'Field %(name)s is required'
                errors.append(Error(CRITICAL, msg % locals()))
        return errors


    def _validate(self, *args, **kwargs):
        """
        Subclasses must implement this for custom validation. Return a list of
        errors.
        """
        return []

    def get_errors(self, level):
        """
        Return a list of Errors of severity superior or equal to level
        """

    def serialize(self):
        """
        Return a unicode serialization of self in the ABOUT format.
        """
        return self._serialize()

    def _serialize(self):
        """
        Return a unicode serialization of self in the ABOUT format.
        Subclasses must implement this for custom validation. 
        """
        return u'%(name)s: %(value)s' % self.__dict__

    @property
    def has_content(self):
        return self.value

    def __repr__(self):
        name = self.name
        value = self.value
        required = self.required
        has_content = self.has_content
        present = self.present
        r = ('Field(name=%(name)r, value=%(value)r, required=%(required)r, '
             'present=%(present)r, has_content=%(has_content)r')
        return r % locals()


class StringField(Field):
    """
    A field containing a string value possibly on multiple lines.
    """
    def _validate(self, *args, **kwargs):
        errors = super(StringField, self)._validate(args, kwargs)
        # single string value: a multi-line string
        if self.value:
            self.value = u'\n'.join(self.value)
        return errors

    def _serialize(self):
        name = self.name
        # prefix each line with one space for continuations
        if not self.has_content:
            value = ''
        else:
            value = self.value.splitlines(True)
            value = u' '.join(value)
        return u'%(name)s: %(value)s' % locals()

    @property
    def has_content(self):
        if self.value:
            return u''.join(self.value).strip()


class SingleLineField(StringField):
    """
    A field containing a string value on a single line.
    """
    def _validate(self, *args, **kwargs):
        errors = super(SingleLineField, self)._validate(args, kwargs)
        if self.value and '\n' in self.value:
            name = self.name
            value = self.value
            msg = (u'Field %(name)s: Cannot span multiple lines: %(value)s'
                   % locals())
            errors.append(Error(ERROR, msg))

        return errors


class ListField(Field):
    """
    A field containing a list of string values, one per line
    """
    def _serialize(self):
        name = self.name
        # add newline
        value = [val.rstrip() + u'\n' for val in self.value]
        # prefix lines with one space for continuations and
        value = u' '.join(value)
        return u'%(name)s: %(value)s' % locals()

    @property
    def has_content(self):
        if self.value:
            return u''.join(self.value).strip()


class PathField(ListField):
    """
    A field pointing to one or more paths relative to the ABOUT file location.
    """
    def _validate(self, *args, **kwargs):
        """
        Ensure that paths point to existing resources. Normalize to posix
        paths. Return a list of errors. base_dir is the directory used to
        resolve a file location from a path.
        """
        errors = super(PathField, self)._validate(args, kwargs)

        self.base_dir = kwargs.get('base_dir')

        name = self.name
        # mapping of normalized paths to a location or None
        paths = OrderedDict()

        for path in self.value:
            path = path.strip()
            path = to_posix(path)
            path = path.lstrip(posixpath.sep)

            if self.base_dir:
                location = posixpath.join(self.base_dir,
                                          posixpath.normpath(path))
                if os.path.exists(location):
                    continue

                msg = (u'Field %(name)s: Path %(path)s not found '
                       u'at: %(location)s' % locals())
                errors.append(Error(CRITICAL, msg))
            else:
                location = None
                msg = (u'Field %(name)s: Unable to verify path: %(path)s:'
                       u' No base directory provided' % locals())
                errors.append(Error(ERROR, msg))

            paths[path] = location

        self.value = paths
        return errors

    @property
    def has_content(self):
        if self.value:
            return u''.join(self.value).strip()


class TextField(PathField):
    """
    An path field pointing to one or more text files such as a license file.
    """
    def _validate(self, *args, **kwargs):
        """
        Load and validate the texts referenced by paths fields. Return a list
        of errors. base_dir is the directory used to resolve a file location
        from a path.
        """
        errors = super(TextField, self)._validate(args, kwargs)
        # a TextField is a PathField
        # self.value is a paths to location ordered mapping
        # we will replace the location with the text content
        name = self.name
        for path, location in self.value.items():
            if not location:
                msg = (u'Field %(name)s: No location available. '
                       u'Unable to load text at: '
                       u'%(path)s' % locals())
                errors.append(Error(ERROR, msg))
                # do not try to load if no location
                continue

            try:
                text = codecs.open(location, encoding='utf-8').read()
                self.value[path] = text
            except Exception, e:
                # only keep the first 100 char of the exception
                emsg = repr(e)[:100]
                msg = (u'Field %(name)s: Failed to load text at path: '
                       u'%(path)s from location: %(location)s '
                       u'with error: %(emsg)s' % locals())
                errors.append(Error(ERROR, msg))
        return errors

    @property
    def has_content(self):
        if self.value:
            return u''.join(self.value).strip()


class BooleanField(StringField):
    """
    An flag field with a boolean value.
    """
    flags = {
        'yes': True,
        'true': True,
        'y': True,
        't': True,
        'no': False,
        'false': False,
        'n': False,
        'f': False,
        }

    flag_values = ', '.join(flags)

    def _validate(self, *args, **kwargs):
        """
        Check that flag are valid. Convert flags to booleans. Return a list of
        errors.
        """
        errors = super(BooleanField, self)._validate(args, kwargs)
        if self.value:
            val = self.value.lower()
            flag = self.flags.get(val, None)
            if flag != None:
                self.value = flag
            else:
                name = self.name
                flag_values = self.flag_values
                msg = (u'Field %(name)s: Invalid flag value: %(val)r is not '
                       u'one of: %(flag_values)s' % locals())
                errors.append(Error(CRITICAL, msg))

        return errors

    @property
    def has_content(self):
        # FIXME: does not work for flags
        if self.value != None:
            return True

    def _serialize(self):
        # default normalized values for serialization
        TRUE = u'yes'
        FALSE = u'no'
        name = self.name
        value = TRUE if self.value else FALSE
        return u'%(name)s: %(value)s' % locals()


class UrlField(ListField):
    """
    A URL field.
    """
    def _validate(self, *args, **kwargs):
        """
        Check that URLs are valid. Return a list of errors.
        """
        errors = super(UrlField, self)._validate(args, kwargs)
        for url in self.value:
            if not is_valid_url(url):
                name = self.name
                msg = (u'Field %(name)s: Invalid URL: %(val)s' % locals())
                errors.append(Error(WARNING, msg))
        return errors


def is_valid_url(url):
    """
    Return True if a URL is valid.
    """
    scheme, netloc, _path, _p, _q, _frg = urlparse.urlparse(url)
    valid = scheme in ('http', 'https', 'ftp') and netloc
    return valid


def validate_fields(fields, base_dir):
    """
    Validate a sequence of Field objects. Return a list of errors.
    Validation may update the Field objects as needed as a side effect.
    """
    errors = []
    for field in fields.values():
        errors.extend(field.validate(base_dir=base_dir))
    return errors


class About(object):
    """
    Represent an ABOUT file and functions to parse and validate a file.
    """

    def create_fields(self):
        """
        Create fields in an ordered dict to keep a standard ordering. We could
        use a metaclass to track ordering django-like but this approach is
        simpler.
        """
        self.fields = OrderedDict(
            about_resource=PathField(required=True),
            name=StringField(required=True),

            version=StringField(),
            download_url=UrlField(),
            description=StringField(),
            home_url=UrlField(),
            notes=StringField(),

            license=ListField(),
            license_name=StringField(),
            license_file=TextField(),
            license_url=UrlField(),
            copyright=StringField(),
            notice_file=TextField(),
            notice_url=UrlField(),

            redistribute=BooleanField(),
            attribute=BooleanField(),
            track_change=BooleanField(),
            modified=BooleanField(),

            changelog_file=TextField(),

            owner=ListField(),
            owner_url=UrlField(),
            contact=ListField(),
            author=ListField(),

            vcs_tool=StringField(),
            vcs_repository=StringField(),
            vcs_path=StringField(),
            vcs_tag=StringField(),
            vcs_branch=Field(),
            vcs_revision=StringField(),

            checksum=ListField(),
            spec_version=StringField(),
        )

        for name, field in self.fields.items():
            # we could have a hack to get the actual field name
            # but setting an attribute is explicit and cleaner
            field.name = name
            setattr(self, name, field)

    def __init__(self, location=None, relative_path=None):
        self.create_fields()
        self.custom_fields = OrderedDict()

        self.errors = []

        # relative location, to the root of an inventory using posix path
        # separators
        self.relative_path = relative_path

        # os native absolute location, using posix path separators
        self.location = location
        self.base_dir = None
        if self.location:
            self.base_dir = os.path.dirname(location)
            self.load(location)

    def __repr__(self):
        return repr(self.all_fields())

    def as_dict(self):
        """
        Return an ordered dictionary of all the fields
        """
        dct = OrderedDict(self.fields)
        dct.update(self.custom_fields)
        return dct

    def all_fields(self):
        """
        Return a list of all Field objects
        """
        return self.as_dict().values()

    def present_fields(self):
        """
        Return a list of present or required Field objects
        """
        return [f for f in self.as_dict().values() if f.present or f.required]

    def hydrate(self, fields):
        """
        Process an iterable of field tuples (name, [value]). Update or create
        Fields attributes and the fields and custom fields dictionaries.
        Return a list of errors.
        """
        errors = []
        seen_fields = OrderedDict()
        for name, value in fields:
            name = name.lower()
            overridden = seen_fields.get(name)
            if overridden:
                msg = ('Field %(name)s: duplicated. Value: %(overridden)r '
                       'overridden with: %(value)r')
                errors.append(Error(WARNING, msg % locals()))
            else:
                seen_fields[name] = value

            standard_field = self.fields.get(name)
            if standard_field:
                standard_field.value = value
                standard_field.present = True
            else:
                val = u'\n'.join(value)
                msg = (u'Field %(name)s is a custom field')
                errors.append(Error(INFO, msg % locals()))

                custom_field = self.custom_fields.get(name)

                if custom_field:
                    custom_field.value = value
                    custom_field.present = True
                else:
                    if name in dir(self):
                        msg = (u'Field %(name)s is an illegal reserved name')
                        errors.append(Error(ERROR, msg % locals()))
                    else:
                        custom_field = StringField(name=name,
                                                   value=value,
                                                   present=True)
                        self.custom_fields[name] = custom_field
                        setattr(self, name, custom_field)

        return errors

    def load(self, location):
        """
        Read, parse, hydrate and validate the ABOUT file at location.
        """
        self.base_dir = posixpath.dirname(to_posix(self.location))
        self._load(location)

    def loads(self, s, base_dir):
        """
        Read, parse, hydrate and validate the ABOUT file content string s.
        Mostly for testing.
        """
        self.base_dir = base_dir
        lines = s.splitlines(True)
        self._load(lines)

    def _load(self, loc_or_list, base_dir=None):
        """
        Read, parse, hydrate and validate the ABOUT file lines list of location.
        """
        parse_errors, fields = parse(loc_or_list)
        fields = lower_names(fields)
        self.errors.extend(parse_errors)
        hydratation_errors = self.hydrate(fields)
        self.errors.extend(hydratation_errors)
        # we validate all fields, not only these hydrated
        validation_errors = validate_fields(self.fields, self.base_dir)
        self.errors.extend(validation_errors)

    def dumps(self):
        """
        Return self as a formatted ABOUT string.
        """
        serialized = [field.serialize() for field in self.all_fields()
                      if field.present]
        return u'\n'.join(serialized)

    def dump(self, location):
        """
        Write formatted ABOUT representation of self to location.
        """
        with codecs.open(location, mode='wb', encoding='utf-8') as dumped:
            dumped.write(self.dumps())


def parse(location_or_lines):
    """
    Parse the ABOUT file at location (or a list of unicode lines). Return a
    list of errors found during parsing and a list of tuples of (name,
    [value]) where the value is a list of strings, one per line.
    """
    # NB: we could define the re as globals but re caching does not
    # require this: having them here makes this clearer

    # line in the form of "name: value"
    field_declaration = re.compile(
        r'^'
        r'(?P<name>[a-z][0-9a-z_]*)'
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

    # accept a location string or a lines list as input
    if isinstance(location_or_lines, list):
        lines = location_or_lines
    else:
        # TODO: do we want to catch errors?
        lines = codecs.open(location_or_lines, encoding='utf-8').readlines()

    errors = []
    # list of parsed name/value tuples to return
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

    return errors, fields


def lower_names(field_tuples):
    """
    Return a list of fields name/value tuples where the name is lowercased
    """
    return [(n.lower(), v,) for n, v in field_tuples]


def check_duplicate_file_names(paths):
    """
    Given an iterable of ABOUT file paths, check for case-insensitive
    duplicate file names. Return a list of errors.

    From spec:
     The case of a file name is not significant. On case-sensitive file
     systems (such as Linux), a tool must raise an error if two ABOUT files
     stored in the same directory have the same lowercase file name.
    """
    seen = {}
    errors = []
    for orig_path in paths:
        path = to_posix(orig_path)
        name = resource_name(path).lower()
        parent = posixpath.dirname(path)
        path = posixpath.join(parent, name)
        path = posixpath.normpath(path)
        path = posixpath.abspath(path)
        existing = seen.get(path)
        if existing:
            msg = ('Duplicate ABOUT files: %(orig_path)r and %(existing)r '
                   'have the same case-insensitive file name' % locals)
            errors.append(Error(CRITICAL, msg))
        else:
            seen[path] = orig_path
    return errors


valid_file_chars = string.digits + string.ascii_letters + '_-.'


def check_file_names(paths):
    """
    Given a sequence of ABOUT file paths, check that file names are valid.
    Return a list of errors.

    From spec :
        A file name can contain only these US-ASCII characters:
        - digits from 0 to 9
        - uppercase and lowercase letters from A to Z
        - the _ underscore, - dash and . period signs.
    """
    errors = []
    for orig_path in paths:
        path = to_posix(orig_path)
        rname = resource_name(path)
        name = rname.lower()
        valid = all(c in valid_file_chars for c in name)
        if not valid:
            msg = ('Invalid characters in ABOUT file name: '
                   '%(name)r at %(orig_path)r' % locals)
            errors.append(Error(CRITICAL, msg))
    return errors


def inventory(location):
    """
    Collect ABOUT files at location and return a list of errors and a list of
    About objects.
    """
    errors = []
    locations = list(get_locations(location))
    duplicate_errors = check_duplicate_file_names(locations)
    errors.extend(duplicate_errors)
    name_errors = check_file_names(locations)
    errors.extend(name_errors)
    abouts = [About(loc) for loc in locations]
    for about in abouts:
        errors.extend(about.errors)
    return errors, abouts


def get_locations(location):
    """
    Return a list of locations of *.ABOUT files given the location of an
    ABOUT file or a directory tree containing ABOUT files.
    Locations are normalized using posix path separators.
    """
    location = os.path.expanduser(location)
    location = os.path.normpath(location)
    location = os.path.abspath(location)
    location = to_posix(location)
    assert os.path.exists(location)

    if os.path.isfile(location) and is_about_file(location):
        yield location
    else:
        for base_dir, _, files in os.walk(location):
            for name in files:
                if not is_about_file(name):
                    continue
                bd = to_posix(base_dir)
                yield posixpath.join(bd, name)


def log_errors(errors, level=NOTSET):
    """
    Iterate of sequence of Error objects and log errors with a severity
    superior or equal to level.
    """
    for severity, message in errors:
        if severity >= level:
            logger.log(severity, message)


def get_relative_path(base_loc, full_loc):
    """
    Return a posix path for a given full location relative to a base location.
    The last segment of the base_loc will become the first segment of the
    returned path.
    """
    base = to_posix(base_loc).rstrip(posixpath.sep)
    base_name = resource_name(base)
    path = to_posix(full_loc).lstrip(posixpath.sep)
    assert path.starts(base)
    relative = path[len(base):]
    return posixpath.join(base_name, relative)


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
