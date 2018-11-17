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
import errno
import logging
import os
import sys

import click
from attributecode.attrib import check_template
import codecs
# silence unicode literals warnings
click.disable_unicode_literals_warning = True

from attributecode import WARNING
from attributecode.util import unique

from attributecode import __about_spec_version__
from attributecode import __version__
from attributecode import DEFAULT_MAPPING
from attributecode import severities
from attributecode.attrib import generate_and_save as generate_attribution_doc
from attributecode.gen import generate as generate_about_files
from attributecode.model import collect_inventory
from attributecode.model import write_output
from attributecode.util import extract_zip
from attributecode.util import inventory_filter


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


reportable_errors = [u'CRITICAL', u'ERROR', u'WARNING']


def print_version():
    click.echo('Running aboutcode-toolkit version ' + __version__)


# we define a main entry command with subcommands
@click.group(name='about')
@click.version_option(version=__version__, prog_name=prog_name, message=intro)
@click.help_option('-h', '--help')
def cli():
    """
Generate licensing attribution and credit notices from .ABOUT files and inventories.

Read, write and collect provenance and license inventories from .ABOUT files to and from JSON or CSV files.

Use about <command> --help for help on a command.
    """


######################################################################
# inventory subcommand
######################################################################

def validate_filter(ctx, param, value):
    """
    Return the parsed filter if valid or raise a UsageError otherwise.
    """
    if not value:
        return

    kvals, errors = parse_key_values(value)
    if errors:
        ive = '\n'.join(sorted('  ' + x for x in errors))
        msg = ('Invalid --filter option(s):\n'
               '{ive}'.format(**locals()))
        raise click.UsageError(msg)
    return kvals


@cli.command(cls=click.Command,
    short_help='Collect .ABOUT files and write an inventory as CSV or JSON.')

@click.argument('location',
    required=True,
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True))

@click.argument('output',
    required=True,
    type=click.Path(exists=False, dir_okay=False, writable=True, resolve_path=True))

# fIXME: this is too complex and should be removed
@click.option('--filter',
    multiple=True,
    metavar='<key>=<value>',
    callback=validate_filter,
    help='Filter the inventory to ABOUT matching these key=value e.g. "license_expression=gpl-2.0')

@click.option('-f', '--format',
    is_flag=False,
    default='csv',
    show_default=True,
    type=click.Choice(['json', 'csv']),
    help='Set OUTPUT inventory file format.')

@click.option('--mapping',
    is_flag=True,
    help='Use the default file mapping.config (./attributecode/mapping.config) '
    'with mapping between input keys and ABOUT field names.')

@click.option('--mapping-file',
    metavar='FILE',
    type=click.Path(exists=True, dir_okay=True, readable=True, resolve_path=True),
    help='Use a custom mapping file with mapping between input keys and ABOUT field names.')

@click.option('-q', '--quiet',
    is_flag=True,
    help='Do not print error or warning messages.')

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')

def inventory(location, output, mapping, mapping_file,
              format, filter, quiet, verbose):  # NOQA
    """
Collect a JSON or CSV inventory of packages from .ABOUT files.

LOCATION: Path to an .ABOUT file or a directory with .ABOUT files.

OUTPUT: Path to the JSON or CSV inventory file to create.
    """
    if not quiet:
        print_version()
        click.echo('Collecting inventory from ABOUT files...')

    if not os.path.exists(os.path.dirname(output)):
        # FIXME: there is likely a better way to return an error
        raise click.UsageError('ERROR: <OUTPUT> path does not exists.')

    # FIXME: do we really want to continue support zip as an input?
    if location.lower().endswith('.zip'):
        # accept zipped ABOUT files as input
        location = extract_zip(location)

    if mapping and mapping_file:
        raise click.UsageError('Invalid combination of options: --mapping and --mapping-file')

    if mapping:
        mapping_file = DEFAULT_MAPPING

    errors, abouts = collect_inventory(location, mapping_file=mapping_file)

    # FIXME: this is too complex
    if filter:
        abouts = inventory_filter(abouts, filter)

    # Do not write the output if one of the ABOUT files has duplicated keys
    # TODO: why stop only for this message??????
    dup_error_msg = u'Duplicated keys'
    halt_output = False
    for err in errors:
        if dup_error_msg in err.message:
            halt_output = True
            break

    if not halt_output:
        write_errors = write_output(abouts=abouts, location=output, format=format)
        for err in write_errors:
            errors.append(err)
    else:
        if not quiet:
            msg = u'Duplicated keys are not supported.\nPlease correct and re-run.'
            click.echo(msg)

    errors_count = report_errors(errors, quiet, verbose, log_file_loc=output + '-error.log')
    if not quiet:
        msg = 'Inventory collected with {severe_error_count} errors or warnings detected.'
        click.echo(msg.format(**locals()))
    sys.exit(errors_count)


######################################################################
# gen subcommand
######################################################################

@cli.command(cls=click.Command,
    short_help='Generate .ABOUT files from an inventory as CSV or JSON.')

