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

from collections import defaultdict
from functools import partial
import io
import os
import sys

import click
# silence unicode literals warnings
click.disable_unicode_literals_warning = True

from aboutcode import __about_spec_version__
from aboutcode import __version__
from aboutcode import Error
from aboutcode import CRITICAL
from aboutcode import WARNING
from aboutcode import severities

from aboutcode.attrib import check_template
from aboutcode.attrib import DEFAULT_TEMPLATE_FILE
from aboutcode.attrib import generate_attribution_doc
from aboutcode.gen import generate_about_files
from aboutcode.inv import collect_inventory
from aboutcode.inv import save_as_json
from aboutcode.inv import save_as_csv
from aboutcode.util import extract_zip
from aboutcode.util import unique


__copyright__ = """
    Copyright (c) 2013-2018 nexB Inc and others. All rights reserved.
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at
        http://www.apache.org/licenses/LICENSE-2.0
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License."""


prog_name = 'AboutCode-toolkit'


intro = '''%(prog_name)s version %(__version__)s
ABOUT spec version: %(__about_spec_version__)s
https://aboutcode.org
%(__copyright__)s
''' % locals()



def print_version():
    click.echo('Running aboutcode-toolkit version ' + __version__)


class AboutCommand(click.Command):
    """
    An enhanced click Command working around some Click quirk.
    """
    def main(self, args=None, prog_name=None, complete_var=None,
             standalone_mode=True, **extra):
        """
        Workaround click bug https://github.com/mitsuhiko/click/issues/365
        """
        return click.Command.main(
            self, args=args, prog_name=self.name,
            complete_var=complete_var, standalone_mode=standalone_mode, **extra)


# we define a main entry command with subcommands
@click.group(name='about')
@click.version_option(version=__version__, prog_name=prog_name, message=intro)
@click.help_option('-h', '--help')
def about():
    """
Generate licensing attribution and credit notices from .ABOUT files and inventories.

Read, write and collect provenance and license inventories from .ABOUT files to and from JSON or CSV files.

Use about <command> --help for help on a command.
    """


######################################################################
# option validators
######################################################################

def validate_key_values(ctx, param, value):
    """
    Return the a dict of {key: [values,...] if valid or raise a UsageError
    otherwise.
    """
    if not value:
        return

    kvals, errors = parse_key_values(value)
    if errors:
        name = param.name
        ive = '\n'.join(sorted('  ' + x for x in errors))
        msg = ('Invalid {name} option(s):\n'
               '{ive}'.format(**locals()))
        raise click.UsageError(msg)
    return kvals


def validate_extensions(ctx, param, value, extensions=tuple(('.csv', '.json',))):
    if not value:
        return
    if not value.endswith(extensions):
        msg = ' '.join(extensions)
        raise click.UsageError(
            'Invalid {param} file extension: must be one of: {msg}'.format(**locals()))
    return value


def validate_api_url(ctx, param, value):
    if value:
        value = value.strip('/')
        if not value.endswith('licenses'):
            value = '/'.join([value, 'licenses'])
    return value


######################################################################
# inventory subcommand
######################################################################

@about.command(cls=AboutCommand,
    short_help='Collect an inventory of .ABOUT files in a CSV or JSON file.')

@click.argument('location',
    required=True,
    metavar='LOCATION',
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True))

@click.argument('output',
    required=True,
    metavar='OUTPUT',
    type=click.Path(exists=False, dir_okay=False, writable=True, resolve_path=True))

@click.option('-f', '--format',
    is_flag=False,
    default='csv',
    show_default=True,
    type=click.Choice(['json', 'csv']),
    help='Set OUTPUT inventory file format.')

@click.option('-c', '--check-files',
    is_flag=True,
    help='Check that code and license files referenced in ABOUT files exist.')

@click.option('-q', '--quiet',
    is_flag=True,
    help='Do not print error or warning messages.')

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')

