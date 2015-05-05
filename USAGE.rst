about.py
========

**Syntax**

::

    about.py [options] input_path output_path

    - Input can be a file or directory.
    - Output must be a file with a .csv extension.

**Options:**

::

      -h, --help            Display help
      --version             Display current version, license notice, and copyright notice
      --overwrite           Overwrites the output file if it exists
      --verbosity=VERBOSITY
                            Print more or fewer verbose messages while processing ABOUT files
                            0 - Do not print any warning or error messages, just a total count (default)
                            1 - Print error messages
                            2 - Print error and warning messages

Purpose
-------
Extract information from the .ABOUT files and save it to the CSV file.

Options
-------

::

    --overwrite
 
        Overwrite the extracted data from .ABOUT files to the output location

    $ python about.py --overwrite <input path> <output path>


genabout.py
===========

**Syntax**

::

    genabout.py [options] input_path output_path

    - Input must be a CSV file
    - Output must be a directory location where the ABOUT files should be generated

**Options:**

::

      -h, --help            Display help
      --version             Display current version, license notice, and copyright notice
      --verbosity=VERBOSITY
                            Print more or fewer verbose messages while processing ABOUT files
                            0 - Do not print any warning or error messages, just a total count (default)
                            1 - Print error messages
                            2 - Print error and warning messages

      --action=ACTION       Handle different behaviors if ABOUT files already existed
                            0 - Do nothing if ABOUT file existed (default)
                            1 - Overwrites the current ABOUT field value if existed
                            2 - Keep the current field value and only add the "new" field and field value
                            3 - Replace the ABOUT file with the current generation

      --copy_files=COPY_FILES
                            Copy the '*_file' from the project to the generated location
                            Project path - Project path

      --license_text_location=LICENSE_TEXT_LOCATION
                            Copy the 'license_text_file' from the directory to the generated location
                            License path - License text files path

      --mapping             Configure the mapping key from the MAPPING.CONFIG

      --extract_license=EXTRACT_LICENSE
                            Extract License text and create <license_key>.LICENSE side-by-side
                                with the .ABOUT from DJE License Library.
                            api_url - URL to the DJE License Library
                            api_username - The regular DJE username
                            api_key - Hash attached to your username which is used to authenticate
                                        yourself in the API. Contact us to get the hash key.

                            Example syntax:
                            genabout.py --extract_license --api_url='api_url' --api_username='api_username' --api_key='api_key'

Purpose
-------
Generate ABOUT files from the input CSV file to output location.

Options
-------

::

    --action=ACTION

        Handle different behaviors if ABOUT files already existed.
        For instance, replace the ABOUT files with the current generation

    $ python genabout.py --action=3 <input path> <output path>

    --copy_files

        Copy the files to the generated location based on the 
        *_file value in the input from the project

        Purpose of this option is for users who want to generate ABOUT files
        in a different location other than the project side by side with the code.

        For instance, the project is located at /home/project/, and users want to
        generate ABOUT files to /home/about/ and also want to copy the
        'license_text_file' and 'notice_text_file' from
        /home/project/ to /home/about/

    $ python genabout.py --copy_files=/home/project/ <input path> /home/about/

    --license_text_location

        Copy the license files to the generated location based on the 
        'license_text_file' value in the input from the directory

        For instance,
        the directory, /home/licenses/, contains all the licenses that users want:
        /home/license/apache2.LICENSE
        /home/license/jquery.js.LICENSE

    $ python genabout.py --license_text_location=/home/licenses/ <input path> <output path>

    --mapping

        This tool needs the input CSV to have the required and/or optional keys to work.
        Since the user input may not have the same column key names used by the tool,
        there are two ways to reconcile that:
        1. Change the key names directly in the input manually to match the field names
        supported by the AboutCode specification.
        Note: genabout.py looks for an about_file field and uses it to derive the mandatory
        output field about_resource.
        2. Use the '--mapping' option to configure the key mapping. This method provides the
        most flexiblity and control. 
        When the '--mapping' option is set, the tool will look into the 'MAPPING.CONFIG'
        file to determine key mapping.
        
        The format of each text line in the MAPPING.CONFIG file is as follows:
            {{about_file_target_field_name}}: {{input_csv_file_field_name}}

        For instance, assume that MAPPING.CONFIG contains the following:
            about_resource: file_name
            about_file: Resource
            name: Component
            version: file_version

        The tool will look into the input CSV and try to find the column key named
        'file_name' and configure to map with the 'about_resource' key that the
        tool uses. The 'Resource' will then configure to map with 'about_file' and
        so on.

        In another word, you do not need to modify the key names of the
        input manually, but rather use the MAPPING.CONFIG to do the key mapping.
        
        Another advantage of using the MAPPING.CONFIG is the ability to specify 
        any field names that are important to you, including custom fields.

    $ python genabout.py --mapping <input path> <output path>

    --extract_license

        Extract license text(s) from DJE License Library and create
        <license_key>.LICENSE side-by-side with the generated .ABOUT files based
        on the 'dje_license' value in the input CSV.

        This option requires 3 parameters:
            api_url - URL to the DJE License Library
            api_username - The regular DJE username
            api_key - Hash attached to your username which is used to authenticate
                        yourself in the API.
        (Please contact us to get the api_* value to use this feature)

    $ python genabout.py --extract_license --api_url='api_url' --api_username='api_username' --api_key='api_key' <input path> <output path>


genattrib.py
============

**Syntax**

::

    genattrib.py [options] input_path output_path component_list

    - Input can be a file or directory.
    - Output of rendered template must be a file (e.g. .html).
    - Component List must be a .csv file which has at least an "about_file" column.

**Options:**

::

    -h, --help          Display help
    --version           Display current version, license notice, and copyright notice
    --overwrite         Overwrites the output file if it exists
    --verbosity=VERBOSITY
                        Print more or fewer verbose messages while processing ABOUT files
                        0 - Do not print any warning or error messages, just a total count (default)
                        1 - Print error messages
                        2 - Print error and warning messages
    --template_location=TEMPLATE_LOCATION
                        Use the custom template for the Attribution Generation
    --mapping           Configure the mapping key from the MAPPING.CONFIG

Purpose
-------
Generate an Attribution HTML file which contains the license information from
the 'component_list' along with the license text.

This tool will look at the components in the 'component_list' and find the
corresponding .ABOUT files in the 'input_path' and generate the output in
the 'output_path'. Therefore, please make sure there are .ABOUT files under
the 'input_path'.

Assuming the follow:

::

    '/home/about_files/'** contains all the ABOUT files from the component_list
    '/home/attribution/attribution.html' is the user's output path
    '/home/project/component_list.csv' is the component list that user want to be generated

::

    $ python genattrib.py /home/about_files/ /home/attribution/attribution.html /home/project/component_list.csv

Options
-------

::

    --template_location
    
        This option allows you to use your own template for Attribution Generation.
        For instance, if the custom template you want to use is located at:
        /home/custom_template/template.html

    $ python genattrib.py --template_location=/home/custom_template/template.html input_path output_path component_list


