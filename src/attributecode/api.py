#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2017 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

import json

try:  # Python 2
    from urllib import urlencode, quote
    from urllib2 import urlopen, Request, HTTPError
except ImportError:  # Python 3
    from urllib.parse import urlencode, quote
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError

from attributecode import ERROR
from attributecode import Error


"""
API call helpers
"""


def request_license_data(url, api_key, license_key):
    """
    Return a dictionary of license data.
    Send a request to a given API URL to gather license data for
    license_key, authenticating through an api_key.
    """
    headers = {
        'Authorization': 'Token %s' % api_key,
    }
    payload = {
        'api_key': api_key,
        'key': license_key,
        'format': 'json'
    }

    url = url.rstrip('/')
    encoded_payload = urlencode(payload)
    full_url = '%(url)s/?%(encoded_payload)s' % locals()
    # handle special characters in URL such as space etc.
    quoted_url = quote(full_url, safe="%/:=&?~#+!$,;'@()*[]")

    license_data = {}
    errors = []
    try:
        request = Request(quoted_url, headers=headers)
        response = urlopen(request)
        response_content = response.read().decode('utf-8')
        license_data = json.loads(response_content)
        if not license_data['results']:
            msg = u"Invalid 'license': %s" % license_key
            errors.append(Error(ERROR, msg))
    except HTTPError as http_e:
        # some auth problem
        if http_e.code == 403:
            msg = (u"Authorization denied. Invalid '--api_key'. "
                   u"License generation is skipped.")
            errors.append(Error(ERROR, msg))
        else:
            # Since no api_url/api_key/network status have
            # problem detected, it yields 'license' is the cause of
            # this exception.
            msg = u"Invalid 'license': %s" % license_key
            errors.append(Error(ERROR, msg))
    except Exception as e:
        errors.append(Error(ERROR, str(e)))
    finally:
        license_data = license_data.get('results')[0] if license_data.get('count') == 1 else {}

    return license_data, errors


def get_license_details_from_api(url, api_key, license_key):
    """
    Return the license_text of a given license_key using an API request.
    Return an empty string if the text is not available.
    """
    license_data, errors = request_license_data(url, api_key, license_key)
    license_name = license_data.get('name', '')
    license_text = license_data.get('full_text', '')
    license_key = license_data.get('key', '')
    return license_name, license_key, license_text, errors
