.. _type_of_errors:

==============
Type of Errors 
==============

We have 6 type of errors as describe below:

NOTSET
======

Trigger:
--------

    * None

Details
^^^^^^^

    We do not have event to trigger this error.


DEBUG
=====

Trigger:
--------

    * None

Details
^^^^^^^

    We do not have event to trigger this error.


INFO
====

Trigger:
--------

    * `about_resource` not found
    * Custom fields detected
    * Empty field value


WARNING
=======

Trigger:
--------

    * Duplicated value being ignored
    * Invalid Package URL from input
    * Invalid URL from input


ERROR
=====

Trigger:
--------

    * Invalid license
    * Invalid API call
    * Invalid character
    * Invalid input
    * Duplicated field name
    * Incorrect input format
    * Failure to write ABOUT file
    * Network problem


CRITICAL
========

Trigger:
--------

    * Invalid template
    * File field not found
    * Duplicated `about_resource`
    * Not supported field format
    * Essential or required field not found
    * Internal error
    * Empty ABOUT file
    * Invalid ABOUT file


.. note::
   If `--verbose` is set, all the detected errors will be reported.
   Otherwise, only "CRITICAL", "ERROR" and 'WARNING" will be reported. 