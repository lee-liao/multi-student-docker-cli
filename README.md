# Multi-Student Docker Compose CLI Tool

A simple command-line tool for managing Docker Compose projects in educational environments. Each student gets their own isolated port range and can create projects from templates.

## 🚀 Quick Start

# 1. Navigate to user's home directory
cd ~

# 2. Clone the CLI tool repository
git clone https://github.com/lee-liao/multi-student-docker-cli.git

# 3. Navigate to the CLI tool directory
cd multi-student-docker-cli

# 4. Run the CLI command to create a common docker compose project from the common template
python3 cli-tool/cli.py create-project common --template common

# 5. Navigate to your docker compose project directory
cd ~/dockeredServices/common

# 6. Run the setup script (automatically builds and starts all services)
./setup.sh

# 7. Wait till the containers to be ready. The user credentials of the services can be found in ~/dockeredServices/common/docker-compose.yml.

## 📋 Requirements

- Python 3.8+
- Docker 20.10+
- Docker Compose 2.0+

