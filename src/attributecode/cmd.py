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

import errno
import logging
import os
from os.path import exists, join
import sys

import click
# silence unicode literals warnings
click.disable_unicode_literals_warning = True

from attributecode import __about_spec_version__
from attributecode import __version__
from attributecode.attrib import generate_and_save as attrib_generate_and_save
from attributecode.gen import generate as gen_generate
from attributecode import model
from attributecode import severities
from attributecode.util import extract_zip
from attributecode.util import to_posix
from attributecode.util import inventory_filter


__copyright__ = """
    Copyright (c) 2013-2017 nexB Inc. All rights reserved.
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


problematic_errors = [u'CRITICAL', u'ERROR', u'WARNING']


def print_version():
    click.echo('Running aboutcode-toolkit version ' + __version__)


class AboutCommand(click.Command):
    def main(self, args=None, prog_name=None, complete_var=None,
             standalone_mode=True, **extra):
        """
        Workaround click 4.0 bug https://github.com/mitsuhiko/click/issues/365
        """
        return click.Command.main(
            self, args=args, prog_name=self.name,
            complete_var=complete_var, standalone_mode=standalone_mode, **extra)


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

@cli.command(cls=AboutCommand,
    short_help='Collect .ABOUT files and write an inventory as CSV or JSON.')

@click.argument('location', nargs=1, required=True,
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True))

@click.argument('output', nargs=1, required=True,
    type=click.Path(exists=False, dir_okay=False, resolve_path=True))

@click.option('--filter', nargs=1, multiple=True,
    help='Filter for the output inventory. e.g. "license_expression=gpl-2.0')

@click.option('-f', '--format', is_flag=False, default='csv', show_default=True,
    type=click.Choice(['json', 'csv']),
    help='Set OUTPUT inventory file format.')

@click.option('--mapping', is_flag=True,
    help='Use the default file mapping.config (./attributecode/mapping.config) with mapping between input keys and ABOUT field names.')

@click.option('--mapping-file', metavar='FILE', nargs=1,
    type=click.Path(exists=True, dir_okay=True, readable=True, resolve_path=True),
    help='Use a custom mapping file with mapping between input keys and ABOUT field names.')

@click.option('--mapping-output', metavar='FILE', nargs=1,
    type=click.Path(exists=True, dir_okay=True, readable=True, resolve_path=True),
    help='Use a custom mapping file with mapping between ABOUT field names and output keys')

@click.option('--verbose', is_flag=True, default=False,
    help='Show all errors and warnings. '
        'By default, the tool only prints these '
        'error levels: CRITICAL, ERROR, and WARNING. '
        'Use this option to print all errors and warning '
        'for any level.'
)

@click.option('-q', '--quiet', is_flag=True,
    help='Do not print error or warning messages.')

@click.help_option('-h', '--help')

def inventory(location, output, mapping, mapping_file, mapping_output, filter, quiet, format, verbose):  # NOQA
    """
Collect a JSON or CSV inventory of components from .ABOUT files.

LOCATION: Path to an .ABOUT file or a directory with .ABOUT files.

