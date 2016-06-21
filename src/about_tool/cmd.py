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

import logging
import codecs
import os
from os.path import exists, join

import click
import unicodecsv

from about_tool import __version__
from about_tool import __about_spec_version__

import about_tool.gen
import about_tool.model
import about_tool.attrib
from about_tool import NOTSET
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
no_stdout = 0

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
@click.option('-v', '--verbose', count=True,
              help='Increase verbosity. Repeat to print more output.')
@click.option('-q', '--quiet', count=True, help='Do not print any output.')
def cli(verbose, quiet):
    # Update the no_stdout value globally
    global no_stdout
    no_stdout = quiet

    pass
    # click.echo('Verbosity: %s' % verbose)


inventory_help = '''
LOCATION: Path to an ABOUT file or a directory containing ABOUT files
OUTPUT: Path to CSV file to write the inventory to
'''
@cli.command(help=inventory_help,
             short_help='LOCATION: directory, OUTPUT: csv file',
             cls=AboutCommand)
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
    click.echo('Running about-code-tool version ' + __version__)
    click.echo('Collecting the inventory from location: ''%(location)s '
               'and writing CSV output to: %(output)s' % locals())

    errors, abouts = about_tool.model.collect_inventory(location)
    log_errors(errors)
    about_tool.model.to_csv(abouts, output)


gen_help = '''
LOCATION: Path to a CSV inventory file
OUTPUT: Path to the directory to write ABOUT files to
'''
@cli.command(help=gen_help,
             short_help='LOCATION: csv file, OUTPUT: directory',
             cls=AboutCommand)
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
    click.echo('Running about-code-tool version ' + __version__)
    click.echo('Generating ABOUT files...')
    errors, abouts = about_tool.gen.generate(location, output)

    lea = len(abouts)
    lee = len(errors)
    click.echo('Generated %(lea)d ABOUT files with %(lee)d errors or warning' % locals())
    log_errors(errors, output)


@cli.command(cls=AboutCommand)
def export():
    click.echo('Running about-code-tool version ' + __version__)
    click.echo('Exporting zip archive...')



@cli.command(cls=AboutCommand)
def fetch(location):
    """
    Given a directory of ABOUT files at location, calls the DejaCode API and
    update or create license data fields and license texts.
    """
    click.echo('Running about-code-tool version ' + __version__)
    click.echo('Updating ABOUT files...')


@cli.command(cls=AboutCommand)
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
    click.echo('Running about-code-tool version ' + __version__)
    click.echo('Generating attribution...')
    errors, abouts = about_tool.model.collect_inventory(location)
    about_tool.attrib.generate_and_save(abouts, output, 
                                             template_loc=template, 
                                             inventory_location=inventory_location)
    log_errors(errors)


@cli.command(cls=AboutCommand)
def redist(input_dir, output, inventory_location=None,):
    """
    Collect redistributable code at output location using:
     - the input_dir of code and ABOUT files,
     - an inventory_location CSV file containing a list of ABOUT files to
     generate redistribution for.
     Only collect code when redistribute=yes
     Return a list of errors.
    """
    click.echo('Running about-code-tool version ' + __version__)
    click.echo('Collecting redistributable files...')


def log_errors(errors, base_dir=False, level=NOTSET):
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
        sever = about_tool.severities[severity]
        if no_stdout == 0:
            print(msg_format % locals())
        if base_dir:
            file_logger.log(30, msg_format % locals())


if __name__ == '__main__':
    cli()
