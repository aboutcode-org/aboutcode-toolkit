#!/usr/bin/env python
# -*- coding: utf8 -*-

# ============================================================================
#  Copyright (c) nexB Inc. http://www.nexb.com/ - All rights reserved.
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

from collections import defaultdict
from functools import partial
import io
import logging
import os
import sys

import click

# silence unicode literals warnings
click.disable_unicode_literals_warning = True

from attributecode import WARNING
from attributecode.util import unique

from attributecode import __about_spec_version__
from attributecode import __version__
from attributecode import severities
from attributecode.attrib import check_template
from attributecode.attrib import DEFAULT_TEMPLATE_FILE, DEFAULT_LICENSE_SCORE
from attributecode.attrib import generate_and_save as generate_attribution_doc
from attributecode.gen import generate as generate_about_files, load_inventory
from attributecode.model import collect_inventory, collect_abouts_license_expression, collect_inventory_license_expression
from attributecode.model import copy_redist_src
from attributecode.model import get_copy_list
from attributecode.model import pre_process_and_fetch_license_dict
from attributecode.model import write_output
from attributecode.transform import transform_csv_to_csv
from attributecode.transform import transform_json_to_json
from attributecode.transform import transform_excel_to_excel
from attributecode.transform import Transformer
from attributecode.util import extract_zip
from attributecode.util import filter_errors
from attributecode.util import get_temp_dir
from attributecode.util import get_file_text
from attributecode.util import write_licenses

__copyright__ = """
    Copyright (c) nexB Inc and others. All rights reserved.
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
    Return the a dict of {key: value} if valid or raise a UsageError
    otherwise.
    """
    if not value:
        return

    kvals, errors = parse_key_values(value)
    if errors:
        ive = '\n'.join(sorted('  ' + x for x in errors))
        msg = ('Invalid {param} option(s):\n'
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

######################################################################
# inventory subcommand
######################################################################


@about.command(cls=AboutCommand,
    short_help='Collect the inventory of .ABOUT files to a CSV/JSON/XLSX file.')

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
    type=click.Choice(['json', 'csv', 'excel']),
    help='Set OUTPUT inventory file format.')

@click.option('-q', '--quiet',
    is_flag=True,
    help='Do not print error or warning messages.')

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')
def inventory(location, output, format, quiet, verbose):  # NOQA
    """
Collect the inventory of .ABOUT files to a CSV/JSON/XLSX file.

LOCATION: Path to an ABOUT file or a directory with ABOUT files.

OUTPUT: Path to the CSV/JSON/XLSX inventory file to create.
    """
    if not quiet:
        print_version()
        click.echo('Collecting inventory from ABOUT files...')

    if location.lower().endswith('.zip'):
        # accept zipped ABOUT files as input
        location = extract_zip(location)
    errors, abouts = collect_inventory(location)
    write_output(abouts=abouts, location=output, format=format)

    errors_count = report_errors(errors, quiet, verbose, log_file_loc=output + '-error.log')
    if not quiet:
        msg = 'Inventory collected in {output}.'.format(**locals())
        click.echo(msg)
    sys.exit(errors_count)

######################################################################
# gen subcommand
######################################################################


@about.command(cls=AboutCommand,
    short_help='Generate .ABOUT files from an inventory as CSV/JSON/XLSX.')

@click.argument('location',
    required=True,
    metavar='LOCATION',
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True))

@click.argument('output',
    required=True,
    metavar='OUTPUT',
    type=click.Path(exists=True, file_okay=False, writable=True, resolve_path=True))

@click.option('--android',
    is_flag=True,
    help='Generate MODULE_LICENSE_XXX (XXX will be replaced by license key) and NOTICE '
         'as the same design as from Android.')

# FIXME: the CLI UX should be improved with two separate options for API key and URL
@click.option('--fetch-license',
    is_flag=True,
    help='Fetch license data and text files from the ScanCode LicenseDB.')