OUTPUT: Path to the JSON or CSV inventory file to create.
    """
    print_version()

    if not exists(os.path.dirname(output)):
        # FIXME: there is likely a better way to return an error
        click.echo('ERROR: <OUTPUT> path does not exists.')
        # FIXME: return error code?
        return

    click.echo('Collecting inventory from: %(location)s and writing output to: %(output)s' % locals())

    # FIXME: do we really want to continue support zip as an input?
    if location.lower().endswith('.zip'):
        # accept zipped ABOUT files as input
        location = extract_zip(location)

    errors, abouts = model.collect_inventory(location, use_mapping=mapping, mapping_file=mapping_file)

    updated_abouts = []
    if filter:
        filter_dict = {}
        # Parse the filter and save to the filter dictionary with a list of value
        for element in filter:
            key = element.partition('=')[0]
            value = element.partition('=')[2]
            if key in filter_dict:
                filter_dict[key].append(value)
            else:
                value_list = [value]
                filter_dict[key] = value_list
        updated_abouts = inventory_filter(abouts, filter_dict)
    else:
        updated_abouts = abouts

    # Do not write the output if one of the ABOUT files has duplicated key names
    dup_error_msg = u'Duplicated key name(s)'
    halt_output = False
    for err in errors:
        if dup_error_msg in err.message:
            halt_output = True
            break

    if not halt_output:
        write_errors = model.write_output(updated_abouts, output, format, mapping_output)
        for err in write_errors:
            errors.append(err)
    else:
        msg = u'Duplicated key names are not supported.\n' + \
                        'Please correct and re-run.'
        print(msg)

    error_count = 0

    for e in errors:
        # Only count as warning/error if CRITICAL, ERROR and WARNING
        if e.severity > 20:
            error_count = error_count + 1

    log_errors(errors, error_count, quiet, verbose, os.path.dirname(output))
    click.echo(' %(error_count)d errors or warnings detected.' % locals())
    sys.exit(0)


######################################################################
# gen subcommand
######################################################################

@cli.command(cls=AboutCommand,
    short_help='Generate .ABOUT files from an inventory as CSV or JSON.')

@click.argument('location', nargs=1, required=True,
    type=click.Path(exists=True, file_okay=True, readable=True, resolve_path=True))

@click.argument('output', nargs=1, required=True,
    type=click.Path(exists=True, writable=True, dir_okay=True, resolve_path=True))

@click.option('--fetch-license', type=str, nargs=2, metavar='KEY',
    help=('Fetch licenses text from a DejaCode API. and create <license>.LICENSE side-by-side '
        'with the generated .ABOUT file using data fetched from a DejaCode License Library. '
        'The "license" key is needed in the input. '
        'The following additional options are required:\n\n'
        'api_url - URL to the DejaCode License Library API endpoint\n\n'
        'api_key - DejaCode API key'
        '\nExample syntax:\n\n'
        "about gen --fetch-license 'api_url' 'api_key'")
    )

# TODO: this option help and long name is obscure and would need to be refactored
@click.option('--license-notice-text-location', nargs=1,
    type=click.Path(exists=True, dir_okay=True, readable=True, resolve_path=True),
    help="Copy the 'license_file' from the directory to the generated location.")

@click.option('--mapping', is_flag=True,
    help='Use the default file mapping.config (./attributecode/mapping.config) with mapping between input keys and ABOUT field names.')

@click.option('--mapping-file', metavar='FILE', nargs=1,
    type=click.Path(exists=True, dir_okay=True, readable=True, resolve_path=True),
    help='Use a custom mapping file with mapping between input keys and ABOUT field names.')

@click.option('--verbose', is_flag=True, default=False,
    help='Show all errors and warnings. '
        'By default, the tool only prints these '
        'error levels: CRITICAL, ERROR, and WARNING. '
        'Use this option to print all errors and warning '
        'for any level.'
)

@click.option('-q', '--quiet', is_flag=True,
    help='Do not print error or warning messages.')

@click.help_option('-h', '--help')

def gen(location, output, mapping, mapping_file, license_notice_text_location, fetch_license,
        quiet, verbose):
    """
Generate .ABOUT files in OUTPUT directory from a JSON or CSV inventory of .ABOUT files at LOCATION.

LOCATION: Path to a JSON or CSV inventory file.

OUTPUT: Path to a directory where ABOUT files are generated.
    """
    print_version()

    if not location.endswith('.csv') and not location.endswith('.json'):
        click.echo('ERROR: Invalid input file format:  must be .csv or .json.')
        sys.exit(errno.EIO)

    click.echo('Generating .ABOUT files...')

    errors, abouts = gen_generate(
        location=location, base_dir=output, license_notice_text_location=license_notice_text_location,
        fetch_license=fetch_license, use_mapping=mapping, mapping_file=mapping_file)

    about_count = len(abouts)
    error_count = 0

    for e in errors:
        # Only count as warning/error if CRITICAL, ERROR and WARNING
        if e.severity > 20:
            error_count = error_count + 1
    log_errors(errors, error_count, quiet, verbose, output)
    click.echo('Generated %(about_count)d .ABOUT files with %(error_count)d errors or warnings' % locals())
    sys.exit(0)


######################################################################
# attrib subcommand
######################################################################

@cli.command(cls=AboutCommand,
    short_help='Generate an attribution document from .ABOUT files.')

@click.argument('location', nargs=1, required=True,
    type=click.Path(exists=True, readable=True, resolve_path=True))

@click.argument('output', nargs=1, required=True,
    type=click.Path(exists=False, writable=True, resolve_path=True))

@click.option('--inventory', required=False,
    type=click.Path(exists=True, file_okay=True, resolve_path=True),
    help='Path to an optional JSON or CSV inventory file listing the '
        'subset of .ABOUT files path to consider when generating attribution.'
    )

@click.option('--mapping', is_flag=True,
    help='Use the default file mapping.config (./attributecode/mapping.config) with mapping between input keys and ABOUT field names.')

@click.option('--mapping-file', metavar='FILE', nargs=1,
    type=click.Path(exists=True, dir_okay=True, readable=True, resolve_path=True),
    help='Use a custom mapping file with mapping between input keys and ABOUT field names.')

@click.option('--template', type=click.Path(exists=True), nargs=1,
    help='Path to an optional custom attribution template used for generation.')

@click.option('--vartext', nargs=1, multiple=True,
    help='Variable texts to the attribution template.')

@click.option('--verbose', is_flag=True, default=False,
    help='Show all errors and warnings. '
        'By default, the tool only prints these '
        'error levels: CRITICAL, ERROR, and WARNING. '
        'Use this option to print all errors and warning '
        'for any level.'
)

@click.option('-q', '--quiet', is_flag=True,
    help='Do not print error or warning messages.')

@click.help_option('-h', '--help')

def attrib(location, output, template, mapping, mapping_file, inventory, vartext, quiet, verbose):
    """
