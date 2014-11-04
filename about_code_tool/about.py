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

from StringIO import StringIO
import codecs
from collections import namedtuple
import csv
from datetime import datetime
from email.parser import HeaderParser
from os.path import basename, dirname, join, normpath, realpath
import errno
import httplib
import logging
import optparse
import os
import posixpath
import socket
import string
import sys
import urlparse
import ntpath


__version__ = '1.0.1'

# See http://dejacode.org
__about_spec_version__ = '1.0'


__copyright__ = """
Copyright (c) 2013-2014 nexB Inc. All rights reserved.

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
    'dje_license',
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


HEADER_ROW_FIELDS = (('about_file',)
                     + MANDATORY_FIELDS
                     + OPTIONAL_FIELDS)


# SPDX License Identifiers from http://spdx.org/licenses/
# based on SPDX License List version 1.18 released on 2013-04-10
SPDX_LICENSES = (
    'AFL-1.1',
    'AFL-1.2',
    'AFL-2.0',
    'AFL-2.1',
    'AFL-3.0',
    'APL-1.0',
    'Aladdin',
    'ANTLR-PD',
    'Apache-1.0',
    'Apache-1.1',
    'Apache-2.0',
    'APSL-1.0',
    'APSL-1.1',
    'APSL-1.2',
    'APSL-2.0',
    'Artistic-1.0',
    'Artistic-2.0',
    'AAL',
    'BitTorrent-1.0',
    'BitTorrent-1.1',
    'BSL-1.0',
    'BSD-2-Clause',
    'BSD-2-Clause-FreeBSD',
    'BSD-2-Clause-NetBSD',
    'BSD-3-Clause',
    'BSD-3-Clause-Clear',
    'BSD-4-Clause',
    'BSD-4-Clause-UC',
    'CECILL-1.0',
    'CECILL-1.1',
    'CECILL-2.0',
    'CECILL-B',
    'CECILL-C',
    'ClArtistic',
    'CNRI-Python',
    'CNRI-Python-GPL-Compatible',
    'CPOL-1.02',
    'CDDL-1.0',
    'CDDL-1.1',
    'CPAL-1.0',
    'CPL-1.0',
    'CATOSL-1.1',
    'Condor-1.1',
    'CC-BY-1.0',
    'CC-BY-2.0',
    'CC-BY-2.5',
    'CC-BY-3.0',
    'CC-BY-ND-1.0',
    'CC-BY-ND-2.0',
    'CC-BY-ND-2.5',
    'CC-BY-ND-3.0',
    'CC-BY-NC-1.0',
    'CC-BY-NC-2.0',
    'CC-BY-NC-2.5',
    'CC-BY-NC-3.0',
    'CC-BY-NC-ND-1.0',
    'CC-BY-NC-ND-2.0',
    'CC-BY-NC-ND-2.5',
    'CC-BY-NC-ND-3.0',
    'CC-BY-NC-SA-1.0',
    'CC-BY-NC-SA-2.0',
    'CC-BY-NC-SA-2.5',
    'CC-BY-NC-SA-3.0',
    'CC-BY-SA-1.0',
    'CC-BY-SA-2.0',
    'CC-BY-SA-2.5',
    'CC-BY-SA-3.0',
    'CC0-1.0',
    'CUA-OPL-1.0',
    'D-FSL-1.0',
    'WTFPL',
    'EPL-1.0',
    'eCos-2.0',
    'ECL-1.0',
    'ECL-2.0',
    'EFL-1.0',
    'EFL-2.0',
    'Entessa',
    'ErlPL-1.1',
    'EUDatagrid',
    'EUPL-1.0',
    'EUPL-1.1',
    'Fair',
    'Frameworx-1.0',
    'FTL',
    'AGPL-1.0',
    'AGPL-3.0',
    'GFDL-1.1',
    'GFDL-1.2',
    'GFDL-1.3',
    'GPL-1.0',
    'GPL-1.0+',
    'GPL-2.0',
    'GPL-2.0+',
    'GPL-2.0-with-autoconf-exception',
    'GPL-2.0-with-bison-exception',
    'GPL-2.0-with-classpath-exception',
    'GPL-2.0-with-font-exception',
    'GPL-2.0-with-GCC-exception',
    'GPL-3.0',
    'GPL-3.0+',
    'GPL-3.0-with-autoconf-exception',
    'GPL-3.0-with-GCC-exception',
    'LGPL-2.1',
    'LGPL-2.1+',
    'LGPL-3.0',
    'LGPL-3.0+',
    'LGPL-2.0',
    'LGPL-2.0+',
    'gSOAP-1.3b',
    'HPND',
    'IPL-1.0',
    'Imlib2',
    'IJG',
    'Intel',
    'IPA',
    'ISC',
    'JSON',
    'LPPL-1.3a',
    'LPPL-1.0',
    'LPPL-1.1',
    'LPPL-1.2',
    'LPPL-1.3c',
    'Libpng',
    'LPL-1.02',
    'LPL-1.0',
    'MS-PL',
    'MS-RL',
    'MirOS',
    'MIT',
    'Motosoto',
    'MPL-1.0',
    'MPL-1.1',
    'MPL-2.0',
    'MPL-2.0-no-copyleft-exception',
    'Multics',
    'NASA-1.3',
    'Naumen',
    'NBPL-1.0',
    'NGPL',
    'NOSL',
    'NPL-1.0',
    'NPL-1.1',
    'Nokia',
    'NPOSL-3.0',
    'NTP',
    'OCLC-2.0',
    'ODbL-1.0',
    'PDDL-1.0',
    'OGTSL',
    'OLDAP-2.2.2',
    'OLDAP-1.1',
    'OLDAP-1.2',
    'OLDAP-1.3',
    'OLDAP-1.4',
    'OLDAP-2.0',
    'OLDAP-2.0.1',
    'OLDAP-2.1',
    'OLDAP-2.2',
    'OLDAP-2.2.1',
    'OLDAP-2.3',
    'OLDAP-2.4',
    'OLDAP-2.5',
    'OLDAP-2.6',
    'OLDAP-2.7',
    'OPL-1.0',
    'OSL-1.0',
    'OSL-2.0',
    'OSL-2.1',
    'OSL-3.0',
    'OLDAP-2.8',
    'OpenSSL',
    'PHP-3.0',
    'PHP-3.01',
    'PostgreSQL',
    'Python-2.0',
    'QPL-1.0',
    'RPSL-1.0',
    'RPL-1.1',
    'RPL-1.5',
    'RHeCos-1.1',
    'RSCPL',
    'Ruby',
    'SAX-PD',
    'SGI-B-1.0',
    'SGI-B-1.1',
    'SGI-B-2.0',
    'OFL-1.0',
    'OFL-1.1',
    'SimPL-2.0',
    'Sleepycat',
    'SMLNJ',
    'SugarCRM-1.1.3',
    'SISSL',
    'SPL-1.0',
    'Watcom-1.0',
    'NCSA',
    'VSL-1.0',
    'W3C',
    'WXwindows',
    'Xnet',
    'X11',
    'XFree86-1.1',
    'YPL-1.0',
    'YPL-1.1',
    'Zimbra-1.3',
    'Zlib',
    'ZPL-1.1',
    'ZPL-2.0',
    'ZPL-2.1',
)


# Maps lowercase id to standard ids with official case
SPDX_LICENSE_IDS = dict((name.lower(), name) for name in SPDX_LICENSES)


# Use DJE License Name
COMMON_LICENSES = (
    'AES-128 v3.0 License',
    'Apache License 1.1',
    'Apache License 2.0',
    'Apple Attribution License 1997',
    'Apple Example Code License',
    'Apple Public Source License 2.0',
    'Arphic Public License',
    'Artistic License (Perl) 1.0',
    'Artistic License 2.0',
    'Bitstream Vera Font License',
    'Boost Software License 1.0',
    'Broadcom CFE License',
    'BSD-Modified',
    'BSD-Original',
    'BSD-Original-UC',
    'BSD-Simplified',
    'CMU Computing Services License',
    'Common Development and Distribution License 1.0',
    'Common Development and Distribution License 1.1',
    'Common Public License 1.0',
    'Creative Commons Attribution License 2.5',
    'Creative Commons Attribution Share Alike License 3.0',
    'Curl License',
    'FreeType Project License',
    'GNU General Public License 2.0',
    'GNU General Public License 2.0 with Bison exception',
    'GNU General Public License 2.0 with GLIBC  exception',
    'GNU General Public License 3.0',
    'GNU Lesser General Public License 2.1',
    'GNU Library General Public License 2.0',
    'GPL 2.0 or later with Linking exception',
    'GPL 2.0 with Broadcom Linking exception',
    'Independent JPEG Group License',
    'ISC License (ISCL)',
    'Larabie Fonts EULA',
    'Libpng License',
    'Microsoft Limited Public License',
    'Microsoft Public License',
    'Microsoft Reciprocal License',
    'Microsoft TrueType Fonts EULA',
    'MIT License',
    'Mozilla Public License 1.1',
    'Net SNMP License',
    'Netscape Public License 1.1',
    'NTP License',
    'OpenSSL/SSLeay License',
    'Original SSLeay License with Windows exception',
    'RSA Data Security MD4',
    'RSA Data Security MD5',
    'SFL License Agreement',
    'SGI Free Software License B v2.0',
    'Sun RPC License',
    'TCL/TK License',
    'Tidy License',
    'University of Illinois/NCSA Open Source License',
    'X11 License',
    'ZLIB License',
)

def posix_path(path):
    """
    Return a path using the posixpath separator given a path that may
    contain posix or windows separators, converting \ to /.
    """
    return path.replace(ntpath.sep, posixpath.sep)


def is_about_file(path):
    """
    Return True if the path represents a valid ABOUT file name.
    """
    return path.lower().endswith('.about')


def resource_name(resource_path):
    """
    Return a resource name based on a posix path (either the filename or
    directory name). Recurse to handle paths that ends with a path separator
    """
    left, right = posixpath.split(resource_path)
    if right:
        return right.strip()
    elif left and left != '/':
        # recurse for directories that end up with a /
        return resource_name(left)
    else:
        return ''


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
                # The following code is to catch is the input contians any
                # multiple licenses
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
        supported = string.digits + string.ascii_letters + '_-.'
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
        return self.parsed.get('dje_license_name', '')

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
        # FIXME: we should not accept both a file and dir location as input
        paths = []
        if location:
            if os.path.isfile(location) and is_about_file(location):
                paths.append(location)
            else:
                for root, _, files in os.walk(location):
                    for name in files:
                        if is_about_file(name):
                            paths.append(os.path.join(root, name))
        # normalize the paths to use posix path separators
        paths = [posix_path(p)for p in paths]
        return paths

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
        user_loc = self.location
        if os.path.isdir(self.normalized_location):
            subpath = location.partition(os.path.basename(os.path.normpath(user_loc)))[2]
            if user_loc[-1] == '/':
                user_loc = user_loc.rpartition('/')[0]
            if user_loc[-1] == '\\':
                user_loc = user_loc.rpartition('\\')[0]
            return (user_loc + subpath).replace('\\', '/')
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

    def generate_attribution(self, template_path=None, limit_to=None):
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
            template_path = join(dirname(realpath(__file__)),
                                 "templates/default.html")

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

        # Following code contains duplication and perhaps needs to do some
        # refactoring
        if limit_to:
            for component in not_process_components:
                for about_object in self:
                    # The about_object.location is the absolute path of the ABOUT
                    # file. The purpose of the following partition is to match
                    # the about_file's location with the input list.
                    about_relative_path = about_object.location.partition(
                                                    normpath(self.location))[2]

                    if component == about_relative_path:
                        component_exist = True
                        about_content = about_object.validated_fields
                        if '\n' in about_object.get_dje_license_name():
                            msg = ('Multiple licenses is not supported. '
                                   'Skipping License generation.')
                            err = Error(GENATTRIB, 'dje_license',
                                        about_object.get_dje_license_name(), msg)
                            self.genattrib_errors.append(err)

                        lic_text = unicode(about_object.license_text(),
                                           errors='replace')
                        notice_text = unicode(about_object.notice_text(),
                                              errors='replace')
                        about_content['license_text'] = lic_text
                        about_content['notice_text'] = notice_text

                        license_dict[about_object.get_dje_license_name()] = about_content['license_text']

                        # report error if no license_text is found
                        if not about_content.get('license_text')\
                            and not about_content.get('notice_text')\
                            and not '\n' in about_object.get_dje_license_name():
                            msg = ('No license_text found. '
                                   'Skipping License generation.')
                            err = Error(GENATTRIB, 'name',
                                        about_object.get_about_name(), msg)
                            self.genattrib_errors.append(err)
                        about_object_fields.append(about_content)
                        break
                if not component_exist:
                    msg = ('The requested ABOUT file: %r does not exist. '
                           'No attribution generated for this file.' % component)
                    err = Error(GENATTRIB, 'about_file', component, msg)
                    self.genattrib_errors.append(err)
        else:
            for about_object in self:
                about_content = about_object.validated_fields
                if '\n' in about_object.get_dje_license_name():
                    msg = ('Multiple licenses is not supported. '
                           'Skipping License generation.')
                    err = Error(GENATTRIB, 'dje_license',
                                about_object.get_dje_license_name(), msg)
                    self.genattrib_errors.append(err)

                lic_text = unicode(about_object.license_text(),
                                   errors='replace')
                notice_text = unicode(about_object.notice_text(),
                                      errors='replace')
                about_content['license_text'] = lic_text
                about_content['notice_text'] = notice_text

                license_dict[about_object.get_dje_license_name()] = about_content['license_text']

                # report error if no license_text is found
                if not about_content.get('license_text')\
                    and not about_content.get('notice_text')\
                    and not '\n' in about_object.get_dje_license_name():
                    msg = ('No license_text found. '
                           'Skipping License generation.')
                    err = Error(GENATTRIB, 'name',
                                about_object.get_about_name(), msg)
                    self.genattrib_errors.append(err)
                about_object_fields.append(about_content)

        # We want to display common_licenses in alphabetical order
        license_key = []
        license_text_list = []
        for key in sorted(license_dict):
            license_key.append(key)
            license_text_list.append(license_dict[key])

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
            msg = ('The requested ABOUT file: %(afp)r does not exist. '
                   'No attribution generated for this file.' % locals())
            err = Error(GENATTRIB, 'about_file', path, msg)
            self.genattrib_errors.append(err)

    def get_genattrib_errors(self):
        return self.genattrib_errors


USAGE_SYNTAX = (
"""
    Input can be a file or directory.
    Output must be a file with a .csv extension.
