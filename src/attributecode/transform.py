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
import json

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
    transformations using the `transformer` Transformer.
    Return a list of Error objects.
    """
    if not transformer:
        raise ValueError('Cannot transform without Transformer')

    rows = read_csv_rows(location)

    field_names, data, errors = transform_csv(rows, transformer)

    if errors:
        return errors
    else:
        write_csv(output, data, field_names)
        return []

def transform_json_to_json(location, output, transformer):
    """
    Read a JSON file at `location` and write a new JSON file at `output`. Apply
    transformations using the `transformer` Transformer.
    Return a list of Error objects.
    """
    if not transformer:
        raise ValueError('Cannot transform without Transformer')

    data = read_json(location)

    new_data, errors = transform_json(data, transformer)

    if errors:
        return errors
    else:
        write_json(output, new_data)
        return []


def transform_csv(rows, transformer):
    """
    Read a list of list of CSV-like data `rows` and apply transformations using the
    `transformer` Transformer.
    Return a tuple of:
       ([field names...], [transformed ordered dict...], [Error objects..])
    """

    if not transformer:
        return rows

    errors = []
    rows = iter(rows)
    field_names = next(rows)
    field_names = transformer.clean_fields(field_names)

    dupes = check_duplicate_fields(field_names)

    if dupes:
        msg = 'Duplicated field name: {name}'
        errors.extend(Error(CRITICAL, msg.format(name)) for name in dupes)
        return field_names, [], errors

    field_names = transformer.apply_renamings(field_names)

    # convert to dicts using the renamed fields
    data = [OrderedDict(zip_longest(field_names, row)) for row in rows]

    if transformer.field_filters:
        data = list(transformer.filter_fields(data))
        field_names = [c for c in field_names if c in transformer.field_filters]

    errors = transformer.check_required_fields(data)

    return field_names, data, errors


def transform_json(data, transformer):
    """
    Read a dictionary and apply transformations using the
    `transformer` Transformer.
    Return a new list of dictionary.
    """

    if not transformer:
        return data

    errors = []
    new_data = []
    renamings = transformer.field_renamings
    #if json is output of scancode-toolkit
    try:
        if(data["headers"][0]["tool_name"] == "scancode-toolkit"):
            #only takes data inside "files"
            data = data["files"]
    except:
        pass
    if isinstance(data, list):
        for item in data:
            element, err = process_json_keys(item, renamings, transformer)
            for e in element:
                new_data.append(e)
            for e in err:
                errors.append(e)
    else: 
        new_data, errors = process_json_keys(data, renamings, transformer)

    return new_data, errors


def process_json_keys(data, renamings, transformer):
    o_dict = OrderedDict()
    for k in data.keys():
        if k in renamings.keys():
            for r_key in renamings.keys():
                if k == r_key:
                    o_dict[renamings[r_key]] = data[k]
        else:
            o_dict[k] = data[k]
        new_data = [o_dict]

    if transformer.field_filters:
        new_data = list(transformer.filter_fields(new_data))
    else:
        new_data = list(new_data)

    errors = transformer.check_required_fields(new_data)
    return new_data, errors


tranformer_config_help = '''
A transform configuration file is used to describe which transformations and
validations to apply to a source CSV file. This is a simple text file using YAML
format, using the same format as an .ABOUT file.

The attributes that can be set in a configuration file are:

* field_renamings:
An optional map of source CSV or JSON field name to target CSV/JSON new field name that
is used to rename CSV fields.

For instance with this configuration the fields "Directory/Location" will be
renamed to "about_resource" and "foo" to "bar":
    field_renamings:
        'Directory/Location' : about_resource
        foo : bar

The renaming is always applied first before other transforms and checks. All
other field names referenced below are these that exist AFTER the renamings
have been applied to the existing field names.

* required_fields:
An optional list of required field names that must have a value, beyond the
standard fields names. If a source CSV/JSON does not have such a field or a row is
missing a value for a required field, an error is reported.

For instance with this configuration an error will be reported if the fields
"name" and "version" are missing or if any row does not have a value set for
these fields:
    required_fields:
        - name
        - version

* field_filters:
An optional list of field names that should be kept in the transformed CSV/JSON. If
this list is provided, all the fields from the source CSV/JSON that should be kept
in the target CSV/JSON must be listed be even if they are standard or required
fields. If this list is not provided, all source CSV/JSON fields are kept in the
transformed target CSV/JSON.

For instance with this configuration the target CSV/JSON will only contains the "name"
and "version" fields and no other field:
    field_filters:
        - name
        - version
'''


@attr.attributes
class Transformer(object):
    __doc__ = tranformer_config_help

    field_renamings = attr.attrib(default=attr.Factory(dict))
    required_fields = attr.attrib(default=attr.Factory(list))
    field_filters = attr.attrib(default=attr.Factory(list))

    # a list of all the standard fields from AboutCode toolkit
    standard_fields = attr.attrib(default=attr.Factory(list), init=False)
    # a list of the subset of standard fields that are essential and MUST be
    # present for AboutCode toolkit to work
    essential_fields = attr.attrib(default=attr.Factory(list), init=False)

    # called by attr after the __init__()
    def __attrs_post_init__(self, *args, **kwargs):
        from attributecode.model import About
        about = About()
        self.essential_fields = list(about.required_fields)
        self.standard_fields = [f.name for f in about.all_fields()]

    @classmethod
    def default(cls):
        """
        Return a default Transformer with built-in transforms.
        """
        return cls(
            field_renamings={},
            required_fields=[],
            field_filters=[],
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
            field_renamings=data.get('field_renamings', {}),
            required_fields=data.get('required_fields', []),
            field_filters=data.get('field_filters', []),
        )

    def check_required_fields(self, data):
        """
        Return a list of Error for a `data` list of ordered dict where a
        dict is missing a value for a required field name.
        """
        errors = []
        required = set(self.essential_fields + self.required_fields)
        if not required:
            return []

        for rn, item in enumerate(data):
            missings = [rk for rk in required if not item.get(rk)]
            if not missings:
                continue

            missings = ', '.join(missings)
            msg = 'Row {rn} is missing required values for fields: {missings}'
            errors.append(Error(CRITICAL, msg.format(**locals())))
        return errors

    def apply_renamings(self, field_names):
        """
        Return a tranformed list of `field_names` where fields are renamed
        based on this Transformer configuration.
        """
        renamings = self.field_renamings
        if not renamings:
            return field_names
        renamings = {n.lower(): rn.lower() for n, rn in renamings.items()}

        renamed = []
        for name in field_names:
            name = name.lower()
            new_name = renamings.get(name, name)
            renamed.append(new_name)
        return renamed

    def clean_fields(self, field_names):
        """
        Apply standard cleanups to a list of fields and return these.
        """
        if not field_names:
            return field_names
        return [c.strip().lower() for c in field_names]

    def filter_fields(self, data):
        """
        Yield transformed dicts from a `data` list of dicts keeping only
        fields with a name in the `field_filters`of this Transformer.
        Return the data unchanged if no `field_filters` exists.
        """
        field_filters = set(self.clean_fields(self.field_filters))
        for entry in data:
            items = ((k, v) for k, v in entry.items() if k in field_filters)
            yield OrderedDict(items)


def check_duplicate_fields(field_names):
    """
    Check that there are no duplicate in the `field_names` list of field name
    strings, ignoring case. Return a list of unique duplicated field names.
    """
    counted = Counter(c.lower() for c in field_names)
    return [field for field, count in sorted(counted.items()) if count > 1]


def read_csv_rows(location):
    """
    Yield rows (as a list of values) from a CSV file at `location`.
    """
    with io.open(location, encoding='utf-8', errors='replace') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            yield row


def read_json(location):
    """
    Yield rows (as a list of values) from a CSV file at `location`.
    """
    with io.open(location, encoding='utf-8', errors='replace') as jsonfile:
        data = json.load(jsonfile, object_pairs_hook=OrderedDict)
        return data


def write_csv(location, data, field_names):  # NOQA
    """
    Write a CSV file at `location` the `data` list of ordered dicts using the
    `field_names`.
    """
    with io.open(location, 'w', encoding='utf-8', newline='\n') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(data)


def write_json(location, data):
    """
    Write a JSON file at `location` the `data` list of ordered dicts.
    """
    with open(location, 'w') as jsonfile:
        json.dump(data, jsonfile, indent=3)