@click.option('--fetch-license-djc',
    nargs=2,
    type=str,
    metavar='api_url api_key',
    help='Fetch license data and text files from a DejaCode License Library '
         'API URL using the API KEY.')

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
def gen(location, output, android, fetch_license, fetch_license_djc, reference, quiet, verbose):
    """
Given a CSV/JSON/XLSX inventory, generate ABOUT files in the output location.

LOCATION: Path to a JSON/CSV/XLSX inventory file.

OUTPUT: Path to a directory where ABOUT files are generated.
    """
    if not quiet:
        print_version()
        click.echo('Generating .ABOUT files...')

    # FIXME: This should be checked in the `click`
    if not location.endswith(('.csv', '.json', '.xlsx')):
        raise click.UsageError('ERROR: Invalid input file extension: must be one .csv or .json or .xlsx.')

    errors, abouts = generate_about_files(
        location=location,
        base_dir=output,
        android=android,
        reference_dir=reference,
        fetch_license=fetch_license,
        fetch_license_djc=fetch_license_djc,
    )

    errors_count = report_errors(errors, quiet, verbose, log_file_loc=output + '-error.log')
    if not quiet:
        abouts_count = len(abouts)
        msg = '{abouts_count} .ABOUT files generated in {output}.'.format(**locals())
        click.echo(msg)
    sys.exit(errors_count)


######################################################################
# gen_license subcommand
######################################################################

@about.command(cls=AboutCommand,
    short_help='Fetch and save all the licenses in the license_expression field to a directory.')

@click.argument('location',
    required=True,
    metavar='LOCATION',
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True))

@click.argument('output',
    required=True,
    metavar='OUTPUT',
    type=click.Path(exists=True, file_okay=False, writable=True, resolve_path=True))

@click.option('--djc',
    nargs=2,
    type=str,
    metavar='api_url api_key',
    help='Fetch licenses from a DejaCode License Library.')

@click.option('--scancode',
    is_flag=True,
    help='Indicate the input JSON file is from scancode_toolkit.')

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')
def gen_license(location, output, djc, scancode, verbose):
    """
Fetch licenses (Default: ScanCode LicenseDB) in the license_expression field and save to the output location.

LOCATION: Path to a JSON/CSV/XLSX/.ABOUT file(s)

OUTPUT: Path to a directory where license files are saved.
    """
    print_version()
    api_url = ''
    api_key = ''
    errors = []

    log_file_loc = os.path.join(output, 'error.log')

    if location.endswith('.csv') or location.endswith('.json') or location.endswith('.xlsx'):
        errors, abouts = collect_inventory_license_expression(location=location, scancode=scancode)
        if errors:
            severe_errors_count = report_errors(errors, quiet=False, verbose=verbose, log_file_loc=log_file_loc)
            sys.exit(severe_errors_count)
    else:
        #_errors, abouts = collect_inventory(location)
        errors, abouts = collect_abouts_license_expression(location)

    if djc:
        # Strip the ' and " for api_url, and api_key from input
        api_url = djc[0].strip("'").strip('"')
        api_key = djc[1].strip("'").strip('"')

    click.echo('Fetching licenses...')
    license_dict, lic_errors = pre_process_and_fetch_license_dict(abouts, api_url, api_key, scancode)

    if lic_errors:
        errors.extend(lic_errors)

    # A dictionary with license file name as the key and context as the value
    lic_dict_output = {}
    for key in license_dict:
        if not key in lic_dict_output:
            lic_filename = license_dict[key][1]
            lic_context = license_dict[key][2]
            lic_dict_output[lic_filename] = lic_context 

    write_errors = write_licenses(lic_dict_output, output)
    if write_errors:
        errors.extend(write_errors)

    severe_errors_count = report_errors(errors, quiet=False, verbose=verbose, log_file_loc=log_file_loc)
    sys.exit(severe_errors_count)


######################################################################
# attrib subcommand
######################################################################


def validate_template(ctx, param, value):
    if not value:
        return None

    with io.open(value, encoding='utf-8', errors='replace') as templatef:
        template_error = check_template(templatef.read())

    if template_error:
        lineno, message = template_error
        raise click.UsageError(
            'Template syntax error at line: '
            '{lineno}: "{message}"'.format(**locals()))
    return value


