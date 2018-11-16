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
import subprocess

"""
Common and global checks such as codestyle and related.
"""


root_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def disabled_test_codestyle():
    # TODO: enable me
    args = [
        os.path.join(root_dir, 'bin', 'pycodestyle'),
        '--ignore',
        'E501,W503,W504,W605',
        '--exclude=lib,lib64,tests,thirdparty,docs,bin,man,settings,local,tmp',
        '.',
    ]
    subprocess.check_output(args=args, cwd=root_dir)


def check_about(path):
    args = [os.path.join(root_dir, 'bin', 'about'), 'check', path]
    try:
        subprocess.check_output(args=args, cwd=root_dir)
    except subprocess.CalledProcessError as cpe:
        print('failed to validate ABOUT files:\n' + cpe.output)
        raise Exception(repr(cpe.output))


def test_about_thirdparty():
    check_about('thirdparty')


def test_about_src():
    check_about('src')


def test_about_etc():
    check_about('etc')


def test_about_myself():
    check_about('about.ABOUT')
