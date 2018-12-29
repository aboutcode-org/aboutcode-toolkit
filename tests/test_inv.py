#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2014-2018 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

from collections import OrderedDict
import io
import shutil
import sys
import unittest
from unittest.case import skipIf

from aboutcode import CRITICAL
from aboutcode import INFO
from aboutcode import Error
from aboutcode import inv
from aboutcode import model
from aboutcode.util import csv
from aboutcode.util import on_windows
from aboutcode.util import to_posix

from testing_utils import check_json
from testing_utils import extract_test_loc
from testing_utils import get_temp_file
from testing_utils import get_test_loc

try:
    # Python 2
    unicode  # NOQA
except NameError:  # pragma: nocover
    # Python 3
    unicode = str  # NOQA


py3 = sys.version_info[0] == 3


def load_csv(location):
    """
    Read CSV at `location` and yield an ordered mapping for each row.
    """
    with io.open(location, encoding='utf-8') as csvfile:
        for row in csv.DictReader(csvfile):
            yield row


def check_csv(expected, result, regen=False):
    """
    Assert that the contents of two CSV files locations `expected` and
    `result` are equal.
    """
    if regen:
        shutil.copyfile(result, expected)
    expected = sorted([sorted(d.items()) for d in load_csv(expected)])
    result = [d.items() for d in load_csv(result)]
    result = sorted(sorted(items) for items in result)

    assert expected == result


def get_test_content(test_location):
    """
    Read file at test_location and return a unicode string.
    """
    return get_unicode_content(get_test_loc(test_location))


def get_unicode_content(location):
    """
    Read file at location and return a unicode string.
    """
    with io.open(location, encoding='utf-8') as doc:
        return doc.read()


def fix_location(packages, test_dir):
    """
    Fix the package.about_file_location by removing the `test_dir` from the path.
    """
    for a in packages:
        loc = a.about_file_location.replace(test_dir, '').strip('/\\')
        a.about_file_location = to_posix(loc)