@about.command(cls=AboutCommand,
    short_help='Generate an attribution document from JSON/CSV/XLSX/.ABOUT files.')

@click.argument('input',
    required=True,
    metavar='INPUT',
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True))

@click.argument('output',
    required=True,
    metavar='OUTPUT',
    type=click.Path(exists=False, dir_okay=False, writable=True, resolve_path=True))

@click.option('--api_url',
    nargs=1,
    type=click.STRING,
    metavar='URL',
    help='URL to DejaCode License Library.')

@click.option('--api_key',
    nargs=1,
    type=click.STRING,
    metavar='KEY',
    help='API Key for the  DejaCode License Library')

@click.option('--min-license-score',
    type=int,
    help='Attribute components that have license score higher than or equal to the defined '
        '--min-license-score.')

@click.option('--scancode',
    is_flag=True,
    help='Indicate the input JSON file is from scancode_toolkit.')

@click.option('--reference',
    metavar='DIR',
    type=click.Path(exists=True, file_okay=False, readable=True, resolve_path=True),
    help='Path to a directory with reference files where "license_file" and/or "notice_file"' 
        ' located.')

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
def attrib(input, output, api_url, api_key, scancode, min_license_score, reference, template, vartext, quiet, verbose):
    """
Generate an attribution document at OUTPUT using JSON, CSV or XLSX or .ABOUT files at INPUT.

INPUT: Path to a file (.ABOUT/.csv/.json/.xlsx), directory or .zip archive containing .ABOUT files.

OUTPUT: Path where to write the attribution document.
    """
    # A variable to define if the input ABOUT file(s)
    is_about_input = False

    rendered = ''
    license_dict = {}
    errors = []

    if not quiet:
        print_version()
        click.echo('Generating attribution...')

    # accept zipped ABOUT files as input
    if input.lower().endswith('.zip'):
        input = extract_zip(input)

    if scancode:
        if not input.endswith('.json'):
            msg = 'The input file from scancode toolkit needs to be in JSON format.'
            click.echo(msg)
            sys.exit(1)
        if not min_license_score and not min_license_score == 0:
            min_license_score=DEFAULT_LICENSE_SCORE

    if min_license_score:
        if not scancode:
            msg = ('This option requires a JSON file generated by scancode toolkit as the input. ' +
                    'The "--scancode" option is required.')
            click.echo(msg)
            sys.exit(1)

    if input.endswith('.json') or input.endswith('.csv') or input.endswith('.xlsx'):
        is_about_input = False
        from_attrib = True
        if not reference:
            # Set current directory as the reference dir
            reference = os.path.dirname(input)
        errors, abouts = load_inventory(
            location=input,
            from_attrib=from_attrib,
            scancode=scancode,
            reference_dir=reference
        )
    else:
        is_about_input = True
        errors, abouts = collect_inventory(input)

    if not abouts:
        if errors:
            errors_count = report_errors(errors, quiet, verbose, log_file_loc=output + '-error.log')
        else:
            msg = 'No ABOUT file or reference is found from the input. Attribution generation halted.'
            click.echo(msg)
            errors_count = 1
        sys.exit(errors_count)

    if not is_about_input:
        # Check if both api_url and api_key present
        if api_url or api_key:
            if not api_url:
                msg = '"--api_url" is required.'
                click.echo(msg)
                sys.exit(1)
            if not api_key:
                msg = '"--api_key" is required.'
                click.echo(msg)
                sys.exit(1)
        else:
            api_url = ''
            api_key = ''
        api_url = api_url.strip("'").strip('"')
        api_key = api_key.strip("'").strip('"')
        license_dict, lic_errors = pre_process_and_fetch_license_dict(abouts, api_url, api_key, scancode, reference)
        errors.extend(lic_errors)
        sorted_license_dict = sorted(license_dict)

        # Read the license_file and store in a dictionary
        for about in abouts:
            if about.license_file.value or about.notice_file.value:
                if not reference:
                    msg = ('"license_file" / "notice_file" field contains value. Use `--reference` to indicate its parent directory.')
                    click.echo(msg)
                    #sys.exit(1)

    if abouts:
        attrib_errors, rendered = generate_attribution_doc(
            abouts=abouts,
            is_about_input=is_about_input,
            license_dict=dict(sorted(license_dict.items())),
            output_location=output,
            scancode=scancode,
            min_license_score=min_license_score,
            template_loc=template,
            vartext=vartext,
        )
        errors.extend(attrib_errors)

    errors_count = report_errors(errors, quiet, verbose, log_file_loc=output + '-error.log')

    if not quiet:
        if rendered:
            msg = 'Attribution generated in: {output}'.format(**locals())
            click.echo(msg)
        else:
            msg = 'Attribution generation failed.'
            click.echo(msg)
    sys.exit(errors_count)

