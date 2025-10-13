#!/usr/bin/env python3
"""
Setup script for Docker Compose CLI tool
"""

from setuptools import setup, find_packages

setup(
    name="docker-compose-cli",
    version="1.0.0",
    description="Multi-Student Docker Compose Management Tool",
    author="Docker Compose CLI Team",
    packages=find_packages(),
    install_requires=[
        "cryptography>=41.0.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        'console_scripts': [
            'docker-compose-cli=cli:main',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)