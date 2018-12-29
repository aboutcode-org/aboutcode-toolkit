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
import io
import os
import re

import attr
import click
from license_expression import Licensing

from aboutcode import CRITICAL
from aboutcode import Error
from aboutcode import saneyaml
from aboutcode import util

if util.python2:
    str = unicode  # NOQA


################################################################################
# Validation and conversion utilities
################################################################################

def validate_custom_fields(about_obj, attribute, value):
    """
    Check a mapping of custom_fields. Raise an Exception on errors.
    """
    if not value:
        return

    errors = []

    if value and not isinstance(value, dict):
        msg = (
            'Custom fields must be a dictionary: %(value)r.')
        raise Exception(Error(CRITICAL, msg % locals()))

    errors.extend(validate_custom_field_names(field_names=value.keys()))

    if errors:
        raise Exception(*errors)

    if value and not isinstance(value, dict):
        msg = (
            'Custom fields must be a dictionary: %(value)r.')
        raise Exception(Error(CRITICAL, msg % locals()))

    errors.extend(validate_custom_field_names(field_names=value.keys()))

    if errors:
        raise Exception(*errors)


def convert_custom_fields(value):
    if value:
        value = {key: string_cleaner(value) for key, value in value.items()}
    return value


def validate_custom_field_names(field_names):
    """
    Check a list of custom field name and return a list of Error.
    """
    if not field_names:
        return []

    errors = []
    is_valid_name = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$').match

    for name in sorted(field_names):
        # Check if names aresafe to use as an attribute name.
        if not is_valid_name(name):
            msg = (
                'Custom field name: %(name)r contains illegal characters. '
                'Only these characters are allowed: '
                'ASCII letters, digits and "_" underscore. '
                'The first character must be a letter.')
            errors.append(Error(CRITICAL, msg % locals()))
        if not name.lower() == name:
            msg = 'Custom field name: %(name)r must be lowercase.'
            errors.append(Error(CRITICAL, msg % locals()))

    return errors


booleans = {
    'yes': True, 'y': True, 'true': True, 'x': True,
    'no': False, 'n': False, 'false': False, }


def boolean_converter(value):
    """
    Convert a yes/no value to a proper True/False boolean value.
    """
    if value is True or value is False:
        return value

    if isinstance(value, str):
        value = value.lower().strip()
        if not value:
            value = False
        elif value in booleans:
            value = booleans[value]
    return value


def validate_flag_field(about_obj, attribute, value):
    """
    Check a boolean flag value for errors. Raise an Exception on errors.
    """
    if value is True or value is False:
        return

    name = attribute.name
    msg = (
        'Field name: %(name)r has an invalid flag value: '
        '%(value)r: should be one of yes or no or true or false.')
    raise Exception(Error(CRITICAL, msg % locals()))


def copyright_converter(value):
    if value:
        value = '\n'.join(v.strip() for v in value.splitlines(False)).strip()
    return value


def path_converter(value):
    if value and isinstance(value, str):
        value = util.to_posix(value).strip().strip('/')
    return value


def about_resource_validator(about_obj, attribute, value):
    if value and not isinstance(value, str):
        msg = 'Required field "about_resource" must be a single string.'
        raise Exception(Error(CRITICAL, msg))

    if not value or not value.strip():
        msg = 'Required field "about_resource" is empty.'
        raise Exception(Error(CRITICAL, msg))

def license_expression_converter(value):
    """
    Validate and normalize the license expression.
    """
    if value:
        licensing = Licensing()
        expression = licensing.parse(value, simple=True)
        value = str(expression)
    return value


def string_cleaner(value):
    if value and isinstance(value, str):
        value = value.strip()
    return value


def split_fields(data, skip_empty=False):
    """
    Given a `data` mapping return two mappings: one with only standard fields
    and one with custom fields.
    """
    standard_fields = {}
    custom_fields = {}

    standard_field_names = set(attr.fields_dict(Package).keys())

    for key, value in data.items():
        if skip_empty and not value:
            continue
        if key in standard_field_names:
            standard_fields[key] = value
        else:
            custom_fields[key] = value
    return standard_fields, custom_fields


