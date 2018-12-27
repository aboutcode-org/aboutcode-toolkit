ABOUT File Specification v4.0


Purpose
~~~~~~~

An ABOUT file provides a simple way to document the provenance (e.g. origin and
license) and other important or interesting information about a software
package. An ABOUT file is a small text file stored in the codebase side-by-side
with the software package file or archive that it documents. No modification of
the documented software is needed.

The ABOUT file format is plain text using the YAML format e.g. "name: value"
pairs separated by a colon. It is easy to read and create by hand and is
designed first for processing by humans, rather than by machines. The format is
well-defined and structured just enough to make it easy to process with software
as well.  An ABOUT file contains enough information to fulfill key license
requirements such as creating credits or attribution notices, collecting
redistributable source code, or providing information about new versions of a
software package.


Getting Started
~~~~~~~~~~~~~~~

A simple and valid ABOUT file named httpd.ABOUT looks like this::

        about_resource: httpd-2.4.3.tar.gz
        name: Apache HTTP Server
        version: 2.4.3
        homepage_url: http://httpd.apache.org
        download_url: http://archive.apache.org/dist/httpd/httpd-2.4.3.tar.gz
        license_expression: apache-2.0
        licenses:
            - key: apache-2.0
            - file: apache-2.0.LICENSE
        notice_file: httpd.NOTICE
        copyright: Copyright (c) 2012 The Apache Software Foundation.

The meaning of this ABOUT file is:

- The file "httpd-2.4.3.tar.gz" is stored in the same directory and side-by-side
  with the ABOUT file "httpd.ABOUT" that documents it.

- The name of this package is "Apache HTTP Server" with version "2.4.3".

- The home URL for this package is http://httpd.apache.org

- The file "httpd-2.4.3.tar.gz" was originally downloaded from
  http://archive.apache.org/dist/httpd/httpd-2.4.3.tar.gz

- This package is licensed under the "apache-2.0" license.

- In the same directory, "apache-2.0.LICENSE" and "httpd.NOTICE" are files that
  contain respectively the license text and the notice text for this package.


Specification
~~~~~~~~~~~~~

ABOUT file name
~~~~~~~~~~~~~~~

An ABOUT file name is suffixed with a ".ABOUT" extension (This extension can use
any combination of uppercase and lowercase characters)

An ABOUT file name can contain only these US-ASCII characters:

- digits from 0 to 9
- uppercase and lowercase letters from A to Z
- the "_" underscore, "-" dash and "." period signs.

- The case of a file name is not significant. On case-sensitive file systems
  (such as on Linux), a tool must report an error if two ABOUT files stored in
  the same directory have the same lowercase file name. This is to ensure that
  ABOUT files can be used across file systems. The convention is to use a
  lowercase file name and an uppercase ABOUT extension.


YAML format, UTF-encoded text
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An ABOUT file contains text using the YAML format. The textmust be UTF-8-encoded.
The YAML style to use is always the block style and never the JSON-like flow
style. When creating ABOUT files, tools must emit YAML in block style.
An ABOUT file can contain only a single YAML document.  This document must be a
YAML mapping of field/values. Lines that start with "#" pound sign must be
ignored and treated as comments.


Line ending
~~~~~~~~~~~

The standard line ending is the LF character. The line ending characters
can be any LF, CR or CR/LF and tools must normalize line endings to LF when
parsing an ABOUT file. When creating ABOUT files, tools must emit LF line
endings.


Field names
~~~~~~~~~~~

A field name can contain only these US-ASCII characters and no space. It must
start with a letter:

- lowercase letters from A to Z
- digits from 0 to 9
- the "_" underscore sign.


Field values
~~~~~~~~~~~~

Leading and trailing white spaces in values must be ignored.

A field value is either:

- a string of one or lines of text.
- a list where each item is prefixed with a "-" dash
- a mapping of field name: value where the field name and value are separated
  by ": " a colon and a space.

When a field string value contains more than one line of text, continuing lines
must start with one or more spaces.

For instance::

    description: This is a long description for a software package that spans
        multiple lines with arbitrary line breaks.


Fields are mandatory or optional
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A field can be mandatory or optional. Tools must report an error for missing
mandatory fields. There is only one mandatory field for now: "about_resource"


Fields validation
~~~~~~~~~~~~~~~~~

When processing an ABOUT file, tools must report a warning or error if a field
is invalid. A field can be invalid for several reasons, such as invalid field
name or an invalid content. Tools should report additional validation error
details. The validation process should check that each field name is
syntactically correct and that fields contain correct values according to its
concise, common sense definition in this specification. For certain fields,
additional and specific validations are relevant such as checksum verification,
URL validation, path resolution and verification, etc. can be done optionally.
Tools should report an info for custom fields.

Multiple occurrences of a field name is an error.

The field order does not matter. Tools should emit ABOUT files using a well
defined order that promotes readability and makes text diffing easier.