def inventory(location, output, format, check_files, quiet, verbose):  # NOQA
    """
Collect the inventory of .ABOUT file data as CSV or JSON.

LOCATION: Path to an .ABOUT file or a directory with .ABOUT files.

OUTPUT: Path to the JSON or CSV inventory file to create.
    """
    if not quiet:
        print_version()
        click.echo('Collecting inventory from ABOUT files...')

    # FIXME: do we really want to continue support zip as an input?
    # accept zipped ABOUT files as input
    if location.lower().endswith('.zip'):
        location = extract_zip(location)

    errors, abouts = collect_inventory(location, check_files=check_files)

    writers = {
        'json': save_as_json,
        'csv': save_as_csv,
    }
    writer = writers[format]
    write_errors = writer(location=output, abouts=abouts)
    errors.extend(write_errors)
    errors_count = report_errors(errors, quiet, verbose, log_file_loc=output + '-error.log')
    if not quiet:
        msg = 'Inventory collected in {output}.'.format(**locals())
        click.echo(msg)
    sys.exit(errors_count)


######################################################################
# gen subcommand
######################################################################

@about.command(cls=AboutCommand,
    short_help='Generate .ABOUT files from an CSV or JSON inventory.')

@click.argument('location',
    required=True,
    metavar='LOCATION',
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True))

@click.argument('output',
    required=True,
    metavar='OUTPUT',
    type=click.Path(exists=True, file_okay=False, writable=True, resolve_path=True))

@click.option('--reference',
    metavar='DIR',
    type=click.Path(exists=True, file_okay=False, readable=True, resolve_path=True),
    help='Path to a directory with reference license data and text files.')

@click.option('-q', '--quiet',
    is_flag=True,
    help='Do not print error or warning messages.')

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')

def gen(location, output, reference, quiet, verbose):
    """
Generate .ABOUT files in OUTPUT from an inventory of .ABOUT files at LOCATION.

LOCATION: Path to a JSON or CSV inventory file.

OUTPUT: Path to a directory where ABOUT files are generated.
    """
    if not quiet:
        print_version()
        click.echo('Generating .ABOUT files...')

    if not location.endswith(('.csv', '.json',)):
        raise click.UsageError('ERROR: Invalid input file extension: must be one .csv or .json.')

    errors, abouts = generate_about_files(
        inventory_location=location,
        target_dir=output,
        reference_dir=reference)

    errors_count = report_errors(errors, quiet, verbose, log_file_loc=output + '-error.log')
    if not quiet:
        abouts_count = len(abouts)
        msg = '{abouts_count} .ABOUT files generated in {output}'.format(**locals())
        click.echo(msg)
    sys.exit(errors_count)


######################################################################
# fetch-licenses subcommand
######################################################################

@about.command(cls=AboutCommand,
    short_help='Fetch licenses from a remote DejaCode License Library API.',
    name='fetch-licenses')

@click.argument('location',
    required=True,
    metavar='LOCATION',
    callback=partial(validate_extensions, extensions=('.csv',)),
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True))

@click.argument('output',
    required=True,
    metavar='OUTPUT',
    type=click.Path(exists=True, dir_okay=True, file_okay=False, writable=True, resolve_path=True))

@click.option('--api-key',
    metavar='API-KEY',
    envvar='DEJACODE_API_KEY',
    type=str,
    help='DejaCode License Library API KEY.')

@click.option('--api-url',
    metavar='API-URL',
    envvar='DEJACODE_API_URL',
    callback=validate_api_url,
    type=str,
    help='DejaCode License Library API URL.')

@click.option('-q', '--quiet',
    is_flag=True,
    help='Do not print error or warning messages.')

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')

def fetch_licenses(location, output, api_key, api_url, quiet, verbose):  # NOQA
    """
Load inventory from LOCATION then fetch license texts and data referenced in
this inventory from a remote DejaCode License Library API and finally save the

LOCATION: Path to a JSON or CSV inventory file.

OUTPUT: Path where to save the retrieved license data and textx..
    """
    from aboutcode import api
    from aboutcode import gen

    if not quiet:
        print_version()
        click.echo('Fetching licenses...')

    errors, abouts = gen.load_inventory(location)

    licenses_by_key, fetch_errors = api.fetch_licenses(abouts, api_url, api_key, verbose)
    errors.extend(fetch_errors)

    for license in licenses_by_key.values():  # NOQA
        license.dump(output)

    errors_count = report_errors(errors, quiet, verbose)
    if not quiet:
        msg = 'Licenses saved to {output}'.format(**locals())
        click.echo(msg)
    sys.exit(errors_count)


