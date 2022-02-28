.. _reference:

=========
Reference
=========

about
=====

Syntax
------

        ..  code-block:: none

                about [OPTIONS] [COMMANDS]

Options
-------

        ..  code-block:: none

                --version        Show the version and exit.
                -h, --help       Show this message and exit.

Commands
--------

        ..  code-block:: none

              attrib              Generate an attribution document from
                                  JSON/CSV/XLSX/.ABOUT files.
              check               Validate that the format of .ABOUT files is correct and
                                  report errors and warnings.
              collect-redist-src  Collect redistributable sources.
              gen                 Generate .ABOUT files from an inventory as
                                  CSV/JSON/XLSX.
              gen-license         Fetch and save all the licenses in the
                                  license_expression field to a directory.
              inventory           Collect the inventory of .ABOUT files to a CSV/JSON/XLSX
                                  file.
              transform           Transform a CSV/JSON/XLSX by applying renamings, filters
                                  and checks.

attrib
======

Syntax
------

        ..  code-block:: none

                about attrib [OPTIONS] LOCATION OUTPUT

                INPUT: Path to a file (.ABOUT/.csv/.json/.xlsx), directory or .zip archive containing .ABOUT files.

                OUTPUT: Path where to write the attribution document.

Options
-------

        ..  code-block:: none

                --api_url URL                URL to DejaCode License Library.
                --api_key KEY                API Key for the  DejaCode License Library
                --min-license-score INTEGER  Attribute components that have license score
                                             higher than the defined --min-license-score.
                --scancode                   Indicate the input JSON file is from
                                             scancode toolkit.
                --reference DIR              Path to a directory with reference files where
                                             "license_file" and/or "notice_file" located.
                --template FILE              Path to an optional custom attribution template to
                                             generate the attribution document. If not provided
                                             the default built-in template is used.
                --vartext <key>=<value>      Add variable text as key=value for use in a custom
                                             attribution template.
                -q, --quiet                  Do not print error or warning messages.
                --verbose                    Show all error and warning messages.
                -h, --help                   Show this message and exit.

Purpose
-------

Generate an attribution file which contains license information from the INPUT along with the license text.

Assume the following:

        ..  code-block:: none

            '/home/about_files/' contains all the ABOUT files [INPUT]
            '/home/project/inventory.csv' is a BOM inventory [INPUT]
            '/home/project/scancode-detection.json' is a detection output from scancode-toolkit[INPUT] 
            '/home/project/licenses/' contains all the license/notice file references
            '/home/attribution/attribution.html' is the user's output path [OUTPUT]


        ..  code-block:: none

            $ about attrib /home/about_files/ /home/attribution/attribution.html
            or
            $ about attrib /home/project/inventory.csv /home/attribution/attribution.html --reference /home/project/licenses/
            or
            $ about attrib --scancode /home/project/scancode-detection.json /home/attribution/attribution.html

Details
^^^^^^^

        ..  code-block:: none

                --api_url URL --api_key

                    This option let user to define where to get the license information such as
                    from DJE. If these options are not set, the tool will get the license
                    information from ScanCode LicenseDB by default

                $ about attrib --api_url <URL> --api_key <KEY> INPUT OUTPUT

                --min-license-score

                    This option is a filter to collect license information where the license score
                    in the scancode toolkit detection is greater than or equal to the defined
                    --min-license-score. This option is specifically design for scancode's input
                    and therefore --scancode is required

                $ about attrib --scancode --min-license-score 85 /home/project/scancode-detection.json OUTPUT

                --reference

                    This option is to define the reference directory where the 'license_file'
                    or 'notice_file' are stored

                $ about attrib --reference /home/project/licenses/ /home/project/inventory.csv OUTPUT

                --template

                    This option allows you to use your own template for attribution generation.
                    For instance, if you have a custom template located at:
                    /home/custom_template/template.html
                
                $ about attrib --template /home/custom_template/template.html INPUT OUTPUT
                
                --vartext
                
                    This option allow you to pass variable texts to the attribution template
                
                $ about attrib --vartext "title=Attribution Notice" --vartext "header=Product 101" LOCATION OUTPUT
                
                    Users can use the following in the template to get the vartext:
                    {{ vartext['title'] }}
                    {{ vartext['header'] }}

                --verbose

                    This option tells the tool to show all errors found.
                    The default behavior will only show 'CRITICAL', 'ERROR', and 'WARNING'