def validate_unique_names(field_names):
    """
    Given a list of field names, validate their unicity and case.
    Return a list of Error.
    """
    errors = []
    keys = set(field_names)
    keys_lower = set([k.lower() for k in keys])
    if len(keys) != len(keys_lower):
        errors.append(Error(CRITICAL, 'Invalid fields: lowercased field names must be unique.'))

    if keys != keys_lower:
        errors.append(Error(CRITICAL, 'Invalid fields: all field names must be lowercase.'))

    empty = False
    for name in field_names:
        if not name:
            empty = True
            break
    if empty:
        errors.append(Error(CRITICAL, 'Invalid empty field name.'))
    return errors


def validate_field_names(standard_field_names, custom_field_names, for_gen=False):
    """
    Validate a `field_names` sequence of field names. Return a list of Error.
    """
    errors = []
    errors.extend(validate_unique_names(
        list(standard_field_names) + list(standard_field_names)))

    if for_gen and 'about_file_path' not in standard_field_names:
        errors.append(Error(CRITICAL, 'Required field "about_file_path" is missing or empty.'))

    if 'about_resource' not in standard_field_names:
        errors.append(Error(CRITICAL, 'Required field "about_resource" is missing.'))

    errors.extend(validate_custom_field_names(custom_field_names))

    return errors


################################################################################
# Models proper
################################################################################

@attr.attributes
class License(object):
    """
    A license object
    """
    # POSIX path relative to the ABOUT file location where the text file lives
    key = attr.attrib(converter=string_cleaner)
    name = attr.attrib(default=None, converter=string_cleaner)
    file = attr.attrib(default=None, repr=False, converter=path_converter)
    url = attr.attrib(default=None, repr=False, converter=string_cleaner)
    text = attr.attrib(default=None, repr=False, converter=string_cleaner)

    def __attrs_post_init__(self, *args, **kwargs):
        if not self.file:
            self.file = self.default_file_name

    def to_dict(self):
        """
        Return an OrderedDict of license data (excluding texts).
        Fields with empty values are not included.
        """
        excluded = set(['text', ])

        def valid_fields(attr, value):
            return (value and attr.name not in excluded)

        return attr.asdict(self, filter=valid_fields, dict_factory=OrderedDict)

    def update(self, other_license):
        """
        Update self "unset" fields with data from another License.
        """
        assert isinstance(other_license, License)
        assert other_license.key == self.key
        self.name = self.name or other_license.name
        self.url = self.url or other_license.url
        self.file = self.file or other_license.file
        self.text = self.text or other_license.text

    @classmethod
    def load(cls, location):
        """
        Return a License object built from the YAML file at `location`.
        """
        with io.open(location, encoding='utf-8') as inp:
            data = saneyaml.load(inp.read(), allow_duplicate_keys=False)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data):
        """
        Return a License object built a `data` mapping.
        """
        return License(
            key=data['key'],
            name=data.get('name'),
            file=data.get('file'),
            url=data.get('url'))

    @property
    def default_file_name(self):
        return self.key + '.LICENSE'

    def file_loc(self, base_dir):
        fn = self.file or self.default_file_name
        return os.path.join(base_dir, fn)

    def load_text(self, base_dir):
        """
        Load the license text found in `base_dir`.
        """
        file_loc = self.file_loc(base_dir)

        # text can be garbage and not valid UTF
        with io.open(file_loc, 'rb') as inp:
            text = inp.read()
        self.text = text.decode(encoding='utf-8', errors='replace')

    def dump(self, target_dir):
        """
        Write this license as a .yml data file and a .LICENSE text file in
        `target_dir`.
        """
        data_loc = os.path.join(target_dir, self.key + '.yml')
        with io.open(data_loc, 'w', encoding='utf-8') as out:
            out.write(saneyaml.dump(self.to_dict()))

        # always write a text file even if this is an empty one
        text = self.text or ''
        if not text:
            click.echo('WARNING: license text is empty for {}'.format(self.key))

        file_loc = self.file_loc(target_dir)
        with io.open(file_loc, 'w', encoding='utf-8') as out:
            out.write(text)


