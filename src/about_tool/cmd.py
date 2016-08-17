#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2013-2016 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

import codecs
import logging
import os
from os.path import exists, join

import click
import unicodecsv

import about_tool
from about_tool import CRITICAL
from about_tool import ERROR
from about_tool import INFO
from about_tool import NOTSET
from about_tool import WARNING
from about_tool import Error
from about_tool import __about_spec_version__
from about_tool import __version__
from about_tool import attrib
from about_tool import gen
from about_tool import model
from about_tool import severities
from about_tool.model import About
from about_tool.util import copy_files
from about_tool.util import extract_zip
from about_tool.util import to_posix


__copyright__ = """
    Copyright (c) 2013-2016 nexB Inc. All rights reserved.
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at
        http://www.apache.org/licenses/LICENSE-2.0
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License."""


prog_name = 'AboutCode'

intro = '''%(prog_name)s, version %(__version__)s
ABOUT spec version: %(__about_spec_version__)s http://dejacode.org
%(__copyright__)s
''' % locals()


class AboutCommand(click.Command):
    def main(self, args=None, prog_name=None, complete_var=None,
             standalone_mode=True, **extra):
        """
        Workaround click 4.0 bug https://github.com/mitsuhiko/click/issues/365
        """
        return click.Command.main(self, args=args, prog_name=self.name,
                                  complete_var=complete_var,
                                  standalone_mode=standalone_mode, **extra)

@click.group(name='about')
@click.version_option(version=__version__, prog_name=prog_name, message=intro)
def cli():
    pass
    # click.echo('Verbosity: %s' % verbose)


# inventory_help = '''
# '''
formats = ['csv', 'json']
@cli.command(cls=AboutCommand, short_help='LOCATION: directory, OUTPUT: csv file')
@click.argument('location', nargs=1, required=True, 
                type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True))
@click.argument('output', nargs=1, required=True, 
                type=click.Path(exists=False, resolve_path=True))
@click.option('-q', '--quiet', is_flag=True, help='Do not print any error/warning.')
@click.option('-f', '--format', is_flag=False, default='csv', show_default=True, type=click.Choice(['json', 'csv']), 
              help='Set OUTPUT file format.')
def inventory(location, output, quiet, format):
    """
Collect a JSON or CSV inventory of components from ABOUT files.

LOCATION: Path to an ABOUT file or a directory with ABOUT files.

OUTPUT: Path to the JSON or CSV inventory file to create.
    """
    click.echo('Running about-code-tool version ' + __version__)
    # Check that the <OUTPUT> parent directory exists
    if not exists(os.path.dirname(output)):
        # FIXME: there is likely a better way to return an error
        click.echo('ERROR: Path to the OUTPUT does not exists. Please check and correct the <output>.')
        return

    click.echo('Collecting inventory from: ''%(location)s and writing output to: %(output)s' % locals())

    # FIXME: do we really want to continue support zip as an input?
    if location.lower().endswith('.zip'):
        # accept zipped ABOUT files as input
        location = extract_zip(location)

    errors, abouts = about_tool.model.collect_inventory(location)

    write_errors = model.write_output(abouts, output, format)
    for err in write_errors:
        errors.append(err)
    log_errors(quiet, errors, os.path.dirname(output))


@cli.command(cls=AboutCommand, short_help='LOCATION: input file, OUTPUT: directory',)
@click.argument('location', nargs=1, required=True, 
                type=click.Path(exists=True, file_okay=True, readable=True, resolve_path=True))
@click.argument('output', nargs=1, required=True,
                type=click.Path(exists=True, writable=True, dir_okay=True, resolve_path=True))
@click.option('--mapping', is_flag=True,  help='Use for mapping between the input keys and the ABOUT field names - MAPPING.CONFIG')
@click.option('--license-text-location', nargs=1,
              type=click.Path(exists=True, dir_okay=True, readable=True, resolve_path=True),
              help="Copy the 'license_file' from the directory to the generated location")
@click.option('--fetch-license', type=str, nargs=2,
              help=('Fetch licenses text from a DejaCode API. and create <dje_license_key>.LICENSE side-by-side '
                'with the generated .ABOUT file using data fetched from a DejaCode License Library. '
                'The following additional options are required:\n\n'
                'api_url - URL to the DejaCode License Library API endpoint\n\n'
                'api_key - DejaCode API key'

                '\nExample syntax:\n\n'
                "about gen --extract_license 'api_url' 'api_key'")
              )
