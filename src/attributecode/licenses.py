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

# Common license keys
COMMON_LICENSES = (
    'aes-128-3.0',
    'apache-1.1',
    'apache-2.0',
    'apple-attribution-1997',
    'apple-excl',
    'apsl-2.0',
    'arphic-public',
    'artistic-perl-1.0',
    'artistic-2.0',
    'bitstream',
    'boost-1.0',
    'broadcom-cfe',
    'bsd-new',
    'bsd-original',
    'bsd-original-uc',
    'bsd-simplified',
    'cmu-computing-services',
    'cddl-1.0',
    'cddl-1.1',
    'cpl-1.0',
    'cc-by-2.5',
    'cc-by-sa-3.0',
    'curl',
    'freetype',
    'gpl-2.0',
    'gpl-2.0-bison',
    'gpl-2.0-glibc',
    'gpl-3.0',
    'lgpl-2.0',
    'lgpl-2.1',
    'gpl-2.0-plus-linking',
    'gpl-2.0-broadcom-linking',
    'ijg',
    'isc',
    'larabie',
    'libpng',
    'ms-limited-public',
    'ms-pl',
    'ms-rl',
    'ms-ttf-eula',
    'mit',
    'mpl-1.1',
    'mpl-2.0',
    'net-snmp',
    'npl-1.1',
    'ntpl',
    'openssl-ssleay',
    'ssleay-windows',
    'rsa-md4',
    'rsa-md5',
    'sfl-license',
    'sgi-freeb-2.0',
    'sun-rpc',
    'tcl',
    'tidy',
    'uoi-ncsa',
    'x11',
    'zlib',
)
