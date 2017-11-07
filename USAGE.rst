about
=====

**Syntax**

::

    about [OPTIONS] [COMMANDS]

**Options:**

::

    --version    Show the version and exit.
    --help       Show this message and exit.

**Commands:**

::

  attrib     LOCATION: directory, OUTPUT: output file
  check      LOCATION: directory
  gen        LOCATION: input file, OUTPUT: directory
  inventory  LOCATION: directory, OUTPUT: csv file


attrib
======

**Syntax**

::

    about attrib [OPTIONS] LOCATION OUTPUT

    LOCATION: Path to an ABOUT file or a directory containing ABOUT files.
    OUTPUT: Path to output file to write the attribution to.

**Options:**

::

    --inventory PATH  Path to an inventory file
    --mapping         Use for mapping between the input keys and the ABOUT field
                      names - mapping.config
    --template PATH   Path to a custom attribution template
    -q, --quiet       Do not print any error/warning.
    --help            Show this message and exit.

Purpose
-------
Generate an attribution file which contains the all license information
from the LOCATION along with the license text.

Assuming the follow:

::

    '/home/about_files/'** contains all the ABOUT files [LOCATION]
    '/home/attribution/attribution.html' is the user's output path [OUTPUT]
    '/home/project/component_list.csv' is the inventory that user want to be generated

::

    $ about attrib /home/about_files/ /home/attribution/attribution.html

Options
-------

::

    --inventory

        This option allows user to define which ABOUT files should be used for attribution generation.
        For instance,
        '/home/project/component_list.csv' is the inventory that user want to be generated

    $ about attrib --inventory /home/project/component_list.csv LOCATION OUTPUT

    --mapping

        See mapping.config for details

    --template

        This option allows users to use their own template for attribution generation.
        For instance, if user has a custom template located at:
        /home/custom_template/template.html

    $ about attrib --template /home/custom_template/template.html LOCATION OUTPUT


The following information are passed to the jinja2 and, therefore, can be used for your custom template:
 * about object: the about objects
 * common_licenses: a common license keys list in licenses.py
 * license_key_and_context: a dictionary list with license_key as a key and license text as the value
 * license_file_name_and_key: a dictionary list with license file name as a key and license key as the value
 * license_key_to_license_name: a dictionary list with license key as a key and license file name as the value


check
=====

**Syntax**

::

    about check [OPTIONS] LOCATION

    LOCATION: Path to an ABOUT file or a directory with ABOUT files.

**Options:**

::

    --show-all               Show all the errors and warning
    --help                   Show this message and exit.

Purpose
-------
Validating ABOUT files at LOCATION.

Options
-------

::

    --show-all

        This option ask the tool to show all kind of errors found.
        The default behavior will only show 'CRITICAL', 'ERROR', and 'WARNING'

    $ about check --show-all /home/project/about_files/


gen
===

**Syntax**

::

    about gen [OPTIONS] LOCATION OUTPUT

    LOCATION: Path to a JSON or CSV inventory file.
    OUTPUT: Path to a directory where ABOUT files are generated.

**Options:**

::

    --fetch-license TEXT...             Fetch licenses text from a DejaCode API. and
                                        create <license>.LICENSE side-by-side
                                        with the generated .ABOUT file using data
                                        fetched from a DejaCode License Library. The
                                        following additional options are required:

                                        api_url - URL to the DejaCode License Library
                                        API endpoint

                                        api_key - DejaCode API key
                                        Example syntax:

                                        about gen --fetch-license 'api_url' 'api_key'
    --license-notice-text-location PATH Copy the 'license_file' from the directory to
                                        the generated location
    --mapping                           Use for mapping between the input keys and
                                        the ABOUT field names - mapping.config
    -q, --quiet                         Do not print any error/warning.
    --help                              Show this message and exit.

Purpose
-------
Given an inventory of ABOUT files at location, generate ABOUT files in base directory.

Options
-------

::

    --fetch-license

        Fetch licenses text from a DejaCode API. and create <license>.LICENSE side-by-side
        with the generated .ABOUT file using data fetched from a DejaCode License Library.

        This option requires 2 parameters:
            api_url - URL to the DJE License Library
            api_key - Hash key to authenticate yourself in the API.
        (Please contact us to get the api_* value to use this feature)

    $ about gen --fetch-license 'api_url' 'api_key' LOCATION OUTPUT

    --license-notice-text-location

        Copy the license files and notice files to the generated location based on the 
        'license_file' and 'notice_file' value in the input from the directory

        For instance,
        the directory, /home/licenses_notices/, contains all the licenses and notices that users want:
        /home/license/apache2.LICENSE
        /home/license/jquery.js.NOTICE

    $ about gen --license-notice-text-location /home/licenses_notices/ LOCATION OUTPUT

    --mapping

        See mapping.config for details


inventory
=========

**Syntax**

::

    about inventory [OPTIONS] LOCATION OUTPUT

    LOCATION: Path to an ABOUT file or a directory with ABOUT files.
    OUTPUT: Path to the JSON or CSV inventory file to create.

**Options:**

::

    -f, --format [json|csv]  Set OUTPUT file format.  [default: csv]
    -q, --quiet              Do not print any error/warning.
    --help                   Show this message and exit.

Purpose
-------
Collect a JSON or CSV inventory of components from ABOUT files.

Options
-------

::

    -f, --format [json|csv]
 
        Set OUTPUT file format.  [default: csv]

    $ about inventory -f json [OPTIONS] LOCATION OUTPUT
