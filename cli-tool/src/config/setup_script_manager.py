#!/usr/bin/env python3
"""
Setup Script Manager

Handles generation of intelligent setup scripts with database detection,
health checking, startup coordination, and error recovery guidance.
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from src.core.port_assignment import PortAssignment
from src.config.cors_config_manager import generate_cors_variables


@dataclass
class SetupScriptConfig:
    """Configuration for setup script generation"""
    username: str
    project_name: str
    template_type: str
    port_assignment: PortAssignment
    has_common_project: bool
    output_dir: str
    services: List[str]
    custom_variables: Optional[Dict[str, Any]] = None


class SetupScriptManager:
    """Manages setup script generation from templates"""
    
    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize setup script manager
        
        Args:
            templates_dir: Directory containing template files
        """
        self.templates_dir = templates_dir
    
    def create_setup_script(self, config: SetupScriptConfig) -> str:
        """
        Create setup script from template with intelligent features
        
        Args:
            config: Setup script generation configuration
            
        Returns:
            Path to generated setup script
        """
        # Generate template variables
        variables = self._generate_setup_variables(config)
        
        # Get template path or create intelligent script
        setup_content = self._generate_intelligent_setup_script(config, variables)
        
        # Write setup script
        setup_path = os.path.join(config.output_dir, "setup.sh")
        with open(setup_path, 'w', encoding='utf-8') as f:
            f.write(setup_content)
        
        # Make script executable (on Unix systems)
        try:
            os.chmod(setup_path, 0o755)
        except (OSError, AttributeError):
            pass  # Windows or permission issues
        
        return setup_path
    
    def _generate_setup_script_content(self, config: SetupScriptConfig) -> str:
        """Generate setup script content (main entry point)"""
        # Generate variables
        variables = self._generate_setup_variables(config)
        
        # Generate intelligent setup script
        return self._generate_intelligent_setup_script(config, variables)
    
    def _generate_setup_variables(self, config: SetupScriptConfig) -> Dict[str, Any]:
        """Generate template variables for setup script"""
        # Get port assignments
        all_ports = config.port_assignment.all_ports
        
        # Basic variables
        variables = {
            'USERNAME': config.username,
            'PROJECT_NAME': config.project_name,
            'TEMPLATE_TYPE': config.template_type,
            'HAS_COMMON_PROJECT': config.has_common_project,
            'SERVICES': config.services,
            'TIMESTAMP': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Port assignments (sequential from available ports)
        port_index = 0
        service_ports = {}
        
        # Common infrastructure ports (first 7 ports)
        if len(all_ports) > port_index:
            service_ports['POSTGRES_PORT'] = all_ports[port_index]
            port_index += 1
        if len(all_ports) > port_index:
            service_ports['MONGODB_PORT'] = all_ports[port_index]
            port_index += 1
        if len(all_ports) > port_index:
            service_ports['REDIS_PORT'] = all_ports[port_index]
            port_index += 1
        if len(all_ports) > port_index:
            service_ports['CHROMADB_PORT'] = all_ports[port_index]
            port_index += 1
        if len(all_ports) > port_index:
            service_ports['JAEGER_UI_PORT'] = all_ports[port_index]
            port_index += 1
        if len(all_ports) > port_index:
            service_ports['PROMETHEUS_PORT'] = all_ports[port_index]
            port_index += 1
        if len(all_ports) > port_index:
            service_ports['GRAFANA_PORT'] = all_ports[port_index]
            port_index += 1
        
        # Application ports (next available ports)
        if len(all_ports) > port_index:
            service_ports['BACKEND_PORT'] = all_ports[port_index]
            port_index += 1
        if len(all_ports) > port_index:
            service_ports['FRONTEND_PORT'] = all_ports[port_index]
            port_index += 1
        if len(all_ports) > port_index:
            service_ports['WORKER_PORT'] = all_ports[port_index]
            port_index += 1
        
        variables.update(service_ports)
        
        # CORS configuration
        cors_variables = generate_cors_variables(
            username=config.username,
            project_name=config.project_name,
            template_type=config.template_type,
            port_assignment=config.port_assignment,
            has_common_project=config.has_common_project,
            frontend_port=service_ports.get('FRONTEND_PORT'),
            backend_port=service_ports.get('BACKEND_PORT')
        )
        variables.update(cors_variables)
        
        # Custom variables
        if config.custom_variables:
            variables.update(config.custom_variables)
        
        return variables
    
    def _generate_intelligent_setup_script(self, config: SetupScriptConfig, variables: Dict[str, Any]) -> str:
        """Generate intelligent setup script with advanced features"""
        
        # Check if template-specific setup script exists
        template_path = os.path.join(self.templates_dir, config.template_type, "setup.sh.template")
        
        if os.path.exists(template_path):
            # Use existing template and enhance it
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Process template variables
            processed_content = self._process_template_variables(template_content, variables)
            return processed_content
        else:
            # Generate intelligent setup script
            return self._create_intelligent_setup_script(config, variables)
    
    def _create_intelligent_setup_script(self, config: SetupScriptConfig, variables: Dict[str, Any]) -> str:
        """Create intelligent setup script with all advanced features"""
        
        script_content = f"""#!/bin/bash

# Intelligent Setup Script for {config.project_name}
# Template: {config.template_type}
# User: {config.username}
# Generated: {variables['TIMESTAMP']}

set -e  # Exit on any error

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
CYAN='\\033[0;36m'
NC='\\033[0m' # No Color

# Function to print colored output
print_status() {{
    echo -e "${{BLUE}}[INFO]${{NC}} $1"
}}

print_success() {{
    echo -e "${{GREEN}}[SUCCESS]${{NC}} $1"
}}

print_warning() {{
    echo -e "${{YELLOW}}[WARNING]${{NC}} $1"
}}

print_error() {{
    echo -e "${{RED}}[ERROR]${{NC}} $1"
}}

print_step() {{
    echo -e "${{CYAN}}[STEP]${{NC}} $1"
}}

# Error handling function
handle_error() {{
    local exit_code=$?
    local line_number=$1
    print_error "Setup failed at line $line_number with exit code $exit_code"
    print_error "Check the logs above for details"
    
    echo ""
    print_status "Troubleshooting suggestions:"
    echo "1. Check if Docker is running: docker info"
    echo "2. Check if ports are available: netstat -tuln | grep <port>"
    echo "3. Check Docker Compose syntax: docker-compose config"
    echo "4. View service logs: docker-compose logs <service>"
    echo "5. Restart Docker if needed"
    echo ""
    exit $exit_code
}}

# Set up error handling
trap 'handle_error ${{LINENO}}' ERR

echo "🚀 Setting up {config.project_name} ({config.template_type} project)"
echo "=================================================="
echo "👤 User: {config.username}"
echo "📅 Started: {variables['TIMESTAMP']}"
echo "🏗️  Template: {config.template_type}"
echo "🔗 Mode: {'Shared infrastructure' if config.has_common_project else 'Self-contained'}"
echo ""

# Step 1: Environment validation
print_step "1. Validating environment..."

# Check if Docker is running
print_status "Checking Docker availability..."
if ! docker info >/dev/null 2>&1; then
    print_error "Docker is not running"
    echo ""
    print_status "Recovery steps:"
    echo "1. Start Docker Desktop (Windows/Mac) or Docker daemon (Linux)"
    echo "2. Wait for Docker to fully start"
    echo "3. Run this script again"
    exit 1
fi
print_success "Docker is running"

# Check if docker-compose is available
print_status "Checking docker-compose availability..."
if ! command -v docker-compose >/dev/null 2>&1; then
    print_error "docker-compose is not installed"
    echo ""
    print_status "Recovery steps:"
    echo "1. Install Docker Compose: https://docs.docker.com/compose/install/"
    echo "2. Verify installation: docker-compose --version"
    echo "3. Run this script again"
    exit 1
fi
print_success "docker-compose is available ($(docker-compose --version))"

# Validate docker-compose.yml
print_status "Validating docker-compose.yml..."
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found in current directory"
    exit 1
fi

if ! docker-compose config >/dev/null 2>&1; then
    print_error "docker-compose.yml has syntax errors"
    echo ""
    print_status "Check syntax with: docker-compose config"
    exit 1
fi
print_success "docker-compose.yml is valid"

"""

        # Add common project detection for shared mode
        if config.has_common_project and config.template_type != 'common':
            script_content += f"""
# Step 2: Common infrastructure validation
print_step "2. Validating common infrastructure..."

NETWORK_NAME="{config.username}-network"
print_status "Checking for common project network: $NETWORK_NAME"

if docker network ls | grep -q "$NETWORK_NAME"; then
    print_success "Common project network found"
    
    # Check if common services are running
    print_status "Checking common services status..."
    COMMON_SERVICES=("postgres" "mongodb" "redis" "chromadb")
    RUNNING_SERVICES=0
    
    for service in "${{COMMON_SERVICES[@]}}"; do
        if docker ps --format "table {{{{.Names}}}}" | grep -q "{config.username}-$service"; then
            print_success "$service is running"
            ((RUNNING_SERVICES++))
        else
            print_warning "$service is not running"
        fi
    done
    
    if [ $RUNNING_SERVICES -eq 0 ]; then
        print_warning "No common services are running"
        print_status "Starting common infrastructure..."
        echo "cd ../common && docker-compose up -d"
        echo "Please start the common project first, then run this script again"
        exit 1
    else
        print_success "$RUNNING_SERVICES/${{#COMMON_SERVICES[@]}} common services are running"
    fi
else
    print_error "Common project network not found"
    echo ""
    print_status "Recovery steps:"
    echo "1. Navigate to common project: cd ../common"
    echo "2. Start common infrastructure: docker-compose up -d"
    echo "3. Return to this project: cd ../{config.project_name}"
    echo "4. Run this script again"
    exit 1
fi

"""
        else:
            script_content += """
# Step 2: Network setup
print_step "2. Setting up Docker network..."

"""
            if config.template_type == 'common':
                script_content += f"""
NETWORK_NAME="{config.username}-network"
print_status "Creating Docker network: $NETWORK_NAME"

if docker network ls | grep -q "$NETWORK_NAME"; then
    print_warning "Network $NETWORK_NAME already exists"
else
    docker network create "$NETWORK_NAME"
    print_success "Created network: $NETWORK_NAME"
fi

"""

        # Add port availability checking
        script_content += """
# Step 3: Port availability check
print_step "3. Checking port availability..."

"""
        
        # Generate port checking based on services
        if config.services:
            port_vars = []
            port_names = []
            
            service_port_map = {
                'postgres': ('POSTGRES_PORT', 'PostgreSQL'),
                'mongodb': ('MONGODB_PORT', 'MongoDB'),
                'redis': ('REDIS_PORT', 'Redis'),
                'chromadb': ('CHROMADB_PORT', 'ChromaDB'),
                'jaeger': ('JAEGER_UI_PORT', 'Jaeger UI'),
                'prometheus': ('PROMETHEUS_PORT', 'Prometheus'),
                'grafana': ('GRAFANA_PORT', 'Grafana'),
                'backend': ('BACKEND_PORT', 'Backend API'),
                'frontend': ('FRONTEND_PORT', 'Frontend'),
                'agent-backend': ('BACKEND_PORT', 'Agent Backend'),
                'agent-frontend': ('FRONTEND_PORT', 'Agent Frontend'),
                'agent-worker': ('WORKER_PORT', 'Agent Worker')
            }
            
            for service in config.services:
                if service in service_port_map:
                    port_var, port_name = service_port_map[service]
                    if port_var in variables:
                        port_vars.append(port_var)
                        port_names.append(port_name)
            
            if port_vars:
                script_content += f"""
PORTS=({' '.join(f'${{{var}}}' for var in port_vars)})
PORT_NAMES=({' '.join(f'"{name}"' for name in port_names)})

for i in "${{!PORTS[@]}}"; do
    PORT=${{PORTS[$i]}}
    SERVICE=${{PORT_NAMES[$i]}}
    
    if command -v netstat >/dev/null 2>&1; then
        if netstat -tuln 2>/dev/null | grep -q ":$PORT "; then
            print_warning "Port $PORT ($SERVICE) is already in use"
            print_warning "This may cause conflicts. Consider stopping other services using this port."
        else
            print_success "Port $PORT ($SERVICE) is available"
        fi
    else
        print_status "Port $PORT ($SERVICE) - netstat not available, skipping check"
    fi
done

"""

        # Add database detection and initialization
        script_content += """
# Step 4: Database detection and initialization
print_step "4. Detecting and preparing databases..."

"""
        
        # Intelligent database detection
        db_services = []
        if 'postgres' in config.services or config.has_common_project:
            db_services.append('postgres')
        if 'mongodb' in config.services or config.has_common_project:
            db_services.append('mongodb')
        
        if db_services:
            script_content += """
# Database detection
"""
            
            if 'postgres' in db_services:
                script_content += """
# PostgreSQL detection
if [ -f "database/init.sql" ] || [ -f "database/postgresql/init.sql" ]; then
    print_success "PostgreSQL initialization script found"
    DB_INIT_POSTGRES=true
else
    print_status "No PostgreSQL initialization script found"
    DB_INIT_POSTGRES=false
fi

"""
            
            if 'mongodb' in db_services:
                script_content += """
# MongoDB detection
if [ -f "database/init.js" ] || [ -f "database/mongodb/init.js" ]; then
    print_success "MongoDB initialization script found"
    DB_INIT_MONGODB=true
else
    print_status "No MongoDB initialization script found"
    DB_INIT_MONGODB=false
fi

"""

        # Add service startup with health checking
        script_content += """
# Step 5: Service startup and health checking
print_step "5. Starting services with health monitoring..."

# Pull latest images
print_status "Pulling Docker images..."
if ! docker-compose pull; then
    print_warning "Failed to pull some images, continuing with local images"
fi

# Start services
print_status "Starting services..."
docker-compose up -d

# Wait for services to initialize
print_status "Waiting for services to initialize..."
sleep 5

# Health checking with retries
print_status "Performing health checks..."
MAX_RETRIES=12
RETRY_INTERVAL=5
HEALTHY_SERVICES=0
TOTAL_SERVICES=0

"""
        
        # Generate health checks for each service
        if config.services:
            for service in config.services:
                script_content += f"""
# Health check for {service}
print_status "Checking {service} health..."
TOTAL_SERVICES=$((TOTAL_SERVICES + 1))

for ((i=1; i<=MAX_RETRIES; i++)); do
    if docker-compose ps {service} | grep -q "Up"; then
        # Additional service-specific health checks
"""
                
                # Service-specific health checks
                if service == 'postgres':
                    script_content += f"""        if docker-compose exec -T postgres pg_isready -U {config.username}_user >/dev/null 2>&1; then
            print_success "{service} is healthy"
            HEALTHY_SERVICES=$((HEALTHY_SERVICES + 1))
            break
        fi
"""
                elif service == 'mongodb':
                    script_content += f"""        if docker-compose exec -T mongodb mongosh --eval "db.adminCommand('ping')" >/dev/null 2>&1; then
            print_success "{service} is healthy"
            HEALTHY_SERVICES=$((HEALTHY_SERVICES + 1))
            break
        fi
"""
                elif service == 'redis':
                    script_content += f"""        if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
            print_success "{service} is healthy"
            HEALTHY_SERVICES=$((HEALTHY_SERVICES + 1))
            break
        fi
"""
                elif service in ['backend', 'frontend', 'agent-backend', 'agent-frontend', 'agent-worker']:
                    port_var = 'BACKEND_PORT' if 'backend' in service else ('FRONTEND_PORT' if 'frontend' in service else 'WORKER_PORT')
                    if port_var in variables:
                        script_content += f"""        if curl -f http://localhost:{variables[port_var]}/health >/dev/null 2>&1; then
            print_success "{service} is healthy"
            HEALTHY_SERVICES=$((HEALTHY_SERVICES + 1))
            break
        fi
"""
                else:
                    # Generic health check
                    script_content += f"""        print_success "{service} is running"
        HEALTHY_SERVICES=$((HEALTHY_SERVICES + 1))
        break
"""
                
                script_content += f"""    fi
    
    if [ $i -eq $MAX_RETRIES ]; then
        print_error "{service} failed to become healthy"
        print_status "Checking {service} logs:"
        docker-compose logs --tail=10 {service}
    else
        print_status "Waiting for {service} to be ready... (attempt $i/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
    fi
done

"""

        # Add database initialization after services are healthy
        if 'postgres' in config.services or 'mongodb' in config.services:
            script_content += """
# Step 6: Database initialization
print_step "6. Initializing databases..."

"""
            
            if 'postgres' in config.services or config.has_common_project:
                script_content += f"""
# Initialize PostgreSQL if needed
if [ "$DB_INIT_POSTGRES" = true ]; then
    print_status "Initializing PostgreSQL database..."
    
    # Wait for PostgreSQL to be ready
    for ((i=1; i<=30; i++)); do
        if docker-compose exec -T postgres pg_isready -U {config.username}_user >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    # Run initialization script
    if [ -f "database/init.sql" ]; then
        print_status "Running database/init.sql..."
        docker-compose exec -T postgres psql -U {config.username}_user -d {config.project_name.replace('-', '_')} -f /docker-entrypoint-initdb.d/init.sql
    elif [ -f "database/postgresql/init.sql" ]; then
        print_status "Running database/postgresql/init.sql..."
        docker-compose exec -T postgres psql -U {config.username}_user -d {config.project_name.replace('-', '_')} -f /docker-entrypoint-initdb.d/init.sql
    fi
    
    print_success "PostgreSQL database initialized"
fi

"""
            
            if 'mongodb' in config.services or config.has_common_project:
                script_content += f"""
# Initialize MongoDB if needed
if [ "$DB_INIT_MONGODB" = true ]; then
    print_status "Initializing MongoDB database..."
    
    # Run initialization script
    if [ -f "database/init.js" ]; then
        print_status "Running database/init.js..."
        docker-compose exec -T mongodb mongosh {config.project_name.replace('-', '_')} /docker-entrypoint-initdb.d/init.js
    elif [ -f "database/mongodb/init.js" ]; then
        print_status "Running database/mongodb/init.js..."
        docker-compose exec -T mongodb mongosh {config.project_name.replace('-', '_')} /docker-entrypoint-initdb.d/init.js
    fi
    
    print_success "MongoDB database initialized"
fi

"""

        # Final status and next steps
        script_content += f"""
# Final status report
echo ""
echo "=================================================="
print_step "Setup Summary"
echo "=================================================="

if [ $HEALTHY_SERVICES -eq $TOTAL_SERVICES ]; then
    print_success "All services are running successfully! ($HEALTHY_SERVICES/$TOTAL_SERVICES)"
else
    print_warning "$HEALTHY_SERVICES/$TOTAL_SERVICES services are healthy"
    print_warning "Some services may need attention"
fi

# Display service information
echo ""
print_status "Service Access Information:"
echo "=================================================="
"""
        
        # Add service access information based on template type
        if config.template_type == 'common':
            script_content += f"""
echo "📊 Grafana Dashboard:    http://localhost:{variables.get('GRAFANA_PORT', 'N/A')}"
echo "   Username: admin"
echo "   Password: {config.username}_password_2024"
echo ""
echo "🔍 Jaeger Tracing:       http://localhost:{variables.get('JAEGER_UI_PORT', 'N/A')}"
echo "📈 Prometheus Metrics:   http://localhost:{variables.get('PROMETHEUS_PORT', 'N/A')}"
echo "🗄️  PostgreSQL Database:  localhost:{variables.get('POSTGRES_PORT', 'N/A')}"
echo "   Database: shared_db"
echo "   Username: {config.username}_user"
echo "   Password: {config.username}_password_2024"
echo ""
echo "📄 MongoDB Database:     localhost:{variables.get('MONGODB_PORT', 'N/A')}"
echo "   Database: shared_db"
echo "   Username: {config.username}_admin"
echo "   Password: {config.username}_password_2024"
echo ""
echo "⚡ Redis Cache:          localhost:{variables.get('REDIS_PORT', 'N/A')}"
echo "   Password: {config.username}_redis_2024"
echo ""
echo "🔍 ChromaDB Vector DB:   http://localhost:{variables.get('CHROMADB_PORT', 'N/A')}"
"""
        else:
            # Application project access info
            if 'backend' in config.services or 'agent-backend' in config.services:
                script_content += f"""
echo "🔧 Backend API:          http://localhost:{variables.get('BACKEND_PORT', 'N/A')}"
echo "   Health check:         http://localhost:{variables.get('BACKEND_PORT', 'N/A')}/health"
echo "   API docs:             http://localhost:{variables.get('BACKEND_PORT', 'N/A')}/docs"
"""
            
            if 'frontend' in config.services or 'agent-frontend' in config.services:
                script_content += f"""
echo "🌐 Frontend UI:          http://localhost:{variables.get('FRONTEND_PORT', 'N/A')}"
"""
            
            if 'agent-worker' in config.services:
                script_content += f"""
echo "⚙️  Agent Worker:         http://localhost:{variables.get('WORKER_PORT', 'N/A')}"
"""
            
            if config.has_common_project:
                script_content += f"""
echo ""
echo "📊 Shared Infrastructure (from common project):"
echo "   PostgreSQL:           localhost:{variables.get('POSTGRES_PORT', 'N/A')}"
echo "   MongoDB:              localhost:{variables.get('MONGODB_PORT', 'N/A')}"
echo "   Redis:                localhost:{variables.get('REDIS_PORT', 'N/A')}"
echo "   ChromaDB:             http://localhost:{variables.get('CHROMADB_PORT', 'N/A')}"
"""

        # Add final instructions
        script_content += f"""
echo ""
print_status "Next Steps:"
echo "=================================================="
echo "1. 📊 Check service status: docker-compose ps"
echo "2. 📋 View logs: docker-compose logs -f"
echo "3. 🔧 Monitor services: docker-compose logs -f <service-name>"
echo "4. 🛑 Stop services: docker-compose down"
echo "5. 📚 Read README.md for detailed usage instructions"
echo ""

# Network information
if [ "{config.template_type}" = "common" ] || [ "{config.has_common_project}" = "True" ]; then
    print_status "Network Information:"
    echo "=================================================="
    echo "🌐 Shared Network: {config.username}-network"
    echo ""
    echo "Application projects can connect using:"
    echo "  - Container hostnames: {config.username}-postgres, {config.username}-mongodb, etc."
    echo "  - Localhost ports: localhost:{variables.get('POSTGRES_PORT', 'N/A')}, localhost:{variables.get('MONGODB_PORT', 'N/A')}, etc."
    echo ""
fi

print_success "Setup completed successfully!"
echo "=================================================="

# Cleanup trap
trap - ERR
"""
        
        return script_content
    
    def _process_template_variables(self, template_content: str, variables: Dict[str, Any]) -> str:
        """Process template variables in setup script"""
        processed_content = template_content
        
        # First process conditional blocks
        processed_content = self._process_conditional_blocks(processed_content, variables)
        
        # Then process regular variables
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            processed_content = processed_content.replace(placeholder, str(value))
        
        return processed_content
    
    def _process_conditional_blocks(self, content: str, variables: Dict[str, Any]) -> str:
        """Process conditional blocks in template"""
        import re
        
        # Handle {{#if VARIABLE}} ... {{else}} ... {{/if}} blocks
        def replace_if_block(match):
            condition = match.group(1).strip()
            if_content = match.group(2)
            else_content = match.group(3) if match.group(3) else ""
            
            # Check condition
            if condition in variables and variables[condition]:
                return if_content
            else:
                return else_content
        
        # Pattern for {{#if CONDITION}} content {{else}} content {{/if}}
        if_pattern = r'\{\{#if\s+([^}]+)\}\}(.*?)\{\{else\}\}(.*?)\{\{/if\}\}'
        content = re.sub(if_pattern, replace_if_block, content, flags=re.DOTALL)
        
        # Pattern for {{#if CONDITION}} content {{/if}} (no else)
        if_pattern_no_else = r'\{\{#if\s+([^}]+)\}\}(.*?)\{\{/if\}\}'
        def replace_if_block_no_else(match):
            condition = match.group(1).strip()
            if_content = match.group(2)
            
            if condition in variables and variables[condition]:
                return if_content
            else:
                return ""
        
        content = re.sub(if_pattern_no_else, replace_if_block_no_else, content, flags=re.DOTALL)
        
        # Handle {{#unless VARIABLE}} ... {{/unless}} blocks
        unless_pattern = r'\{\{#unless\s+([^}]+)\}\}(.*?)\{\{/unless\}\}'
        def replace_unless_block(match):
            condition = match.group(1).strip()
            unless_content = match.group(2)
            
            # Unless is the opposite of if
            if condition in variables and not variables[condition]:
                return unless_content
            else:
                return ""
        
        content = re.sub(unless_pattern, replace_unless_block, content, flags=re.DOTALL)
        
        return content
    
    def validate_setup_script(self, template_type: str) -> List[str]:
        """Validate setup script template for missing variables or issues"""
        template_path = os.path.join(self.templates_dir, template_type, "setup.sh.template")
        issues = []
        
        if not os.path.exists(template_path):
            issues.append(f"No setup script template found for {template_type}")
            return issues
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for common required variables
            required_vars = [
                'USERNAME', 'PROJECT_NAME'
            ]
            
            for var in required_vars:
                if f"{{{{{var}}}}}" not in content:
                    issues.append(f"Missing required variable: {var}")
            
            # Check for bash syntax issues
            if not content.startswith('#!/bin/bash'):
                issues.append("Missing bash shebang")
            
            if 'set -e' not in content:
                issues.append("Missing 'set -e' for error handling")
            
        except Exception as e:
            issues.append(f"Failed to read template: {e}")
        
        return issues


def create_setup_script_config(username: str, project_name: str, template_type: str,
                              port_assignment: PortAssignment, output_dir: str,
                              services: List[str], has_common_project: bool = False,
                              custom_variables: Optional[Dict[str, Any]] = None) -> SetupScriptConfig:
    """Create setup script configuration with default settings"""
    return SetupScriptConfig(
        username=username,
        project_name=project_name,
        template_type=template_type,
        port_assignment=port_assignment,
        has_common_project=has_common_project,
        output_dir=output_dir,
        services=services,
        custom_variables=custom_variables or {}
    )


def generate_setup_script(username: str, project_name: str, template_type: str,
                         port_assignment: PortAssignment, output_dir: str,
                         services: List[str], has_common_project: bool = False,
                         templates_dir: str = "templates") -> str:
    """Convenience function to generate setup script"""
    manager = SetupScriptManager(templates_dir)
    config = create_setup_script_config(
        username=username,
        project_name=project_name,
        template_type=template_type,
        port_assignment=port_assignment,
        output_dir=output_dir,
        services=services,
        has_common_project=has_common_project
    )
    
    return manager.create_setup_script(config)