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

    LOCATION: Path to an ABOUT file or a directory containing ABOUT files
    OUTPUT: Path to CSV file to write the inventory to

**Options:**

::

    -q, --quiet           Do not print any error/warning.
    -f, --format <style>  Set <output_file> format <style> to one of the
                          supported formats: csv or json  [default: csv]
    --mapping             Use for mapping between the input keys and the ABOUT
                          field names - MAPPING.CONFIG
    --help                Show this message and exit.

Purpose
-------
Extract information from the .ABOUT files and save it to a CSV or JSON file.

Options
-------

::

    -f, --format
 
        Set the output format [default: csv]

    $ about inventory -f json [OPTIONS] LOCATION OUTPUT

    --mapping

        See MAPPING.CONFIG for details


gen
===

**Syntax**

::

    about gen [OPTIONS] LOCATION OUTPUT

    LOCATION: Path to a inventory file (CSV or JSON file)
    OUTPUT: Path to the directory to write ABOUT files to

**Options:**

::

    -q, --quiet                     Do not print any error/warning.
    --mapping                       Use for mapping between the input keys and
                                    the ABOUT field names - MAPPING.CONFIG
    --license_text_location DIRECTORY
                                    Copy the 'license_text_file' from the
                                    directory to the generated location
    --extract_license TEXT...       Extract License text and create
                                    <dje_license_key>.LICENSE side-by-side with the
                                    generated .ABOUT file using data fetched
                                    from a DejaCode License Library. The
                                    following additional options are required:

                                    api_url - URL to the DejaCode License
                                    Library API endpoint

                                    api_key - DejaCode API key
                                    Example syntax:

                                    about gen --extract_license 'api_url' 'api_key'
    --help                          Show this message and exit.

Purpose
-------
Generate ABOUT files from the input to the output location.

Options
-------

::

    --mapping

        See MAPPING.CONFIG for details

    --license_text_location

        Copy the license files to the generated location based on the 
        'license_file' value in the input from the directory

        For instance,
        the directory, /home/licenses/, contains all the licenses that users want:
        /home/license/apache2.LICENSE
        /home/license/jquery.js.LICENSE

    $ about gen --license_text_location /home/licenses/ LOCATION OUTPUT

    --extract_license

        Extract license text(s) from DJE License Library and create
        <dje_license_key>.LICENSE side-by-side with the generated .ABOUT files based
        on the 'dje_license_key' value in the input.

        This option requires 2 parameters:
            api_url - URL to the DJE License Library
            api_key - Hash key to authenticate yourself in the API.
        (Please contact us to get the api_* value to use this feature)

    $ about gen --extract_license 'api_url' 'api_key' LOCATION OUTPUT


attrib
======

**Syntax**

::

    about attrib [OPTIONS] LOCATION OUTPUT [INVENTORY_LOCATION]

    LOCATION: Path to an ABOUT file or a directory containing ABOUT files
    OUTPUT: Path to output file to write the attribution to
    INVENTORY_LOCATION: Path to a CSV file which contains the 'about_file_path' key [OPTIONAL]

**Options:**

::

    -q, --quiet      Do not print any error/warning.
    --template PATH  Use the custom template for the Attribution Generation
    --mapping        Use for mapping between the input keys and the ABOUT field
                     names - MAPPING.CONFIG
    --help           Show this message and exit.

Purpose
-------
Generate an attribution file which contains the all license information
from the LOCATION along with the license text.

Supplying an INVENTORY_LOCATION will generate an attribution file which contains
license information for ONLY the listed components in the INVENTORY_LOCATION.

This tool will look at the components in the INVENTORY_LOCATION and find the
corresponding .ABOUT files in the LOCATION and generate the output. 

Assuming the follow:

::

    '/home/about_files/'** contains all the ABOUT files
    '/home/attribution/attribution.html' is the user's output path
    '/home/project/component_list.csv' is the INVENTORY_LOCATION that user want to be generated

::

    $ about attrib /home/about_files/ /home/attribution/attribution.html /home/project/component_list.csv

Options
-------

::

    --template
    
        This option allows users to use their own template for Attribution Generation.
        For instance, if user has a custom template located at:
        /home/custom_template/template.html

    $ about attrib --template /home/custom_template/template.html LOCATION OUTPUT [INVENTORY_LOCATION]

    --mapping

        See MAPPING.CONFIG for details

