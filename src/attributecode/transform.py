#!/usr/bin/env python
# -*- coding: utf8 -*-
# ============================================================================
#  Copyright (c) 2013-2018 nexB Inc. http://www.nexb.com/ - All rights reserved.
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
from attributecode.model import About
from attributecode.util import csv
from attributecode.util import python2


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

    if transformer.kept_columns:
        data = list(transformer.filter_columns(data))
        column_names = [c for c in column_names if c in transformer.kept_columns]

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
        'Directory/Location': about_resource
        foo: bar

The renaming is always applied first before other transforms and checks. All
other column names referenced below are these that exist AFTER the renamings
have been applied to the existing column names.

* kept_columns:
An optional list of column names that should be kept in the transformed CSV.
If this list is NOT provided, all the columns from the source CSV will be kept
and eventually added in generated .ABOUT files.
If this list is provided, only the listed columns are kept in the transformed
CSV and other columns are removed.

For instance with this configuration the target CSV will only contains the "name"
and "version" columns and no other column:
    kept_columns:
        - name
        - version

* required_columns:
An optional list of required column names that must have a value, beyond the
standard columns names. If a source CSV does not have such a column or a row is
missing a value for a listed required column, an error is reported.
This validation occurs after processing the CVS for "kept_columns"

For instance with this configuration an error will be reported if the columns
"name" and "version" are missing or if any row does not have a value set for
these columns:
    required_columns:
        - name
        - version
'''


@attr.attributes
class Transformer(object):
    __doc__ = tranformer_config_help

    column_renamings = attr.attrib(default=attr.Factory(dict))
    required_columns = attr.attrib(default=attr.Factory(list))
    kept_columns = attr.attrib(default=attr.Factory(list))

    # a list of all the standard columns from AboutCode toolkit
    standard_columns = attr.attrib(default=attr.Factory(list), init=False)
    # a list of the subset of standard columns that are essential and MUST be
    # present for AboutCode toolkit to work
    essential_columns = attr.attrib(default=attr.Factory(list), init=False)

    # called by attr after the __init__()
    def __attrs_post_init__(self, *args, **kwargs):
        self.essential_columns = ['about_resource', 'about_file_path']
        self.standard_columns = About.standard_fields()

    @classmethod
    def default(cls):
        """
        Return a default Transformer with built-in transforms.
        """
        return cls(
            column_renamings={},
            required_columns=[],
            kept_columns=[])

    @classmethod
    def from_file(cls, location):
        """
        Load and return a Transformer instance from a YAML configuration file at
        `location`.
        """
        with io.open(location, encoding='utf-8') as conf:
            data = saneyaml.load(conf.read())
        return cls(
            column_renamings=data.get('column_renamings', {}),
            required_columns=data.get('required_columns', []),
            kept_columns=data.get('kept_columns', []),
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
        Apply standard cleanups to a list of column names and return these.
        """
        if not column_names:
            return column_names
        return [c.strip().lower() for c in column_names]

    def filter_columns(self, data):
        """
        Yield transformed mappings from a `data` list of mapping keeping only
        columns with a name in the `kept_columns`of this Transformer.
        Return the data unchanged if `kept_columns` does not exist or is empty.
        """
        kept_columns = set(self.clean_columns(self.kept_columns))
        for entry in data:
            if kept_columns:
                items = ((k, v) for k, v in entry.items() if k in kept_columns)
                yield OrderedDict(items)
            else:
                yield entry


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
    # note: Excel can produce unreadable UTF files
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
