#!/usr/bin/env python3
"""
README Generation Manager

Handles generation of student-specific README files with port assignments,
CORS configuration, Docker commands, and troubleshooting guides.
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from src.core.port_assignment import PortAssignment
from src.config.cors_config_manager import CorsConfigManager, create_cors_config


@dataclass
class ReadmeConfig:
    """Configuration for README generation"""
    username: str
    project_name: str
    template_type: str
    port_assignment: PortAssignment
    has_common_project: bool
    output_dir: str
    custom_variables: Optional[Dict[str, Any]] = None


class ReadmeManager:
    """Manages README generation from templates"""
    
    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize README manager
        
        Args:
            templates_dir: Directory containing template files
        """
        self.templates_dir = templates_dir
    
    def create_readme_file(self, config: ReadmeConfig) -> str:
        """
        Create README file from template with student-specific configuration
        
        Args:
            config: README generation configuration
            
        Returns:
            Path to generated README file
        """
        # Generate template variables
        variables = self._generate_readme_variables(config)
        
        # Get template path
        template_path = self._get_readme_template_path(config.template_type)
        
        # Process template
        readme_content = self._process_readme_template(template_path, variables)
        
        # Write README file
        readme_path = os.path.join(config.output_dir, "README.md")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        return readme_path
    
    def _generate_readme_variables(self, config: ReadmeConfig) -> Dict[str, Any]:
        """Generate template variables for README"""
        # Get port assignments
        all_ports = config.port_assignment.all_ports
        
        # Basic variables
        variables = {
            'USERNAME': config.username,
            'PROJECT_NAME': config.project_name,
            'TEMPLATE_TYPE': config.template_type,
            'TOTAL_PORTS': len(all_ports),
            'SEGMENT1_START': config.port_assignment.segment1_start,
            'SEGMENT1_END': config.port_assignment.segment1_end,
            'HAS_TWO_SEGMENTS': config.port_assignment.has_two_segments,
        }
        
        # Add segment2 info if available
        if config.port_assignment.has_two_segments:
            variables.update({
                'SEGMENT2_START': config.port_assignment.segment2_start,
                'SEGMENT2_END': config.port_assignment.segment2_end,
            })
        
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
        
        # CORS configuration using CORS manager
        cors_manager = CorsConfigManager()
        cors_config = create_cors_config(
            username=config.username,
            project_name=config.project_name,
            template_type=config.template_type,
            port_assignment=config.port_assignment,
            has_common_project=config.has_common_project,
            frontend_port=service_ports.get('FRONTEND_PORT'),
            backend_port=service_ports.get('BACKEND_PORT')
        )
        cors_variables = cors_manager.generate_cors_config(cors_config)
        variables.update(cors_variables)
        
        # Common project configuration
        variables['HAS_COMMON_PROJECT'] = config.has_common_project
        
        # Custom variables
        if config.custom_variables:
            variables.update(config.custom_variables)
        
        return variables
    

    def _get_readme_template_path(self, template_type: str) -> str:
        """Get path to README template for given template type"""
        template_path = os.path.join(self.templates_dir, template_type, "README.md.template")
        
        if not os.path.exists(template_path):
            # Create basic template if it doesn't exist
            self._create_basic_readme_template(template_type, template_path)
        
        return template_path
    
    def _create_basic_readme_template(self, template_type: str, template_path: str):
        """Create a basic README template if one doesn't exist"""
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        
        basic_template = f"""# {{{{PROJECT_NAME}}}} Project - {{{{USERNAME}}}}

## Overview

This is a {template_type} project created for {{{{USERNAME}}}}.

## Your Assigned Ports

{{{{#if HAS_COMMON_PROJECT}}}}
**Shared Infrastructure Mode** - Using existing common project services

**Your Application Ports:**
- Backend API: localhost:{{{{BACKEND_PORT}}}}
- Frontend: localhost:{{{{FRONTEND_PORT}}}}

**Shared Infrastructure Ports (from common project):**
- PostgreSQL: localhost:{{{{POSTGRES_PORT}}}}
- MongoDB: localhost:{{{{MONGODB_PORT}}}}
- Redis: localhost:{{{{REDIS_PORT}}}}
- ChromaDB: localhost:{{{{CHROMADB_PORT}}}}
{{{{else}}}}
**Self-Contained Mode** - All services included in this project

**Your Assigned Ports:**
- PostgreSQL: localhost:{{{{POSTGRES_PORT}}}}
- Redis: localhost:{{{{REDIS_PORT}}}}
- ChromaDB: localhost:{{{{CHROMADB_PORT}}}}
- Backend API: localhost:{{{{BACKEND_PORT}}}}
- Frontend: localhost:{{{{FRONTEND_PORT}}}}
{{{{/if}}}}

**Total Port Allocation:** {{{{TOTAL_PORTS}}}} ports

## Quick Start

1. **Start services:**
   ```bash
   docker-compose up -d
   ```

2. **View logs:**
   ```bash
   docker-compose logs -f
   ```

3. **Stop services:**
   ```bash
   docker-compose down
   ```

## Local Development Configuration

### Environment Variables
Update your .env file with:
```bash
# Database Configuration
DATABASE_URL=postgresql://{{{{USERNAME}}}}_user:{{{{USERNAME}}}}_password_2024@localhost:{{{{POSTGRES_PORT}}}}/{{{{PROJECT_NAME}}}}

# CORS Configuration
CORS_ORIGINS={{{{CORS_ORIGINS_CSR}}}}
```

## Docker Commands

### Build Custom Images
```bash
# Build backend image
docker build -t {{{{USERNAME}}}}-{template_type}-backend:latest ./backend/

# Build frontend image  
docker build -t {{{{USERNAME}}}}-{template_type}-frontend:latest ./frontend/
```

## Troubleshooting

### Common Issues
- **Connection refused**: Check if services are running with `docker-compose ps`
- **Port conflicts**: Verify your assigned ports are not in use by other applications
- **CORS errors**: Update CORS_ORIGINS in your .env file

For more help, contact your instructor or check the project documentation.
"""
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(basic_template)
    
    def _process_readme_template(self, template_path: str, variables: Dict[str, Any]) -> str:
        """Process README template with variable substitution"""
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Simple template variable substitution
        processed_content = template_content
        
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            processed_content = processed_content.replace(placeholder, str(value))
        
        # Handle conditional blocks (basic implementation)
        processed_content = self._process_conditional_blocks(processed_content, variables)
        
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
        
        return content
    
    def validate_readme_template(self, template_type: str) -> List[str]:
        """Validate README template for missing variables or issues"""
        template_path = self._get_readme_template_path(template_type)
        issues = []
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for common required variables
            required_vars = [
                'USERNAME', 'PROJECT_NAME', 'BACKEND_PORT', 'FRONTEND_PORT',
                'POSTGRES_PORT', 'CORS_ORIGINS_CSR'
            ]
            
            for var in required_vars:
                if f"{{{{{var}}}}}" not in content:
                    issues.append(f"Missing required variable: {var}")
            
            # Check for malformed template syntax
            import re
            malformed_vars = re.findall(r'\{\{[^}]*\}\}', content)
            for var in malformed_vars:
                if not re.match(r'\{\{[A-Z_]+\}\}', var) and not var.startswith('{{#'):
                    issues.append(f"Potentially malformed variable: {var}")
            
        except Exception as e:
            issues.append(f"Failed to read template: {e}")
        
        return issues


def create_readme_config(username: str, project_name: str, template_type: str,
                        port_assignment: PortAssignment, output_dir: str,
                        has_common_project: bool = False,
                        custom_variables: Optional[Dict[str, Any]] = None) -> ReadmeConfig:
    """Create README configuration with default settings"""
    return ReadmeConfig(
        username=username,
        project_name=project_name,
        template_type=template_type,
        port_assignment=port_assignment,
        has_common_project=has_common_project,
        output_dir=output_dir,
        custom_variables=custom_variables or {}
    )


def generate_readme(username: str, project_name: str, template_type: str,
                   port_assignment: PortAssignment, output_dir: str,
                   has_common_project: bool = False,
                   templates_dir: str = "templates") -> str:
    """Convenience function to generate README file"""
    manager = ReadmeManager(templates_dir)
    config = create_readme_config(
        username=username,
        project_name=project_name,
        template_type=template_type,
        port_assignment=port_assignment,
        output_dir=output_dir,
        has_common_project=has_common_project
    )
    
    return manager.create_readme_file(config)