######################################################################
# attrib subcommand
######################################################################

def validate_template(ctx, param, value):
    if not value:
        return DEFAULT_TEMPLATE_FILE

    with io.open(value, encoding='utf-8') as templatef:
        template_error = check_template(templatef.read())

    if template_error:
        lineno, message = template_error
        raise click.UsageError(
            'Template syntax error at line: '
            '{lineno}: "{message}"'.format(**locals()))
    return value


@about.command(cls=AboutCommand,
    short_help='Generate an attribution document from .ABOUT files.')

@click.argument('location',
    required=True,
    metavar='LOCATION',
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True))

@click.argument('output',
    required=True,
    metavar='OUTPUT',
    type=click.Path(exists=False, dir_okay=False, writable=True, resolve_path=True))

@click.option('--template',
    metavar='FILE',
    callback=validate_template,
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
    help='Path to an optional custom attribution template to generate the '
         'attribution document. If not provided the default built-in template is used.')

@click.option('--vartext',
    multiple=True,
    callback=validate_key_values,
    metavar='<key>=<value>',
    help='Add variable text as key=value for use in a custom attribution template.')

@click.option('-q', '--quiet',
    is_flag=True,
    help='Do not print error or warning messages.')

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')

def attrib(location, output, template, vartext, quiet, verbose):
    """
Generate an attribution document at OUTPUT using .ABOUT files at LOCATION.

LOCATION: Path to a file, directory or .zip archive containing .ABOUT files.

OUTPUT: Path where to write the attribution document.
    """
    if not quiet:
        print_version()
        click.echo('Generating attribution...')

    errors = []

    template_error = check_template(template)
    if template_error:
        lineno, message = template_error
        errors.apend(Error(
            CRITICAL,
            'Template validation error at line: {lineno}: "{message}"'.format(**locals())
        ))

    else:
        # FIXME: this is not a feature. Unzipping should be done by the users IMHO
        # accept zipped ABOUT files as input
        if location.lower().endswith('.zip'):
            location = extract_zip(location)

        errors, abouts = collect_inventory(location)

        # load all files
        for about in abouts:
            about.load_files()

        attrib_errors = generate_attribution_doc(
            abouts=abouts,
            output_location=output,
            template_loc=template,
            variables=vartext,
        )
        errors.extend(attrib_errors)

    errors_count = report_errors(errors, quiet, verbose, log_file_loc=output + '-error.log')

    if not quiet:
        msg = 'Attribution generated in: {output}'.format(**locals())
        click.echo(msg)
    sys.exit(errors_count)


######################################################################
# check subcommand
######################################################################

# FIXME: This is really only a dupe of the Inventory command

@about.command(cls=AboutCommand,
    short_help='Validate the format of .ABOUT files.')

@click.argument('location',
    required=True,
    metavar='LOCATION',
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True))

@click.option('-c', '--check-files',
    is_flag=True,
    help='Check that code and license files referenced in ABOUT files exist.')

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')

def check(location, check_files, verbose):
    """
Check .ABOUT file(s) at LOCATION for validity and print error messages.

LOCATION: Path to a file or directory containing .ABOUT files.
    """
    print_version()
    click.echo('Checking ABOUT files...')
    errors, _abouts = collect_inventory(location, check_files=check_files)
    severe_errors_count = report_errors(errors, quiet=False, verbose=verbose)
    sys.exit(severe_errors_count)


######################################################################
# transform subcommand
######################################################################

def print_config_help(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    from aboutcode.transform import tranformer_config_help
    click.echo(tranformer_config_help)
    ctx.exit()


@about.command(cls=AboutCommand,
    short_help='Transform a CSV by renaming and filtering columns.')

@click.argument('location',
    required=True,
    callback=partial(validate_extensions, extensions=('.csv',)),
    metavar='LOCATION',
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True))

@click.argument('output',
    required=True,
    callback=partial(validate_extensions, extensions=('.csv',)),
    metavar='OUTPUT',
    type=click.Path(exists=False, dir_okay=False, writable=True, resolve_path=True))

