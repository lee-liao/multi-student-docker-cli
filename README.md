# Multi-Student Docker Compose CLI Tool

A simple command-line tool for managing Docker Compose projects in educational environments. Each student gets their own isolated port range and can create projects from templates.

## 🚀 Quick Start

```bash
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
```

## 📋 Requirements

- Python 3.8+
- Docker 20.10+
- Docker Compose 2.0+

## 🛠 Installation

### Method 1: Direct Use (Recommended)
```bash
# Clone this repository
git clone <repository-url>
cd multi-student-docker-cli

# Install dependencies
pip install -r requirements.txt

# Use directly
python cli-tool/cli.py --help
```

### Method 2: System Installation
```bash
# Install dependencies and package
pip install -r requirements.txt
pip install -e .

# Use system-wide
docker-compose-cli --help
```

## 🎯 Available Commands

```bash
# Project Management
python cli-tool/cli.py create-project <name> --template <type>
python cli-tool/cli.py copy-project <source> <destination>
python cli-tool/cli.py list-projects

# Port Management
python cli-tool/cli.py show-ports
python cli-tool/cli.py verify-ports <project>

# System Status
python cli-tool/cli.py status
python cli-tool/cli.py health-check

# Maintenance
python cli-tool/cli.py cleanup
python cli-tool/cli.py security-check
```

## 📚 Available Templates

### RAG Template
- **Services**: Python app, PostgreSQL, Vector DB
- **Use Case**: AI applications with document retrieval
- **Ports**: 5 ports automatically assigned

### Agent Template
- **Services**: Python agent, MongoDB, Redis, API Gateway
- **Use Case**: AI agents with persistent state
- **Ports**: 6 ports automatically assigned

### Common Template
- **Services**: Shared infrastructure (databases, monitoring)
- **Use Case**: Shared services for multiple projects
- **Ports**: 7 ports automatically assigned

## 🔧 Common Workflows

### Create and Start a Project
```bash
# 1. Create project
python cli-tool/cli.py create-project my-chatbot --template rag

# 2. Verify ports
python cli-tool/cli.py verify-ports my-chatbot

# 3. Start services
cd ~/dockeredServices/my-chatbot
docker-compose up -d

# 4. Check status
python cli-tool/cli.py project-status my-chatbot
```

### Copy Project for Experimentation
```bash
# Copy existing project
python cli-tool/cli.py copy-project my-chatbot my-chatbot-v2

# Start the copy
cd ~/dockeredServices/my-chatbot-v2
docker-compose up -d
```

## 🚨 Troubleshooting

### Port Conflicts
```bash
# Check port usage
python cli-tool/cli.py verify-ports --all

# Optimize ports
python cli-tool/cli.py optimize-ports
```

### Docker Issues
```bash
# Check Docker status
docker version

# Health check
python cli-tool/cli.py health-check
```

### Permission Issues
```bash
# Security check
python cli-tool/cli.py security-check
```

## 📖 Documentation

For detailed documentation, see the [docs/](docs/) directory:

- [Installation Guide](docs/installation.md)
- [Usage Examples](docs/usage.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🆘 Getting Help

```bash
# General help
python cli-tool/cli.py --help

# Command-specific help
python cli-tool/cli.py create-project --help

# System diagnostics
python cli-tool/cli.py health-check --comprehensive
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Version**: 1.0.0  
**For Students**: Simple, powerful Docker Compose management  
**Support**: Check docs/ directory for detailed guides
