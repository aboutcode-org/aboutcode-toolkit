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

from __future__ import print_function

import schematics
import unittest

import about_code_tool
from about_code_tool import schematics_model

from schematics.exceptions import ValidationError


class ExampleTest(unittest.TestCase):

    def test_Field_has_content(self):
        #about = schematics_model.About({'name': u'component', 'version': u'1.0'})
        about = schematics_model.About()
        about.name = u'component'
        about.version = u'1.0'
        about.validate()

    def test_missing_field(self):
        about = schematics_model.About()
        about.name = u'component'
        try:
            about.validate()
        except ValidationError, e:
            expected_error =  {'version': ['This field is required.']}
            assert expected_error == e.messages

    def test_missing_value(self):
        about = schematics_model.About()
        about.name = u'component'
        about.version = u''
        try:
            # The to_primitive gives the about dict.
            # This following validation function is created for custom message.
            about.validate_empty_value(about.to_primitive())
        except ValidationError, e:
            expected_error = [u'version : Field is empty.']
            assert expected_error == e.messages