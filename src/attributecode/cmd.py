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

import codecs
import logging
import os
from os.path import exists, join
import sys

import click
# silence unicode literals warnings
click.disable_unicode_literals_warning = True

import attributecode
from attributecode import CRITICAL
from attributecode import ERROR
from attributecode import INFO
from attributecode import NOTSET
from attributecode import WARNING
from attributecode import __about_spec_version__
from attributecode import __version__
from attributecode import attrib
from attributecode import Error
from attributecode import gen
from attributecode import model
from attributecode.model import About
from attributecode import severities
from attributecode.util import extract_zip
from attributecode.util import to_posix


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

Use about-code <command> --help for help on a command.
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

@click.option('-f', '--format', is_flag=False, default='csv', show_default=True,
    type=click.Choice(['json', 'csv']),
    help='Set OUTPUT inventory file format.')

@click.option('-q', '--quiet', is_flag=True,
    help='Do not print error or warning messages.')

@click.help_option('-h', '--help')

def inventory(location, output, quiet, format):
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

    click.echo('Collecting inventory from: %(location)r and writing output to: %(output)r' % locals())

    # FIXME: do we really want to continue support zip as an input?
    if location.lower().endswith('.zip'):
        # accept zipped ABOUT files as input
        location = extract_zip(location)

    errors, abouts = attributecode.model.collect_inventory(location)

    write_errors = model.write_output(abouts, output, format)
    for err in write_errors:
        errors.append(err)
        log_errors(errors, quiet, os.path.dirname(output))


######################################################################
# gen subcommand
######################################################################

@cli.command(cls=AboutCommand,
    short_help='Generate .ABOUT files from an inventory as CSV or JSON.')

@click.argument('location', nargs=1, required=True,
    type=click.Path(exists=True, file_okay=True, readable=True, resolve_path=True))

@click.argument('output', nargs=1, required=True,
    type=click.Path(exists=True, writable=True, dir_okay=True, resolve_path=True))

@click.option('--fetch-license', type=str, nargs=2,
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
    help="Copy the 'license_file' from the directory to the generated location")

@click.option('--mapping', is_flag=True,
    help='Use file mapping.config with mapping between input keys and ABOUT field names')

@click.option('-q', '--quiet', is_flag=True,
    help='Do not print error or warning messages.')

@click.help_option('-h', '--help')

def gen(location, output, mapping, license_notice_text_location, fetch_license, quiet):
    """
Generate .ABOUT files in OUTPUT directory from a JSON or CSV inventory of .ABOUT files at LOCATION.

LOCATION: Path to a JSON or CSV inventory file.

OUTPUT: Path to a directory where ABOUT files are generated.
    """
    print_version()

    if not location.endswith('.csv') and not location.endswith('.json'):
        click.echo('ERROR: Invalid input file format:  must be .csv or .json.')
        # FIXME: return error code?
        return

    click.echo('Generating .ABOUT files...')

    errors, abouts = attributecode.gen.generate(
        location=location, base_dir=output, mapping=mapping,
        license_notice_text_location=license_notice_text_location,
        fetch_license=fetch_license)

    about_count = len(abouts)
    error_count = 0

    for e in errors:
        # Only count as warning/error if CRITICAL, ERROR and WARNING
        if e.severity > 20:
            error_count = error_count + 1
    click.echo(
        'Generated %(about_count)d .ABOUT files with %(error_count)d errors or warnings' % locals())
    log_errors(errors, quiet, output)
    # FIXME: return error code?


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
        'subset of .ABOUT files path to consider when generating attribution '
    )

@click.option('--mapping', is_flag=True,
    help='Use the file "mapping.config" with mappings between the CSV '
        'inventory columns names and .ABOUT field names')

@click.option('--template', type=click.Path(exists=True), nargs=1,
    help='Path to an optional custom attribution template used for generation.')

@click.option('-q', '--quiet', is_flag=True,
    help='Do not print error or warning messages.')

@click.help_option('-h', '--help')

def attrib(location, output, template, mapping, inventory, quiet):
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

    inv_errors, abouts = model.collect_inventory(location)
    no_match_errors = attributecode.attrib.generate_and_save(
        abouts=abouts, output_location=output,
        use_mapping=mapping, template_loc=template,
        inventory_location=inventory)

    for no_match_error in no_match_errors:
        inv_errors.append(no_match_error)

    log_errors(inv_errors, quiet, os.path.dirname(output))
    click.echo('Finished.')
    # FIXME: return error code?


######################################################################
# check subcommand
######################################################################

@cli.command(cls=AboutCommand, short_help='Validate that the format of .ABOUT files is correct.')

@click.argument('location', nargs=1, required=True,
    type=click.Path(exists=True, readable=True, resolve_path=True))

@click.option('--show-all', is_flag=True, default=False,
    help='Show all errors and warnings. '
        'By default, running a check only reports these '
        'error levels: CRITICAL, ERROR, and WARNING. '
        'Use this option to report all errors and warning '
        'for any level.'
)

@click.help_option('-h', '--help')

def check(location, show_all):
    """
Check and validate .ABOUT file(s) at LOCATION for errors and
print error messages on the terminal.

LOCATION: Path to a .ABOUT file or a directory containing .ABOUT files.
    """
    click.echo('Running aboutcode-toolkit version ' + __version__)
    click.echo('Checking ABOUT files...')

    errors, abouts = attributecode.model.collect_inventory(location)

    msg_format = '%(sever)s: %(message)s'
    print_errors = []
    for severity, message in errors:
        sever = severities[severity]
        if show_all:
            print_errors.append(msg_format % locals())
        elif sever in problematic_errors:
            print_errors.append(msg_format % locals())

    number_of_errors = len(print_errors)

    for err in print_errors:
        print(err)

    if print_errors:
        click.echo('Found {} errors.'.format(number_of_errors))
        # FIXME: not sure this is the right way to exit with a retrun code
        sys.exit(1)
    else:
        click.echo('No error found.')
    # FIXME: return error code?


def log_errors(errors, quiet, base_dir=False):
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

    # FIXME: do not create log file if there are NO errors
    # Create error.log
    if base_dir:
        bdir = to_posix(base_dir)
        LOG_FILENAME = 'error.log'
        log_path = join(bdir, LOG_FILENAME)
        if exists(log_path):
            os.remove(log_path)

        file_handler = logging.FileHandler(log_path)
        file_logger.addHandler(file_handler)

    for severity, message in errors:
        sever = severities[severity]
        if not quiet:
            print(msg_format % locals())
        if base_dir:
            file_logger.log(severity, msg_format % locals())


if __name__ == '__main__':
    cli()
