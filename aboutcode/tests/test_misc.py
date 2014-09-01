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

import unittest

import aboutcode
from aboutcode import Error
from aboutcode import CRITICAL
from aboutcode import ERROR
from aboutcode import INFO
from aboutcode import WARNING
from aboutcode import DEBUG
from aboutcode import NOTSET


class MiscTest(unittest.TestCase):

    def test_log_errors(self):
        errors = [Error(CRITICAL, 'msg1'),
                  Error(ERROR, 'msg2'),
                  Error(INFO, 'msg3'),
                  Error(WARNING, 'msg4'),
                  Error(DEBUG, 'msg4'),
                  Error(NOTSET, 'msg4'),
                  ]

        class MockLogger(object):
            logged = []
            def log(self, severity, message):
                self.logged.append((severity, message,))

        logger = MockLogger()
        aboutcode.log_errors(errors, logger, level=NOTSET)
        result = logger.logged
        expected = [(CRITICAL, 'msg1'),
                    (ERROR, 'msg2'),
                    (INFO, 'msg3'),
                    (WARNING, 'msg4'),
                    (DEBUG, 'msg4'),
                    (NOTSET, 'msg4')]
        self.assertEqual(expected, result)
