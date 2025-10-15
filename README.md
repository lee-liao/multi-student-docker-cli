# Multi-Student Docker Compose CLI Tool

A simple command-line tool for managing Docker Compose projects in educational environments. Each student gets their own isolated port range and can create projects from templates.

## 🚀 Quick Start

# 1. Clone the repository
git clone https://github.com/lee-liao/multi-student-docker-cli.git
cd multi-student-docker-cli

# 2. Create a new project from the common template
python3 cli-tool/cli.py create-project common --template common

# 3. Navigate to your project directory
cd ~/dockeredServices/common

# 4. Run the setup script (automatically builds and starts all services)
./setup.sh


## 📋 Requirements

- Python 3.8+
- Docker 20.10+
- Docker Compose 2.0+

# Note
The passwords of services/portal can be found in docker-compose.yml


## 🩺 Backup Plan (if you need to stop or reset the environment)
docker-compose down          # Stop and remove containers
docker-compose down -v       # Stop, remove containers, and delete volumes