def get_reference_licenses(reference_dir):
    """
    Return reference licenses text and data loaded from `reference_dir`as a
    tuple of two mappings: a mapping of notices as {notice_file: notice text}
    and a mapping of {license key: License} loaded from a `reference_dir`.

    In the `reference_dir` there can be pairs of text and data files for a license key:
      - a license text file must be named after its license key as `key.LICENSE`
      - a license .yml YAML data file with license data to load as a License object.
    All other files not part of a license files pair are treated as "notice files".

    For instance, we can have the files foo.LICENSE and foo.yml where foo.yml contains:

        key: foo
        name: The Foo License
        url: http://zddfsdfsd.com/FOO
    """

    notices_by_name = {}
    licenses_by_key = {}
    ref_files = os.listdir(reference_dir)
    data_files = [f for f in ref_files if f.endswith('.yml')]
    text_files = set([f for f in ref_files if not f.endswith('.yml')])

    for data_file in data_files:
        loc = os.path.join(reference_dir, data_file)
        lic = License.load(loc)
        licenses_by_key[lic.key] = lic

        if lic.file not in text_files:
            click.echo(
                'ERROR: The reference license: {} does not have a '
                'corresponding text file: {}'.format(lic.key, lic.file))
        else:
            lic.load_text(reference_dir)
            text_files.remove(lic.file)

        assert lic.text is not None, 'Incorrect reference license with no text: {}'.format(lic.key)

    # whatever is left are "notice" files
    for notice_file in text_files:
        loc = os.path.join(reference_dir, notice_file)
        # text can be garbage and not valid UTF
        with io.open(loc, 'rb') as inp:
            text = inp.read()
        text = text.decode(encoding='utf-8', errors='replace')
        notices_by_name[notice_file] = text

    return notices_by_name, licenses_by_key


