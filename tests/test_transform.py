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

from collections import OrderedDict
import unittest

from testing_utils import get_test_loc

from attributecode.transform import check_duplicate_fields
from attributecode.transform import transform_data
from attributecode.transform import normalize_dict_data
from attributecode.transform import strip_trailing_fields_csv
from attributecode.transform import strip_trailing_fields_json
from attributecode.transform import Transformer
from attributecode.transform import read_csv_rows, read_excel, read_json
from attributecode.transform import transform_csv, transform_excel, transform_json


class TransformTest(unittest.TestCase):
    def test_transform_data_new_col(self):
        data = [
            OrderedDict(
                [
                    ("Directory/Filename", "/tmp/test.c"),
                    ("Component", "test.c"),
                    ("version", "1"),
                    ("notes", "test"),
                    ("temp", "foo"),
                ]
            )
        ]
        configuration = get_test_loc("test_transform/configuration_new_cols")
        transformer = Transformer.from_file(configuration)

        data, err = transform_data(data, transformer)

        expected_data = [
            dict(
                OrderedDict(
                    [
                        ("path", "/tmp/test.c"),
                        ("about_resource", "/tmp/test.c"),
                        ("name", "test.c"),
                        ("version", "1"),
                        ("notes", "test"),
                        ("temp", "foo"),
                    ]
                )
            )
        ]
        assert len(data) == len(expected_data)
        for d in data:
            assert dict(d) in expected_data

    def test_transform_data(self):
        data = [
            OrderedDict(
                [
                    ("Directory/Filename", "/tmp/test.c"),
                    ("Component", "test.c"),
                    ("version", "1"),
                    ("notes", "test"),
                    ("temp", "foo"),
                ]
            )
        ]
        configuration = get_test_loc("test_transform/configuration")
        transformer = Transformer.from_file(configuration)

        data, err = transform_data(data, transformer)

        expect_name = ["about_resource", "name", "version"]
        expected_data = [
            dict(
                OrderedDict(
                    [("about_resource", "/tmp/test.c"), ("name", "test.c"), ("version", "1")]
                )
            )
        ]

        assert len(data) == len(expected_data)
        for d in data:
            assert dict(d) in expected_data

    def test_transform_data_mutli_rows(self):
        data = [
            OrderedDict(
                [
                    ("Directory/Filename", "/tmp/test.c"),
                    ("Component", "test.c"),
                    ("Confirmed Version", "v0.01"),
                ]
            ),
            OrderedDict(
                [
                    ("Directory/Filename", "/tmp/tmp.h"),
                    ("Component", "tmp.h"),
                    ("Confirmed Version", None),
                ]
            ),
        ]
        configuration = get_test_loc("test_transform/configuration2")
        transformer = Transformer.from_file(configuration)

        data, err = transform_data(data, transformer)

        expect_name = ["about_resource", "name", "version"]
        expected_data = [
            dict(
                OrderedDict(
                    [("about_resource", "/tmp/test.c"), ("name", "test.c"), ("version", "v0.01")]
                )
            ),
            dict(
                OrderedDict(
                    [("about_resource", "/tmp/tmp.h"), ("name", "tmp.h"), ("version", None)]
                )
            ),
        ]

        assert len(data) == len(expected_data)
        for d in data:
            assert dict(d) in expected_data

    def test_normalize_dict_data_scancode(self):
        test_file = get_test_loc("test_transform/input_scancode.json")
        json_data = read_json(test_file)
        data = normalize_dict_data(json_data)
        expected_data = [
            OrderedDict(
                [
                    ("path", "samples"),
                    ("type", "directory"),
                    ("name", "samples"),
                    ("base_name", "samples"),
                    ("extension", ""),
                    ("size", 0),
                    ("date", None),
                    ("sha1", None),
                    ("md5", None),
                    ("mime_type", None),
                    ("file_type", None),
                    ("programming_language", None),
                    ("is_binary", False),
                    ("is_text", False),
                    ("is_archive", False),
                    ("is_media", False),
                    ("is_source", False),
                    ("is_script", False),
                    ("licenses", []),
                    ("license_expressions", []),
                    ("copyrights", []),
                    ("holders", []),
                    ("authors", []),
                    ("packages", []),
                    ("emails", []),
                    ("urls", []),
                    ("files_count", 33),
                    ("dirs_count", 10),
                    ("size_count", 1161083),
                    ("scan_errors", []),
                ]
            )
        ]
        assert data == expected_data

    def test_normalize_dict_data_json(self):
        json_data = OrderedDict(
            [
                ("Directory/Filename", "/aboutcode-toolkit/"),
                ("Component", "AboutCode-toolkit"),
                ("version", "1.2.3"),
                ("note", "test"),
                ("temp", "foo"),
            ]
        )
        data = normalize_dict_data(json_data)
        expected_data = [
            OrderedDict(
                [
                    ("Directory/Filename", "/aboutcode-toolkit/"),
                    ("Component", "AboutCode-toolkit"),
                    ("version", "1.2.3"),
                    ("note", "test"),
                    ("temp", "foo"),
                ]
            )
        ]
        assert data == expected_data

    def test_normalize_dict_data_json_array(self):
        json_data = [
            OrderedDict(
                [
                    ("Directory/Filename", "/aboutcode-toolkit/"),
                    ("Component", "AboutCode-toolkit"),
                    ("version", "1.0"),
                    ("temp", "fpp"),
                ]
            ),
            OrderedDict(
                [
                    ("Directory/Filename", "/aboutcode-toolkit1/"),
                    ("Component", "AboutCode-toolkit1"),
                    ("version", "1.1"),
                    ("temp", "foo"),
                ]
            ),
        ]
        data = normalize_dict_data(json_data)
        expected_data = [
            OrderedDict(
                [
                    ("Directory/Filename", "/aboutcode-toolkit/"),
                    ("Component", "AboutCode-toolkit"),
                    ("version", "1.0"),
                    ("temp", "fpp"),
                ]
            ),
            OrderedDict(
                [
                    ("Directory/Filename", "/aboutcode-toolkit1/"),
                    ("Component", "AboutCode-toolkit1"),
                    ("version", "1.1"),
                    ("temp", "foo"),
                ]
            ),
        ]
        assert data == expected_data

    def test_check_duplicate_fields(self):
        field_name = ["path", "name", "path", "version"]
        expected = ["path"]
        dups = check_duplicate_fields(field_name)
        assert dups == expected

    def test_strip_trailing_fields_csv(self):
        test = ["about_resource", "name ", " version "]
        expected = ["about_resource", "name", "version"]
        result = strip_trailing_fields_csv(test)
        assert result == expected

    def test_strip_trailing_fields_json(self):
        test = [
            OrderedDict(
                [("about_resource", "/this.c"), ("name ", "this.c"), (" version ", "0.11.0")]
            )
        ]
        expected = [
            OrderedDict([("about_resource", "/this.c"), ("name", "this.c"), ("version", "0.11.0")])
        ]
        result = strip_trailing_fields_json(test)
        assert result == expected

    def test_read_excel(self):
        test_file = get_test_loc("test_transform/simple.xlsx")
        error, data = read_excel(test_file)
        assert not error
        expected = [
            OrderedDict(
                [("about_resource", "/test.c"), ("name", "test.c"), ("license_expression", "mit")]
            ),
            OrderedDict(
                [
                    ("about_resource", "/test2.c"),
                    ("name", "test2.c"),
                    ("license_expression", "mit and apache-2.0"),
                ]
            ),
        ]
        assert data == expected

    def test_read_csv_rows(self):
        test_file = get_test_loc("test_transform/simple.csv")
        data = read_csv_rows(test_file)
        expected = [
            ["about_resource", "name", "license_expression"],
            ["/test.c", "test.c", "mit"],
            ["/test2.c", "test2.c", "mit and apache-2.0"],
        ]
        assert list(data) == expected

    def test_transform_csv(self):
        test_file = get_test_loc("test_transform/input.csv")
        data, err = transform_csv(test_file)
        expected = [
            {
                "Directory/Filename": "/aboutcode-toolkit/",
                "Component": "AboutCode-toolkit",
                "Confirmed Version": "123",
                "notes": "",
            }
        ]
        assert len(err) == 0
        assert data == expected

    def test_transform_excel(self):
        test_file = get_test_loc("test_transform/input.xlsx")
        data, err = transform_excel(test_file)
        expected = [
            OrderedDict(
                [
                    ("Directory/Filename", "/aboutcode-toolkit/"),
                    ("Component", "AboutCode-toolkit"),
                    ("Confirmed Version", 123),
                    ("notes", ""),
                ]
            )
        ]
        assert len(err) == 0
        assert data == expected

    def test_transform_json(self):
        test_file = get_test_loc("test_transform/input.json")
        data, err = transform_json(test_file)
        expected = [
            {
                "Directory/Filename": "/aboutcode-toolkit/",
                "Component": "AboutCode-toolkit",
                "Confirmed Version": "123",
                "notes": "",
            }
        ]
        assert len(err) == 0
        assert data == expected

    def test_apply_renamings(self):
        data = [
            OrderedDict(
                [
                    ("Directory/Filename", "/tmp/test.c"),
                    ("Component", "test.c"),
                    ("version", "1"),
                    ("notes", "test"),
                    ("temp", "foo"),
                ]
            )
        ]
        configuration = get_test_loc("test_transform/configuration")
        transformer = Transformer.from_file(configuration)

        expected = [
            OrderedDict(
                [
                    ("about_resource", "/tmp/test.c"),
                    ("name", "test.c"),
                    ("version", "1"),
                    ("notes", "test"),
                    ("temp", "foo"),
                ]
            )
        ]
        renamed_field_data = transformer.apply_renamings(data)
        assert renamed_field_data == expected

    def test_apply_renamings_nested_list(self):
        data = [
            {
                "path": "samples/JGroups-error.log",
                "name": "JGroups-error.log",
                "license_detections": [
                    {
                        "license_expression": "apache-1.1 AND apache-2.0",
                        "matches": [
                            {
                                "score": 90.0,
                                "start_line": 4,
                                "end_line": 4,
                                "license_expression": "apache-1.1",
                            },
                            {
                                "score": 100.0,
                                "start_line": 5,
                                "end_line": 5,
                                "license_expression": "apache-2.0",
                            },
                        ],
                    }
                ],
            }
        ]
        configuration = get_test_loc("test_transform/configuration3")
        transformer = Transformer.from_file(configuration)

        expected = [
            {
                "about_resource": "samples/JGroups-error.log",
                "name": "JGroups-error.log",
                "license_detections": [
                    {
                        "license_expression": "apache-1.1 AND apache-2.0",
                        "matches": [
                            {
                                "score_renamed": 90.0,
                                "start_line": 4,
                                "end_line": 4,
                                "license_expression": "apache-1.1",
                            },
                            {
                                "score_renamed": 100.0,
                                "start_line": 5,
                                "end_line": 5,
                                "license_expression": "apache-2.0",
                            },
                        ],
                    }
                ],
            }
        ]
        updated_data = transformer.apply_renamings(data)
        assert updated_data == expected

    def test_filter_excluded(self):
        data = [
            OrderedDict(
                [
                    ("Directory/Filename", "/tmp/test.c"),
                    ("Component", "test.c"),
                    ("version", "1"),
                    ("notes", "test"),
                    ("temp", "foo"),
                ]
            )
        ]
        configuration = get_test_loc("test_transform/configuration")
        transformer = Transformer.from_file(configuration)

        expected = [
            OrderedDict(
                [
                    ("Directory/Filename", "/tmp/test.c"),
                    ("Component", "test.c"),
                    ("version", "1"),
                    ("notes", "test"),
                ]
            )
        ]
        updated_data = transformer.filter_excluded(data)
        assert updated_data == expected

    def test_filter_excluded_nested_list(self):
        data = [
            {
                "path": "samples/JGroups-error.log",
                "type": "file",
                "name": "JGroups-error.log",
                "license_detections": [
                    {
                        "license_expression": "apache-1.1 AND apache-2.0",
                        "matches": [
                            {
                                "score": 90.0,
                                "start_line": 4,
                                "end_line": 4,
                                "license_expression": "apache-1.1",
                            },
                            {
                                "score": 100.0,
                                "start_line": 5,
                                "end_line": 5,
                                "license_expression": "apache-2.0",
                            },
                        ],
                    }
                ],
            }
        ]
        configuration = get_test_loc("test_transform/configuration3")
        transformer = Transformer.from_file(configuration)

        expected = [
            {
                "path": "samples/JGroups-error.log",
                "name": "JGroups-error.log",
                "license_detections": [
                    {
                        "license_expression": "apache-1.1 AND apache-2.0",
                        "matches": [
                            {"score": 90.0, "end_line": 4, "license_expression": "apache-1.1"},
                            {"score": 100.0, "end_line": 5, "license_expression": "apache-2.0"},
                        ],
                    }
                ],
            }
        ]
        updated_data = transformer.filter_excluded(data)
        assert updated_data == expected

    def test_filter_fields(self):
        data = [
            OrderedDict(
                [
                    ("about_resource", "/tmp/test.c"),
                    ("name", "test.c"),
                    ("version", "1"),
                    ("notes", "test"),
                    ("temp", "foo"),
                ]
            )
        ]
        configuration = get_test_loc("test_transform/configuration")
        transformer = Transformer.from_file(configuration)

        updated_data = transformer.filter_fields(data)

        expected = [
            OrderedDict(
                [
                    ("about_resource", "/tmp/test.c"),
                    ("name", "test.c"),
                    ("version", "1"),
                    ("temp", "foo"),
                ]
            )
        ]

        for d in updated_data:
            assert dict(d) in expected
