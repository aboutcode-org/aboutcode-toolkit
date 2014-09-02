#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) 2014 nexB Inc. http://www.nexb.com/ - All rights reserved.
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

import aboutcode
from aboutcode import model

logger = logging.getLogger(__name__)


__version__ = '0.11.0'


__about_spec_version__ = '0.9.0'


__copyright__ = """
    Copyright (c) 2013-2014 nexB Inc. All rights reserved.
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
    errors, abouts = model.collect_inventory(location)
    aboutcode.log_errors(errors, logger)
    to_csv(abouts, output)


@cli.command()
def export():
    click.echo('Export a zip archive ABOUT files and related files in a directory tree')


@cli.command()
def gen():
    click.echo('Generate ABOUT files from an inventory')


@cli.command()
def attrib():
    click.echo('Generate attribution documentation')


@cli.command()
def redist():
    click.echo('Collect redistributable files')


def to_csv(abouts, location):
    """
    Given a list of About objects, write a CSV file at location.
    """
    fieldnames = model.field_names(abouts)
    with codecs.open(location, mode='wb', encoding='utf-8') as csvfile:
        writer = unicodecsv.DictWriter(csvfile, fieldnames)
        writer.writeheader()
        for a in abouts:
            writer.writerow(a.as_dict())


if __name__ == '__main__':
    cli()

