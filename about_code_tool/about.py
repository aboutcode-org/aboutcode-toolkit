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

"""
AboutCode is a tool to process ABOUT files. ABOUT files are small text files
that document the provenance (aka. the origin and license) of software
components as well as the essential obligation such as attribution/credits and
source code redistribution. See the ABOUT spec at http://dejacode.org.

AbouCode reads and validates ABOUT files and collect software components
inventories.
"""

from __future__ import print_function

from StringIO import StringIO
import codecs
from collections import namedtuple
import csv
from datetime import datetime
from email.parser import HeaderParser
import errno
import httplib
import logging
import optparse
import os
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import normpath
from os.path import realpath
import socket
import string
import sys
import urlparse

from help import VERBOSITY_HELP
from help import __full_info__
from help import __version_info__
from licenses import COMMON_LICENSES
from licenses import SPDX_LICENSE_IDS
from util import ImprovedFormatter
from util import canonical_path
from util import is_about_file
from util import on_windows
from util import path_exists
from util import posix_path
from util import remove_unc


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.CRITICAL)
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)


def repr_problem(obj):
    """
    Return a formatted representation of a given Warn or Error object
    suitable for reporting.
    """
    field_name = obj.field_name
    field_value = obj.field_value
    message = obj.message
    return ('Field: %(field_name)s, '
            'Value: %(field_value)s, '
            'Message: %(message)s' % locals())


Warn = namedtuple('Warn', 'code field_name field_value message',)
Warn.__repr__ = repr_problem


Error = namedtuple('Error', 'code field_name field_value message',)
Error.__repr__ = repr_problem


IGNORED = 'field or line ignored problem'
VALUE = 'missing or empty or multiple value problem'
FILE = 'file problem'
URL = 'URL problem'
VCS = 'Version control problem'
DATE = 'Date problem'
ASCII = 'ASCII problem'
SPDX = 'SPDX license problem'
UNKNOWN = 'Unknown problem'
GENATTRIB = 'Attribution generation problem'


MANDATORY_FIELDS = (
    'name',
    'version',
)


BASIC_FIELDS = (
    'about_resource',
    'spec_version',
    'date',
    'description',
    'description_file',
    'home_url',
    'download_url',
    'readme',
    'readme_file',
    'install',
    'install_file',
    'changelog',
    'changelog_file',
    'news',
    'news_file',
    'news_url',
    'notes',
    'notes_file',
)


OWNERSHIP_FIELDS = (
    'contact',
    'owner',
    'author',
    'author_file',
    'copyright',
    'copyright_file',
)


LICENSE_FIELDS = (
    'notice_file',
    'notice_url',
    'license_text_file',
    'license_url',
    'license_spdx',
)


FLAG_FIELDS = (
    'redistribute',
    'attribute',
    'track_changes',
)


VCS_FIELDS = (
    'vcs_tool',
    'vcs_repository',
    'vcs_path',
    'vcs_tag',
    'vcs_branch',
    'vcs_revision',
)


CHECKSUM_FIELDS = (
    'checksum_sha1',
    'checksum_md5',
    'checksum_sha256'
)


DJE_FIELDS = (
    'dje_component',
    'dje_license_key',
    'dje_organization',
    'dje_license_name'
)


OPTIONAL_FIELDS = (BASIC_FIELDS
                   + OWNERSHIP_FIELDS
                   + LICENSE_FIELDS
                   + FLAG_FIELDS
                   + VCS_FIELDS
                   + CHECKSUM_FIELDS
                   + DJE_FIELDS)


FILE_LOCATIONS_FIELDS = (
    'about_resource_location',
    'description_file_location',
    'readme_file_location',
    'install_file_location',
    'changelog_file_location',
    'news_file_location',
    'notes_file_location',
    'author_file_location',
    'copyright_file_location',
    'notice_file_location',
    'license_text_file_location',
)


ERROR_WARN_FIELDS = (
    'warnings',
    'errors'
)


HEADER_ROW_FIELDS = ('about_file',) + MANDATORY_FIELDS + OPTIONAL_FIELDS


