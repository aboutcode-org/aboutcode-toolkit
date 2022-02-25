.. _general:

=======
General
=======

AboutCode Toolkit Defined
=========================

AboutCode Toolkit is a tool for your software development team to document your code inside your codebase, typically in preparation for a product release, side-by-side with the actual code. ABOUT file(s) have a simple, standard format that identifies components and their associated licenses. The current AboutCode Toolkit subcommands are:

-   **attrib**: Generate a Product Attribution notice document from your ABOUT file(s), JSON, CSV or XLSX. You can also generate documents for other purposes (such as a License Reference) by varying your input control file and your template.

-   **check**: A simple command to validate the ABOUT file(s) and output errors/warnings on the terminal.

-   **collect_redist_src**: A command to collect and copy sources that have the 'redistribute' flagged as 'True' in ABOUT file(s) or from an inventory.

-   **gen**: Create ABOUT file(s) from a Software Inventory file (.csv, .json or .xlsx format) which is typically created from a software audit, and insert these AboutCode Toolkit files into your codebase. You can regenerate the AboutCode Toolkit files from a new Software Inventory file whenever you make changes.

-   **gen_license**: Fetch licenses in the license_expression field and save to the output location.

-   **inventory**: Generate a Software Inventory list (.csv, .json or .xlsx format) from your codebase based on ABOUT file(s). Note that this Software Inventory will only include components that have AboutCode Toolkit data. In another word, if you do not create AboutCode Toolkit files for your own original software components, these components will not show up in the generated inventory.

-   **transform**: A command to transform an input CSV/JSON/XLSX by applying renaming and/or filtering and then output to a new CSV/JSON/XLSX file.

Additional AboutCode Toolkit information is available at:

- See :ref:`specification` for an overview and a link to the ABOUT File specification.

- https://github.com/nexB/aboutcode-toolkit/ for the AboutCode Toolkit tools.

Key Terminology
===============
Some key terminology that applies to AboutCode Toolkit tool usage:

-   **Software Inventory or Inventory** - means a list of all of the components in a Development codebase and the associated data about those components with a focus on software pedigree/provenance- related data for open source and third-party components.

-   **Product BOM or BOM** - means a subset list of the components in a Development codebase (Software Inventory) that are Deployed on a particular Product Release (a Product Bill of Materials).

Using gen to Generate ABOUT file(s)
===================================

Prepare Your Software Inventory for gen Standard Field Names
------------------------------------------------------------

You should start with a software inventory of your codebase in spreadsheet or JSON format. You need to prepare a version of it that will identify the field values that you want to appear in your .ABOUT files. Note the following standard field names (defined in the ABOUT File Specification), which gen will use to look for the values that it will store in your generated .ABOUT files, as well as any additional text files that you identify, which it will copy and store next to the .ABOUT files.

