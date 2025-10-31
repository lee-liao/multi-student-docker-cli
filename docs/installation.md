# Installation Guide

## System Requirements

- **Python**: 3.8 or higher
- **Docker**: 20.10 or higher  
- **Docker Compose**: 2.0 or higher
- **Operating System**: Windows 10+, macOS 10.15+, Ubuntu 18.04+

## Installation Methods

### Method 1: Direct Use (Recommended for Students)

1. **Download the CLI tool**:
   ```bash
   git clone <repository-url>
   cd multi-student-docker-cli
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Test the installation**:
   ```bash
   python cli-tool/cli.py --help
   ```

4. **Check your port assignment**:
   ```bash
   python cli-tool/cli.py show-ports
   ```

### Method 2: System Installation

1. **Install as a Python package**:
   ```bash
   pip install -e .
   ```

2. **Use system-wide**:
   ```bash
   docker-compose-cli --help
   ```

## Verification

After installation, verify everything works:

```bash
# Check CLI functionality
python cli-tool/cli.py --help

# Check Docker connectivity
python cli-tool/cli.py health-check

# Check your port assignment
python cli-tool/cli.py show-ports
```

## Next Steps

1. **Create your first project**: See [Usage Guide](usage.md)
2. **Learn about templates**: Run python cli-tool/cli.py template-info rag
3. **Get help**: Run python cli-tool/cli.py --help for all commands
