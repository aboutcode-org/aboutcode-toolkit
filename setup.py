#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
    name='AboutCode',
    version='3.0.0.dev3',
    license='Apache-2.0',
    description=('Document the provenance (origin and license) of '
                 'third-party software using small text files. '
                 'Collect inventories, generate attribution documentation.'),
    long_description=('AboutCode provides a simple way to document the'
        'provenance (i.e. origin and license) of software components that'
        'you use in your project. This documentation is stored in *.ABOUT'
        'files, side-by-side with the documented code.'),
    author='Jillian Daguil, Thomas Druez, Chin-Yeung Li, Philippe Ombredanne and others.',
    author_email='info@nexb.com',
    url='http://dejacode.org',
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
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'Topic :: Software Development :: Documentation',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: System :: Software Distribution',
        'Topic :: Utilities',
    ],
    keywords=[
        'license', 'about', 'metadata', 'package', 'copyright', 'attribution', 'software', 'inventory',
    ],
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

    entry_points='''
        [console_scripts]
        about-code=abouttool.cmd:cli
    ''',
    install_requires=[
        'jinja2 >= 2.7.3, < 2.8',
        'click >= 3.2, < 4',
        'unicodecsv >= 0.9.4,  < 1.0',
        'schematics >= 1.0-0, <2.0',
        'pyyaml >= 3.11, < 3.13',
     ],

    extras_require={
        'base': [
            'certifi',
            'setuptools',
            'wheel',
            'pip',
            'wincertstore',
        ],
        'dev': [
            'pytest',
            'py',
        ],
    }
)