def check_network_connection():
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


has_network_connectivity = check_network_connection()


class AboutFile(object):
    """
    Represent an ABOUT file and functions to parse and validate a file.
    """
    def __init__(self, location=None):
        self.about_resource = None
        # The os.path.abspath(None) will cause error in linux system.
        # See https://bugs.python.org/issue22587
        # Note that the os.path.abspath is needed for windows when there
        # is long path/filename.
        if on_windows:
            self.location = os.path.abspath(location)
        else:
            self.location = location

        self.parsed = None
        self.parsed_fields = None
        self.validated_fields = {}

        # map _file fields to a resolved OS file system absolute location
        # this is not used at all for now
        self.file_fields_locations = {}

        self.warnings = []
        self.errors = []

        if self.location:
            self.parse()

    def __repr__(self):
        return repr((self.parsed, self.parsed_fields, self.validated_fields,))

    def parse(self):
        """
        Parse and validate a the file at self.location object in an ABOUT
        structure.
        """
        try:
            with open(self.location, 'rU') as file_in:
                # FIXME: we should open the file only once, it is always small
                # enough to be kept in memory
                no_blank_lines, pre_proc_warnings = self.pre_process(file_in)
                self.warnings.extend(pre_proc_warnings)
                # HeaderParser.parse returns the parsed file as keys and
                # values (allows for multiple keys, and it doesn't validate)
                self.parsed = HeaderParser().parse(no_blank_lines)
        except IOError as e:
            err_msg = 'Cannot read ABOUT file:' + repr(e)
            self.errors.append(Error(FILE, None, self.location, err_msg))
        except Exception as e:
            err_msg = 'Unknown ABOUT processing error:' + repr(e)
            self.errors.append(Error(UNKNOWN, None, self.location, err_msg))

        if self.parsed:
            self.warnings.extend(self.normalize())
            self.validate()

    def pre_process(self, file_in):
        """
        Pre-process an ABOUT file before using the email header parser.
        Return a tuple with a file-like object and a list of warnings.
        In the file-like object we remove:
         - blank/empty lines
         - invalid lines that cannot be parsed
         - spaces around the colon separator
        This also checks for field names with incorrect characters that could
        not be otherwise parsed.
        """
        # TODO: add line endings normalization to LF
        about_string = ''
        warnings = []
        last_line_is_field_or_continuation = False

        for line in file_in.readlines():
            # continuation line
            if line.startswith(' '):
                warn = self.check_line_continuation(
                    line, last_line_is_field_or_continuation)
                if last_line_is_field_or_continuation:
                    about_string += line
                if warn:
                    warnings.append(warn)
                continue

            # empty or blank line
            if not line.rstrip():
                last_line_is_field_or_continuation = False
                continue

            # From here, we should have a field line and consider not a field
            # line if there is no colon
            warn, has_colon = self.check_line_has_colon(line)
            if not has_colon:
                last_line_is_field_or_continuation = False
                warnings.append(warn)
                continue

            # invalid space characters
            splitted = line.split(':', 1)
            field_name = splitted[0].rstrip()
            warn = self.check_invalid_space_characters(field_name, line)
            if warn:
                last_line_is_field_or_continuation = False
                warnings.append(warn)
                continue
            else:
                line = field_name + ':' + splitted[1]

            # invalid field characters
            _invalid_chars, warn = (
                    check_invalid_chars(field_name, line))
            if warn:
                warnings.append(warn)
                last_line_is_field_or_continuation = False
                continue

            # finally add valid field lines
            last_line_is_field_or_continuation = True
            about_string += line

        # TODO: we should either yield and not return a stringIO or return a
        # string
        return StringIO(about_string), warnings

    @staticmethod
    def check_line_continuation(line, continuation):
        warnings = ''
        if not continuation:
            msg = 'Line does not contain a field or continuation: ignored.'
            warnings = Warn(IGNORED, None, line, msg)
        return warnings

    @staticmethod
    def check_line_has_colon(line):
        warnings = ''
        has_colon = True
        if ':' not in line:
            msg = 'Line does not contain a field: ignored.'
            warnings = Warn(IGNORED, None, line, msg)
            has_colon = False
        return warnings, has_colon

    @staticmethod
    def check_invalid_space_characters(field_name, line):
        warnings = ''
        if ' ' in field_name:
            msg = 'Field name contains spaces: line ignored.'
            warnings = Warn(IGNORED, field_name, line, msg)
        return warnings


    def normalize(self):
        """
        Convert field names to lower case. If a field name occurs multiple
        times, keep only the last occurrence.
        """
        warnings = []
        for field_name, value in self.parsed.items():
            field_name = field_name.lower()
            if field_name in self.validated_fields:
                field_value = self.validated_fields[field_name]
                msg = 'Duplicate field names found: ignored.'
                warnings.append(Warn(IGNORED, field_name, field_value, msg))
            # if this is a multi-line value, we want to strip the first space
            # of the continuation lines
            if '\n' in value:
                value = value.replace('\n ', '\n')
            self.validated_fields[field_name] = value
        return warnings

    def validate(self):
        """
        Validate a parsed about file.
        """
        invalid_name = self.invalid_chars_in_about_file_name(self.location)
        if invalid_name:
            msg = 'The filename contains invalid character.'
            self.errors.append(Error(ASCII, None, invalid_name, msg))
        dup_name = self.duplicate_file_names_when_lowercased(self.location)
        if dup_name:
            msg = 'Duplicated filename in the same directory detected.'
            self.errors.append(Error(FILE, None, dup_name, msg))
        self.validate_field_values_are_not_empty()
        self.validate_about_resource_exist()
        self.validate_mandatory_fields_are_present()

        for field_name, value in self.validated_fields.items():
            self.check_is_ascii(self.validated_fields.get(field_name))
            self.validate_file_field_exists(field_name, value)
            self.validate_url_field(field_name, network_check=False)
            self.validate_spdx_license(field_name, value)
            self.check_date_format(field_name)

    def validate_field_values_are_not_empty(self):
        for field_name, value in self.validated_fields.items():
            if value.strip():
                continue

            if field_name in MANDATORY_FIELDS:
                err = Error(VALUE, field_name, None,
                            'This mandatory field has no value.')
                self.errors.append(err)
            elif field_name in OPTIONAL_FIELDS:
                err = Warn(VALUE, field_name, None,
                           'This optional field has no value.')
                self.warnings.append(err)
            else:
                warn = Warn(VALUE, field_name, None,
                            'This field has no value.')
                self.warnings.append(warn)

    def _exists(self, file_path):
        """
        Return True if path exists.
        """
        if file_path:
            return os.path.exists(self._location(file_path))

    def _location(self, file_path):
        """
        Return absolute location for a posix file_path.
        """
        if file_path:
            file_path = os.path.join(os.path.dirname(self.location),
                                     file_path.strip())
            file_path = os.path.abspath(file_path)
        return file_path

    def _save_location(self, field_name, file_path):
        # TODO: we likely should not inject this in the validated fields and
        # maybe use something else for this
        self.file_fields_locations[field_name] = self._location(file_path)

    def validate_about_resource_exist(self):
        """
        Ensure that the resource referenced by the about_resource field
        exists.
        """
        about_resource = 'about_resource'
        # Note: a missing 'about_resource' field error will be caught in
        # validate_mandatory_fields_are_present(self)
        if (about_resource in self.validated_fields
            and self.validated_fields[about_resource]):
            self.about_resource = self.validated_fields[about_resource]

            if not self._exists(self.about_resource):
                self.errors.append(Error(FILE, about_resource,
                                         self.about_resource,
                                         'File does not exist.'))
        self._save_location(about_resource, self.about_resource)

    def validate_file_field_exists(self, field_name, file_path):
        """
        Ensure a _file field in the OPTIONAL_FIELDS points to an existing
        file.
        """
        if not field_name.endswith('_file'):
            return

        if not file_path:
            return

        if not field_name in OPTIONAL_FIELDS:
            return

        if not self._exists(file_path):
            self.warnings.append(Warn(FILE, field_name, file_path,
                                      'File does not exist.'))
            return

        self._save_location(field_name, file_path)

        try:
            with codecs.open(self._location(file_path),
                             'r', 'utf8', errors='replace') as f:
                # attempt to read the file to catch codec errors
                f.readlines()
        except Exception as e:
            self.errors.append(Error(FILE, field_name, file_path,
                                     'Cannot read file: %s' % repr(e)))
            return

    def validate_mandatory_fields_are_present(self):
        """
        Validate that mandatory fields are present.
        """
        for field_name in MANDATORY_FIELDS:
            if field_name not in self.validated_fields:
                self.errors.append(Error(VALUE, field_name, None,
                                         'Mandatory field missing'))

    def validate_known_optional_fields(self, field_name):
        """
        Validate which known optional fields are present.
        """
        if (field_name not in OPTIONAL_FIELDS
                and field_name not in MANDATORY_FIELDS
                and field_name not in FILE_LOCATIONS_FIELDS):
            msg = 'Not a mandatory or optional field'
            self.warnings.append(Warn(IGNORED, field_name,
                                      self.validated_fields[field_name],
                                      msg))

    def validate_spdx_license(self, field_name, field_value):
        if not field_name == 'license_spdx':
            return
        # FIXME: do we support more than one ID?
        # Not support multiple IDs
        spdx_id = field_value
        # valid id, matching the case
        if spdx_id in SPDX_LICENSE_IDS.values():
            return

        spdx_id_lower = spdx_id.lower()

        # conjunctions
        if spdx_id_lower in ['or', 'and']:
            return

        # lowercase check
        try:
            standard_id = SPDX_LICENSE_IDS[spdx_id_lower]
        except KeyError:
            self.errors.append(Error(SPDX, field_name, spdx_id,
                                     'Invalid SPDX license id.'))
        else:
            msg = ('Non standard SPDX license id case. Should be %r.'
                   % (standard_id))
            self.warnings.append(Warn(SPDX, field_name, id, msg))

    def validate_url_field(self, field_name, network_check=False):
        """
        Ensure that URL field is a valid URL. If network_check is True, do a
        network check to verify if it points to a live URL.
        """
        if (not field_name.endswith('_url')
            or field_name not in OPTIONAL_FIELDS):
            return

        # The "field is empty" warning will be thrown in the
        # "validate_field_values_are_not_empty"
        value = self.validated_fields[field_name]
        if not value:
            return

        try:
            is_url = self.check_url(value, network_check)
            if not is_url:
                msg = ('URL is not in a valid format or is not reachable.')
                self.warnings.append(Warn(URL, field_name, value, msg))
        except KeyError:
            return

    def check_is_ascii(self, s):
        """
        Return True if string is composed only of US-ASCII characters.
        """
        try:
            s.decode('ascii')
        except (UnicodeEncodeError, UnicodeDecodeError):
            msg = '%s is not valid US-ASCII.' % (s,)
            self.errors.append(Error(ASCII, s, None, msg))
            return False
        return True

    def check_date_format(self, field_name):
        """
        Return True if date_string has a valid date format: YYYY-MM-DD.
        """
        if field_name != 'date':
            return

        date_strings = self.validated_fields[field_name]
        if not date_strings:
            return

        supported_dateformat = '%Y-%m-%d'
        try:
            formatted = datetime.strptime(date_strings, supported_dateformat)
            return formatted
        except ValueError:
            msg = 'Unsupported date format, use YYYY-MM-DD.'
            self.warnings.append(Warn(DATE, field_name, date_strings, msg))
        return False

    def check_url(self, url, network_check=False):
        """
        Return True if a URL is valid. Optionally check that this is a live
        URL (using a HEAD request without downloading the whole file).
        """
        scheme, netloc, path, _p, _q, _frg = urlparse.urlparse(url)

        url_has_valid_format = scheme in ('http', 'https', 'ftp') and netloc
        if not url_has_valid_format:
            return False

        if network_check:
            if has_network_connectivity:
                # FIXME: HEAD request DO NOT WORK for ftp://
                return self.check_url_reachable(netloc, path)
            else:
                print('No network connection detected.')
        return url_has_valid_format

    @staticmethod
    def check_url_reachable(host, path):
        # FIXME: we are only checking netloc and path ... NOT the whole url
        # FXIME: this will not work with FTP
        try:
            conn = httplib.HTTPConnection(host)
            conn.request('HEAD', path)
        except (httplib.HTTPException, socket.error):
            return False
        else:
            # FIXME: we will consider a 404 as a valid status (True value)
            # This is the list of all the HTTP status code
            # http://en.wikipedia.org/wiki/List_of_HTTP_status_codes
            return conn.getresponse().status

    def get_custom_field_keys(self):
        custom_key = []
        for key in self.validated_fields:
            if key not in MANDATORY_FIELDS + OPTIONAL_FIELDS:
                custom_key.append(key)
        return custom_key

    def get_row_data(self, updated_path, custom_keys):
        """
        Create a csv compatible row of data for this object.
        """
        row = [updated_path]
        no_multi_license_fields = ('license_text_file',
                                    'license_spdx',
                                    'dje_license',
                                    'dje_license_name')
        for field in MANDATORY_FIELDS + OPTIONAL_FIELDS:
            if field in self.validated_fields:
                row += [self.validated_fields[field]]
                # The following code is to catch if the input contains any multiple licenses
                if field in no_multi_license_fields:
                    for lic_field in no_multi_license_fields:
                        try:
                            if '\n' in self.validated_fields[lic_field]:
                                self.errors.append(Error(VALUE,
                                                         lic_field,
                                                         self.validated_fields[field],
                                                         "Multiple Licenses are not supported."))
                        except:
                            pass
            else:
                row += ['']

        # Add custom field value
        for key in custom_keys:
            try:
                row += [self.validated_fields[key]]
            except:
                row += ['']

        warnings = [repr(w) for w in self.warnings]
        errors = [repr(e) for e in self.errors]
        row += ['\n'.join(warnings), '\n'.join(errors)]
        return row

    @staticmethod
    def invalid_chars_in_about_file_name(file_path):
        """
        Return a sequence of invalid characters found in a file name.
        From spec 0.8.0:
            A file name can contain only these US-ASCII characters:
            <li> digits from 0 to 9 </li>
            <li> uppercase and lowercase letters from A to Z</li>
            <li> the _ underscore, - dash and . period signs. </li>
        """
        supported = string.digits + string.ascii_letters + '_-.+'
        # Using the resource_name(file_path) will yield the following error on
        # windows:
        # Field: None, Value: [':', '\\', '\\', '\\', '\\', '\\', '\\'],
        # Message: The filename contains invalid character.
        # Perhaps it is better to simply use the os.path.basename(file_path)
        # file_name = resource_name(file_path)
        file_name = os.path.basename(file_path)
        return [char for char in file_name if char not in supported]

    @staticmethod
    def duplicate_file_names_when_lowercased(file_location):
        """
        Return a sequence of duplicate file names in the same directory as
        file_location when lower cased.
        From spec 0.8.0:
            The case of a file name is not significant. On case-sensitive file
            systems (such as Linux), a tool must raise an error if two ABOUT
            files stored in the same directory have the same lowercase file
            name.
        """
        # TODO: Add a test, only for a case sensitive FS, such as on Linux
        names = []
        for name in os.listdir(os.path.dirname(file_location)):
            if name.lower() in names:
                names.append(name)
        return names

    def license_text(self):
        """
        Return the license text if the license_text_file field exists and the
        field value (file) exists.
        """
        location = self.file_fields_locations.get('license_text_file',)
        if location and os.path.exists(location):
            try:
                with open(location, 'rU') as f:
                    return f.read()
            except Exception :
                pass
        return ''

    def notice_text(self):
        """
        Return the text in a notice file if the notice_file field exists in a
        .ABOUT file and the file that is in the notice_file field exists
        """
        location = self.file_fields_locations.get('notice_file', '')
        if location:
            try:
                with open(location, 'rU') as f:
                    return f.read()
            except Exception:
                pass
        return ''

    def get_about_name(self):
        """
        Return the about object's name.
        """
        return self.parsed.get('name', '')

    def get_dje_license_name(self):
        """
        Return the about object's dje_license_name.
        """
        try:
            return self.parsed.get('dje_license_name', '')
        except:
            return ''

