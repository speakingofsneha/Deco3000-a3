#!/usr/bin/env python3
"""
setup script for reframe
"""

from setuptools import setup, find_packages

# read the readme file for the long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# read requirements from requirements.txt, skip comments and empty lines
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# configure the package setup
setup(
    name="reframe",
    version="2.3.0 ?",
    author="alyssa & sneha",
    author_email="-",
    description="Convert student visual reports into ux case studies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="-",
    # automatically find all packages in the project
    packages=find_packages(),
    # package metadata for pypi
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    # install all the dependencies from requirements.txt
    install_requires=requirements,
)