The following data are passed to jinja2 and, therefore, can be used for a custom template:
 * about object: the about objects
 * common_licenses: a common license keys list in licenses.py
 * licenses_list: a license object list contains all the licenses found in about objects. It contains the following attribute: key, name, filename, url, text

check
=====

Syntax
------

        ..  code-block:: none

                about check [OPTIONS] LOCATION

                LOCATION: Path to an ABOUT file or a directory with ABOUT files.

Options
-------

        ..  code-block:: none

                --djc api_url api_key  Validate license_expression from a DejaCode License
                                       Library API URL using the API KEY.
                --log FILE             Path to a file to save the error messages if any.
                --verbose              Show all error and warning messages.
                -h, --help             Show this message and exit.

Purpose
-------

Validating ABOUT files at LOCATION.

Details
^^^^^^^

        ..  code-block:: none

                ---djc

                    Validate license_expression from a DejaCode License.

                    This option requires 2 parameters:
                        api_url - URL to the DJE License Library.
                        api_key - Hash key to authenticate yourself in the API.

                    In addition, the input needs to have the 'license_expression' field.
                    (Please contact nexB to get the api_* value for this feature)

                $ about check --djc 'api_url' 'api_key' /home/project/about_files/

                --log

                    This option save the error log to the defined location

                $ about check --log /home/project/error.log /home/project/about_files/

                --verbose

                    This option tells the tool to show all errors found.
                    The default behavior will only show 'CRITICAL', 'ERROR', and 'WARNING'

                $ about check --verbose /home/project/about_files/

Special Notes
-------------
If no `--djc` option is set, the tool will default to check license_expression from
ScanCode LicenseDB.

collect_redist_src
==================

Syntax
------

        ..  code-block:: none

                about collect_redist_src [OPTIONS] LOCATION OUTPUT
                
                LOCATION: Path to a directory containing sources that need to be copied
                (and containing ABOUT files if `inventory` is not provided)
                
                OUTPUT: Path to a directory or a zip file where sources will be copied to.

Options
-------

        ..  code-block:: none

                --from-inventory FILE  Path to an inventory CSV/JSON file as the base list
                                       for files/directories that need to be copied which
                                       have the 'redistribute' flagged.
                --with-structures      Copy sources with directory structure.
                --zip                  Zip the copied sources to the output location.
                -q, --quiet            Do not print error or warning messages.
                --verbose              Show all error and warning messages.
                -h, --help             Show this message and exit.

Purpose
-------

Collect sources that have 'redistribute' flagged as 'True' in .ABOUT files or inventory to the output location.

Details
^^^^^^^

        ..  code-block:: none

                --from-inventory
                
                    Provide an inventory CSV/JSON file with the 'redistribute' field filled as
                    the indication of which files/sources need to be copied.
                
                $ about collect_redist_src --from-inventory 'path to the inventory' LOCATION OUTPUT
                
                --with-structures
                
                    Copy the file(s) along with its parent directories
                
                    For instance, assuming we want to copy the following file:
                    /project/work/hello/foo.c
                
                    OUTPUT: /output/
                
                $ about collect_redist_src --with-structure /project/ /output/
                
                    OUTPUT: /output/work/hello/foo.c
                
                $ about collect_redist_src /project/ /output/
                
                    OUTPUT: /output/foo.c
                
                --zip
                
                    Zip the copied sources to the output location
                
                $ about collect_redist_src --zip /project/ /output/output.zip
                
                --verbose
                
                    This option tells the tool to show all errors found.
                    The default behavior will only show 'CRITICAL', 'ERROR', and 'WARNING'

gen
===

Syntax
------

        ..  code-block:: none

                about gen [OPTIONS] LOCATION OUTPUT
                
                LOCATION: Path to a JSON/CSV/XLSX inventory file.
                OUTPUT: Path to a directory where ABOUT files are generated.