@click.option('-c', '--configuration',
    metavar='FILE',
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
    help='Path to an optional YAML configuration file. See --help-format for '
         'format help.')

@click.option('--help-format',
    is_flag=True, is_eager=True, expose_value=False,
    callback=print_config_help,
    help='Show configuration file format help and exit.')

@click.option('-q', '--quiet',
    is_flag=True,
    help='Do not print error or warning messages.')

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')

def transform(location, output, configuration, quiet, verbose):  # NOQA
    """
Transform and validate the CSV file at LOCATION by applying renamings and
filters and write a new CSV to OUTPUT.

LOCATION: Path to a CSV file.

OUTPUT: Path to CSV inventory file to create.
    """
    from aboutcode.transform import transform_csv_to_csv
    from aboutcode.transform import Transformer

    if not quiet:
        print_version()
        click.echo('Transforming CSV...')

    if not configuration:
        transformer = Transformer.default()
    else:
        transformer = Transformer.from_file(configuration)

    errors = transform_csv_to_csv(location, output, transformer)

    errors_count = report_errors(errors, quiet, verbose)
    if not quiet:
        msg = 'Transformed CSV written to {output}.'.format(**locals())
        click.echo(msg)
    sys.exit(errors_count)


######################################################################
# Error management
######################################################################

def report_errors(errors, quiet, verbose, log_file_loc=None):
    """
    Report the `errors` list of Error objects to screen based on the `quiet` and
    `verbose` flags.

    If `log_file_loc` file location is provided also write a verbose log to this
    file.
    Return True if there were severe error reported.
    """
    errors = unique(errors)
    messages, severe_errors_count = get_error_messages(errors, quiet, verbose)
    for msg in messages:
        click.echo(msg)
    if log_file_loc:
        log_msgs, _ = get_error_messages(errors, quiet=False, verbose=True)
        with io.open(log_file_loc, 'w', encoding='utf-8') as lf:
            lf.write('\n'.join(log_msgs))
    return severe_errors_count


def get_error_messages(errors, quiet=False, verbose=False):
    """
    Return a tuple of (list of error message strings to report,
    severe_errors_count) given an `errors` list of Error objects and using the
    `quiet` and `verbose` flags.
    """
    errors = unique(errors)
    severe_errors = filter_errors(errors, WARNING)
    severe_errors_count = len(severe_errors)

    messages = []

    if severe_errors and not quiet:
        error_msg = 'Command completed with {} errors or warnings.'.format(severe_errors_count)
        messages.append(error_msg)

    for error in errors:
        severity = error.severity
        message = error.message
        path = error.path
        sevcode = severities.get(severity) or 'UNKNOWN'

        msg = '{sevcode}: '
        if path:
            msg += 'in ABOUT file: "{path}": '
        msg += '{message}'
        msg = msg.format(**locals())
        if not quiet:
            if verbose:
                messages.append(msg)
            elif severity >= WARNING:
                messages .append(msg)
    return messages, severe_errors_count

######################################################################
# Misc
######################################################################

def parse_key_values(key_values):
    """
    Given a list of "key=value" strings, return:
    - a dict {key: value}
    - a sorted list of unique error messages for invalid entries where there is
      a missing a key or value or duplicated key.
    """
    if not key_values:
        return {}, []

    errors = set()
    parsed_key_values = {}
    for key_value in key_values:
        key, _, value = key_value.partition('=')

        key = key.strip().strip('\'"').lower()
        if not key:
            errors.add('missing <key> in "{key_value}".'.format(**locals()))
            continue

        if key in parsed_key_values:
            errors.add('duplicated <key> already defined: "{key_value}".'.format(**locals()))
            continue

        value = value.strip()
        if not value:
            errors.add('missing <value> in "{key_value}".'.format(**locals()))
            continue

        parsed_key_values[key] = value

    return parsed_key_values, sorted(errors)


def filter_errors(errors, minimum_severity=WARNING):
    """
    Return a list of unique `errors` Error object filtering errors that have a
    severity below `minimum_severity`.
    """
    return unique([e for e in errors if e.severity >= minimum_severity])


if __name__ == '__main__':
    about()
