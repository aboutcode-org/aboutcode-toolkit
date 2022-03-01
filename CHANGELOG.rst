2022-03-01
    Release 7.0.0

    * Add '@' as a supported character for filename #451
    * Add support to collect redistributable sources #22
    * Handle trailing spaces in field names during `transform` #456
    * Remove restriction of python27 only on windows #453
    * Documentation updated
    * Code enhancement
    * Remove thirdparty/
    * Update configuration scripts
    * Use readthedocs for documentation
    * Add Dockerfile to run aboutcode with docker
    * Add new option to choose extract license from ScanCode LicenseDB or DJC License Library
    * Add ability to transform XLSX file 
    * Support XLSX file format for `inventory`, `gen` and `attrib`
    * Add 'spdx_license_key' support
    * Add option to save error log in `check` command
    * New `gen_license` option
    * Bump PyYAML to 6.0
    * Add '%" as a supported character
    * Update default template
    * All errors are logged if and only if the `verbose` option is set. Otherwise, ony 'Critical' and 'Warning' errors will be showed/logged
    * Ability to generate attribution notice directly from an input inventory
    * Remove the restriction of requiring 'about_resource' field in the input if performing `attrib` from an inventory

2021-04-02
    Release 6.0.0

    * This new release has no feature changes.
    * It has relaxed PyYAML dependencies and drop Python 2 support

2020-09-01
    Release 5.1.0

    * Add support for `package_url` #396
    * Fixed #443 and #444 issue with multiple licenses/license_files
    * Fixed #442 no special characters allowed for `license_key`, `license_name` and `license_expression`
    * Fixed #446 Better error handling

2020-08-11
    Release 5.0.0

	* Enhance the `transform` to also work with JSON file
    * Update transform code (See #427 and #428)
    * Fixed #431 - Error handling for empty "_file" fields
    * Fixed #432 - Handled UTF-8 variant invented by Microsoft
    * Fixed #433 - problem was caused by the different multi-lic file format between json and CSV (CSV with '\n' line break)
    * Fixed #436 - issue about copy with the `--reference` option
    * Fixed #396 - support for alternative output for Android

2020-05-05
    Release 4.0.2

    * Upgrade license-expression library to v1.2
    * Fix the missing `multi_sort` filter for Jinja2
    * Update help text for `--vartext`

2019-10-17
    Release 4.0.1

    * Declare to follow SemVer for versioning schema
    * Update REFERENCE.rst and README.rst
    * Update license-expression library


2019-10-09

    Release 4.0.0

    * Support filenames/path with special characters #310 #378 #392
    * Update ABOUT file format to match the specification
    * Log version of which AbcTK was used #397
    * Fix the licenses (key, name, file) not in sync issue #406
    * Correct invalid msg for boolean fields #403
    * Remove the `about_file_path` key/column from input/output #364
    * Use ',' to support multiple files #404
    * Fix bugs in `transform` #408, #412

2018-11-15

    Release 3.3.0

    * Update the list of common license keys
    * New UrlListField introduced for list of urls
    * The UrlField is now only taking single URL value
    * The owner is now a StringField instead of ListField
    * Format the ordering of the generated ABOUT file (See https://github.com/nexB/aboutcode-toolkit/issues/349#issuecomment-438871444)
    * '+' and '(' and ')' is now supported in license_expression
    * The key 'about_resource_path' is removed
    * Revert back the requirement of the 'name' field
    * Add a new supported 'internal_use_only' key

2018-10-23

    Release 3.2.2

    * Fix the version number
    * `name` field is no longer a required field

2018-10-22

    Release 3.2.1

    * The 'license' field is now become 'license_key'
    * Multiple licenses support
    * No support for referenceing multuiple resources
    * Fix the incorrect boolean field behaviors
    * Display number of errors/warnings in the error log

2018-09-19

    Release 3.1.3

    * Minor update

2018-09-19

    Release 3.1.2

    * New `--vartext` option for `attrib`
    * Add support for `checksum_sha256` and `author_file`
    * `check` command will not count INFO message as error when `--verbose` is set
    * Update `track_change` to `track_changes`
    * New `--filter` and `--mapping-output` options for `inventory`

2018-6-25

    Release 3.1.1

    * No support of multiple occurrence keys in the input
    * Updated the specification document
    * Fixed bug that cause template processing error in attrib

    etc...


2018-6-8  Chin-Yeung Li  <tli@nexb.com>

    Release 3.1.0

    * Fixed JSON input from AboutCode manger export and ScanCode output
    * Added a new option `mapping-file` to support using a custom file for mapping 
    * Change the name of the option `--show-all` to `--verbose`
    * Better error handling for copying file with permission issue
    * Support timestamp in attribution output

    etc...


2017-11-17  Chin-Yeung Li  <tli@nexb.com>

    Release 3.0.*

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
    `home_url` is now `homepage_url`

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
