# Troubleshooting Guide

## Common Issues

### Docker Not Running

**Problem**: docker: command not found or connection errors

**Solution**:
`ash
# Check Docker status
docker version

# Start Docker (Linux)
sudo systemctl start docker

# Restart Docker Desktop (Windows/macOS)
# Use GUI or restart application
`

### Port Conflicts

**Problem**: port already in use errors

**Solution**:
`ash
# Check port usage
python cli-tool/cli.py verify-ports --all

# Find what's using the port
netstat -tulpn | grep :8080

# Optimize port assignments
python cli-tool/cli.py optimize-ports
`

### Permission Issues

**Problem**: Permission denied errors

**Solution**:
`ash
# Run security check
python cli-tool/cli.py security-check

# Fix common issues (Linux/macOS)
chmod 755 ~/dockeredServices
sudo usermod -aG docker \

# Log out and back in
`

### Project Won't Start

**Problem**: docker-compose up fails

**Solution**:
`ash
# Check project status
python cli-tool/cli.py project-status <project-name>

# Validate Docker Compose file
cd ~/dockeredServices/<project-name>
docker-compose config

# Check logs
docker-compose logs
`

## Getting Help

### Built-in Help
`ash
# General help
python cli-tool/cli.py --help

# Command-specific help
python cli-tool/cli.py create-project --help
`

### Diagnostic Commands
`ash
# System health check
python cli-tool/cli.py health-check --comprehensive

# Security validation
python cli-tool/cli.py security-check

# System status
python cli-tool/cli.py status --verbose
`

### Debug Mode
`ash
# Enable verbose output
python cli-tool/cli.py --verbose <command>

# JSON output for analysis
python cli-tool/cli.py <command> --json
`

## Contact Support

If you continue to have issues:

1. **Check the logs**: Look in ~/.dockeredServices/.logs/
2. **Run diagnostics**: python cli-tool/cli.py health-check --comprehensive
3. **Contact your instructor**: Provide the diagnostic output