######################################################################
# collect_redist_src subcommand
######################################################################


@about.command(cls=AboutCommand,
    short_help='Collect redistributable sources.')

@click.argument('location',
    required=True,
    metavar='LOCATION',
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True))

@click.argument('output',
    required=True,
    metavar='OUTPUT')

@click.option('--from-inventory',
    metavar='FILE',
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
    help='Path to an inventory CSV/JSON file as the base list for files/directories '
         'that need to be copied which have the \'redistribute\' flagged.')

@click.option('--with-structures',
    is_flag=True,
    help='Copy sources with directory structure.')

@click.option('--zip',
    is_flag=True,
    help='Zip the copied sources to the output location.')

@click.option('-q', '--quiet',
    is_flag=True,
    help='Do not print error or warning messages.')

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')
def collect_redist_src(location, output, from_inventory, with_structures, zip, quiet, verbose):
    """
Collect sources that have 'redistribute' flagged as 'True' in .ABOUT files or inventory
to the output location.

LOCATION: Path to a directory containing sources that need to be copied
(and containing ABOUT files if `inventory` is not provided)

OUTPUT: Path to a directory or a zip file where sources will be copied to.
    """
    if zip:
        if not output.endswith('.zip'):
            click.echo('The output needs to be a zip file.')
            sys.exit()

    if not quiet:
        print_version()
        click.echo('Collecting inventory from ABOUT files...')

    if location.lower().endswith('.zip'):
        # accept zipped ABOUT files as input
        location = extract_zip(location)

    if from_inventory:
        errors, abouts = load_inventory(from_inventory, location)
    else:
        errors, abouts = collect_inventory(location)

    if zip:
        # Copy to a temp location and the zip to the output location
        output_location = get_temp_dir()
    else:
        output_location = output

    copy_list, copy_list_errors = get_copy_list(abouts, location)
    copy_errors = copy_redist_src(copy_list, location, output_location, with_structures)

    if zip:
        import shutil
        # Stripped the .zip extension as the `shutil.make_archive` will
        # append the .zip extension
        output_no_extension = output.rsplit('.', 1)[0]
        shutil.make_archive(output_no_extension, 'zip', output_location)

    errors.extend(copy_list_errors)
    errors.extend(copy_errors)
    errors_count = report_errors(errors, quiet, verbose, log_file_loc=output + '-error.log')
    if not quiet:
        msg = 'Redistributed sources are copied to {output}.'.format(**locals())
        click.echo(msg)
    sys.exit(errors_count)

######################################################################
# check subcommand
######################################################################

# FIXME: This is really only a dupe of the Inventory command


@about.command(cls=AboutCommand,
    short_help='Validate that the format of .ABOUT files is correct and report '
               'errors and warnings.')

@click.argument('location',
    required=True,
    metavar='LOCATION',
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True))

@click.option('--djc',
    nargs=2,
    type=str,
    metavar='api_url api_key',
    help='Validate license_expression from a DejaCode License Library '
         'API URL using the API KEY.')

@click.option('--log',
    nargs=1,
    metavar='FILE',
    help='Path to a file to save the error messages if any.')

@click.option('--verbose',
    is_flag=True,
    help='Show all error and warning messages.')

