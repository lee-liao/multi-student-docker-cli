#!/usr/bin/env python3
"""
Multi-Student Docker Compose CLI Tool - Setup Script
Distribution package setup for the multi-student Docker Compose management system.
"""

from setuptools import setup, find_packages
import os
import sys
from pathlib import Path

# Ensure we're using Python 3.8+
if sys.version_info < (3, 8):
    sys.exit("Python 3.8 or higher is required")

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read version from version file
version_file = this_directory / "VERSION"
if version_file.exists():
    version = version_file.read_text().strip()
else:
    version = "1.0.0"

# Read requirements
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    requirements = requirements_file.read_text().splitlines()
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]
else:
    requirements = []

# Development requirements
dev_requirements = [
    "pytest>=6.0.0",
    "pytest-cov>=2.10.0",
    "black>=21.0.0",
    "flake8>=3.8.0",
    "mypy>=0.800",
    "coverage>=5.0.0",
]

setup(
    name="multi-student-docker-compose",
    version=version,
    author="Multi-Student Docker Compose Team",
    author_email="support@multi-student-docker.edu",
    description="A comprehensive CLI tool for managing Docker Compose projects in multi-user educational environments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/multi-student-docker-compose",
    project_urls={
        "Bug Tracker": "https://github.com/your-org/multi-student-docker-compose/issues",
        "Documentation": "https://github.com/your-org/multi-student-docker-compose/blob/main/MULTI_STUDENT_DOCKER_COMPOSE_DOCUMENTATION.md",
        "Source Code": "https://github.com/your-org/multi-student-docker-compose",
    },
    packages=find_packages(where="cli-tool"),
    package_dir={"": "cli-tool"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Education",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Education",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
        "test": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "coverage>=5.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "docker-compose-cli=cli:main",
            "dcli=cli:main",
            "multi-student-docker=cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": [
            "templates/**/*",
            "examples/**/*",
            "*.md",
            "*.txt",
            "*.yml",
            "*.yaml",
            "*.json",
        ],
    },
    data_files=[
        ("templates/common", [
            "templates/common/docker-compose.yml.template",
            "templates/common/setup.sh.template",
        ]),
        ("templates/rag", [
            "templates/rag/docker-compose.yml.template",
            "templates/rag/setup.sh.template",
        ]),
        ("templates/agent", [
            "templates/agent/docker-compose.yml.template",
            "templates/agent/setup.sh.template",
        ]),
        ("examples", [
            "examples/cors_configuration_examples.md",
        ]),
        ("docs", [
            "MULTI_STUDENT_DOCKER_COMPOSE_DOCUMENTATION.md",
            "QUICK_START_GUIDE.md",
            "README.md",
        ]),
    ],
    zip_safe=False,
    keywords=[
        "docker",
        "docker-compose",
        "education",
        "multi-user",
        "cli",
        "containerization",
        "port-management",
        "project-management",
        "security",
        "isolation",
    ],
    platforms=["any"],
    license="MIT",
)