class InventoryTest(unittest.TestCase):

    def test_collect_inventory_return_errors(self):
        test_loc = get_test_loc('test_inv/collect_inventory_errors')
        errors, _packages = inv.collect_inventory(test_loc)
        expected_errors = []
        assert expected_errors == errors

    @skipIf(on_windows and not py3, 'Windows support for long path requires https://docs.python.org/3/using/windows.html#removing-the-max-path-limitation')
    def test_collect_inventory_with_long_path(self):
        test_loc = extract_test_loc('test_inv/longpath.zip')
        _errors, packages = inv.collect_inventory(test_loc)

        expected_paths = [
            'longpath/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/non-supported_date_format.ABOUT',
            'longpath/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/supported_date_format.ABOUT'
        ]
        fix_location(packages, test_loc)

        assert sorted(expected_paths) == sorted([a.about_file_location for a in packages])

        expected_name = ['distribute', 'date_test']
        result_name = [a.name for a in packages]
        assert sorted(expected_name) == sorted(result_name)

    def test_collect_inventory_can_collect_a_single_file(self):
        test_loc = get_test_loc('test_inv/single_file/django_snippets_2413.ABOUT')
        errors, packages = inv.collect_inventory(test_loc)
        expected = []
        assert expected == errors
        expected_loc = get_test_loc('test_inv/single_file/django_snippets_2413.ABOUT-expected.json')
        result = [a.to_dict(with_path=True) for a in packages]
        check_json(expected_loc, result, regen=False)

    def test_collect_inventory_return_no_warnings_and_model_can_use_relative_paths(self):
        test_loc = get_test_loc('test_inv/rel/allAboutInOneDir')
        errors, _packages = inv.collect_inventory(test_loc)
        expected_errors = []
        result = [(e.severity, e.message) for e in errors if e.severity > INFO]
        assert expected_errors == result

    def test_collect_inventory_populate_about_file_path(self):
        test_loc = get_test_loc('test_inv/complete')
        errors, packages = inv.collect_inventory(test_loc)
        expected = []
        assert expected == errors

        expected = get_test_loc('test_inv/complete-expected.json')
        result = [a.to_dict(with_path=True) for a in packages]
        check_json(expected, result)

    def test_collect_inventory_with_multi_line(self):
        test_loc = get_test_loc('test_inv/multi_line_license_expression.ABOUT')
        errors, packages = inv.collect_inventory(test_loc)
        assert [] == errors
        expected = [
            'https://enterprise.dejacode.com/urn/?urn=urn:dje:license:mit',
            'https://enterprise.dejacode.com/urn/?urn=urn:dje:license:apache-2.0']
        results = [l.url for l in packages[0].licenses]
        assert expected == results

        assert 'mit OR apache-2.0' == packages[0].license_expression

    def test_collect_inventory_always_collects_custom_fields(self):
        test_loc = get_test_loc('test_inv/custom_fields.ABOUT')
        errors, packages = inv.collect_inventory(test_loc)
        expected = []
        assert expected == errors
        assert {'custom_mapping': 'test', 'resource': '.'} == packages[0].custom_fields

    def test_collect_inventory_does_not_raise_error_and_maintains_order_on_custom_fields(self):
        test_loc = get_test_loc('test_inv/custom_fields2.ABOUT')
        errors, packages = inv.collect_inventory(test_loc)
        expected_errors = []
        assert expected_errors == errors

        expected = [OrderedDict([
            ('about_resource', u'.'),
            ('name', u'test'),
            (u'custom_mapping', u'test'),
            (u'resource', u'.')])]
        assert expected == [a.to_dict() for a in packages]

    def test_collect_inventory_works_with_relative_paths(self):
        # FIXME: This test need to be run under src/aboutcode/
        # or otherwise it will fail as the test depends on the launching
        # location
        test_loc = get_test_loc('test_inv/relative')
        # Use '.' as the indication of the current directory
        test_loc1 = test_loc + '/./'
        # Use '..' to go back to the parent directory
        test_loc2 = test_loc + '/../relative'
        errors1, packages1 = inv.collect_inventory(test_loc1)
        assert [] == errors1
        expected = get_test_loc('test_inv/relative-1-expected.json')
        result = [a.to_dict() for a in packages1]
        check_json(expected, result)

        errors2, packages2 = inv.collect_inventory(test_loc2)
        assert [] == errors2
        expected = get_test_loc('test_inv/relative-2-expected.json')
        result = [a.to_dict() for a in packages2]
        check_json(expected, result)

    def test_collect_inventory_basic_from_directory(self):
        test_dir = get_test_loc('test_inv/basic')
        result_file = get_temp_file()
        errors, packages = inv.collect_inventory(test_dir)

        inv.save_as_csv(result_file, packages)
        assert [] == errors

        expected = get_test_loc('test_inv/basic/expected.csv')
        check_csv(expected, result_file)

    def test_collect_inventory_with_about_resource_path_from_directory(self):
        test_dir = get_test_loc('test_inv/basic_with_about_resource_path')
        result_file = get_temp_file()
        errors, packages = inv.collect_inventory(test_dir)

        inv.save_as_csv(result_file, packages)
        expected_errors = []
        assert expected_errors == errors
        expected = get_test_loc('test_inv/basic_with_about_resource_path/expected.csv')
        check_csv(expected, result_file)

    def test_collect_inventory_is_empty_when_about_resource_is_missing(self):
        test_dir = get_test_loc('test_inv/no_about_resource_key')
        result_file = get_temp_file()
        errors, packages = inv.collect_inventory(test_dir)

        inv.save_as_csv(result_file, packages)

        expected_errors = [
            Error(CRITICAL,
                  'Required field "about_resource" is missing.',
                  path='about/about.ABOUT')]
        assert expected_errors == errors

        expected = get_test_loc('test_inv/no_about_resource_key/expected.csv')
        check_csv(expected, result_file, regen=False)

    def test_collect_inventory_contains_only_about_with_about_resource(self):
        test_dir = get_test_loc('test_inv/some_missing_about_resource')
        result_file = get_temp_file()
        errors, packages = inv.collect_inventory(test_dir)
        fix_location(packages, test_dir)

        inv.save_as_csv(result_file, packages)

        expected_errors = [
            Error(CRITICAL,
                  'Required field "about_resource" is missing.',
                  path='about/about.ABOUT')]
        assert expected_errors == errors

        expected = get_test_loc('test_inv/some_missing_about_resource/expected.csv')
        check_csv(expected, result_file, regen=False)

    def test_collect_inventory_complex_from_directory(self):
        test_dir = get_test_loc('test_inv/complex')
        result_file = get_temp_file()
        errors, packages = inv.collect_inventory(test_dir)

        inv.save_as_csv(result_file, packages)

        assert all(e.severity == INFO for e in errors)

        expected = get_test_loc('test_inv/complex/expected.csv')
        check_csv(expected, result_file)

    def test_collect_inventory_does_not_damage_line_endings(self):
        test_dir = get_test_loc('test_inv/crlf')
        result_file = get_temp_file()
        errors, packages = inv.collect_inventory(test_dir)
        errors2 = inv.save_as_csv(result_file, packages)
        errors.extend(errors2)

        assert all(e.severity == INFO for e in errors)

        expected = get_test_loc('test_inv/crlf/expected.csv')
        check_csv(expected, result_file)

    def test_write_output_csv(self):
        test_file = get_test_loc('test_inv/this.ABOUT')
        package = model.Package.load(test_file)
        result_file = get_temp_file()
        inv.save_as_csv(result_file, [package])
        expected = get_test_loc('test_inv/expected.csv')
        check_csv(expected, result_file)

    def test_write_output_json(self):
        test_file = get_test_loc('test_inv/this.ABOUT')
        package = model.Package.load(about_file_location=test_file)
        result_file = get_temp_file()
        inv.save_as_json(result_file, [package])
        expected = get_test_loc('test_inv/expected.json')
        check_json(expected, result_file)

    def test_is_about_file(self):
        assert inv.is_about_file('test.About')
        assert inv.is_about_file('test2.aboUT')
        assert not inv.is_about_file('no_about_ext.something')
        assert not inv.is_about_file('about')
        assert not inv.is_about_file('about.txt')

    def test_is_about_file_is_false_if_only_bare_extension(self):
        assert not inv.is_about_file('.ABOUT')


