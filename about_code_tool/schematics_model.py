#!/usr/bin/env python
# -*- coding: utf8 -*-
# ============================================================================
#  Copyright (c) 2013-2016 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

from schematics.models import Model
from schematics.types import StringType
from schematics.exceptions import ValidationError


class About(Model):
    # The min_length is needed to make sure the key has value
    # Otherwise, an empty value key is accepted.
    name = StringType(required=True, min_length = 1)
    version = StringType(required=True, min_length = 1)

    MESSAGES = {
        'empty': ' : Field is empty.'
    }

    def validate_empty_value(self, about):
        for k in about.keys():
            if len(about[k]) < 1:
                raise ValidationError(k + self.MESSAGES['empty'])