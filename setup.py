#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from setuptools import setup

from about_code_tool import about


setup(
    name="about-code-tool",
    version=about.__version__,
    description="Document the origin of third-party software.",
    author="Jillian Daguil, Chin Yeung Li, Philippe Ombredanne, Thomas Druez",
    author_email="info@nexb.com",
    url="http://dejacode.org",
    long_description="""The ABOUT tool and ABOUT files provide a simple way
    to document the provenance (origin and license) and other important or
    interesting information about third-party software components that you use
    in your project.""",
    license='Apache License 2.0',
    packages=[
        'about_code_tool',
        'about_code_tool.tests'
    ],
    package_data={
        'about_code_tool': ['templates/*'],
    },
    include_package_data=True,
    zip_safe=False,
    test_suite='about_code_tool.tests',
    platforms='any',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
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