Options
-------

        ..  code-block:: none

                --android                           Generate MODULE_LICENSE_XXX (XXX will be
                                                    replaced by license key) and NOTICE as the same
                                                    design as from Android.
                --fetch-license                     Fetch license data and text files from the
                                                    ScanCode LicenseDB.
                --fetch-license-djc api_url api_key Fetch licenses data from DejaCode License
                                                    Library and create <license>.LICENSE
                                                    side-by-side with the generated .ABOUT file.
                                                    The following additional options are required:

                                                    api_url - URL to the DejaCode License Library
                                                    API endpoint

                                                    api_key - DejaCode API key
                                                    Example syntax:

                                                    about gen --fetch-license-djc api_url api_key
                --reference PATH                    Path to a directory with reference license
                                                    data and text files.
                -q, --quiet                         Do not print any error/warning.
                --verbose                           Show all the errors and warning.
                -h, --help                          Show this message and exit.

Purpose
-------

Given a CSV/JSON/XLSX inventory, generate ABOUT files in the output location.

Details
^^^^^^^

        ..  code-block:: none

                --android

                    Create an empty file named `MODULE_LICENSE_XXX` where `XXX` is the license
                    key and create a NOTICE file which these two files follow the design from
                    Android Open Source Project.

                    The input **must** have the license key information as this is needed to
                    create the empty MODULE_LICENSE_XXX

                $ about gen --android LOCATION OUTPUT

                --fetch-license

                    Fetch licenses text and create <license>.LICENSE side-by-side
                    with the generated .ABOUT file using the data fetched from the the ScanCode LicenseDB.

                    The input needs to have the 'license_expression' field.

                $ about gen --fetch-license LOCATION OUTPUT

                --fetch-license-djc

                    Fetch licenses text from a DejaCode API, and create <license>.LICENSE side-by-side
                    with the generated .ABOUT file using the data fetched from the DejaCode License Library.

                    This option requires 2 parameters:
                        api_url - URL to the DJE License Library.
                        api_key - Hash key to authenticate yourself in the API.

                    In addition, the input needs to have the 'license_expression' field.
                    (Please contact nexB to get the api_* value for this feature)

                $ about gen --fetch-license-djc 'api_url' 'api_key' LOCATION OUTPUT

                --reference

                    Copy the reference files such as 'license_files' and 'notice_files' to the
                    generated location from the specified directory.

                    For instance,
                    the specified directory, /home/licenses_notices/, contains all the licenses and notices:
                    /home/licenses_notices/apache2.LICENSE
                    /home/licenses_notices/jquery.js.NOTICE

                $ about gen --reference /home/licenses_notices/ LOCATION OUTPUT

                --verbose

                    This option tells the tool to show all errors found.
                    The default behavior will only show 'CRITICAL', 'ERROR', and 'WARNING'

gen_license
===========

Syntax
------

        ..  code-block:: none

                about gen_license [OPTIONS] LOCATION OUTPUT

                LOCATION: Path to a JSON/CSV/XLSX/.ABOUT file(s)
                OUTPUT: Path to a directory where license files are saved.

Options
-------

        ..  code-block:: none

                --djc api_url api_key   Fetch licenses data from DejaCode License
                                        Library and create <license>.LICENSE to the
                                        OUTPUT location.
                --scancode              Indicate the input JSON file is from
                                        scancode_toolkit.
                 --verbose              Show all the errors and warning.
                -h, --help              Show this message and exit.

Purpose
-------

Fetch licenses (Default: ScanCode LicenseDB) in the license_expression field and save to the output location.

Details
^^^^^^^

        ..  code-block:: none

                --djc

                    Fetch licenses text from a DejaCode API, and create <license>.LICENSE to the 
                    OUTPUT Location using the data fetched from the DejaCode License Library.

                    This option requires 2 parameters:
                        api_url - URL to the DJE License Library.
                        api_key - Hash key to authenticate yourself in the API.

                    In addition, the input needs to have the 'license_expression' field.
                    (Please contact nexB to get the api_* value for this feature)

                $ about gen_license --djc 'api_url' 'api_key' LOCATION OUTPUT

                --scancode

                    Indicates the JSON input is from scancode toolkit license detection

                $ about gen_license --scancode /home/project/scancode-license-detection.json OUTPUT

                --verbose

                    This option tells the tool to show all errors found.
                    The default behavior will only show 'CRITICAL', 'ERROR', and 'WARNING'

Special Notes
-------------
If no `--djc` option is set, the tool will default to fetch licenses from ScanCode LicenseDB.

