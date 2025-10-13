#!/usr/bin/env python3
"""
Dockerfile Template System

Manages Dockerfile template generation for backend and frontend services
with multi-stage builds, security best practices, and project-specific optimizations.
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from src.core.template_processor import TemplateProcessor, create_template_context
from src.core.port_assignment import PortAssignment


@dataclass
class DockerfileConfig:
    """Configuration for Dockerfile generation"""
    username: str
    project_name: str
    template_type: str
    service_type: str  # 'backend' or 'frontend'
    port_assignment: PortAssignment
    output_dir: str
    target_stage: str  # 'development', 'production', 'worker', etc.
    custom_variables: Dict[str, Any]


class DockerfileManager:
    """Manages Dockerfile template system"""
    
    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize Dockerfile manager
        
        Args:
            templates_dir: Directory containing template files
        """
        self.templates_dir = templates_dir
        self.template_processor = TemplateProcessor(templates_dir)
        
        # Service type mappings
        self.service_mappings = {
            'common': ['backend', 'frontend'],
            'rag': ['backend', 'frontend'],
            'agent': ['backend', 'frontend']
        }
        
        # Template file mappings
        self.template_files = {
            'backend': {
                'common': 'common/backend/Dockerfile.template',
                'rag': 'rag/backend/Dockerfile.template',
                'agent': 'agent/backend/Dockerfile.template'
            },
            'frontend': {
                'common': 'common/frontend/Dockerfile.template',
                'rag': 'rag/frontend/Dockerfile.template',
                'agent': 'agent/frontend/Dockerfile.template'
            }
        }
        
        # Default build configurations
        self.default_configs = {
            'backend': {
                'python_version': '3.11',
                'base_image': 'python:3.11-slim',
                'port': 8000,
                'health_endpoint': '/health',
                'worker_class': 'uvicorn.workers.UvicornWorker',
                'workers': 1
            },
            'frontend': {
                'node_version': '18',
                'base_image': 'node:18-alpine',
                'port': 3000,
                'health_endpoint': '/api/health',
                'build_command': 'npm run build',
                'start_command': 'npm start'
            }
        }
    
    def get_supported_services(self, template_type: str) -> List[str]:
        """
        Get list of supported services for a template type
        
        Args:
            template_type: Type of template (common, rag, agent)
            
        Returns:
            List of supported service types
        """
        return self.service_mappings.get(template_type, [])
    
    def generate_dockerfile(self, config: DockerfileConfig) -> str:
        """
        Generate Dockerfile from template
        
        Args:
            config: Dockerfile configuration
            
        Returns:
            Generated Dockerfile content
        """
        # Get template file path
        template_file = self.template_files.get(config.service_type, {}).get(config.template_type)
        
        if not template_file:
            raise ValueError(
                f"No {config.service_type} Dockerfile template available for {config.template_type} projects"
            )
        
        template_path = os.path.join(self.templates_dir, template_file)
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Dockerfile template not found: {template_path}")
        
        # Create template context
        context = create_template_context(
            username=config.username,
            project_name=config.project_name,
            template_type=config.template_type,
            port_assignment=config.port_assignment,
            has_common_project=False  # Dockerfile generation is service-specific
        )
        
        # Generate template variables
        variables = self.template_processor.generate_template_variables(context)
        
        # Add Dockerfile-specific variables
        variables.update(self._generate_dockerfile_variables(config))
        
        # Add custom variables
        variables.update(config.custom_variables)
        
        # Process template
        return self.template_processor.process_template_file(template_path, variables)
    
    def _generate_dockerfile_variables(self, config: DockerfileConfig) -> Dict[str, Any]:
        """Generate Dockerfile-specific template variables"""
        # Get default configuration for service type
        defaults = self.default_configs.get(config.service_type, {})
        
        # Get port assignments
        backend_port = None
        frontend_port = None
        
        ports = config.port_assignment.all_ports
        if len(ports) >= 2:
            backend_port = ports[0]
            frontend_port = ports[1]
        elif len(ports) == 1:
            if config.service_type == 'backend':
                backend_port = ports[0]
            else:
                frontend_port = ports[0]
        
        variables = {
            'SERVICE_TYPE': config.service_type,
            'TARGET_STAGE': config.target_stage,
            'BUILD_DATE': datetime.now().isoformat(),
            'BACKEND_PORT': backend_port or defaults.get('port', 8000),
            'FRONTEND_PORT': frontend_port or defaults.get('port', 3000),
            'HEALTH_ENDPOINT': defaults.get('health_endpoint', '/health'),
            'PYTHON_VERSION': defaults.get('python_version', '3.11'),
            'NODE_VERSION': defaults.get('node_version', '18'),
            'BASE_IMAGE': defaults.get('base_image', 'python:3.11-slim')
        }
        
        # Add service-specific variables
        if config.service_type == 'backend':
            variables.update({
                'WORKER_CLASS': defaults.get('worker_class', 'uvicorn.workers.UvicornWorker'),
                'WORKERS': defaults.get('workers', 1),
                'UVICORN_HOST': '0.0.0.0',
                'UVICORN_PORT': backend_port or 8000
            })
        elif config.service_type == 'frontend':
            variables.update({
                'BUILD_COMMAND': defaults.get('build_command', 'npm run build'),
                'START_COMMAND': defaults.get('start_command', 'npm start'),
                'DEV_COMMAND': 'npm run dev',
                'NEXT_PORT': frontend_port or 3000
            })
        
        # Add template-specific variables
        if config.template_type == 'rag':
            variables.update({
                'MAX_FILE_SIZE': '50MB',
                'CHUNK_SIZE': 1000,
                'CHUNK_OVERLAP': 200,
                'EMBEDDING_MODEL': 'text-embedding-ada-002',
                'VECTOR_DIMENSION': 1536,
                'OPENAI_API_BASE': 'https://api.openai.com/v1'
            })
        elif config.template_type == 'agent':
            variables.update({
                'AGENT_MAX_ITERATIONS': 10,
                'AGENT_TIMEOUT': 300,
                'MEMORY_RETENTION_DAYS': 30,
                'TOOL_EXECUTION_TIMEOUT': 60,
                'MAX_CONCURRENT_AGENTS': 5,
                'WORKER_CONCURRENCY': 4,
                'TASK_TIMEOUT': 600,
                'ENABLE_TOOL_SAFETY_CHECKS': 'true',
                'AGENT_LOG_LEVEL': 'INFO',
                'WORKER_LOG_LEVEL': 'INFO'
            })
        
        return variables
    
    def validate_dockerfile(self, dockerfile_content: str, service_type: str) -> List[str]:
        """
        Validate Dockerfile content
        
        Args:
            dockerfile_content: Dockerfile content
            service_type: Type of service (backend, frontend)
            
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        lines = dockerfile_content.split('\n')
        
        # Check for multi-stage build
        if 'FROM' not in dockerfile_content or dockerfile_content.count('FROM') < 2:
            warnings.append("Consider using multi-stage build for optimization")
        
        # Check for non-root user
        if 'USER' not in dockerfile_content:
            warnings.append("Missing USER instruction - running as root is a security risk")
        
        # Check for health check
        if 'HEALTHCHECK' not in dockerfile_content:
            warnings.append("Missing HEALTHCHECK instruction")
        
        # Check for proper signal handling
        if 'dumb-init' not in dockerfile_content and 'tini' not in dockerfile_content:
            warnings.append("Consider using dumb-init or tini for proper signal handling")
        
        # Check for security best practices
        if '--no-cache-dir' not in dockerfile_content:
            warnings.append("Consider using --no-cache-dir for pip/npm installs")
        
        # Service-specific validations
        if service_type == 'backend':
            warnings.extend(self._validate_backend_dockerfile(dockerfile_content))
        elif service_type == 'frontend':
            warnings.extend(self._validate_frontend_dockerfile(dockerfile_content))
        
        return warnings
    
    def _validate_backend_dockerfile(self, content: str) -> List[str]:
        """Validate backend-specific Dockerfile content"""
        warnings = []
        
        # Check for Python best practices
        if 'PYTHONUNBUFFERED' not in content:
            warnings.append("Missing PYTHONUNBUFFERED environment variable")
        
        if 'PYTHONDONTWRITEBYTECODE' not in content:
            warnings.append("Missing PYTHONDONTWRITEBYTECODE environment variable")
        
        # Check for dependency management
        if 'requirements.txt' not in content:
            warnings.append("No requirements.txt found - dependency management unclear")
        
        # Check for proper port exposure
        if 'EXPOSE' not in content:
            warnings.append("Missing EXPOSE instruction")
        
        return warnings
    
    def _validate_frontend_dockerfile(self, content: str) -> List[str]:
        """Validate frontend-specific Dockerfile content"""
        warnings = []
        
        # Check for Node.js best practices
        if 'NODE_ENV' not in content:
            warnings.append("Missing NODE_ENV environment variable")
        
        # Check for package management
        if 'package.json' not in content:
            warnings.append("No package.json found - dependency management unclear")
        
        # Check for build optimization
        if 'npm ci' not in content and 'yarn install --frozen-lockfile' not in content:
            warnings.append("Consider using npm ci or yarn install --frozen-lockfile for reproducible builds")
        
        return warnings
    
    def create_dockerfile_files(self, config: DockerfileConfig) -> Dict[str, str]:
        """
        Create Dockerfile files for a project
        
        Args:
            config: Dockerfile configuration
            
        Returns:
            Dictionary mapping file paths to their content
        """
        supported_services = self.get_supported_services(config.template_type)
        created_files = {}
        
        for service_type in supported_services:
            if config.service_type == 'all' or config.service_type == service_type:
                # Create config for this service type
                service_config = DockerfileConfig(
                    username=config.username,
                    project_name=config.project_name,
                    template_type=config.template_type,
                    service_type=service_type,
                    port_assignment=config.port_assignment,
                    output_dir=config.output_dir,
                    target_stage=config.target_stage,
                    custom_variables=config.custom_variables
                )
                
                try:
                    # Generate Dockerfile content
                    dockerfile_content = self.generate_dockerfile(service_config)
                    
                    # Validate Dockerfile
                    warnings = self.validate_dockerfile(dockerfile_content, service_type)
                    if warnings:
                        print(f"⚠️  {service_type.upper()} Dockerfile validation warnings:")
                        for warning in warnings[:3]:
                            print(f"  - {warning}")
                        if len(warnings) > 3:
                            print(f"  ... and {len(warnings) - 3} more warnings")
                    
                    # Determine output file path
                    output_file = os.path.join(config.output_dir, service_type, 'Dockerfile')
                    
                    # Create directory if it doesn't exist
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    
                    # Write file
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(dockerfile_content)
                    
                    created_files[output_file] = dockerfile_content
                    
                except Exception as e:
                    print(f"⚠️  Failed to create {service_type} Dockerfile: {e}")
        
        return created_files
    
    def get_build_info(self, config: DockerfileConfig) -> Dict[str, Any]:
        """
        Get build information for a Dockerfile configuration
        
        Args:
            config: Dockerfile configuration
            
        Returns:
            Dictionary with build information
        """
        variables = self._generate_dockerfile_variables(config)
        
        build_info = {
            'username': config.username,
            'project_name': config.project_name,
            'template_type': config.template_type,
            'service_type': config.service_type,
            'target_stage': config.target_stage,
            'build_context': f"./{config.service_type}",
            'dockerfile_path': f"./{config.service_type}/Dockerfile",
            'image_name': f"{config.username}-{config.project_name}-{config.service_type}",
            'image_tag': variables.get('BUILD_DATE', 'latest'),
            'ports': [],
            'environment': {}
        }
        
        # Add port information
        if config.service_type == 'backend':
            build_info['ports'].append(variables.get('BACKEND_PORT', 8000))
        elif config.service_type == 'frontend':
            build_info['ports'].append(variables.get('FRONTEND_PORT', 3000))
        
        # Add environment variables
        build_info['environment'] = {
            'NODE_ENV': 'production' if config.target_stage == 'production' else 'development',
            'PYTHONUNBUFFERED': '1',
            'BUILD_DATE': variables.get('BUILD_DATE')
        }
        
        return build_info


def create_dockerfile_config(username: str, project_name: str, template_type: str,
                           service_type: str, port_assignment: PortAssignment,
                           output_dir: str, target_stage: str = 'production',
                           custom_variables: Optional[Dict[str, Any]] = None) -> DockerfileConfig:
    """
    Create Dockerfile configuration
    
    Args:
        username: Student's login ID
        project_name: Name of the project
        template_type: Type of template (common, rag, agent)
        service_type: Type of service (backend, frontend, all)
        port_assignment: Student's port assignment
        output_dir: Output directory for generated files
        target_stage: Target build stage (development, production, worker)
        custom_variables: Custom template variables
        
    Returns:
        DockerfileConfig object
    """
    return DockerfileConfig(
        username=username,
        project_name=project_name,
        template_type=template_type,
        service_type=service_type,
        port_assignment=port_assignment,
        output_dir=output_dir,
        target_stage=target_stage,
        custom_variables=custom_variables or {}
    )


# Convenience functions for common operations
def generate_backend_dockerfile(username: str, project_name: str, template_type: str,
                              port_assignment: PortAssignment, output_dir: str,
                              target_stage: str = 'production') -> str:
    """Generate backend Dockerfile"""
    manager = DockerfileManager()
    config = create_dockerfile_config(
        username=username,
        project_name=project_name,
        template_type=template_type,
        service_type='backend',
        port_assignment=port_assignment,
        output_dir=output_dir,
        target_stage=target_stage
    )
    return manager.generate_dockerfile(config)


def generate_frontend_dockerfile(username: str, project_name: str, template_type: str,
                               port_assignment: PortAssignment, output_dir: str,
                               target_stage: str = 'production') -> str:
    """Generate frontend Dockerfile"""
    manager = DockerfileManager()
    config = create_dockerfile_config(
        username=username,
        project_name=project_name,
        template_type=template_type,
        service_type='frontend',
        port_assignment=port_assignment,
        output_dir=output_dir,
        target_stage=target_stage
    )
    return manager.generate_dockerfile(config)


def create_all_dockerfiles(username: str, project_name: str, template_type: str,
                         port_assignment: PortAssignment, output_dir: str,
                         target_stage: str = 'production') -> Dict[str, str]:
    """Create all Dockerfiles for a project"""
    manager = DockerfileManager()
    config = create_dockerfile_config(
        username=username,
        project_name=project_name,
        template_type=template_type,
        service_type='all',
        port_assignment=port_assignment,
        output_dir=output_dir,
        target_stage=target_stage
    )
    return manager.create_dockerfile_files(config)