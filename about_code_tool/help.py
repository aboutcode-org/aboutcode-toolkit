#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2015 nexB Inc. http://www.nexb.com/ - All rights reserved.
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


__about_spec_version__ = '1.0'

__version__ = '2.2.0'

__copyright__ = """
Copyright (c) 2013-2015 nexB Inc. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

__version_info__ = 'AboutCode v {0}\n'.format(__version__)


__full_info__ = 'AboutCode tool v {0}\n{1}'.format(__version__, __copyright__)


VERBOSITY_HELP = """\
Print more or less verbose messages while processing:
0 - Do not print warning or error messages, only a total count (default).
1 - Print error messages.
2 - Print error and warning messages.
"""


MAPPING_HELP = """\
Load the about_code_tool/MAPPING.CONFIG file. This file contains a mapping between AboutCode keys 
(or column names) and custom keys (or column names).
"""