.. list-table::
    :widths: 10 45 45
    :header-rows: 1

    * - Standard Field Name
      - Description
      - Notes
    * - about_resource
      - Name/path of the component resource
      - Mandatory
    * - name
      - Component name
      - Mandatory
    * - version
      - Component version
      - Optional
    * - download_url
      - Direct URL to download the original file or archive documented by this ABOUT file
      - Optional
    * - description
      - Component description
      - Optional
    * - homepage_url
      - URL to the homepage for this component
      - Optional
    * - package_url
      - Package URL for this component (See https://github.com/package-url/purl-spec for SPEC)
      - Optional
    * - notes
      - notes text
      - Optional
    * - license_expression
      - Expression for the license of the component using ScanCode license key(s).
      - Optional. You can separate each identifier using " OR " and " AND " to document the relationship between multiple license identifiers, such as a choice among multiple licenses.
    * - license_key
      - ScanCode license key for the component.
      - Optional. gen will obtain license information from ScanCode LicenseDB or DejaCode Enterprise if the --fetch-license or --fetch-license-djc option is set, including the license text, in order to create and write the appropriate .LICENSE file in the .ABOUT file target directory.
    * - license_name
      - License name for the component.
      - Optional. This field will be generated if the --fetch-license or --fetch-license-djc option is set.
    * - license file
      - license file name   
      - Optional. gen will look for the file name (if a directory is specified in the --reference option) to copy that file to the .ABOUT file target directory.
    * - license_url 
      - URL to the license text for the component
      - Optional
    * - spdx_license_key 
      - The ScanCode LicenseDB spdx_license_key defined for the license at https://scancode-licensedb.aboutcode.org/index.html
      - Optional
    * - copyright
      - copyright statement for the component
      - Optional
    * - notice_file
      - notice text file name
      - Optional
    * - notice_url
      - URL to the notice text for the component
      - Optional
    * - redistribute
      - Yes/No. Does the component license require source redistribution.
      - Optional
    * - attribute
      - Yes/No. Does the component license require publishing an attribution or credit notice.
      - Optional
    * - track_changes
      - Yes/No. Does the component license require tracking changes made to the component.
      - Optional
    * - modified
      - Yes/No. Have the component been modified.
      - Optional
    * - internal_use_only
      - Yes/No. Is the component internal use only.
      - Optional
    * - changelog_file
      - changelog text file name
      - Optional
    * - owner
      - name of the organization or person that owns or provides the component
      - Optional
    * - owner_url
      - URL to the owner for the component
      - Optional
    * - contact
      - Contact information
      - Optional
    * - author
      - author of the component
      - Optional
    * - author_file
      - author text file name
      - Optional
    * - vcs_tool
      - Name of the version control tool.
      - Optional
    * - vcs_repository
      - Name of the version control repository.
      - Optional
    * - vcs_path
      - Name of the version control path.
      - Optional
    * - vcs_tag
      - Name of the version control tag.
      - Optional
    * - vcs_branch
      - Name of the version control branch.
      - Optional
    * - vcs_revision
      - Name of the version control revision.
      - Optional
    * - checksum_md5
      - MD5 value for the file
      - Optional
    * - checksum_sha1
      - SHA1 value for the file
      - Optional
    * - checksum_sha256
      - SHA256 value for the file
      - Optional
    * - spec_version
      - The version of the ABOUT file format specification used for this file.
      - Optional


Fields Renaming and Optional Custom Fields
------------------------------------------

Since your input's field name may not match with the AboutCode Toolkit standard field name, you can use the transform subcommand to do the transformation.

A transform configuration file is used to describe which transformations and validations to apply to a source CSV/JSON/XLSX file. This is a simple text file using YAML format, using the same format as an .ABOUT file.

The attributes that can be set in a configuration file are:

-   field_renamings: An optional map of source field name to target new field name that is used to rename CSV/JSON/XLSX fields.

        ..  code-block:: none

            field_renamings:
                about_resource : 'Directory/Location'
                bar : foo


The renaming is always applied first before other transforms and checks. All other field names referenced below are AFTER the renaming have been applied.
For instance with this configuration, the field "Directory/Location" will be renamed to "about_resource" and "foo" to "bar":

-   required_fields: An optional list of required field names that must have a value, beyond the standard field names. If a source CSV/JSON/XLSX does not have such a field or an entry is missing a value for a required field, an error is reported.

For instance with this configuration, an error will be reported if the fields "name" and "version" are missing, or if any entry does not have a value set for these fields:

        ..  code-block:: none

            required_fields:
                - name
                - version

-   field_filters: An optional list of fields that should be kept in the transformed file. If this list is provided, only the fields that are in the list will be kept. All others will be filtered out even if they are AboutCode Toolkit standard fields. If this list is not provided, all source fields are kept in the transformed target file.

For instance with this configuration, the target file will only contains the "name" and "version" fields:

        ..  code-block:: none

            field_filters:
                - name
                - version

-   exclude_fields: An optional list of field names that should be excluded in the transformed file. If this list is provided, all the fields from the source file that should be excluded in the target file must be listed. Excluding required fields will cause an error. If this list is not provided, all source fields are kept in the transformed target file.

For instance with this configuration, the target file will not contain the "type" and "temp" fields:

        ..  code-block:: none

            exclude_fields:
                - type
                - temp

Run gen to Generate ABOUT file(s)
---------------------------------

When your software inventory is ready, you can save it as a .csv, .json or .xlsx file, and use it as input to run gen to generate ABOUT file(s). The official gen parameters are defined here: :ref:`reference`

Here is an example of a gen command:

        ..  code-block:: none

                about gen --fetch-license --reference /Users/harrypotter/myLicenseNoticeFiles/ /Users/harrypotter/myAboutFiles/myProject-bom.csv /Users/harrypotter/myAboutFiles/

This gen example command does the following:

-   Activates the --fetch-license option to get license information from ScanCode LicenseDB.

-   Activates the --reference option to get license text files and notice text files that you have specified in your software inventory to be copied next to the associated .ABOUT files when those are created.

-   Specifies the path of the software inventory to control the processing.

-   Specifies a target output directory.

Review the generated ABOUT file(s) to determine if it meets your requirements. Here is a simple example of a linux-redhat-7.2.ABOUT file that documents the directory /linux-redhat-7.2/ :

        ..  code-block:: none

                about_resource: .
                name: Linux RedHat
                version: v 7.2
                attribute: Y
                copyright: Copyright (c) RedHat, Inc.
                license_expression: gpl-2.0
                licenses:
                    -   key: gpl-2.0
                        name: GPL 2.0
                        file: gpl-2.0.LICENSE
                        url: https://scancode-licensedb.aboutcode.org/gpl-2.0.LICENSE
                        spdx_license_key: GPL-2.0-only
                owner: Red Hat
                redistribute: Y

You can make appropriate changes to your input software inventory and then run gen as often as necessary to replace the ABOUT file(s) with the improved version.

Using attrib to Generate a Product Attribution Notice Package
=============================================================

Prepare an Attribution Template to Use
--------------------------------------

You can run attrib using the default_html.template (or default_json.template) provided with the AboutCode Toolkit tools:

https://github.com/nexB/aboutcode-toolkit/blob/develop/templates/default_html.template

If you choose to do that, you will most likely want to edit the generated .html file to provide header information about your own organization and product.

Running attrib with the default_html.template file is probably your best choice when you are still testing your AboutCode Toolkit process. Once you have a good understanding of the generated output, you can customize the template to provide the standard text that serve your needs. You can also create alternative versions of the template to use attrib to generate other kinds of documents, such as a License Reference.

Use jinja2 Features to Customize Your Attribution Template
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The attrib tool makes use of the open source python library jinja2 (http://jinja.pocoo.org/docs/dev/templates/) in order to extend .html capabilities and transform AboutCode Toolkit input data into the final format of the generated attribution file. The ``default_html.template`` file contains text that complies with jinja2 syntax specifications in order to support grouping, ordering, formatting and presentation of your AboutCode Toolkit data. If your attribution requirements are complex, you may wish to study the jinja2 documentation to modify the default_html.template logic or create your own template; alternatively, here are a few relatively simple concepts that relate to the attribution document domain.

The simplest modifications to the default_html.template file involve the labels and standard text. For example, here is the default template text for the Table of Contents:

        ..  code-block:: none

                <div class="oss-table-of-contents">
                    {% for about_object in abouts %}
                        <p><a href="#component_{{ loop.index0 }}">{{ about_object.name.value }}
                        {% if about_object.version.value %} {{ about_object.version.value }}
                        {% endif %}</a></p>
                    {% endfor %}
                </div>

If you would prefer something other than a simple space between the component name and the component version, you can modify it to something like this:

        ..  code-block:: none

                <div class="oss-table-of-contents">
                    {% for about_object in abouts %}
                        <p><a href="#component_{{ loop.index0 }}">{{ about_object.name.value }}
                        {% if about_object.version.value %}  - Version  {{ about_object.version.value }}
                        {% endif %}</a></p>
                    {% endfor %}
                </div>

The ``if about_object.version.value`` is checking for a component version, and if one exists it generates output text that is either a space followed by the actual version value, or, as in this customized template, it generates output text as " - Version ", followed by the actual version value. You will, of course, want to test your output to get exactly the results that you need.

Note that you can actually use attrib to generate an AboutCode Toolkit-sourced document of any kind for varying business purposes, and you may want to change the grouping/ordering of the data for different reporting purposes. (Here we get into somewhat more complex usage of jinja2 features, and you may wish to consult the jinja2 documentation to reach a more comprehensive understanding of the syntax and features.) The default ordering is by component, but In the following example, which is intended to support a "license reference" rather than an attribution document, the customized template modifies the data grouping to use a custom field called "confirmed_license":

        ..  code-block:: none

                <div class="oss-table-of-contents">
                    {% for group in abouts | groupby('confirmed_license') %}
                    <p>
                        {% for license in group.grouper.value %}
                        <a href="#group_{{ loop.index0 }}">{{ license }}
                        </a>
                        {% endfor %}
                    </p>
                    {% endfor %}
                </div>

After the table of contents, this example customized template continues with the license details using the jinja2 for-loop capabilities. Notice that the variable "group.grouper.value" is actually the license name here, and that “License URL” can be any URL that you have chosen to store in your .ABOUT files:

        ..  code-block:: none

                {% for group in abouts | groupby('confirmed_license') %}
                    {% for confirmed_license in group.grouper.value %}
                
                    <div id="group_{{ loop.index0 }}">
                    <h3>{{ confirmed_license }}</h3>
                    <p>This product contains the following open source software packages licensed under the terms of the license: {{confirmed_license}}</p>
                
                    <div class="oss-component" id="component_{{ loop.index0 }}">
                        {%for about_object in group.list %}         
                            {% if loop.first %}
                                {% if about_object.license_url.value %}
                                    {% for lic_url in about_object.license_url.value %}
                                    <p>License URL: <a href="{{lic_url}}
                                            ">{{lic_url }}</a> </p>
                                    {% endfor %}
                                {% endif %}
                            {% endif %}
                            <li>
                            {{ about_object.name.value }}{% if about_object.version.value %}  - Version  
                            {{ about_object.version.value }}{% endif %}
                            </li>
                            {% if about_object.copyright.value %}<pre>{{about_object.copyright.value}}</pre>{% endif %}
                            {% if loop.last %}
                            <pre>
                            {% for lic_key in about_object.license_file.value %}
                                {{about_object.license_file.value[lic_key]}}
                            {% endfor %}
                            </pre>
                            {% endif %}
                        {% endfor %}
                    </div>
                    <hr>
                    </div>
                    {% endfor %}
                {% endfor %}
                <hr>

In summary, you can start with simple, cosmetic customizations to the default_html.template, and gradually introduce a more complex structure to the attrib output to meet varying business requirements.

Run attrib to Generate a Product Attribution Notice Package
-----------------------------------------------------------

You can then run the attrib to generate your product attribution notice package from the generated ABOUT file(s) or from an inventory (.csv/.json/.xlsx). The official attrib parameters are defined here: :ref:`reference`

Here is an example of a attrib command:

``about attrib --template /Users/harrypotter/myAboutFiles/my_attribution_template_v1.html /Users/harrypotter/myAboutFiles/ /Users/harrypotter/myAboutFiles/myProject-attribution-document.html``

Note that this example attrib command does the following:

-   Activates the --template option to specify a custom output template.

-   Specifies the path of the ABOUT file(s) that use to generate the output attribution.

-   Specifies the full path (include file name) of the output document to be generated.

A successful execution of attrib will create a .html (or .json depends on the template) file that is ready to use to meet your attribution requirements.

Using inventory to Generate a Software Inventory
================================================

Generate a Software Inventory of Your Codebase from ABOUT file(s)
-----------------------------------------------------------------

One of the major features of the ABOUT File specification is that the .ABOUT files are very simple text files that can be created, viewed and edited using any standard text editor. Your software development and maintenance processes may require or encourage your software developers to maintain .ABOUT files and/or associated text files manually. For example, when a developer addresses a software licensing issue with a component, it is appropriate to adjust the associated ABOUT file(s) manually.

If your organization adopts the practice of manually creating and maintaining ABOUT file(s), you can easily re-create your software inventory from your codebase using inventory. The official inventory parameters are defined here: :ref:`reference`

A successful execution of inventory will create a complete software inventory in .csv, .json or .xlsx format based on defined format.