@click.argument('location',
    required=True,
    type=click.Path(exists=True, file_okay=True, readable=True, resolve_path=True))

@click.argument('output',
    required=True,
    type=click.Path(exists=False, writable=True, dir_okay=False, resolve_path=True))

# FIXME: the CLI UX should be improved with two separate options for API key and URL
@click.option('--fetch-license',
    nargs=2,
    type=str,
    metavar='KEY',
    help='Fetch license data and texts from a a DejaCode License Library API. '
         'Create <license>.LICENSE files from the text of each license key '
         'side-by-side with the generated .ABOUT file. Also enhance the .ABOUT '
         'file with other data such name and category.\n\n'
         'The following additional options are required:\n\n'
         'api_url - URL to the DejaCode License Library API endpoint\n\n'
         'api_key - DejaCode API key'
         '\nExample syntax:\n\n'
         "about gen --fetch-license 'api_url' 'api_key'")

# TODO: this option help and long name is obscure and would need to be refactored
@click.option('--license-notice-text-location',
    type=click.Path(exists=True, dir_okay=True, readable=True, resolve_path=True),
    help="Copy the 'license_file' from the directory to the generated location.")

@click.option('--mapping',
    is_flag=True,
    help='Use the default file mapping.config (./attributecode/mapping.config) '
    'with mapping between input keys and ABOUT field names.')

@click.option('--mapping-file',
    metavar='FILE',
    type=click.Path(exists=True, dir_okay=True, readable=True, resolve_path=True),
    help='Use a custom mapping file with mapping between input keys and ABOUT field names.')

@click.option('-q', '--quiet',
    is_flag=True,
    help='Do not print error or warning messages.')

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')

def gen(location, output,
        fetch_license,
        license_notice_text_location,
        mapping, mapping_file,
        quiet, verbose):
    """
Generate .ABOUT files in OUTPUT directory from a JSON or CSV inventory of .ABOUT files at LOCATION.

LOCATION: Path to a JSON or CSV inventory file.

OUTPUT: Path to a directory where ABOUT files are generated.
    """
    if not quiet:
        print_version()
        click.echo('Generating .ABOUT files...')

    if mapping and mapping_file:
        raise click.UsageError('Invalid combination of options: --mapping and --mapping-file')
    if mapping:
        mapping_file = DEFAULT_MAPPING

    if not location.endswith(('.csv', '.json',)):
        raise click.UsageError('ERROR: Invalid input file extension: must be one .csv or .json.')

    errors, abouts = generate_about_files(
        location=location,
        base_dir=output,
        license_notice_text_location=license_notice_text_location,
        fetch_license=fetch_license,
        mapping_file=mapping_file
    )
    abouts_count = len(abouts)

    errors_count = report_errors(errors, quiet, verbose, log_file_loc=output + '-error.log')
    if not quiet:
        msg = '{abouts_count} .ABOUT files generated with {errors_count} errors/warnings.'
        click.echo(msg.format(**locals()))
    sys.exit(errors_count)


######################################################################
# attrib subcommand
######################################################################

def validate_variables(ctx, param, value):
    """
    Return the variables if valid or raise a UsageError otherwise.
    """
    if not value:
        return

    kvals, errors = parse_key_values(value)
    if errors:
        ive = '\n'.join(sorted('  ' + x for x in errors))
        msg = ('Invalid --variable option(s):\n'
               '{ive}'.format(**locals()))
        raise click.UsageError(msg)
    return kvals


@cli.command(cls=click.Command,
    short_help='Generate an attribution document from .ABOUT files.')

@click.argument('location',
    required=True,
    type=click.Path(exists=True, readable=True, resolve_path=True))

@click.argument('output',
    required=True,
    type=click.Path(exists=False, writable=True, resolve_path=True))

@click.option('--template',
    metavar='TEMPLATE_FILE_PATH',
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
    help='Path to an optional custom attribution template to generate the attribution document.')

@click.option('--variable',
    multiple=True,
    callback=validate_variables,
    metavar='<key>=<value>',
    help='Add variable(s) as key=value for use in a custom attribution template.')

@click.option('--inventory',
    type=click.Path(exists=True, file_okay=True, resolve_path=True),
    help='Path to an optional JSON or CSV inventory file listing the '
         'subset of .ABOUT files paths to consider when generating the attribution document.')

@click.option('--mapping',
    is_flag=True,
    help='Use the default file mapping.config (./attributecode/mapping.config) '
    'with mapping between input keys and ABOUT field names.')

@click.option('--mapping-file',
    metavar='FILE',
    type=click.Path(exists=True, dir_okay=True, readable=True, resolve_path=True),
    help='Use a custom mapping file with mapping between input keys and ABOUT field names.')

@click.option('-q', '--quiet',
    is_flag=True,
    help='Do not print error or warning messages.')

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')

