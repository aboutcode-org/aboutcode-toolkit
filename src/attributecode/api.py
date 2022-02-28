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

import json

from urllib.parse import quote
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen
from urllib.error import HTTPError

from attributecode import ERROR
from attributecode import Error

"""
API call helpers
"""


# FIXME: args should start with license_key
def request_license_data(api_url, api_key, license_key):
    """
    Return a tuple of (dictionary of license data, list of errors) given a
    `license_key`. Send a request to `api_url` authenticating with `api_key`.
    """
    headers = {
        'Authorization': 'Token %s' % api_key,
    }
    payload = {
        'api_key': api_key,
        'key': license_key,
        'format': 'json'
    }

    api_url = api_url.rstrip('/')
    payload = urlencode(payload)

    full_url = '%(api_url)s/?%(payload)s' % locals()
    # handle special characters in URL such as space etc.
    quoted_url = quote(full_url, safe="%/:=&?~#+!$,;'@()*[]")

    license_data = {}
    errors = []
    try:
        request = Request(quoted_url, headers=headers)
        response = urlopen(request)
        response_content = response.read().decode('utf-8')
        # FIXME: this should be an ordered dict
        license_data = json.loads(response_content)
        if not license_data['results']:
            msg = u"Invalid 'license': %s" % license_key
            errors.append(Error(ERROR, msg))
    except HTTPError as http_e:
        # some auth problem
        #if http_e.code == 403:
        msg = (u"Authorization denied. Invalid '--api_key'. "
               u"License generation is skipped.")
        errors.append(Error(ERROR, msg))
    except Exception as e:
        errors.append(Error(ERROR, str(e)))

    finally:
        if license_data.get('count') == 1:
            license_data = license_data.get('results')[0]
        else:
            license_data = {}

    return license_data, errors


# FIXME: args should start with license_key
def get_license_details_from_api(api_url, api_key, license_key):
    """
    Return a tuple of license data given a `license_key` using the `api_url`
    authenticating with `api_key`.
    The details are a tuple of (license_name, license_key, license_text, errors)
    where errors is a list of strings.
    Missing values are provided as empty strings.
    """
    license_data, errors = request_license_data(api_url, api_key, license_key)
    return license_data, errors
