#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) nexB Inc. http://www.nexb.com/ - All rights reserved.
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

import unittest

from testing_utils import get_temp_dir
from testing_utils import get_test_loc

from attributecode import ERROR
from attributecode import INFO
from attributecode import CRITICAL
from attributecode import Error
from attributecode import gen
from unittest.case import skip


class GenTest(unittest.TestCase):

    def test_check_duplicated_columns(self):
        test_file = get_test_loc('test_gen/dup_keys.csv')
        expected = [Error(ERROR, 'Duplicated column name(s): copyright with copyright\nPlease correct the input and re-run.')]
        result = gen.check_duplicated_columns(test_file)
        assert expected == result

    def test_check_duplicated_columns_handles_lower_upper_case(self):
        test_file = get_test_loc('test_gen/dup_keys_with_diff_case.csv')
        expected = [Error(ERROR, 'Duplicated column name(s): copyright with Copyright\nPlease correct the input and re-run.')]
        result = gen.check_duplicated_columns(test_file)
        assert expected == result

    def test_check_duplicated_about_resource(self):
        arp_list = ['/test/test.c', 'test/test1.h']
        arp1 = '/test/test.c'
        arp2 = '/test/tmp/test.c'
        expected = Error(CRITICAL,
                  "The input has duplicated values in 'about_resource' field: " + arp1)
        result1 = gen.check_duplicated_about_resource(arp1, arp_list)
        result2 = gen.check_duplicated_about_resource(arp2, arp_list)
        assert result1 == expected
        assert result2 == ''

    def test_check_newline_in_file_field(self):
        test_dict1 = {'about_resource': '/test/test.c', 'name': 'test.c', 'notice_file': 'NOTICE\nNOTICE2'}
        test_dict2 = {'about_resource': '/test/test.c', 'name': 'test.c', 'notice_file': 'NOTICE, NOTICE2'}
        expected = [
            Error(CRITICAL,
                  "New line character detected in 'notice_file' for '/test/test.c' which is not supported."
                  "\nPlease use ',' to declare multiple files.")]
        result1 = gen.check_newline_in_file_field(test_dict1)
        result2 = gen.check_newline_in_file_field(test_dict2)
        assert result1 == expected
        assert result2 == []

    def test_check_about_resource_filename(self):
        arp1 = '/test/t@est.c'
        arp2 = '/test/t!est.c'
        msg = ("Invalid characters present in 'about_resource' "
                   "field: " + arp2)
        expected2 = Error(ERROR, msg)
        result1 = gen.check_about_resource_filename(arp1)
        result2 = gen.check_about_resource_filename(arp2)
        assert result1 == ''
        assert result2 == expected2

    def test_load_inventory(self):
        location = get_test_loc('test_gen/inv.csv')
        base_dir = get_temp_dir()
        errors, abouts = gen.load_inventory(location, base_dir=base_dir)

        expected_num_errors = 29
        assert len(errors) == expected_num_errors 

        expected = (
'''about_resource: .
name: AboutCode
version: 0.11.0
description: |
  multi
  line
custom1: |
  multi
  line
'''
        )
        result = [a.dumps() for a in abouts]
        assert expected == result[0]

    def test_load_inventory_without_about_resource(self):
        location = get_test_loc('test_gen/inv_no_about_resource.csv')
        base_dir = get_temp_dir()
        from_attrib = False
        errors, abouts = gen.load_inventory(location, base_dir=base_dir, from_attrib=from_attrib)
        expected_error = [Error(CRITICAL,  "The essential field 'about_resource' is not found in the <input>")]

        assert errors == expected_error
        assert abouts == [] 

    def test_load_inventory_without_about_resource_from_attrib(self):
        location = get_test_loc('test_gen/inv_no_about_resource.csv')
        base_dir = get_temp_dir()
        from_attrib = True
        errors, abouts = gen.load_inventory(location, base_dir=base_dir, from_attrib=from_attrib)

        expected_num_errors = 0
        assert len(errors) == expected_num_errors 

        expected = (
'''about_resource: .
name: AboutCode
version: 0.11.0
license_expression: apache-2.0
'''
        )
        result = [a.dumps() for a in abouts]
        assert expected == result[0]

    def test_load_inventory_with_errors(self):
        location = get_test_loc('test_gen/inv4.csv')
        base_dir = get_temp_dir()
        errors, abouts = gen.load_inventory(location, base_dir=base_dir)
        expected_errors = [
            Error(ERROR, "Field name: ['confirmed copyright'] contains illegal name characters (or empty spaces) and is ignored."),
            Error(INFO, 'Field about_resource: Path'),
            Error(INFO, "Field ['resource', 'test'] is a custom field.")
        ]

        for exp, err in zip(expected_errors, errors):
            assert exp.severity == err.severity
            assert err.message.startswith(exp.message)

        expected = (
            'about_resource: .\n'
            'name: AboutCode\n'
            'version: 0.11.0\n'
            'description: |\n'
            '  multi\n'
            '  line\n'
            # 'confirmed copyright: Copyright (c) nexB, Inc.\n'
            'resource: this.ABOUT\n'
            'test: This is a test\n'
        )
        result = [a.dumps() for a in abouts]
        assert expected == result[0]

    def test_load_inventory_simple_xlsx(self):
        location = get_test_loc('test_gen/load/simple_sample.xlsx')
        base_dir = get_temp_dir()
        errors, abouts = gen.load_inventory(location, base_dir=base_dir)
        expected_errors = []
        result = [(level, e) for level, e in errors if level > INFO]
        assert expected_errors == result

        assert abouts[0].name.value == 'cryptohash-sha256'
        assert abouts[1].name.value == 'some_component'
        
        assert abouts[0].version.value == 'v 0.11.100.1'
        assert abouts[1].version.value == 'v 0.0.1'

        assert abouts[0].license_expression.value == 'bsd-new and mit'
        assert abouts[1].license_expression.value == 'mit'


    def test_load_scancode_json(self):
        location = get_test_loc('test_gen/load/clean-text-0.3.0-lceupi.json')
        inventory = gen.load_scancode_json(location)

        expected = {'about_resource': 'clean-text-0.3.0', 'type': 'directory',
                    'name': 'clean-text-0.3.0', 'base_name': 'clean-text-0.3.0',
                    'extension': '', 'size': 0, 'date': None, 'sha1': None,
                    'md5': None, 'sha256': None, 'mime_type': None, 'file_type': None,
                    'programming_language': None, 'is_binary': False, 'is_text': False,
                    'is_archive': False, 'is_media': False, 'is_source': False,
                    'is_script': False, 'licenses': [], 'license_expressions': [],
                    'percentage_of_license_text': 0, 'copyrights': [], 'holders': [],
                    'authors': [], 'packages': [], 'emails': [], 'urls': [], 'files_count': 9,
                    'dirs_count': 1, 'size_count': 32826, 'scan_errors': []}

        # We will only check the first element in the inventory list 
        assert inventory[0] == expected


    def test_generation_dir_endswith_space(self):
        location = get_test_loc('test_gen/inventory/complex/about_file_path_dir_endswith_space.csv')
        base_dir = get_temp_dir()
        errors, _abouts = gen.generate(location, base_dir)
        expected_errors_msg1 = 'contains directory name ends with spaces which is not allowed. Generation skipped.'
        expected_errors_msg2 = 'Field about_resource'
        assert errors
        assert len(errors) == 2
        assert expected_errors_msg1 in errors[0].message or expected_errors_msg1 in errors[1].message
        assert expected_errors_msg2 in errors[0].message or expected_errors_msg2 in errors[1].message

    def test_generation_with_no_about_resource(self):
        location = get_test_loc('test_gen/inv2.csv')
        base_dir = get_temp_dir()
        errors, abouts = gen.generate(location, base_dir)
        expected = dict([('.', None)])
        assert abouts[0].about_resource.value == expected
        assert len(errors) == 1

    def test_generation_with_no_about_resource_reference(self):
        location = get_test_loc('test_gen/inv3.csv')
        base_dir = get_temp_dir()

        errors, abouts = gen.generate(location, base_dir)
        expected = dict([('test.tar.gz', None)])

        assert abouts[0].about_resource.value == expected
        assert len(errors) == 1
        msg = 'Field about_resource'
        assert msg in errors[0].message

    def test_generation_with_no_about_resource_reference_no_resource_validation(self):
        location = get_test_loc('test_gen/inv3.csv')
        base_dir = get_temp_dir()

        errors, abouts = gen.generate(location, base_dir)
        expected = dict([('test.tar.gz', None)])

        assert abouts[0].about_resource.value == expected
        assert len(errors) == 1

    def test_generate(self):
        location = get_test_loc('test_gen/inv.csv')
        base_dir = get_temp_dir()

        errors, abouts = gen.generate(location, base_dir)
        err_msg_list = []
        for severity, message in errors:
            err_msg_list.append(message)
        msg1 = "Field ['custom1'] is a custom field."

        assert msg1 in err_msg_list

        result = [a.dumps() for a in abouts][0]
        expected = (
'''about_resource: .
name: AboutCode
version: 0.11.0
description: |
  multi
  line
custom1: |
  multi
  line
'''
        )
        assert expected == result

    def test_generate_multi_lic_issue_443(self):
        location = get_test_loc('test_gen/multi_lic_issue_443/test.csv')
        base_dir = get_temp_dir()

        errors, abouts = gen.generate(location, base_dir)

        result = [a.dumps() for a in abouts][0]
        expected = (
'''about_resource: test
name: test
version: '1.5'
licenses:
  - key: License1
    name: License1
    file: LIC1.LICENSE
  - key: License2
    name: License2
    file: LIC2.LICENSE
  - key: License3
    name: License3
    file: LIC3.LICENSE
'''
        )
        assert expected == result

    def test_generate_multi_lic_issue_444(self):
        location = get_test_loc('test_gen/multi_lic_issue_444/test1.csv')
        base_dir = get_temp_dir()

        errors, abouts = gen.generate(location, base_dir)

        result = [a.dumps() for a in abouts][0]
        expected = (
'''about_resource: test.c
name: test.c
licenses:
  - key: License1
    name: License1
    file: LIC1.LICENSE, LIC2.LICENSE
'''
        )
        assert expected == result

    def test_generate_license_key_with_custom_file_450_no_fetch(self):
        location = get_test_loc('test_gen/lic_issue_450/custom_and_valid_lic_key_with_file.csv')
        base_dir = get_temp_dir()

        errors, abouts = gen.generate(location, base_dir)

        result = [a.dumps() for a in abouts][0]
        expected = (
'''about_resource: test.c
name: test.c
license_expression: mit AND custom
licenses:
  - file: custom.txt
'''
        )
        assert expected == result


    def test_generate_license_key_with_custom_file_450_with_fetch_with_order(self):
        location = get_test_loc('test_gen/lic_issue_450/custom_and_valid_lic_key_with_file.csv')
        base_dir = get_temp_dir()

        errors, abouts = gen.generate(location, base_dir)

        lic_dict = {u'mit': [u'MIT License',
                                       u'mit.LICENSE',
                                       u'This component is released under MIT License.',
                                       u'https://enterprise.dejacode.com/urn/?urn=urn:dje:license:mit',
                                       u'mit'
                                       ]}
        # The first row from the test file
        a = abouts[0]
        a.license_key.value.append('mit')
        a.license_key.value.append('custom')
        result1 = a.dumps(lic_dict)
        # The second row from the test file
        b = abouts[1]
        b.license_key.value.append('custom')
        b.license_key.value.append('mit')
        result2 = b.dumps(lic_dict)

        expected1 = (
'''about_resource: test.c
name: test.c
license_expression: mit AND custom
licenses:
  - key: mit
    name: MIT License
    file: mit.LICENSE
    url: https://enterprise.dejacode.com/urn/?urn=urn:dje:license:mit
    spdx_license_key: mit
  - key: custom
    name: custom
    file: custom.txt
'''
        )

        expected2 = (
'''about_resource: test.h
name: test.h
license_expression: custom AND mit
licenses:
  - key: custom
    name: custom
    file: custom.txt
  - key: mit
    name: MIT License
    file: mit.LICENSE
    url: https://enterprise.dejacode.com/urn/?urn=urn:dje:license:mit
    spdx_license_key: mit
'''
        )
        assert expected1 == result1
        assert expected2 == result2

    @skip('FIXME: this test is making a failed, live API call')
    def test_generate_not_overwrite_original_license_file(self):
        location = get_test_loc('test_gen/inv5.csv')
        base_dir = get_temp_dir()
        reference_dir = None
        fetch_license = ['url', 'lic_key']

        _errors, abouts = gen.generate(
            location, base_dir, reference_dir, fetch_license)

        result = [a.dumps()for a in abouts][0]
        expected = (
            'about_resource: .\n'
            'name: AboutCode\n'
            'version: 0.11.0\n'
            'licenses:\n'
            '    -   file: this.LICENSE\n')
        assert expected == result

    def test_boolean_value_not_lost(self):
        location = get_test_loc('test_gen/inv6.csv')
        base_dir = get_temp_dir()

        _errors, abouts = gen.generate(location, base_dir)

        in_mem_result = [a.dumps() for a in abouts][0]
        expected = (u'about_resource: .\n'
                    u'name: AboutCode\n'
                    u'version: 0.11.0\n'
                    u'redistribute: yes\n'
                    u'attribute: yes\n'
                    u'modified: no\n')
        assert expected == in_mem_result
