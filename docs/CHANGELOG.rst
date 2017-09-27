2017-xx-xx  xxxxx

    Release 3.0.0

    ABOUT files is now YAML formatted.
    Supported license expression.
    Supported JSON input and output format: https://github.com/nexB/aboutcode-toolkit/issues/246 and https://github.com/nexB/aboutcode-toolkit/issues/277
    Support Python 3: https://github.com/nexB/aboutcode-toolkit/issues/280
    Refined help texts
    Refined USAGE texts
    Refined SPECs

    Input key changes:
    ==================
    `about_file` is replaced by `about_file_path`
    `dje_license_key` is replaced by `license_expression`
    `version` is no longer a required field

    API Updated:
    ============
     - Break down the 3 major functions: `inventory`, `genabout` and `genattrib` into 3 subcommands:
        i.e.
        `about inventory`, `about generate` and `about attrib`

     - A new `check` subcommand: https://github.com/nexB/aboutcode-toolkit/issues/281

     - Some options changes
        `--extract_license` becomes `--fetch-license`
        `--license_text_location` becomes `--license-notice-text-location`

    etc...


2016-06-27  Chin-Yeung Li  <tli@nexb.com>

    Release 2.3.2

    * Documentation updates


2016-03-29  Philippe Ombredanne <pombredanne@nexb.com>

    Release 2.3.1

    * Various minor bug fixes and improvements
    * Support for the latest DejaCode API if you use DejaCode


2016-03-28  Philippe Ombredanne <pombredanne@nexb.com>

    Release 2.3.0

    * Various minor bug fixes and improvements
    * Support for the latest DejaCode API if you use DejaCode


2015-10-23  Chin-Yeung Li  <tli@nexb.com>

    Release 2.2.0

    * Improved CLI error messages
    * Fixed the filtering of dicts with empty values.
    * Refined help texts
    * Updated configure script
    * Refactorings and code simplifications
    * Fixed misleading error message when using invalid api_url


2015-10-09  Chin-Yeung Li  <tli@nexb.com>

    Release 2.1.0

    * Minor code refactoring
    * Handle long path error on Windows OS when using genattrib with a zip


2015-09-29  Chin-Yeung Li  <tli@nexb.com>

    Release 2.0.4

    * Added support to run genattrib with a zip file and tests
    * Display a "Completed" message once the generation is completed


2015-08-01  Chin-Yeung Li  <tli@nexb.com>

    Release 2.0.3

    * Fix the bug of using genattrib.py on Windows OS
    * Display version when running about.py, genabout.py and genattrib.py


2015-07-07  Chin-Yeung Li  <tli@nexb.com>

    Release 2.0.2

    * Handle input's encoding issues
    * Better error handling
    * Writing to and reading from Windows OS with paths > 255 chars


2015-06-09  Chin-Yeung Li  <tli@nexb.com>

    Release 2.0.1

    * Configuration script fixes and updates basic documentation.


2015-05-05  Chin-Yeung Li  <tli@nexb.com>

    Release 2.0.0

    * Breaking API changes:

      * the dje_license field has been renamed to dje_license_key
      * when a dje_license_key is present, a new dje_license_url will be
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