@click.help_option('-h', '--help')
def check(location, djc, log, verbose):
    """
Check .ABOUT file(s) at LOCATION for validity and print error messages.

LOCATION: Path to an ABOUT file or a directory with ABOUT files.
    """
    print_version()

    if log:
        # Check if the error log location exist and create the parent directory if not
        parent = os.path.dirname(log)
        if not parent:
            os.makedirs(parent)

    api_url = ''
    api_key = ''
    if djc:
        # Strip the ' and " for api_url, and api_key from input
        api_url = djc[0].strip("'").strip('"')
        api_key = djc[1].strip("'").strip('"')
    click.echo('Checking ABOUT files...')
    errors, abouts = collect_inventory(location)

    # Validate license_expression
    _key_text_dict, errs = pre_process_and_fetch_license_dict(abouts, api_url, api_key)
    for e in errs:
        errors.append(e)

    severe_errors_count = report_errors(errors, quiet=False, verbose=verbose, log_file_loc=log)
    sys.exit(severe_errors_count)

######################################################################
# transform subcommand
######################################################################


def print_config_help(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    from attributecode.transform import tranformer_config_help
    click.echo(tranformer_config_help)
    ctx.exit()


@about.command(cls=AboutCommand,
    short_help='Transform a CSV/JSON/XLSX by applying renamings, filters and checks.')

@click.argument('location',
    required=True,
    callback=partial(validate_extensions, extensions=('.csv', '.json', '.xlsx',)),
    metavar='LOCATION',
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True))

@click.argument('output',
    required=True,
    callback=partial(validate_extensions, extensions=('.csv', '.json', '.xlsx',)),
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
Transform the CSV/JSON/XLSX file at LOCATION by applying renamings, filters and checks
and then write a new CSV/JSON/XLSX to OUTPUT (Format for input and output need to be
the same).

LOCATION: Path to a CSV/JSON/XLSX file.

OUTPUT: Path to CSV/JSON/XLSX inventory file to create.
    """
    if not configuration:
        transformer = Transformer.default()
    else:
        transformer = Transformer.from_file(configuration)

    if location.endswith('.csv') and output.endswith('.csv'):
        errors = transform_csv_to_csv(location, output, transformer)
    elif location.endswith('.json') and output.endswith('.json'):
        errors = transform_json_to_json(location, output, transformer)
    elif location.endswith('.xlsx') and output.endswith('.xlsx'):
        errors = transform_excel_to_excel(location, output, transformer)
    else:
        msg = 'Extension for the input and output need to be the same.'
        click.echo(msg)
        sys.exit()

    if not quiet:
        print_version()
        click.echo('Transforming...')

    errors_count = report_errors(errors, quiet, verbose, log_file_loc=output + '-error.log')
    if not quiet and not errors:
        msg = 'Transformed file is written to {output}.'.format(**locals())
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
    severe_errors_count = 0
    if errors:
        log_msgs, severe_errors_count = get_error_messages(errors, verbose)
        if not quiet:
            for msg in log_msgs:
                click.echo(msg)
        if log_msgs and log_file_loc:
            with io.open(log_file_loc, 'w', encoding='utf-8', errors='replace') as lf:
                lf.write('\n'.join(log_msgs))
            click.echo("Error log: " + log_file_loc)
    return severe_errors_count


def get_error_messages(errors, verbose=False):
    """
    Return a tuple of (list of error message strings to report,
    severe_errors_count) given an `errors` list of Error objects and using the
    `verbose` flags.
    """
    if verbose:
        severe_errors = errors
    else:
        severe_errors = filter_errors(errors, WARNING)

    severe_errors = unique(severe_errors)
    severe_errors_count = len(severe_errors)

    messages = []

    if severe_errors:
        error_msg = 'Command completed with {} errors or warnings.'.format(severe_errors_count)
        messages.append(error_msg)

    for severity, message in severe_errors:
        sevcode = severities.get(severity) or 'UNKNOWN'
        msg = '{sevcode}: {message}'.format(**locals())
        messages.append(msg)

    return messages, severe_errors_count

######################################################################
# Misc
######################################################################


def parse_key_values(key_values):
    """
    Given a list of "key=value" strings, return:
    - a dict {key: value}
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

        parsed_key_values[key] = value

    return dict(parsed_key_values), sorted(errors)


if __name__ == '__main__':
    about()
