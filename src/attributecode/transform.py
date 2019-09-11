#!/usr/bin/env python
# -*- coding: utf8 -*-
# ============================================================================
#  Copyright (c) 2013-2019 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

from collections import Counter
from collections import OrderedDict
import io

import attr

from attributecode import CRITICAL
from attributecode import Error
from attributecode import saneyaml
from attributecode.util import csv
from attributecode.util import python2
from attributecode.util import replace_tab_with_spaces


if python2:  # pragma: nocover
    from itertools import izip_longest as zip_longest  # NOQA
else:  # pragma: nocover
    from itertools import zip_longest  # NOQA


def transform_csv_to_csv(location, output, transformer):
    """
    Read a CSV file at `location` and write a new CSV file at `output`. Apply
    transformations using the `transformer` Tranformer.
    Return a list of Error objects.
    """
    if not transformer:
        raise ValueError('Cannot transform without Transformer')

    rows = read_csv_rows(location)

    column_names, data, errors = transform_data(rows, transformer)

    if errors:
        return errors
    else:
        write_csv(output, data, column_names)
        return []


def transform_data(rows, transformer):
    """
    Read a list of list of CSV-like data `rows` and apply transformations using the
    `transformer` Tranformer.
    Return a tuple of:
       ([column names...], [transformed ordered dict...], [Error objects..])
    """

    if not transformer:
        return rows

    errors = []
    rows = iter(rows)
    column_names = next(rows)
    column_names = transformer.clean_columns(column_names)

    dupes = check_duplicate_columns(column_names)

    if dupes:
        msg = 'Duplicated column name: {name}'
        errors.extend(Error(CRITICAL, msg.format(name)) for name in dupes)
        return column_names, [], errors

    column_names = transformer.apply_renamings(column_names)

    # convert to dicts using the renamed columns
    data = [OrderedDict(zip_longest(column_names, row)) for row in rows]

    if transformer.column_filters:
        data = list(transformer.filter_columns(data))
        column_names = [c for c in column_names if c in transformer.column_filters]

    errors = transformer.check_required_columns(data)
    if errors:
        return column_names, data, errors

    return column_names, data, errors


tranformer_config_help = '''
A transform configuration file is used to describe which transformations and
validations to apply to a source CSV file. This is a simple text file using YAML
format, using the same format as an .ABOUT file.

The attributes that can be set in a configuration file are:

* column_renamings:
An optional map of source CSV column name to target CSV new column name that
is used to rename CSV columns.

For instance with this configuration the columns "Directory/Location" will be
renamed to "about_resource" and "foo" to "bar":
    column_renamings:
        'Directory/Location' : about_resource
        foo : bar

The renaming is always applied first before other transforms and checks. All
other column names referenced below are these that exist AFTER the renamings
have been applied to the existing column names.

* required_columns:
An optional list of required column names that must have a value, beyond the
standard columns names. If a source CSV does not have such a column or a row is
missing a value for a required column, an error is reported.

For instance with this configuration an error will be reported if the columns
"name" and "version" are missing or if any row does not have a value set for
these columns:
    required_columns:
        - name
        - version

* column_filters:
An optional list of column names that should be kept in the transformed CSV. If
this list is provided, all the columns from the source CSV that should be kept
in the target CSV must be listed be even if they are standard or required
columns. If this list is not provided, all source CSV columns are kept in the
transformed target CSV.

For instance with this configuration the target CSV will only contains the "name"
and "version" columns and no other column:
    column_filters:
        - name
        - version
'''


@attr.attributes
class Transformer(object):
    __doc__ = tranformer_config_help

    column_renamings = attr.attrib(default=attr.Factory(dict))
    required_columns = attr.attrib(default=attr.Factory(list))
    column_filters = attr.attrib(default=attr.Factory(list))

    # a list of all the standard columns from AboutCode toolkit
    standard_columns = attr.attrib(default=attr.Factory(list), init=False)
    # a list of the subset of standard columns that are essential and MUST be
    # present for AboutCode toolkit to work
    essential_columns = attr.attrib(default=attr.Factory(list), init=False)

    # called by attr after the __init__()
    def __attrs_post_init__(self, *args, **kwargs):
        from attributecode.model import About
        about = About()
        self.essential_columns = list(about.required_fields)
        self.standard_columns = [f.name for f in about.all_fields()]

    @classmethod
    def default(cls):
        """
        Return a default Transformer with built-in transforms.
        """
        return cls(
            column_renamings={},
            required_columns=[],
            column_filters=[],
        )

    @classmethod
    def from_file(cls, location):
        """
        Load and return a Transformer instance from a YAML configuration file at
        `location`.
        """
        with io.open(location, encoding='utf-8') as conf:
            data = saneyaml.load(replace_tab_with_spaces(conf.read()))
        return cls(
            column_renamings=data.get('column_renamings', {}),
            required_columns=data.get('required_columns', []),
            column_filters=data.get('column_filters', []),
        )

    def check_required_columns(self, data):
        """
        Return a list of Error for a `data` list of ordered dict where a
        dict is missing a value for a required column name.
        """
        errors = []
        required = set(self.essential_columns + self.required_columns)
        if not required:
            return []

        for rn, item in enumerate(data):
            missings = [rk for rk in required if not item.get(rk)]
            if not missings:
                continue

            missings = ', '.join(missings)
            msg = 'Row {rn} is missing required values for columns: {missings}'
            errors.append(Error(CRITICAL, msg.format(**locals())))
        return errors

    def apply_renamings(self, column_names):
        """
        Return a tranformed list of `column_names` where columns are renamed
        based on this Transformer configuration.
        """
        renamings = self.column_renamings
        if not renamings:
            return column_names
        renamings = {n.lower(): rn.lower() for n, rn in renamings.items()}

        renamed = []
        for name in column_names:
            name = name.lower()
            new_name = renamings.get(name, name)
            renamed.append(new_name)
        return renamed

    def clean_columns(self, column_names):
        """
        Apply standard cleanups to a list of columns and return these.
        """
        if not column_names:
            return column_names
        return [c.strip().lower() for c in column_names]

    def filter_columns(self, data):
        """
        Yield transformed dicts from a `data` list of dicts keeping only
        columns with a name in the `column_filters`of this Transformer.
        Return the data unchanged if no `column_filters` exists.
        """
        column_filters = set(self.clean_columns(self.column_filters))
        for entry in data:
            items = ((k, v) for k, v in entry.items() if k in column_filters)
            yield OrderedDict(items)


def check_duplicate_columns(column_names):
    """
    Check that there are no duplicate in the `column_names` list of column name
    strings, ignoring case. Return a list of unique duplicated column names.
    """
    counted = Counter(c.lower() for c in column_names)
    return [column for column, count in sorted(counted.items()) if count > 1]


def read_csv_rows(location):
    """
    Yield rows (as a list of values) from a CSV file at `location`.
    """
    with io.open(location, encoding='utf-8', errors='replace') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            yield row


def write_csv(location, data, column_names):  # NOQA
    """
    Write a CSV file at `location` the `data` list of ordered dicts using the
    `column_names`.
    """
    with io.open(location, 'w', encoding='utf-8', newline='\n') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=column_names)
        writer.writeheader()
        writer.writerows(data)
