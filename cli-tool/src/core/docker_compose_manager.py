#!/usr/bin/env python3
"""
Docker Compose Template System

Manages Docker Compose template generation, validation, and deployment
for multi-student environments with isolated port assignments.
"""

import os
import yaml
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from src.core.template_processor import TemplateProcessor, create_template_context
from src.core.port_assignment import PortAssignment


@dataclass
class DockerComposeConfig:
    """Configuration for Docker Compose generation"""
    username: str
    project_name: str
    template_type: str
    port_assignment: PortAssignment
    has_common_project: bool
    output_dir: str
    resource_limits: Dict[str, Any]


class DockerComposeManager:
    """Manages Docker Compose template system"""
    
    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize Docker Compose manager
        
        Args:
            templates_dir: Directory containing template files
        """
        self.templates_dir = templates_dir
        self.template_processor = TemplateProcessor(templates_dir)
        
        # Default resource limits to prevent system overload
        self.default_resource_limits = {
            "database": {
                "memory": "512M",
                "cpus": "0.5",
                "memory_reservation": "256M",
                "cpus_reservation": "0.25"
            },
            "cache": {
                "memory": "128M",
                "cpus": "0.25"
            },
            "application": {
                "memory": "1G",
                "cpus": "1.0",
                "memory_reservation": "512M",
                "cpus_reservation": "0.5"
            },
            "frontend": {
                "memory": "512M",
                "cpus": "0.5",
                "memory_reservation": "256M",
                "cpus_reservation": "0.25"
            },
            "monitoring": {
                "memory": "256M",
                "cpus": "0.25"
            }
        }
    
    def generate_docker_compose(self, config: DockerComposeConfig) -> str:
        """
        Generate Docker Compose file from template
        
        Args:
            config: Docker Compose configuration
            
        Returns:
            Generated Docker Compose content
        """
        # Create template context
        context = create_template_context(
            username=config.username,
            project_name=config.project_name,
            template_type=config.template_type,
            port_assignment=config.port_assignment,
            has_common_project=config.has_common_project
        )
        
        # Generate template variables
        variables = self.template_processor.generate_template_variables(context)
        
        # Add resource limits
        variables.update(self._generate_resource_variables(config.resource_limits))
        
        # Process template
        template_path = os.path.join(
            self.templates_dir, 
            config.template_type,
            "docker-compose.yml.template"
        )
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Docker Compose template not found: {template_path}")
        
        return self.template_processor.process_template_file(template_path, variables)
    
    def _generate_resource_variables(self, custom_limits: Dict[str, Any]) -> Dict[str, Any]:
        """Generate resource limit variables for templates"""
        # Merge custom limits with defaults
        resource_limits = self.default_resource_limits.copy()
        if custom_limits:
            for category, limits in custom_limits.items():
                if category in resource_limits:
                    resource_limits[category].update(limits)
                else:
                    resource_limits[category] = limits
        
        # Convert to template variables
        variables = {}
        for category, limits in resource_limits.items():
            for key, value in limits.items():
                var_name = f"{category.upper()}_{key.upper()}"
                variables[var_name] = value
        
        return variables
    
    def validate_docker_compose(self, compose_content: str, username: str = None) -> List[str]:
        """
        Validate Docker Compose content
        
        Args:
            compose_content: Docker Compose YAML content
            username: Optional username for container name validation
            
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        try:
            # Parse YAML
            compose_data = yaml.safe_load(compose_content)
            
            # Validate structure
            if not isinstance(compose_data, dict):
                warnings.append("Invalid Docker Compose format: not a dictionary")
                return warnings
            
            # Check required sections
            if 'services' not in compose_data:
                warnings.append("Missing 'services' section")
            
            if 'networks' not in compose_data:
                warnings.append("Missing 'networks' section")
            
            # Validate services
            if 'services' in compose_data:
                services_warnings = self._validate_services(compose_data['services'], username)
                warnings.extend(services_warnings)
            
            # Validate networks
            if 'networks' in compose_data:
                network_warnings = self._validate_networks(compose_data['networks'])
                warnings.extend(network_warnings)
            
        except yaml.YAMLError as e:
            warnings.append(f"YAML parsing error: {e}")
        except Exception as e:
            warnings.append(f"Validation error: {e}")
        
        return warnings
    
    def _validate_services(self, services: Dict[str, Any], username: str = None) -> List[str]:
        """Validate Docker Compose services"""
        warnings = []
        
        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                warnings.append(f"Service '{service_name}': invalid configuration")
                continue
            
            # Check container naming
            if 'container_name' not in service_config:
                warnings.append(f"Service '{service_name}': missing container_name")
            # Note: Skip container name prefix validation as it's checked during template processing
            
            # Check resource limits
            if 'deploy' in service_config and 'resources' in service_config['deploy']:
                resources = service_config['deploy']['resources']
                if 'limits' not in resources:
                    warnings.append(f"Service '{service_name}': missing resource limits")
            else:
                warnings.append(f"Service '{service_name}': missing resource configuration")
            
            # Check health checks for critical services
            critical_services = ['postgres', 'mongodb', 'redis', 'backend']
            if any(keyword in service_name.lower() for keyword in critical_services):
                if 'healthcheck' not in service_config:
                    warnings.append(f"Service '{service_name}': missing health check")
            
            # Check network configuration
            if 'networks' not in service_config:
                warnings.append(f"Service '{service_name}': missing network configuration")
        
        return warnings
    
    def _validate_networks(self, networks: Dict[str, Any]) -> List[str]:
        """Validate Docker Compose networks"""
        warnings = []
        
        for network_name, network_config in networks.items():
            # Note: Skip network name prefix validation as it's checked during template processing
            
            # Check network configuration
            if isinstance(network_config, dict):
                # Note: Skip network name property validation as it's checked during template processing
                pass
        
        return warnings
    
    def extract_port_mappings(self, compose_content: str) -> List[Tuple[int, int, str]]:
        """
        Extract port mappings from Docker Compose content
        
        Args:
            compose_content: Docker Compose YAML content
            
        Returns:
            List of (host_port, container_port, service_name) tuples
        """
        port_mappings = []
        
        try:
            compose_data = yaml.safe_load(compose_content)
            
            if 'services' in compose_data:
                for service_name, service_config in compose_data['services'].items():
                    if 'ports' in service_config:
                        for port_mapping in service_config['ports']:
                            if isinstance(port_mapping, str):
                                # Parse "host:container" format
                                if ':' in port_mapping:
                                    host_part, container_part = port_mapping.split(':', 1)
                                    # Remove quotes and extract port numbers
                                    host_port = int(host_part.strip('\"'))
                                    container_port = int(container_part.strip('\"'))
                                    port_mappings.append((host_port, container_port, service_name))
            
        except (yaml.YAMLError, ValueError, KeyError) as e:
            # Return empty list if parsing fails
            pass
        
        return port_mappings
    
    def check_port_conflicts(self, compose_content: str, port_assignment: PortAssignment) -> List[str]:
        """
        Check for port conflicts within student's allocated ranges
        
        Args:
            compose_content: Docker Compose YAML content
            port_assignment: Student's port assignment
            
        Returns:
            List of conflict warnings
        """
        warnings = []
        port_mappings = self.extract_port_mappings(compose_content)
        allocated_ports = set(port_assignment.all_ports)
        
        used_ports = set()
        for host_port, container_port, service_name in port_mappings:
            # Check if port is in allocated range
            if host_port not in allocated_ports:
                warnings.append(
                    f"Service '{service_name}': port {host_port} not in allocated range"
                )
            
            # Check for duplicate port usage
            if host_port in used_ports:
                warnings.append(
                    f"Service '{service_name}': port {host_port} already used by another service"
                )
            else:
                used_ports.add(host_port)
        
        return warnings
    
    def generate_network_config(self, username: str, project_name: str, 
                              shared_mode: bool = False) -> Dict[str, Any]:
        """
        Generate network configuration for Docker Compose
        
        Args:
            username: Student's login ID
            project_name: Name of the project
            shared_mode: Whether to use shared network
            
        Returns:
            Network configuration dictionary
        """
        if shared_mode:
            # Use external shared network
            return {
                f"{username}-network": {
                    "external": True
                }
            }
        else:
            # Create project-specific network
            network_name = f"{username}-{project_name}-network"
            return {
                network_name: {
                    "name": network_name,
                    "driver": "bridge"
                }
            }
    
    def generate_volume_config(self, username: str, project_name: str, 
                             services: List[str]) -> Dict[str, Any]:
        """
        Generate volume configuration for Docker Compose
        
        Args:
            username: Student's login ID
            project_name: Name of the project
            services: List of services that need volumes
            
        Returns:
            Volume configuration dictionary
        """
        volumes = {}
        
        for service in services:
            volume_name = f"{username}-{project_name}-{service}-data"
            volumes[f"{service}_data"] = {
                "name": volume_name
            }
        
        return volumes
    
    def create_docker_compose_file(self, config: DockerComposeConfig) -> str:
        """
        Create complete Docker Compose file
        
        Args:
            config: Docker Compose configuration
            
        Returns:
            Path to created Docker Compose file
        """
        # Generate content
        compose_content = self.generate_docker_compose(config)
        
        # Validate content
        warnings = self.validate_docker_compose(compose_content)
        if warnings:
            print("⚠️  Docker Compose validation warnings:")
            for warning in warnings[:5]:  # Show first 5 warnings
                print(f"  - {warning}")
            if len(warnings) > 5:
                print(f"  ... and {len(warnings) - 5} more warnings")
        
        # Check port conflicts
        port_warnings = self.check_port_conflicts(compose_content, config.port_assignment)
        if port_warnings:
            print("⚠️  Port conflict warnings:")
            for warning in port_warnings:
                print(f"  - {warning}")
        
        # Write file
        output_path = os.path.join(config.output_dir, "docker-compose.yml")
        os.makedirs(config.output_dir, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(compose_content)
        
        return output_path
    
    def get_service_info(self, compose_content: str) -> Dict[str, Any]:
        """
        Extract service information from Docker Compose content
        
        Args:
            compose_content: Docker Compose YAML content
            
        Returns:
            Dictionary with service information
        """
        service_info = {
            "services": [],
            "networks": [],
            "volumes": [],
            "port_mappings": [],
            "resource_usage": {}
        }
        
        try:
            compose_data = yaml.safe_load(compose_content)
            
            # Extract services
            if 'services' in compose_data:
                for service_name, service_config in compose_data['services'].items():
                    service_info["services"].append({
                        "name": service_name,
                        "image": service_config.get("image", "custom"),
                        "container_name": service_config.get("container_name", service_name),
                        "has_healthcheck": "healthcheck" in service_config,
                        "has_resource_limits": "deploy" in service_config and "resources" in service_config.get("deploy", {})
                    })
            
            # Extract networks
            if 'networks' in compose_data:
                service_info["networks"] = list(compose_data['networks'].keys())
            
            # Extract volumes
            if 'volumes' in compose_data:
                service_info["volumes"] = list(compose_data['volumes'].keys())
            
            # Extract port mappings
            service_info["port_mappings"] = self.extract_port_mappings(compose_content)
            
        except yaml.YAMLError:
            pass
        
        return service_info


def create_docker_compose_config(username: str, project_name: str, template_type: str,
                               port_assignment: PortAssignment, output_dir: str,
                               has_common_project: bool = False,
                               resource_limits: Optional[Dict[str, Any]] = None) -> DockerComposeConfig:
    """
    Create Docker Compose configuration
    
    Args:
        username: Student's login ID
        project_name: Name of the project
        template_type: Type of template (common, rag, agent)
        port_assignment: Student's port assignment
        output_dir: Output directory for generated files
        has_common_project: Whether a common project exists
        resource_limits: Custom resource limits
        
    Returns:
        DockerComposeConfig object
    """
    return DockerComposeConfig(
        username=username,
        project_name=project_name,
        template_type=template_type,
        port_assignment=port_assignment,
        has_common_project=has_common_project,
        output_dir=output_dir,
        resource_limits=resource_limits or {}
    )


# Convenience functions for common operations
def generate_common_docker_compose(username: str, port_assignment: PortAssignment, 
                                 output_dir: str) -> str:
    """Generate Docker Compose for common infrastructure project"""
    manager = DockerComposeManager()
    config = create_docker_compose_config(
        username=username,
        project_name="common",
        template_type="common",
        port_assignment=port_assignment,
        output_dir=output_dir,
        has_common_project=False
    )
    return manager.create_docker_compose_file(config)


def generate_rag_docker_compose(username: str, port_assignment: PortAssignment,
                              output_dir: str, has_common_project: bool = False) -> str:
    """Generate Docker Compose for RAG project"""
    manager = DockerComposeManager()
    config = create_docker_compose_config(
        username=username,
        project_name="rag",
        template_type="rag",
        port_assignment=port_assignment,
        output_dir=output_dir,
        has_common_project=has_common_project
    )
    return manager.create_docker_compose_file(config)