# Usage Examples

## Basic Project Creation

### Create a RAG Project
```bash
# Create the project
python cli-tool/cli.py create-project my-rag --template rag

# Navigate to project
cd ~/dockeredServices/my-rag

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### Create an Agent Project
```bash
# Create the project
python cli-tool/cli.py create-project my-agent --template agent

# Navigate and start
cd ~/dockeredServices/my-agent
docker-compose up -d
```

## Project Management

### List Your Projects
```bash
# List all projects
python cli-tool/cli.py list-projects

# Get detailed status
python cli-tool/cli.py status
```

### Copy a Project
```bash
# Copy for experimentation
python cli-tool/cli.py copy-project my-rag my-rag-v2

# Start the copy
cd ~/dockeredServices/my-rag-v2
docker-compose up -d
```

## Port Management

### Check Your Ports
```bash
# See your assigned port range
python cli-tool/cli.py show-ports

# Verify project ports
python cli-tool/cli.py verify-ports my-rag
```

### Handle Port Conflicts
```bash
# Check for conflicts
python cli-tool/cli.py verify-ports --all

# Optimize port usage
python cli-tool/cli.py optimize-ports
```

## Maintenance

### Clean Up Resources
```bash
# Clean unused Docker resources
python cli-tool/cli.py cleanup

# System maintenance
python cli-tool/cli.py maintenance --suggestions
```

### Security Checks
```bash
# Validate system security
python cli-tool/cli.py security-check

# Check specific project
python cli-tool/cli.py security-check --project my-rag
```

## Advanced Usage

### Template Information
```bash
# Get template details
python cli-tool/cli.py template-info rag
python cli-tool/cli.py template-info agent
```

### System Health
```bash
# Basic health check
python cli-tool/cli.py health-check

# Comprehensive check
python cli-tool/cli.py health-check --comprehensive
```

### JSON Output
```bash
# Get machine-readable output
python cli-tool/cli.py status --json
python cli-tool/cli.py list-projects --json
```
