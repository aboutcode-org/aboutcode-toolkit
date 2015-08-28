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

import logging
import codecs

import click
import unicodecsv

import about_code_tool.gen
import about_code_tool.model
import about_code_tool.attrib

from about_code_tool import NOTSET


__version__ = '3.0.0dev'


__about_spec_version__ = '2.0.0dev'


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
    limitations under the License."""


prog_name = 'AboutCode'


intro = '''%(prog_name)s, version %(__version__)s
ABOUT spec version: %(__about_spec_version__)s http://dejacode.org
%(__copyright__)s
''' % locals()


@click.group()
@click.version_option(version=__version__, prog_name=prog_name, message=intro)
@click.option('-v', '--verbose', count=True,
              help='Increase verbosity. Repeat to print more output.')
@click.option('-q', '--quiet', count=True, help='Do not print any output.')
def cli(verbose, quiet):
    pass
    # click.echo('Verbosity: %s' % verbose)


inventory_help = '''
LOCATION: Path to an ABOUT file or a directory containing ABOUT files
OUTPUT: Path to CSV file to write the inventory to
'''

@cli.command(help=inventory_help,
             short_help='LOCATION: directory, OUTPUT: csv file')
@click.argument('location', nargs=1, required=True,
                type=click.Path(exists=True, file_okay=True,
                                dir_okay=True, writable=False,
                                readable=True, resolve_path=True))
@click.argument('output', nargs=1, required=True,
                type=click.Path(exists=False, file_okay=True, writable=True,
                                dir_okay=False, resolve_path=True))
def inventory(location, output):
    """
    Inventory components from an ABOUT file or a directory tree of ABOUT
    files.
    """
    click.echo('Collecting the inventory from location: ''%(location)s '
               'and writing CSV output to: %(output)s' % locals())

    errors, abouts = about_code_tool.model.collect_inventory(location)
    log_errors(errors)
    about_code_tool.model.to_csv(abouts, output)


gen_help = '''
LOCATION: Path to a CSV inventory file
OUTPUT: Path to the directory to write ABOUT files to
'''
@cli.command(help=gen_help,
             short_help='LOCATION: csv file, OUTPUT: directory')
@click.argument('location', nargs=1, required=True,
                type=click.Path(exists=True, file_okay=True,
                                dir_okay=False, writable=False,
                                readable=True, resolve_path=True))
@click.argument('output', nargs=1, required=True,
                type=click.Path(exists=True, file_okay=False, writable=True,
                                dir_okay=True, resolve_path=True))
def gen(location, output):
    """
    Given a CVS inventory of ABOUT files at location, generate ABOUT files in
    base directory.
    """
    click.echo('Generating ABOUT files...')
    errors, abouts = about_code_tool.gen.generate(location, output)
    lea = len(abouts)
    lee = len(errors)
    click.echo('Generated %(lea)d ABOUT files with %(lee)d errors or warning' % locals())
    log_errors(errors)


@cli.command()
def export():
    click.echo('Exporting zip archive...')



@cli.command()
def fetch(location):
    """
    Given a directory of ABOUT files at location, calls the DejaCode API and
    update or create license data fields and license texts.
    """
    click.echo('Updating ABOUT files...')


@cli.command()
@click.argument('location', nargs=1, required=True,
                type=click.Path(exists=True, file_okay=True,
                                dir_okay=True, writable=False,
                                readable=True, resolve_path=True))
@click.argument('output', nargs=1, required=True,
                type=click.Path(exists=False, file_okay=True, writable=True,
                                dir_okay=False, resolve_path=True))
@click.argument('template', nargs=1, required=False,
                type=click.Path(exists=False, file_okay=True, writable=True,
                                dir_okay=False, resolve_path=True))
@click.argument('inventory_location', nargs=1, required=False,
                type=click.Path(exists=False, file_okay=True, writable=True,
                                dir_okay=False, resolve_path=True))
def attrib(location, output, template=None, inventory_location=None,):
    """
    Generate attribution document at output using the directory of
    ABOUT files at location, the template file (or a default) and an
    inventory_location CSV file containing a list of ABOUT files path to
    generate attribution for.
    """
    click.echo('Generating attribution...')
    errors, abouts = about_code_tool.model.collect_inventory(location)
    about_code_tool.attrib.generate_and_save(abouts, output, 
                                             template_loc=template, 
                                             inventory_location=inventory_location)
    log_errors(errors)


@cli.command()
def redist(input_dir, output, inventory_location=None,):
    """
    Collect redistributable code at output location using:
     - the input_dir of code and ABOUT files,
     - an inventory_location CSV file containing a list of ABOUT files to
     generate redistribution for.
     Only collect code when redistribute=yes
     Return a list of errors.
    """
    click.echo('Collecting redistributable files...')


def log_errors(errors, level=NOTSET):
    """
    Iterate of sequence of Error objects and print errors with a severity
    superior or equal to level.
    """
    msg_format = '%(sever)s: %(message)s'

    for severity, message in errors:
        sever = about_code_tool.severities[severity]
        print(msg_format % locals())


if __name__ == '__main__':
    cli()