"""
)


VERBOSITY_HELP = (
"""
Print more or fewer verbose messages while processing ABOUT files:
0 - Do not print any warning or error messages, just a total count (default)
1 - Print error messages
2 - Print error and warning messages
"""
)


ERROR = 0
OK = 1
def main(parser, options, args):
    overwrite = options.overwrite
    verbosity = options.verbosity

    if options.version:
        print('ABOUT tool {0}\n{1}'.format(__version__, __copyright__))
        return ERROR

    if verbosity == 1:
        handler.setLevel(logging.ERROR)
    elif verbosity >= 2:
        handler.setLevel(logging.WARNING)

    if not len(args) == 2:
        print('Input and Output paths are required.')
        print()
        parser.print_help()
        return errno.EEXIST

    input_path, output_path = args
    output_path = os.path.abspath(output_path)

    if not os.path.exists(input_path):
        print('Input path does not exist.')
        print()
        parser.print_help()
        return errno.EEXIST

    if os.path.isdir(output_path):
        print('Output must be a file, not a directory.')
        print()
        parser.print_help()
        return errno.EISDIR

    if not output_path.endswith('.csv'):
        print('Output file name must end with ".csv".')
        print()
        parser.print_help()
        return errno.EINVAL

    if os.path.exists(output_path) and not overwrite:
        print('Output file already exists. Select a different file name '
              'or use the --overwrite option.')
        print()
        parser.print_help()
        return errno.EEXIST

    if (not os.path.exists(output_path)
        or (os.path.exists(output_path) and overwrite)):
        collector = Collector(input_path)
        collector.write_to_csv(output_path)
        if collector.errors:
            print('%d errors detected.' % len(collector.errors))
        if collector.warnings:
            print('%d warnings detected.' % len(collector.warnings))
        return OK
    else:
        # we should never reach this
        assert False, 'Unsupported option(s).'


def get_parser():
    class MyFormatter(optparse.IndentedHelpFormatter):
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

    parser = optparse.OptionParser(
        usage='%prog [options] input_path output_path',
        description=USAGE_SYNTAX,
        add_help_option=False,
        formatter=MyFormatter(),
    )
    parser.add_option('-h', '--help', action='help', help='Display help')
    parser.add_option(
        '--version', action='store_true',
        help='Display current version, license notice, and copyright notice')
    parser.add_option('--overwrite', action='store_true',
                      help='Overwrite the output file if it exists')
    parser.add_option('--verbosity', type=int, help=VERBOSITY_HELP)
    return parser


if __name__ == '__main__':
    parser = get_parser()
    options, args = parser.parse_args()
    sys.exit(main(parser, options, args))
