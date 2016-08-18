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
    gen        LOCATION: input file, OUTPUT: directory
    inventory  LOCATION: directory, OUTPUT: csv file


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


gen
===

**Syntax**

::

    about gen [OPTIONS] LOCATION OUTPUT

    LOCATION: Path to a JSON or CSV inventory file.
    OUTPUT: Path to a directory where ABOUT files are generated.

**Options:**

::

    --fetch-license TEXT...         Fetch licenses text from a DejaCode API. and
                                    create <license>.LICENSE side-by-side
                                    with the generated .ABOUT file using data
                                    fetched from a DejaCode License Library. The
                                    following additional options are required:

                                    api_url - URL to the DejaCode License Library
                                    API endpoint
    
                                    api_key - DejaCode API key
                                    Example syntax:
    
                                    about gen --fetch-license 'api_url' 'api_key'
    --license-text-location PATH    Copy the 'license_file' from the directory to
                                    the generated location
    --mapping                       Use for mapping between the input keys and
                                    the ABOUT field names - mapping.config
    -q, --quiet                     Do not print any error/warning.
    --help                          Show this message and exit.

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

    --license_text_location

        Copy the license files to the generated location based on the 
        'license_file' value in the input from the directory

        For instance,
        the directory, /home/licenses/, contains all the licenses that users want:
        /home/license/apache2.LICENSE
        /home/license/jquery.js.LICENSE

    $ about gen --license_text_location /home/licenses/ LOCATION OUTPUT

    --mapping

        See mapping.config for details

    $ about gen --extract_license 'api_url' 'api_key' LOCATION OUTPUT


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

    '/home/about_files/'** contains all the ABOUT files
    '/home/attribution/attribution.html' is the user's output path
    '/home/project/component_list.csv' is the inventory that user want to be generated

::

    $ about attrib /home/about_files/ /home/attribution/attribution.html /home/project/component_list.csv

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