class TestGetLocations(unittest.TestCase):

    def test_get_locations(self):
        test_dir = get_test_loc('test_inv/about_locations')
        expected = sorted([
            'file with_spaces.ABOUT',
            'file1',
            'file2',
            'dir1/file2',
            'dir1/file2.aBout',
            'dir1/dir2/file1.about',
            'dir2/file1'])

        result = sorted(inv.get_locations(test_dir))
        result = [l.partition('/about_locations/')[-1] for l in result]
        assert expected == result

    def test_get_about_locations(self):
        test_dir = get_test_loc('test_inv/about_locations')
        expected = sorted([
            'file with_spaces.ABOUT',
            'dir1/file2.aBout',
            'dir1/dir2/file1.about',
        ])

        result = sorted(inv.get_about_locations(test_dir))
        result = [l.partition('/about_locations/')[-1] for l in result]
        assert expected == result

    def test_get_locations_can_yield_a_single_file(self):
        test_file = get_test_loc('test_inv/about_locations/file with_spaces.ABOUT')
        result = list(inv.get_locations(test_file))
        assert 1 == len(result)

    def test_get_about_locations_for_about(self):
        location = get_test_loc('test_inv/get_about_locations')
        result = list(inv.get_about_locations(location))
        expected = 'get_about_locations/about.ABOUT'
        assert result[0].endswith(expected)

    @skipIf(on_windows and not py3, 'Windows support for long path requires https://docs.python.org/3/using/windows.html#removing-the-max-path-limitation')
    def test_get_locations_with_very_long_path(self):
        longpath = (
            'longpath'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
            '/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1/longpath1'
        )
        test_loc = extract_test_loc('test_inv/locations/longpath.zip')
        result = list(inv.get_locations(test_loc))
        assert any(longpath in r for r in result)
