#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from setuptools import setup, find_packages

import about_code_tool


setup(
    name='AboutCode',
    version=about_code_tool.__version__,
    description=('Document the provenance (origin and license) of '
                 'third-party software using small text files. '
                 'Collect inventories, generate attribution documentation.'),

    author='Jillian Daguil, Thomas Druez, Chin-Yeung Li, Philippe Ombredanne and others.',

    author_email='info@nexb.com',

    url='http://dejacode.org',

    long_description=('AboutCode provides a simple way to document the'
        'provenance (i.e. origin and license) of software components that'
        'you use in your project. This documentation is stored in *.ABOUT'
        'files, side-by-side with the documented code.'),

    license='Apache-2.0',
    packages=find_packages(),
    include_package_data=True,

    data_files=[('about',
        [
            'about.ABOUT',
            'about.bat',
            'about',
            'configure.bat',
            'configure',
            'about.cfg',
            'README.rst',
            'apache-2.0.LICENSE',
            'NOTICE',
            'SPEC',
            'USAGE.rst',
        ]),
    ],

    zip_safe=False,
    entry_points='''
        [console_scripts]
        about-code=about_code_tool.cmd:cli
    ''',
    install_requires=[
        'jinja2 >= 2.7.3',
        'click >= 3.2',
        'unicodecsv >= 0.9.4',
        'schematics >= 1.0-0',
        'pyyaml >= 3.11',
     ],

    test_suite='about_code_tool.tests',
    platforms='any',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Topic :: Software Development',
        'Topic :: Software Development :: Documentation',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: System :: Software Distribution',
        'Topic :: Utilities',
    ],
)