Generate an attribution document at OUTPUT using .ABOUT files at LOCATION.

LOCATION: Path to an .ABOUT file, a directory containing .ABOUT files or a .zip archive containing .ABOUT files.

OUTPUT: Path to output file to write the attribution to.
    """
    print_version()
    click.echo('Generating attribution...')

    # accept zipped ABOUT files as input
    if location.lower().endswith('.zip'):
        location = extract_zip(location)

    inv_errors, abouts = model.collect_inventory(location, use_mapping=mapping, mapping_file=mapping_file)
    no_match_errors = attrib_generate_and_save(
        abouts=abouts, output_location=output,
        use_mapping=mapping, mapping_file=mapping_file, template_loc=template,
        inventory_location=inventory, vartext=vartext)

    if not no_match_errors:
        # Check for template error
        with open(output, 'r') as output_file:
            first_line = output_file.readline()
            if first_line.startswith('Template'):
                click.echo(first_line)
                sys.exit(errno.ENOEXEC)

    for no_match_error in no_match_errors:
        inv_errors.append(no_match_error)

    error_count = 0

    for e in inv_errors:
        # Only count as warning/error if CRITICAL, ERROR and WARNING
        if e.severity > 20:
            error_count = error_count + 1

    log_errors(inv_errors, error_count, quiet, verbose, os.path.dirname(output))
    click.echo(' %(error_count)d errors or warnings detected.' % locals())
    click.echo('Finished.')
    sys.exit(0)


######################################################################
# check subcommand
######################################################################

@cli.command(cls=AboutCommand, short_help='Validate that the format of .ABOUT files is correct.')

@click.argument('location', nargs=1, required=True,
    type=click.Path(exists=True, readable=True, resolve_path=True))

@click.option('--verbose', is_flag=True, default=False,
    help='Show all errors and warnings. '
        'By default, the tool only prints these '
        'error levels: CRITICAL, ERROR, and WARNING. '
        'Use this option to print all errors and warning '
        'for any level.'
)

@click.help_option('-h', '--help')

def check(location, verbose):
    """
Check and validate .ABOUT file(s) at LOCATION for errors and
print error messages on the terminal.

LOCATION: Path to a .ABOUT file or a directory containing .ABOUT files.
    """
    click.echo('Running aboutcode-toolkit version ' + __version__)
    click.echo('Checking ABOUT files...')

    errors, abouts = model.collect_inventory(location)

    msg_format = '%(sever)s: %(message)s'
    print_errors = []
    number_of_errors = 0
    for severity, message in errors:
        sever = severities[severity]
        # Only problematic_errors should be counted.
        # Others such as INFO should not be counted as error.
        if sever in problematic_errors:
            number_of_errors = number_of_errors + 1
        if verbose:
            print_errors.append(msg_format % locals())
        elif sever in problematic_errors:
            print_errors.append(msg_format % locals())

    for err in print_errors:
        print(err)

    if print_errors:
        click.echo('Found {} errors.'.format(number_of_errors))
        # FIXME: not sure this is the right way to exit with a return code
        sys.exit(1)
    else:
        click.echo('No error found.')
    sys.exit(0)


def log_errors(errors, err_count, quiet, verbose, base_dir=False):
    """
    Iterate of sequence of Error objects and print and log errors with
    a severity superior or equal to level.
    """
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    handler.setLevel(logging.CRITICAL)
    handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(handler)
    file_logger = logging.getLogger(__name__ + '_file')

    msg_format = '%(sever)s: %(message)s'

    # Create error.log if problematic_error detected
    if base_dir and have_problematic_error(errors):
        bdir = to_posix(base_dir)
        LOG_FILENAME = 'error.log'
        log_path = join(bdir, LOG_FILENAME)
        if exists(log_path):
            os.remove(log_path)
        f = open(log_path, "a")
        error_msg = str(err_count) + u" errors or warnings detected."
        f.write(error_msg)
        file_handler = logging.FileHandler(log_path)
        file_logger.addHandler(file_handler)

    for severity, message in errors:
        sever = severities[severity]
        if not quiet:
            if verbose:
                print(msg_format % locals())
            elif sever in problematic_errors:
                print(msg_format % locals())
        if base_dir:
            # The logger will only log error for severity >= 30
            file_logger.log(severity, msg_format % locals())


def have_problematic_error(errors):
    for severity, message in errors:  # NOQA
        sever = severities[severity]
        if sever in problematic_errors:
            return True
    return False

if __name__ == '__main__':
    cli()