def check_invalid_chars(field_name, line):
    """
    Return a sequence of invalid characters in a field name.
    From spec 0.8.0:
        A field name can contain only these US-ASCII characters:
        <li> digits from 0 to 9 </li>
        <li> uppercase and lowercase letters from A to Z</li>
        <li> the _ underscore sign. </li>
    """
    supported = string.digits + string.ascii_letters + '_'
    warnings = ''
    invalid_chars = [char for char in field_name
                     if char not in supported]
    if invalid_chars:
        msg = ('Field name contains invalid characters: %r: line ignored.'
               % (''.join(invalid_chars)))

        warnings = Warn(IGNORED, field_name, line, msg)
    return invalid_chars, warnings



class Collector(object):
    """
    Collect ABOUT files.
    """
    def __init__(self, location):
        """
        Collect ABOUT files at location and create one AboutFile instance per
        file.
        """
        assert location
        self.location = location
        normed_loc = os.path.expanduser(location)
        normed_loc = os.path.normpath(normed_loc)
        normed_loc = os.path.abspath(normed_loc)
        normed_loc = posix_path(normed_loc)
        assert os.path.exists(normed_loc)
        self.normalized_location = normed_loc
        self.abouts = [AboutFile(f) for f in self.collect(normed_loc)]

        self._errors = []
        self._warnings = []
        self.genattrib_errors = []
        self.summarize_issues()

    def __iter__(self):
        """
        Iterate collected AboutFile.
        """
        return iter(self.abouts)

    @staticmethod
    def collect(location):
        """
        Return a list of locations of *.ABOUT files given the location of an
        ABOUT file or a directory tree containing ABOUT files.
        Locations are normalized using posix path separators.
        """
        paths = []

        location = canonical_path(location)
        assert os.path.exists(location)

        if is_about_file(location):
            paths.append(location)
        else:
            for root, _, files in os.walk(location):
                for name in files:
                    if is_about_file(name):
                        paths.append(os.path.join(root, name))
        # always return posix paths
        return [posix_path(p) for p in paths]

    @property
    def errors(self):
        """
        Return a list of about.errors for every about instances.
        """
        # FIXME: this function is not needed.
        return self._errors

    @property
    def warnings(self):
        """
        Return a list of about.warnings for every about instances.
        """
        # FIXME: this function is not needed.
        return self._warnings

    def summarize_issues(self):
        """
        Summarize and log errors and warnings.
        """
        for about_object in self:
            relative_path = self.get_relative_path(about_object.location)

            if about_object.errors or about_object.warnings:
                logger.error('ABOUT File: %s' % relative_path)

            if about_object.errors:
                self._errors.extend(about_object.errors)
                logger.error(about_object.errors)

            if about_object.warnings:
                self._warnings.extend(about_object.warnings)
                logger.warning(about_object.warnings)

    def get_relative_path(self, location):
        """
        Return a path for a given ABOUT file location relative to and based on
        the provided collector normalized location.
        """
        user_loc = normpath(self.location)
        if os.path.isdir(self.normalized_location):
            # Making sure both are in posix path format before
            # doing any string partition.
            location = posix_path(location)
            user_loc = posix_path(user_loc)
            parent_name = basename(user_loc)
            subpath = '/' + parent_name + location.partition(user_loc)[2]
            if user_loc[-1] == '/':
                user_loc = user_loc.rpartition('/')[0]
            if user_loc[-1] == '\\':
                user_loc = user_loc.rpartition('\\')[0]
            return subpath.replace('\\', '/')
        else:
            return user_loc.replace('\\', '/')

    def custom_keys(self):
        custom_keys = []
        for about_object in self:
            keys = about_object.get_custom_field_keys()
            for key in keys:
                if key not in custom_keys:
                    custom_keys.append(key)
        return custom_keys

    def write_to_csv(self, output_path):
        """
        Build a row for each about instance and write results in CSV file
        located at `output_path`.
        """
        custom_keys = self.custom_keys()
        with open(output_path, 'wb') as output_file:
            csv_writer = csv.writer(output_file)
            header_row = HEADER_ROW_FIELDS
            # Add the non-supported fields if exist
            for key in custom_keys:
                header_row += (key,)
            header_row += ERROR_WARN_FIELDS
            csv_writer.writerow(header_row)

            for about_object in self:
                relative_path = self.get_relative_path(about_object.location)
                row_data = about_object.get_row_data(relative_path, custom_keys)
                csv_writer.writerow(row_data)

    def get_about_context(self, about_object):
        about_content = about_object.validated_fields
        has_multiple_licenses = '\n' in about_object.get_dje_license_name()
        if has_multiple_licenses:
            msg = 'Multiple licenses is not supported. Skipping License generation.'
            about_object.location = remove_unc(about_object.location)
            err = Error(GENATTRIB, 'dje_license', about_object.location, msg)
            self.genattrib_errors.append(err)

        lic_text = unicode(about_object.license_text(), errors='replace')
        notice_text = unicode(about_object.notice_text(), errors='replace')
        about_content['license_text'] = lic_text
        about_content['notice_text'] = notice_text

        # report error if no license_text is found
        if not lic_text and not notice_text and not has_multiple_licenses:
            msg = 'No license_text found. Skipping License generation.'
            about_object.location = remove_unc(about_object.location)
            err = Error(GENATTRIB, 'license_text_file', about_object.location, msg)
            self.genattrib_errors.append(err)
        return about_content

    def generate_attribution(self, template_path=None, limit_to=None, verification=None):
        """
        Generate an attribution file from the current list of ABOUT objects.
        The optional `limit_to` parameter allows to restrict the generated
        attribution to a specific list of component names.
        """
        try:
            import jinja2 as j2
        except ImportError:
            print('The Jinja2 templating library is required to generate '
                  'attribution texts. You can install it by running:'
                  '"configure"')
            return

        if not template_path:
            template_path = join(dirname(realpath(__file__)), 'templates/default.html')

        # FIXME: the template dir should be outside the code tree
        template_dir = dirname(template_path)
        template_file_name = basename(template_path)
        loader = j2.FileSystemLoader(template_dir)
        jinja_env = j2.Environment(loader=loader)
        try:
            template = jinja_env.get_template(template_file_name)
        except j2.TemplateNotFound:
            return
        limit_to = limit_to or []

        about_object_fields = []
        license_dict = {}

        not_process_components = list(limit_to)
        component_exist = False

        if limit_to:
            for component in not_process_components:
                for about_object in self:
                    # The about_object.location is the absolute path of the ABOUT
                    # file. The purpose of the following string partition is to
                    # match the about_file's location with the input list.
                    about_relative_path = about_object.location.partition(normpath(self.location))[2]
                    if component == posix_path(about_relative_path):
                        component_exist = True
                        about_content = self.get_about_context(about_object)
                        license_dict[about_object.get_dje_license_name()] = about_content['license_text']
                        about_object_fields.append(about_content)
                        break

                if not component_exist:
                    self.location = remove_unc(self.location)
                    loc = self.location + component
                    msg = 'The requested ABOUT file: %r does not exist. No attribution generated for this file.' % loc
                    err = Error(GENATTRIB, 'about_file', loc, msg)
                    self.genattrib_errors.append(err)
        else:
            for about_object in self:
                about_content = self.get_about_context(about_object)
                license_dict[about_object.get_dje_license_name()] = about_content['license_text']
                about_object_fields.append(about_content)

        # We want to display common_licenses in alphabetical order
        license_key = []
        license_text_list = []
        for key in sorted(license_dict):
            license_key.append(key)
            license_text_list.append(license_dict[key])

        # Create the verification CSV output
        if verification:
            # Define what will be shown in the verification output
            header_row = ('name', 'version', 'copyright', 'dje_license_name')
            with open(verification, 'wb') as verification_file:
                csv_writer = csv.writer(verification_file)
                csv_writer.writerow(header_row)
                for component in about_object_fields:
                    row_data = []
                    for key in header_row:
                        try:
                            row_data.append(component[key])
                        except:
                            row_data.append('')
                    csv_writer.writerow(row_data)

        # We should only pass the about_objects to the template.
        # However, this is a temp fix for the license summarization feature.
        rendered = template.render(about_objects=about_object_fields,
                                   license_keys=license_key,
                                   license_texts=license_text_list,
                                   common_licenses=COMMON_LICENSES)
        return rendered

    def check_paths(self, paths):
        """
        Check if each path in a list of ABOUT file paths exist in the
        collected ABOUT files. Add errors if it does not.
        """
        for path in paths:
            path = posix_path(path)
            afp = join(self.location, path)
            afp = remove_unc(afp)
            msg = ('The requested ABOUT file: %(afp)r does not exist. No attribution generated for this file.' % locals())
            err = Error(GENATTRIB, 'about_file', path, msg)
            self.genattrib_errors.append(err)

    def get_genattrib_errors(self):
        return self.genattrib_errors


