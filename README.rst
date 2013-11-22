ABOUT tool
==========

.. image:: https://api.travis-ci.org/dejacode/about-code-tool.png?branch=develop
   :target: https://travis-ci.org/dejacode/about-code-tool

.. image:: https://coveralls.io/repos/dejacode/about-code-tool/badge.png?branch=develop
  :target: https://coveralls.io/r/dejacode/about-code-tool?branch=develop


The ABOUT tool and ABOUT files provide a simple way to document the
(origin and license) and other important or interesting information about
third-party software components that you use in your project.

You start by storing ABOUT files (a small text file with field/value pairs)
side-by-side with each of the third-party software components you use.
Each ABOUT file documents one software component origin and license.
For more information on the ABOUT file format, visit http://www.dejacode.org
There are many examples of ABOUT files (valid or invalid) in the testdata/
directory of the whole repository.

The current version of the ABOUT tool can read these ABOUT files so that you
can collect and validate the inventory of third-party components that you use.

In future versions, this tool will be able to generate attribution notices and
collect redistributable source code used in your project to help you comply
with open source licenses requirements.

This version of the ABOUT tool follows the ABOUT specification version 0.8.0 at:
http://www.dejacode.org/about_spec_v0.8.0.html


REQUIREMENTS
------------
The ABOUT tool is tested with Python 2.6 or 2.7 on Linux, Mac and Windows.
You will need to install a Python interpreter if you do not have one already
installed.

On Linux and Mac, Python is typically pre-installed. To verify which
version may be pre-installed, open a terminal and type::

    python --version
    python2.6 --version
    python2.7 --version

On Windows or Mac, you can download Python 2.6 here:
    http://www.python.org/download/releases/2.6.6/

or Python 2.7 here:
    http://www.python.org/download/releases/2.7.5/

Download the .msi installer for Windows or the .dmg archive for Mac.
Open and run the installer using all the default options.


INSTALLATION
------------
Download and save the about.py file from:
https://raw.github.com/dejacode/about-code-tool/master/about.py


TESTS
-----
Optionally, to verify that everything works fine you can run the test suite,
download the whole repository at:
https://github.com/dejacode/about-code-tool/archive/master.zip

Then open a terminal or command prompt, extract the download if needed and run::

    python setup.py test


USAGE
-----
The ABOUT tool command syntax is::

    $ python about.py [--options] <input> <output>

    [--options]
    --overwrite          Overwrites the output file if it exists
    -v,--version         Display current version, license notice, and copyright notice
    -h,--help            Display syntax help
    --verbosity  <arg>   Print more or less verbose messages while processing ABOUT files
    <arg>
            0 - Do not print any warning or error messages, just a total count (default)
            1 - Print error messages
            2 - Print error and warning messages

    <input> - Path location where the .ABOUT file(s) located.
              The location can be pointing to a file or directory.

    <output> - Path location where the generated output will be saved.
               The <output> must be a path with an output filename ending
               with the ".csv" extension.

Example::

    $ python about.py ./thirdparty_code/ thirdparty_about.csv


In this example, the .ABOUT files in the directory /thirdparty_code/ will
be parsed and validated to collect the data they contain. The collected
information will be saved to the CSV file named "thirdparty_about.csv".


HELP and SUPPORT
----------------
If you have a question or find a bug, enter a ticket at:

    https://github.com/dejacode/about-code-tool

For issues, you can use:

    https://github.com/dejacode/about-code-tool/issues


SOURCE CODE
-----------
The ABOUT tool is available through GitHub. For the latest version visit:

    https://github.com/dejacode/about-code-tool


HACKING
-------
We accept pull requests provided under the same license as this tool.


LICENSE
-------
The ABOUT tool is released under the Apache 2.0 license.
See (of course) the about.ABOUT file for details.