@click.option('-q', '--quiet', is_flag=True, help='Do not print any error/warning.')
def gen(location, output, mapping, license_text_location, fetch_license, quiet):
    """
Given an inventory of ABOUT files at location, generate ABOUT files in base
directory.

LOCATION: Path to a JSON or CSV inventory file.

OUTPUT: Path to a directory where ABOUT files are generated.
    """
    click.echo('Running about-code-tool version ' + __version__)
    if not location.endswith('.csv') and not location.endswith('.json'):
        click.echo('ERROR: Input file. Only .csv and .json files are supported.')
        return
    click.echo('Generating ABOUT files...')

    errors, abouts = about_tool.gen.generate(mapping, license_text_location, fetch_license, location, output)

    lea = len(abouts)
    lee = 0

    for e in errors:
        # Only count as warning/error if CRITICAL, ERROR and WARNING
        if e.severity > 20:
            lee = lee + 1
    click.echo('Generated %(lea)d ABOUT files with %(lee)d errors and/or warning' % locals())
    log_errors(quiet, errors, output)


@cli.command(cls=AboutCommand, short_help='LOCATION: directory, OUTPUT: output file')
@click.argument('location', nargs=1, required=True, type=click.Path(exists=True, readable=True, resolve_path=True))
@click.argument('output', nargs=1, required=True, type=click.Path(exists=False, writable=True, resolve_path=True))
@click.option('--template', type=click.Path(exists=True), nargs=1, 
              help='Path to a custom attribution template')
@click.option('--inventory', required=False, type=click.Path(exists=True, file_okay=True, resolve_path=True),
              help='Path to an inventory file')
@click.option('--mapping', is_flag=True, help='Use for mapping between the input keys and the ABOUT field names - MAPPING.CONFIG')
@click.option('-q', '--quiet', is_flag=True, help='Do not print any error/warning.')
def attrib(quiet, location, output, template, mapping, inventory):
    """
Generate an attribution OUTPUT document using the directory of ABOUT files at
LOCATION. You can provide a custom template file. You can also provide an inventory
file listing the subset of ABOUT files path to consider when generating
attribution and its column mapping file.

LOCATION: Path to an ABOUT file or a directory containing ABOUT files.

OUTPUT: Path to output file to write the attribution to.

INVENTORY_LOCATION: Optional path to a CSV inventory file with an 'about_file_path' column.
    """
    click.echo('Running about-code-tool version ' + __version__)
    click.echo('Generating attribution...')

    if location.lower().endswith('.zip'):
        # accept zipped ABOUT files as input
        location = extract_zip(location)

    if mapping:
        about_tool.util.have_mapping = True

    err, abouts = model.collect_inventory(location)
    no_match_errors = about_tool.attrib.generate_and_save(abouts, output, mapping,
                                                          template_loc=template,
                                                          inventory_location=inventory)
    errors = []
    for e in err:
        errors.append(e)
    for no_match_error in no_match_errors:
        errors.append(no_match_error)
    log_errors(quiet, errors, os.path.dirname(output))
    click.echo('Finished.')


# @cli.command(cls=AboutCommand)
# def export():
#    click.echo('Running about-code-tool version ' + __version__)
#    click.echo('Exporting zip archive...')


# @cli.command(cls=AboutCommand)
# def fetch(location):
    """
    Given a directory of ABOUT files at location, calls the DejaCode API and
    update or create license data fields and license texts.
    """
#    click.echo('Running about-code-tool version ' + __version__)
#    click.echo('Updating ABOUT files...')


# @cli.command(cls=AboutCommand)
# def redist(input_dir, output, inventory_location=None,):
    """
    Collect redistributable code at output location using:
     - the input_dir of code and ABOUT files,
     - an inventory_location CSV file containing a list of ABOUT files to
     generate redistribution for.
     Only collect code when redistribute=yes
     Return a list of errors.
    """
#    click.echo('Running about-code-tool version ' + __version__)
#    click.echo('Collecting redistributable files...')


def log_errors(quiet, errors, base_dir=False):
    """
    Iterate of sequence of Error objects and print and log errors with a severity
    superior or equal to level.
    """
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    handler.setLevel(logging.CRITICAL)
    handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(handler)
    file_logger = logging.getLogger(__name__ + '_file')

    msg_format = '%(sever)s: %(message)s'
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
