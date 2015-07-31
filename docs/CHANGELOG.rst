2015-07-31  Chin-Yeung Li  <tli@nexb.com>

    Release 2.0.3

    * Fix the bug of using genattrib.py on Windows OS
    * Display version when running about.py, genabout.py and genattrib.py


2015-07-06  Chin-Yeung Li  <tli@nexb.com>

    Release 2.0.2

    * Handle input's encoding issues
    * Better error handling
    * Writing to and reading from Windows OS with paths > 255 chars


2015-06-08  Chin-Yeung Li  <tli@nexb.com>

    Release 2.0.1

    * Fixes the configure scripts and updates basic documentation.


2015-03-06  Chin-Yeung Li  <tli@nexb.com>

    Release 2.0.0

    * Breaking API changes:

      * the dje_license field has been renamed to dje_license_keys
      * when a dje_license-key is present, a new dje_license_url will be
        reported when fetching data from the DejaCode API.
      * In genabout, the '--all_in_one' command line option has been removed.
        It was not well specified and did not work as advertised.

    * in genattrib:

      * the Component List is now optional.
      * there is a new experimental '--verification_location' command line
        option.  This option will be removed in the future version. Do not use
        it.
    * the '+' character is now supported in file names.
    * several bugs have been fixed.
    * error handling and error and warning reporting have been improved.
    * New documentation in doc: UsingAboutCodetoDocumentYourSoftwareAssets.pdf


2014-11-05  Philippe Ombredanne <pombredanne@nexb.com>

    Release 1.0.2

    * Minor bug fixes and improved error reporting.


2014-11-03  Philippe Ombredanne <pombredanne@nexb.com>

    Release 1.0.1

    * Minor bug fixes, such as extraneous debug printouts.


2014-10-31  Philippe Ombredanne <pombredanne@nexb.com>

    Release 1.0.0

    * Some changes in the spec, such as supporting only text in external 
       files.
    * Several refinements including support for common licenses.

2014-06-24  Chin-Yeung Li  <tli@nexb.com>

    Release 0.8.1

    * Initial release with minimal capabilities to read and validate 
      ABOUT files format 0.8.0 and output a CSV inventory.