Custom fields
~~~~~~~~~~~~~

A custom field is a field with a name that is not defined in this specification.
These fields must be processed by tools as any other fields but are not subject
to content validation.


Field referencing a file
~~~~~~~~~~~~~~~~~~~~~~~~

Certain fields reference a file path such "about_resource", or fields pointing
to a notice file or a license text file.  In these case, the path must be a
POSIX path (using a slash "/" as path segments separator) and be relative to the
path of the ABOUT file. 

For notice and license text files, the content must be UTF-8-encoded text. As a
(non-mandatory) convention, the notice files use a .NOTICE file extension and
the license file use a .LICENSE file extension.

For example, here the license text is stored in a separate file named
gpl-2.0.LICENSE::

    licenses:
        - key: gpl-2.0
        - file: gpl-2.0.LICENSE

In this example, the NOTICE file is stored in a "docs" sub-directory.
Note the usage of the POSIX path syntax::

    notice_file: docs/NOTICE


Field referencing a URL
~~~~~~~~~~~~~~~~~~~~~~~

Some fields contain a URL such as a homepage URL or a download URL. These are
purely informational. URL field names are suffixed with "_url" and the field
value must be a valid absolute URL.


Flag fields
~~~~~~~~~~~

Some fields are flags with either a true or false value.

- "True", "T", "Yes", "Y"  or "x" in any case combination must be interpreted as
  a "true" value.
- "False", "F", "No", "N" in any case combination or the absence of a value must
  be interpreted as "false".


Referencing the file or directory documented by an ABOUT file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An ABOUT file documents one file or directory. The mandatory "about_resource"
field reference the documented file or directory. The value of the
"about_resource" field is the name or path of the referenced file or directory
relative to the ABOUT file location.

A tool processing an ABOUT file must report an error if this field is missing.

By convention, an ABOUT file is stored side-by-side to the file or directory
that it documents. This is not mandatory but a very common convention.

For example, a file named django.ABOUT contains the following field to document
the django-1.2.3.tar.gz archive stored in the same directory::

      about_resource: django-1.2.3.tar.gz

In this example, an ABOUT file documents a whole linux-kernel-2.6.23 directory::

      about_resource: linux-kernel-2.6.23

In this example, the ABOUT file documents all the files in the directory where
it is stored, using "." (period) as its "about_resource" value::

      about_resource: .



Optional Information fields
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- spec_version: The version of the ABOUT file format specification used for this
  file. This is provided as a hint to readers and tools in order to support
  future versions of this specification.

- name: Package name.

- version: Package version. A package usually has a version, such as a "1.2.6"
  or a revision number or hash from a version control system. 
  If not available, the version could be the date the packages was created or
  fetched in an ISO date format such as'YYYY-MM-DD'.

- description: Package description text.

- download_url: A direct URL to download the package file or archive documented
  by this ABOUT file.

- homepage_url: URL to the homepage for this package.

- changelog_file: Changelog file for the package.

- notes: Notes and comments about the package.

- vcs_url: a VCS URL as defined in the SPDX specification. For example::

      vcs_url: git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git@b59958d90b3e75a3b66cd31

- md5: MD5 for the file in the "download_url" field.

- sha1: SHA1 for the file in the "download_url" field.

- sha256: SHA256 for the file in the "download_url" field.

- sha512: SHA512 for the file in the "download_url" field.

All the checksums above are hex-encoded strings and computed as in the GNU tools.
For example::

      md5: f30b9c173b1f19cf42ffa44f78e4b96c


Optional Licensing fields
~~~~~~~~~~~~~~~~~~~~~~~~~

- copyright: Copyright statement for the package.

- notice_file: Legal notice or credits file for the package.
- notice_url: URL to the notice for this package.

- license_expression: The license expression that apply to the package. The
  syntax is the SPDX license expression synatx but the license keys should be
  ScanCode or DEjaCode license keys.

- licenses: a list of name/value pairs for each license key in the
  license_expression field.
    - key: A license key
    - name: Short name for this license key.
    - url: URL to the license text for this license key.
    - file: Path to a file that contains the full text of this license.

- redistribute: flag set to "yes" if the license requires source code redistribution.

- attribute: flag set to "yes" if the license requires publishing an attribution
  or credit notice.

- track_changes: flag set to "yes" if the license requires tracking changes
  made to a the package.

- modified: flag set to yes if the package has been modified.

- internal_use_only: flag set to yes if the package is for internal use only.

- changelog_file: Path to a file that contains the log of changes made to this package.


Optional Owner and Author fields
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- owner: The name of the primary organization or person(s) that owns or provides
  the package.

- owner_url: URL to the homepage for the owner.

- contact: Contact information (such as an email address or physical address)
  for the package owner.

- author: Name of the organization(s) or person(s) that authored the package.