inventory
=========

Syntax
------

        ..  code-block:: none

                about inventory [OPTIONS] LOCATION OUTPUT
                
                LOCATION: Path to an ABOUT file or a directory with ABOUT files.
                OUTPUT: Path to the CSV/JSON/XLSX inventory file to create.

Options
-------

        ..  code-block:: none

                -f, --format [json|csv|excel]   Set OUTPUT file format.  [default: csv]
                -q, --quiet                     Do not print any error/warning.
                --verbose                       Show all the errors and warning.
                -h, --help                      Show this message and exit.

Purpose
-------

Create a JSON/CSV/XLSX inventory of components from ABOUT files.

Details
^^^^^^^

        ..  code-block:: none

                -f, --format [json|csv|excel]
                
                    Set OUTPUT file format.  [default: csv]
                
                $ about inventory -f json LOCATION OUTPUT
                
                --verbose
                
                    This option tells the tool to show all errors found.
                    The default behavior will only show 'CRITICAL', 'ERROR', and 'WARNING'

Special Notes
-------------

Multiple licenses support format
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The multiple licenses support format for CSV files are separated by line break

+----------------+------+--------------+---------------+---------------------+
| about_resource | name | license_key  | license_name  | license_file        |
+================+======+==============+===============+=====================+
| test.tar.xz    | test | | apache-2.0 | | Apache 2.0  | | apache-2.0.LICENSE|
|                |      | | mit        | | MIT License | | mit.LICENSE       |
+----------------+------+--------------+---------------+---------------------+

The multiple licenses support format for ABOUT files are by "grouping" with the keyword "licenses"

        ..  code-block:: none

                about_resource: test.tar.xz
                name: test
                licenses:
                    -   key: apache 2.0
                        name: Apache 2.0
                        file: apache-2.0.LICENSE
                    -   key: mit
                        name: MIT License
                        file: mit.LICENSE

Multiple license_file support
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To support multiple license file for a license, the correct format is to separate by comma

+----------------+------+--------------+---------------+---------------------+
| about_resource | name | license_key  | license_name  | license_file        |
+================+======+==============+===============+=====================+
| test.tar.xz    | test | | gpl-2.0    | | GPL 2.0     | | COPYING, COPYINGv2|
|                |      | | mit        | | MIT License | | mit.LICENSE       |
+----------------+------+--------------+---------------+---------------------+

        ..  code-block:: none

                about_resource: test.tar.xz
                name: test
                licenses:
                    -   key: gpl-2.0
                        name: gpl-2.0
                        file: COPYING, COPYING.v2
                    -   key: mit
                        name: mit
                        file: mit.LICENSE

Note that if license_name is not provided, the license key will be used as the license name.

transform
=========

Syntax
------

        ..  code-block:: none

                about transform [OPTIONS] LOCATION OUTPUT
                
                LOCATION: Path to a CSV/JSON/XLSX file.
                OUTPUT: Path to CSV/JSON/XLSX inventory file to create.

Options
-------

        ..  code-block:: none

                -c, --configuration FILE  Path to an optional YAML configuration file. See
                                          --help-format for format help.
                --help-format             Show configuration file format help and exit.
                -q, --quiet               Do not print error or warning messages.
                --verbose                 Show all error and warning messages.
                -h, --help                Show this message and exit.

Purpose
-------

Transform the CSV/JSON/XLSX file at LOCATION by applying renamings, filters and checks and then write a new CSV/JSON/Excel to OUTPUT (Format for input and output need to be the same).

Details
^^^^^^^

        ..  code-block:: none

                -c, --configuration
                
                    Path to an optional YAML configuration file. See--help-format for format help.
                
                $ about transform -c 'path to the YAML configuration file' LOCATION OUTPUT
                
                --help-format
                
                    Show configuration file format help and exit.
                    This option will print out examples of the the YAML configuration file.
                
                    Keys configuration are: `field_renamings`, `required_fields` and `field_filters`
                
                $ about transform --help-format
                
                --verbose
                
                    This option tells the tool to show all errors found.
                    The default behavior will only show 'CRITICAL', 'ERROR', and 'WARNING'

Special Notes
-------------
When using the field_filters configuration, all the standard required columns (about_resource and name) and the user defined required_fields need to be included.