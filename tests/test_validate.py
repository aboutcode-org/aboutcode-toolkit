#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2018 nexB Inc. http://www.nexb.com/ - All rights reserved.
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
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

from testing_utils import run_about_command_test

"""
Common and global checks such as codestyle and check own ABOUT files.
"""


root_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def disabled_test_codestyle():

    # TODO: enable me
    import subprocess
    args = [
        os.path.join(root_dir, 'bin', 'pycodestyle'),
        '--ignore',
        'E501,W503,W504,W605',
        '--exclude=lib,lib64,tests,thirdparty,docs,bin,man,settings,local,tmp',
        '.',
    ]

    subprocess.check_output(args=args, cwd=root_dir)


def test_about_thirdparty():
    run_about_command_test(['check', 'thirdparty'])


def test_about_src():
    run_about_command_test(['check', 'src'])


def test_about_etc():
    run_about_command_test(['check', 'etc'])


def test_about_myself():
    run_about_command_test(['check', 'about.ABOUT'])