USAGE_SYNTAX = (
"""
    <input_path> can be a file or directory containing .ABOUT files.
    <output_path> must be a file with a .csv extension to save the inventory collected from .ABOUT files.
"""
)


ERROR = 0
OK = 1

def main(parser, options, args):
    """
    Main commnand line entry point.
    """
    overwrite = options.overwrite
    verbosity = options.verbosity

    if options.version:
        print(__full_info__)
        return ERROR

    if verbosity == 1:
        handler.setLevel(logging.ERROR)
    elif verbosity >= 2:
        handler.setLevel(logging.WARNING)

    if not len(args) == 2:
        print('ERROR: <input_path> and <output_path> are required.')
        print()
        parser.print_help()
        return errno.EEXIST

    input_path, output_path = args
    output_path = os.path.abspath(output_path)

    if not path_exists(input_path):
        print('ERROR: <input_path>  does not exist.')
        print()
        parser.print_help()
        return errno.EEXIST

    if os.path.isdir(output_path):
        print('ERROR: <output_path> must be a file, not a directory.')
        print()
        parser.print_help()
        return errno.EISDIR

    if not output_path.endswith('.csv'):
        print('ERROR: <output_path> must be a CSV file ending with ".csv".')
        print()
        parser.print_help()
        return errno.EINVAL

    if path_exists(output_path) and not overwrite:
        print('ERROR: <output_path> file already exists. Select a different file name or use the --overwrite option.')
        print()
        parser.print_help()
        return errno.EEXIST

    if (not path_exists(output_path)
        or (path_exists(output_path) and overwrite)):
        collector = Collector(input_path)
        collector.write_to_csv(output_path)
        print('Completed.')
        if collector.errors:
            print('%d errors detected.' % len(collector.errors))
        if collector.warnings:
            print('%d warnings detected.' % len(collector.warnings))
        return OK
    else:
        # we should never reach this
        assert False, 'ERROR: Unsupported option(s).'


def get_parser():
    """
    Return a command line options parser.
    """
    parser = optparse.OptionParser(
        usage='%prog [options] input_path output_path',
        description=USAGE_SYNTAX,
        add_help_option=False,
        formatter=ImprovedFormatter(),
    )
    parser.add_option('-h', '--help', action='help', help='Print this help message and exit.')
    parser.add_option('--version', action='store_true', help='Print the current version and copyright notice and exit.')
    parser.add_option('--overwrite', action='store_true', help='Overwrite the file at <output_path> if it exists.')
    parser.add_option('--verbosity', type=int, help=VERBOSITY_HELP)
    return parser


if __name__ == '__main__':
    print(__version_info__)
    parser = get_parser()
    options, args = parser.parse_args()
    sys.exit(main(parser, options, args))
