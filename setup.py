#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

from glob import glob
import io
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

from setuptools import find_packages
from setuptools import setup


def read(*names, **kwargs):
    return io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ).read()


setup(
    name='aboutcode-toolkit',
    version='3.3.0',
    license='Apache-2.0',
    description=(
        'AboutCode-toolkit is a tool to document the provenance (origin and license) of '
        'third-party software using small text files. '
        'Collect inventories, generate attribution documentation.'
    ),
    long_description=(
        'AttributeCode provides a simple way to document the'
        'provenance (i.e. origin and license) of software components that'
        'you use in your project. This documentation is stored in *.ABOUT'
        'files, side-by-side with the documented code.'
    ),
    author='Chin-Yeung Li, Jillian Daguil, Thomas Druez, Philippe Ombredanne and others.',
    author_email='info@nexb.com',
    url='http://aboutcode.org',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Software Development',
        'Topic :: Software Development :: Documentation',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: System :: Software Distribution',
        'Topic :: Utilities',
    ],
    keywords=[
        'license', 'about', 'metadata', 'package', 'copyright',
        'attribution', 'software', 'inventory',
    ],
    install_requires=[
        'jinja2 >= 2.9, < 3.0',
        'click >= 6.7, < 7.0',
        "backports.csv ; python_version<'3.6'",
        'PyYAML >= 3.0, < 4.0',
        'boolean.py >= 3.5, < 4.0',
        'license_expression >= 0.94, < 1.0',
    ],
    extras_require={
        ":python_version < '3.6'": ['backports.csv'],
    },
    entry_points={
        'console_scripts': [
            'about=attributecode.cmd:cli',
        ]
    },
)
