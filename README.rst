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

This version of the ABOUT tool follows the ABOUT specification version 0.8.1 at:
http://www.dejacode.org/about_spec_v0.8.1.html


REQUIREMENTS
------------
The ABOUT tool is tested with Python 2.6 or 2.7 on Linux, Mac and Windows.
You will need to install a Python interpreter if you do not have one already
installed.

On Linux and Mac, Python is typically pre-installed. To verify which
version may be pre-installed, open a terminal and type::

    python --version
    python2.7 --version

On Windows or Mac, you can download the latest Python 2.7.x here:
    https://www.python.org/downloads/

Download the .msi installer for Windows or the .dmg archive for Mac.
Open and run the installer using all the default options.


INSTALLATION
------------
Checkout or download and extract the AboutCode tool from:
    https://github.com/dejacode/about-code-tool/

To install all the needed dependencies in a virtualenv, run (on posix)::
    source configure 
or on windows::
    configure


TESTS and DEVLOPMENT
--------------------
To install all the needed development dependencies, run (on posix)::
    source configure etc/conf/dev
or on windows::
    configure etc/conf/dev

To verify that everything works fine you can run the test suite with::
    py.test



HELP and SUPPORT
----------------
If you have a question or find a bug, enter a ticket at:

    https://github.com/dejacode/about-code-tool

For issues, you can use:

    https://github.com/dejacode/about-code-tool/issues


SOURCE CODE
-----------
AboutCode is available through GitHub. For the latest version visit:
    https://github.com/dejacode/about-code-tool


HACKING
-------
We accept pull requests provided under the same license as this tool.
You agree to the http://developercertificate.org/ 


LICENSE
-------
AboutCode is released under the Apache 2.0 license.
See (of course) the about.ABOUT file for details.
