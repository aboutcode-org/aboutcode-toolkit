#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from setuptools import setup, find_packages

from aboutcode import about


setup(
    name='AboutCode',
    version=about.__version__,
    description=('Document the provenance (origin and license) of '
                'third-party software using small text files. '
                'Collect inventories, generate attribution documentation.'),
    author=('Jillian Daguil, Thomas Druez, Chin-Yeung Li, '
            'Philippe Ombredanne and others.'),
    author_email='info@nexb.com',
    url='http://dejacode.org',

    long_description=('AboutCode provides a simple way to document the'
        'provenance (i.e. origin and license) of software components that'
        'you use in your project. This documentation is stored in *.ABOUT'
        'files, side-by-side with the documented code.'),

    license='Apache License 2.0',
    packages=find_packages(),
    package_data={
        'aboutcode': ['templates/*'],
        'aboutcode': ['tests/testdata/*'],
    },
    include_package_data=True,
    zip_safe=False,

    entry_points='''
        [console_scripts]
        about-code=aboutcode.cmd:cli
    ''',
#     install_requires=[
#         'Jinja2',
#         'MarkuSafe',
#         'click',
#         'jinja2==2.7.3'
#         'MarkupSafe==0.23'
#         'schematics==0.9-5'
#         'unicodecsv==0.9.4'
#         'pytest==2.6.1'
#         'colorama==0.3.1'
#         'py==1.4.23'
#     ],

     test_suite='aboutcode.tests',
#     tests_require=[
#         'pytest',
#         'py',
#         'colorama',
#     ],

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