def attrib(location, output, template, variable,
           inventory, mapping, mapping_file,
           quiet, verbose):
    """
Generate an attribution document at OUTPUT using .ABOUT files at LOCATION.

LOCATION: Path to a file, directory or .zip archive containing .ABOUT files.

OUTPUT: Path where to write the attribution document.
    """
    if not quiet:
        print_version()
        click.echo('Generating attribution...')

    if mapping and mapping_file:
        raise click.UsageError('Invalid combination of options: --mapping and --mapping-file')
    if mapping:
        mapping_file = DEFAULT_MAPPING

    # Check for template early
    with codecs.open(template, 'rb', encoding='utf-8') as templatef:
        template_error = check_template(templatef.read())
    if template_error:
        lineno, message = template_error
        raise click.UsageError(
            'Template validation error at line: {lineno}: "{message}"'.format(**locals()))

    # accept zipped ABOUT files as input
    if location.lower().endswith('.zip'):
        location = extract_zip(location)

    errors, abouts = collect_inventory(location, mapping_file=mapping_file)

    attrib_errors = generate_attribution_doc(
        abouts=abouts,
        output_location=output,
        template_loc=template,
        variables=variable,
        mapping_file=mapping_file,
        inventory_location=inventory,
    )
    errors.extend(attrib_errors)

    errors_count = report_errors(errors, quiet, verbose, log_file_loc=output + '-error.log')

    if not quiet:
        msg = 'Attribution generated with {errors_count} errors/warnings.'
        click.echo(msg.format(**locals()))
    sys.exit(errors_count)


######################################################################
# check subcommand
######################################################################

@cli.command(cls=click.Command,
    short_help='Validate that the format of .ABOUT files is correct.')

@click.argument('location',
    required=True,
    type=click.Path(exists=True, readable=True, resolve_path=True))

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')

def check(location, verbose):
    """
Check .ABOUT file(s) at LOCATION for validity and print error messages.

LOCATION: Path to a file or directory containing .ABOUT files.
    """
    print_version()
    click.echo('Checking ABOUT files...')
    errors, _abouts = collect_inventory(location)
    if verbose:
        reportable = errors
    else:
        reportable = filter_errors(errors, minimum_severity=WARNING)

    severe_errors_count = report_errors(reportable, quiet=False, verbose=True)

    if severe_errors_count:
        click.echo('Found {severe_error_count} errors or warnings.'.format(severe_errors_count))
    else:
        click.echo('No error found.')
    sys.exit(severe_errors_count)


######################################################################
# Error management
######################################################################

def report_errors(errors, quiet, verbose, log_file_loc=None):
    """
    Return a number of severe errors and display the `errors` list of Error
    objects based on the `quiet` and `verbose` flags.

    If `log_file_loc` directory is provided also write the log to a
     file  as this location if severe errors are detected.
    """
    errors = unique(errors)

    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    handler.setLevel(logging.CRITICAL)
    handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(handler)

    file_logger = logging.getLogger(__name__ + '_file')

    severe_errors = filter_errors(errors, WARNING)
    severe_errors_count = len(severe_errors)

    log_file_obj = None
    try:
        # Create error.log if problematic_error detected
        if severe_errors and log_file_loc:
            # FIXME: this
            log_file = open(log_file_loc, 'w')
            error_msg = '{} errors or warnings detected.'.format(severe_errors_count)
            log_file.write(error_msg)
            file_handler = logging.FileHandler(log_file)
            file_logger.addHandler(file_handler)


        for severity, message in errors:
            sevcode = severities.get(severity) or 'UNKNOWN'
            msg = '{sevcode}: {message}'.format(**locals())
            if not quiet:
                if verbose:
                    click.echo(msg)
                elif severity >= WARNING:
                    click.echo(msg)
            if log_file_loc:
                # The logger will only log error for severity >= 30
                file_logger.log(severity, msg)

    finally:
        if log_file_obj:
            try:
                log_file_obj.close()
            except:
                pass
    return severe_errors_count


def filter_errors(errors, minimum_severity=WARNING):
    """
    Return a list of unique `errors` Error object filtering errors that have a
    severity below `minimum_severity`.
    """
    return unique([e for e in errors if e.severity >= minimum_severity])


######################################################################
# Misc
######################################################################

def parse_key_values(key_values):
    """
    Given a list of "key=value" strings, return:
    - a mapping {key: [value, value, ...]}
    - a sorted list of unique error messages for invalid entries where there is
      a missing a key or value.
    """
    if not key_values:
        return {}, []

    errors = set()
    parsed_key_values = defaultdict(list)
    for key_value in key_values:
        key, _, value = key_value.partition('=')

        key = key.strip().lower()
        if not key:
            errors.add('missing <key> in "{key_value}".'.format(**locals()))
            continue

        value = value.strip()
        if not value:
            errors.add('missing <value> in "{key_value}".'.format(**locals()))
            continue

        values = parsed_key_values[key]
        if value not in values:
            parsed_key_values[key].append(value)

    return dict(parsed_key_values), sorted(errors)


if __name__ == '__main__':
    cli()
