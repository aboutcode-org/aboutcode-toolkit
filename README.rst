AboutCode tool
==============

.. image:: https://travis-ci.org/dejacode/about-code-tool.svg?branch=master
  :target: https://travis-ci.org/dejacode/about-code-tool

.. image:: https://coveralls.io/repos/dejacode/about-code-tool/badge.svg?branch=master 
  :target: https://coveralls.io/r/dejacode/about-code-tool?branch=master


The AboutCode tool and ABOUT files provide a simple way to document the
(origin and license) and other important or interesting information about
third-party software components that you use in your project.

You start by storing ABOUT files (a small text file with field/value pairs)
side-by-side with each of the third-party software components you use.
Each ABOUT file documents one software component origin and license.
For more information on the ABOUT file format, visit http://www.dejacode.org
There are many examples of ABOUT files (valid or invalid) in the testdata/
directory of the whole repository.

The current version of AboutCode can read these ABOUT files so that you
can collect and validate the inventory of third-party components that you use.

This version of AboutCode follows the ABOUT specification version 1.0.0 at:
https://github.com/dejacode/about-code-tool/blob/master/SPEC


License
-------
AboutCode is released under the Apache 2.0 license.
See (of course) the about.ABOUT file for details.


Requirements
------------
The AboutCode tool requires an installation Python 2.7 on Linux, Mac and Windows.
You need to install Python if you do not have one already installed.

On Linux and Mac, Python is typically pre-installed. To verify which
version may be pre-installed, open a terminal and type::

    python --version
    python2.7 --version

On Linux, Python2.7 may be available from your distro package manager.

On Windows and Mac if version 2.7 is not installed, you can download the latest
Python 2.7.x here https://www.python.org/downloads/ :

* Download the .msi installer for Windows or the .dmg archive for Mac.
* Open and run the installer using all the default options.
* On Windows, make sure you install Python in the default c:\\Python27 and not
  on another drive.


Installation
------------
Download the AboutCode tool from a released version at:
    https://github.com/dejacode/about-code-tool/releases

Extract the archive to a directory and open a command prompt or shell in this
directory. Then on Linux or Mac run::

    source configure

And on Windows::

    configure


For instance on Linux the whole installation would be like this::

   $ wget https://github.com/dejacode/about-code-tool/archive/v2.3.2.zip
   $ unzip  v2.3.2.zip
   $ cd attributecode-2.3.2/
   $ source configure

On Windows, the whole installation would be like this:

 * Download and extract https://github.com/dejacode/about-code-tool/archive/v2.3.2.zip
 * open a command prompt and cd to the directory where the zip extraction directory
 * run configure


Later on, if opening a new shell or command prompt on an already installed 
AboutCode you need to **activate** this installation.

On Linux or Mac, run this::

   source bin/activate

On Windows, run this::

   bin\\activate


Usage
-----
Once installed, the AboutCode tool is used from the command line.
There are three scripts: about.py, genabout.py and genattrib.py.
Once you have installed or activated AboutCode, the scripts are invoked from a
shell or command prompt in this way::

    $ python about_code_tool/about.py <options ....>


See docs/UsingAboutCodetoDocumentYourSoftwareAssets.pdf for a detailed
documentation and tutorial or read on the quick instructions below.


**Using the about.py script**

The about.py script is used to collect existing ABOUT files, validate that
they are correct and collect inventories of the documented components in a CSV
file.

::

    Usage: about.py [options] input_path output_path

    input_path can be a file or directory containing .ABOUT files.
    output_path is a file with a .csv extension.

    Options:
      -h, --help            Display help
      --version             Display current version, license notice, and copyright notice
      --overwrite           Overwrites the output file if it exists
      --verbosity=VERBOSITY
                            Print more or fewer verbose messages while processing ABOUT files
                            0 - Do not print any warning or error messages, just a total count (default)
                            1 - Print error messages
                            2 - Print error and warning messages

Example::

    $ python about_code_tool/about.py ./thirdparty/ thirdparty_about.csv


In this example, the .ABOUT files in the directory thirdparty/ will
be parsed and validated to collect the data they contain. The collected
information will be saved to the CSV file named "thirdparty_about.csv".



**Using the genabout.py script**

The genabout.py script is used to generate new ABOUT files by using a CSV file
as an input.

::

    Usage: genabout.py [options] input_path output_path
    
        input_path is a CSV file using the same format as the CSV created with about.py
        output_path is a directory where the new .ABOUT files are generated
    
    
    Options:
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
    
      --mapping             Use the mapping between columns names in your CSV and the ABOUT field
                            names as defined in the MAPPING.CONFIG mapping configuration file.
    
      --extract_license
                            Extract License text and create <license_key>.LICENSE side-by-side
                            with the generated .ABOUT file using data fetched from a DejaCode License Library.
                            The following additional options are required:
                            --api_url - URL to the DejaCode License Library API endpoint
                            --api_key - DejaCode API key

                            Example syntax:
                            python about_code_tool/genabout.py --extract_license --api_url='api_url' --api_key='api_key'


Example::

    $ mkdir tmp
    $ python about_code_tool/genabout.py thirdparty_code.csv tmp/thirdparty_about

In this example, the tool will use the list in the "thirdparty_code.csv" file
and generate .ABOUT files in a directory tmp/thirdparty_about/


**Using the genattrib.py script**

The genattrib.py script is used to generate a credit and license attribution
documentation in HTML from a directory containing .ABOUT files.

::

    Usage: genattrib.py [options] input_path output_path component_list

        input can be a file or directory.
        output of rendered template must be a file (e.g. .html).
        component_list is an optional .csv file with an "about_file" column.
            It is used to limit the attribution generation to the subset of 
            ABOUT files listed here.

    Options:
      -h, --help            Display help
      -v, --version         Display current version, license notice, and copyright notice
      --overwrite           Overwrites the output file if it exists
      --verbosity=VERBOSITY
                            Print more or fewer verbose messages while processing ABOUT files
                            0 - Do not print any warning or error messages, just a total count (default)
                            1 - Print error messages
                            2 - Print error and warning messages

      --template_location=TEMPLATE_LOCATION
                            Use the custom template for the Attribution Generation

      --mapping             Configure the mapping key from the MAPPING.CONFIG

Example::

    $ python about_code_tool/genattrib.py tmp/thirdparty_about/ tmp/attribution.html thirdparty_code.csv

In this example, the tool will look at the .ABOUT files listed in the "thirdparty_code.csv" 
from the /tmp/thirdparty_about/ and then generate the attribution output to
/tmp/thirdparty_attribution/attribution.html


(See USAGE for a details explaining of each scripts and options.)



Help and Support
----------------
If you have a question or find a bug, enter a ticket at:

    https://github.com/dejacode/about-code-tool

For issues, you can use:

    https://github.com/dejacode/about-code-tool/issues


Hacking, tests and source code
------------------------------
For the latest stable version visit::

    https://github.com/dejacode/about-code-tool

The development takes places in the develop branch. We use the git flow 
branching model.

**Tests**

You can run the test suite with::

    python setup.py test


**Contributing**

We accept bugs, patches and pull requests for code and documentation provided 
under the same license (Apache-2.0) as this tool.
When contributing, you are agreeing to the http://developercertificate.org/ 