@attr.attributes
class Package(object):
    """
    A package object
    """
    # the absolute location where this is stored
    location = attr.attrib(default=None, repr=False)

    # a relative posix path where this file is stored
    about_file_path = attr.attrib(default=None, repr=False)

    # this is a path relative to the ABOUT file location
    about_resource = attr.attrib(default=None,
        converter=path_converter, validator=about_resource_validator)

    # everything else is optional

    name = attr.attrib(default=None, converter=string_cleaner)
    version = attr.attrib(default=None, converter=string_cleaner)
    description = attr.attrib(default=None, repr=False, converter=string_cleaner)
    homepage_url = attr.attrib(default=None, repr=False, converter=string_cleaner)
    download_url = attr.attrib(default=None, repr=False, converter=string_cleaner)
    notes = attr.attrib(default=None, repr=False, converter=string_cleaner)

    copyright = attr.attrib(
        default=None, repr=False, converter=copyright_converter)
    license_expression = attr.attrib(
        default=None, repr=False, converter=license_expression_converter)

    # boolean flags as yes/no
    attribute = attr.attrib(
        default=False, type=bool, repr=False,
        validator=validate_flag_field, converter=boolean_converter,)

    redistribute = attr.attrib(
        default=False, type=bool, repr=False,
        validator=validate_flag_field, converter=boolean_converter,)

    modified = attr.attrib(
        default=False, type=bool, repr=False,
        validator=validate_flag_field, converter=boolean_converter,)

    track_changes = attr.attrib(
        default=False, type=bool, repr=False,
        validator=validate_flag_field, converter=boolean_converter,)

    internal_use_only = attr.attrib(
        default=False, type=bool, repr=False,
        validator=validate_flag_field, converter=boolean_converter,)

    # a list of License objects
    licenses = attr.attrib(default=attr.Factory(list), repr=False)

    # path relative to the ABOUT file location
    notice_file = attr.attrib(default=None, repr=False, converter=path_converter)
    # the text loaded from notice_file
    notice_text = attr.attrib(default=None, repr=False, converter=string_cleaner)
    notice_url = attr.attrib(default=None, repr=False, converter=string_cleaner)

    # path relative to the ABOUT file location
    changelog_file = attr.attrib(default=None, repr=False, converter=path_converter)

    owner = attr.attrib(default=None, repr=False, converter=string_cleaner)
    owner_url = attr.attrib(default=None, repr=False, converter=string_cleaner)

    # SPDX-like VCS URL
    vcs_url = attr.attrib(default=None, repr=False, converter=string_cleaner)

    md5 = attr.attrib(default=None, repr=False, converter=string_cleaner)
    sha1 = attr.attrib(default=None, repr=False, converter=string_cleaner)
    sha256 = attr.attrib(default=None, repr=False, converter=string_cleaner)
    sha512 = attr.attrib(default=None, repr=False, converter=string_cleaner)

    spec_version = attr.attrib(default=None, repr=False, converter=string_cleaner)

    # custom files as name: value
    custom_fields = attr.attrib(
        default=attr.Factory(dict), repr=False,
        validator=validate_custom_fields, converter=convert_custom_fields)

    # list of Error object
    errors = attr.attrib(default=attr.Factory(list), repr=False)

    def __attrs_post_init__(self, *args, **kwargs):
        # populate licenses from expression
        if self.license_expression and not self.licenses:
            keys = Licensing().license_keys(
                self.license_expression, unique=True, simple=True)
            licenses = [License(key=key) for key in keys]
            self.licenses = licenses

    @classmethod
    def from_dict(cls, data):
        """
        Return a Package object built a `data` mapping.
        """
        data = dict(data)
        standard_fields, custom_fields = split_fields(data, skip_empty=True)
        standard_fields.pop('errors', None)

        errors = validate_field_names(
            standard_fields.keys(), custom_fields.keys())
        if errors:
            raise Exception(*errors)

        licenses = standard_fields.pop('licenses', []) or []
        licenses = [License.from_dict(l) for l in licenses]
        return Package(licenses=licenses, custom_fields=custom_fields, **standard_fields)

    @classmethod
    def load(cls, location):
        """
        Return a Package object built from the YAML file at `location` or None.
        Raise Exception on non-recoverable errors.
        """
        # TODO: expand/resolve/abs/etc
        loc = util.to_posix(location)

        with io.open(loc, encoding='utf-8') as inp:
            text = inp.read()
        package = cls.loads(text)
        if package:
            package.location = location
            return package

    @classmethod
    def loads(cls, text):
        """
        Return a Package object built from a YAML `text` or None.
        Raise Exception on non-recoverable errors.
        """
        data = saneyaml.load(text, allow_duplicate_keys=False)
        return cls.from_dict(data)

    # these fields are excluded from a to_dict() serialization
    _excluded_fields = set([
        'location',
        'errors',
        'custom_fields',
        'notice_text',
        # this is for the licenses.text attribute
        'text',
    ])

    def to_dict(self, with_licenses=True, with_path=False, excluded_fields=_excluded_fields):
        """
        Return an OrderedDict of Package data (excluding texts and ABOUT file path).
        Fields with empty values are not included.
        """
        excluded_fields = set(excluded_fields)
        if not with_licenses:
            excluded_fields.add('licenses')
        if not with_path:
            excluded_fields.add('about_file_path')

        def valid_fields(attr, value):
            return (value and attr.name not in excluded_fields)

        data = attr.asdict(self,
            recurse=True, filter=valid_fields, dict_factory=OrderedDict)

        # add custom fields
        # note: we sort these fields by name
        for key, value in sorted(self.custom_fields.items()):
            if value:
                data[key] = value

        return data

    def hashable(self):
        """
        Return a hashable data representing this object and that is usable for
        comparison and unicity checks. The about_resource filed is ignored and
        not included. All texts are included if present.
        """
        excluded_fields = set([
            'location', 'errors', 'custom_fields',
            'about_file_path', 'about_resource'])
        return repr(tuple(self.to_dict(excluded_fields=excluded_fields).items()))

    def dumps(self):
        """
        Return a YAML representation for this Package.
        If `with_files` is True, also write any reference notice or license file.
        """
        return saneyaml.dump(self.to_dict(), indent=2)

    def dump(self, location, with_files=False):
        """
        Write this Package object to the YAML file at `location`.
        If `with_files` is True, also write any reference notice or license file.
        """
        parent = os.path.dirname(location)
        if not os.path.exists(parent):
            os.makedirs(parent)

        with io.open(location, 'w', encoding='utf-8') as out:
            out.write(self.dumps())

        if with_files:
            base_dir = os.path.dirname(location)
            self.write_files(base_dir)

    @classmethod
    def standard_fields(cls):
        """
        Return a list of standard field names available in this class.
        """
        return [f for f in attr.fields_dict(cls).keys()
                if f not in cls._excluded_fields]

    def fields(self):
        """
        Return a list of standard field names and a list of custom field names
        in use (with a value set) in this object.
        """

        def valid_fields(attribute, value):
            return (value and attribute.name not in self._excluded_fields)

        standard = attr.asdict(
            self, recurse=False, filter=valid_fields, dict_factory=OrderedDict)
        standard = list(standard.keys())

        custom = [key for key, value in self.custom_fields.items() if value]

        return standard, custom

    def field_names(self):
        """
        Return a list of all field names in use in this object.
        """
        standard = list(attr.fields_dict(self.__class__).keys())
        custom = [k for k, v in self.custom_fields.items() if v]
        return standard + custom

    def write_files(self, base_dir=None):
        """
        Write all referenced license and notice files.
        """
        base_dir = base_dir or os.path.dirname(self.location)

        def _write(text, target_loc):
            if target_loc:
                text = text or ''
                parent = os.path.dirname(target_loc)
                if not os.path.exists(parent):
                    os.makedirs(parent)

                with io.open(target_loc, 'w', encoding='utf-8') as out:
                    out.write(text)

        _write(self.notice_text, self.notice_file_loc(base_dir))

        for license in self.licenses:  # NOQA
            _write(license.text, license.file_loc(base_dir))

    def about_resource_loc(self, base_dir=None):
        """
        Return the location to the about_resource.
        """
        base_dir = base_dir or os.path.dirname(self.location)
        return self.about_resource and os.path.join(base_dir, self.about_resource)

    def notice_file_loc(self, base_dir=None):
        """
        Return the location to the notice_file or None.
        """
        base_dir = base_dir or os.path.dirname(self.location)
        return self.notice_file and os.path.join(base_dir, self.notice_file)

    def changelog_file_loc(self, base_dir=None):
        """
        Return the location to the changelog_file or None.
        """
        base_dir = base_dir or os.path.dirname(self.location)
        return self.changelog_file and os.path.join(base_dir, self.changelog_file)

    def check_files(self, base_dir=None):
        """
        Check that referenced files exist. Update and return self.errors.
        """
        if self.location and not os.path.exists(self.location):
            msg = 'ABOUT file location: {} does not exists.'.format(self.location)
            self.errors.append(Error(CRITICAL, msg))

        base_dir = base_dir or os.path.dirname(self.location)

        if not os.path.exists(base_dir):
            msg = 'base_dir: {} does not exists: unable to check files existence.'.format(base_dir)
            self.errors.append(Error(CRITICAL, msg))
            return

        about_resource_loc = self.about_resource_loc(base_dir)
        if about_resource_loc and not os.path.exists(about_resource_loc):
            msg = 'File about_resource: "{}" does not exists'.format(self.about_resource)
            self.errors.append(Error(CRITICAL, msg))

        notice_file_loc = self.notice_file_loc(base_dir)
        if notice_file_loc and not os.path.exists(notice_file_loc):
            msg = 'File notice_file: "{}" does not exists'.format(self.notice_file)
            self.errors.append(Error(CRITICAL, msg))

        changelog_file_loc = self.changelog_file_loc(base_dir)
        if changelog_file_loc and not os.path.exists(changelog_file_loc):
            msg = 'File changelog_file: "{}" does not exists'.format(self.changelog_file)
            self.errors.append(Error(CRITICAL, msg))

        for license in self.licenses:  # NOQA
            license_file_loc = license.file_loc(base_dir)
            if not os.path.exists(license_file_loc):
                msg = 'License file: "{}" does not exists'.format(license.file)
                self.errors.append(Error(CRITICAL, msg))

        return self.errors

    def load_files(self, base_dir=None):
        """
        Load all referenced license and notice texts. Return a list of errors.
        """
        base_dir = base_dir or os.path.dirname(self.location)
        errors = []

        def _load_text(loc):
            if loc:
                text = None
                try:
                    # text can be garbage and not valid UTF
                    with io.open(loc, 'rb') as inp:
                        text = inp.read()
                    text = text.decode(encoding='utf-8', errors='replace')

                except Exception as e:
                    msg = 'Unable to read text file: {}\n'.format(loc) + str(e)
                    errors.append(Error(CRITICAL, msg))
                return text

        text = _load_text(self.notice_file_loc(base_dir))
        if text:
            self.notice_text = text

        for license in self.licenses:  # NOQA
            text = _load_text(license.file_loc(base_dir))
            if text:
                license.text = text

        return errors
