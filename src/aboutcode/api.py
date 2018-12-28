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

import click

from aboutcode import ERROR
from aboutcode import Error
from aboutcode import util
from aboutcode import model
from aboutcode.util import python2

if python2:  # pragma: nocover
    from urllib2 import HTTPError  # NOQA
    from urllib import urlencode  # NOQA
    from urlparse import urljoin  # NOQA
    from urlparse import urlparse  # NOQA
    from urllib import quote  # NOQA
    from urllib2 import Request  # NOQA
    from urllib2 import urlopen  # NOQA
else:  # pragma: nocover
    from urllib.error import HTTPError  # NOQA
    from urllib.parse import urlencode  # NOQA
    from urllib.parse import urljoin  # NOQA
    from urllib.parse import urlparse  # NOQA
    from urllib.parse import quote  # NOQA
    from urllib.request import Request  # NOQA
    from urllib.request import urlopen  # NOQA

from license_expression import Licensing


"""
API helpers
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
        license_data = json.loads(response_content)

        if not license_data['results']:
            msg = 'Invalid license key: %s' % license_key
            errors.append(Error(ERROR, msg))

    except HTTPError as http_e:
        # some auth problem
        if http_e.code == 403:
            msg = (u"Authorization denied. Invalid '--api-key'. "
                   u"License generation is skipped.")
            errors.append(Error(ERROR, msg))
        else:
            # Since no api_url/api_key/network status have
            # problem detected, it yields 'license' is the cause of
            # this exception.
            msg = 'Invalid license key: %s' % license_key
            errors.append(Error(ERROR, msg))

    except Exception as e:
        errors.append(Error(ERROR, str(e)))

    finally:
        if license_data.get('count') == 1:
            license_data = license_data.get('results')[0]
        else:
            license_data = {}

    return license_data, errors


def get_license_details(api_url, api_key, license_key):
    """
    Return a License object given a `license_key` using the `api_url`
    authenticating with `api_key`.
    """
    license_data, errors = request_license_data(api_url, api_key, license_key)
    if 'key' in license_data:
        dje_domain = '{uri.scheme}://{uri.netloc}/'.format(uri=urlparse(api_url))
        dje_license_url = urljoin(dje_domain, 'urn/?urn=urn:dje:license:{license_key}')
        url = dje_license_url.format(license_key=license_key)

        lic = model.License(
            key=license_data['key'],
            name=license_data.get('name'),
            text=license_data.get('full_text'),
            url=url,
        )
    else:
        lic = None
    return lic, errors


def fetch_licenses(packages, api_url, api_key, verbose=False):
    """
    Return a mapping of {license key: License object} given an `packages` list of
    Package object and a list of Error.
    """

    errors = []

    if have_network_connection():
        if not valid_api_url(api_url):
            msg = "URL not reachable. Invalid '--api_url'. License retrieval is skipped."
            errors.append(Error(ERROR, msg))
    else:
        msg = 'Network problem. Please check your Internet connection. License retrieval is skipped.'
        errors.append(Error(ERROR, msg))

    msg = "Authorization denied. Invalid '--api_key'. License retrieval is skipped."
    auth_error = Error(ERROR, msg)

    # collect unique license keys
    license_keys = set()
    licensing = Licensing()
    for package in packages:
        if not package.license_expression:
            # TODO: we should have a check for this
            continue
        package_license_keys = licensing.license_keys(
            package.license_expression, unique=True, simple=True)
        license_keys.update(package_license_keys)

    licenses_by_key = {}

    # fetch license key proper
    for license_key in sorted(license_keys):
        # No need to go through fetching all the licensesif  we detected invalid '--api_key'
        if auth_error in errors:
            break
        license, errs = get_license_details(api_url, api_key, license_key)  # NOQA
        errors.extend(errs)
        if license:
            licenses_by_key[license_key] = license

            if verbose:
                click.echo('Fetched license: {}'.format(license_key))

    return licenses_by_key, util.unique(errors)


def valid_api_url(api_url):
    try:
        request = Request(api_url)
        # This will always goes to exception as no key are provided.
        # The purpose of this code is to validate the provided api_url is correct
        urlopen(request)
    except HTTPError as http_e:
        # The 403 error code is refer to "Authentication credentials were not provided.".
        # This is correct as no key are provided.
        if http_e.code == 403:
            return True
    except:
        # All other exceptions yield to invalid api_url
        pass
    return False


# FIXME: rename to is_online: BUT do we really need this at all????
def have_network_connection():
    """
    Return True if an HTTP connection to some public web site is possible.
    """
    import socket
    if python2:
        import httplib  # NOQA
    else:
        import http.client as httplib  # NOQA

    http_connection = httplib.HTTPConnection('dejacode.org', timeout=10)  # NOQA
    try:
        http_connection.connect()
    except socket.error:
        return False
    else:
        return True
