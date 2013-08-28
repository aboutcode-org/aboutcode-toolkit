#!/usr/bin/env python
from setuptools import setup

setup(
    name="about-code-tool",
    version="0.8.1",
    description="Document the origin of third-party software.",
    author="Jillian Daguil, Chin Yeung Li, Philippe Ombredanne, Thomas Druez",
    author_email="info@nexb.com",
    url="http://dejacode.org",
    long_description="""The ABOUT tool and ABOUT files provide a simple way
    to document the provenance (origin and license) and other important or
    interesting information about third-party software components that you use
    in your project.""",
    license='Apache License 2.0',
    py_modules=['about', 'genabout'],
    zip_safe=False
)
