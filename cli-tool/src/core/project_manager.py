#!/usr/bin/env python3
"""
Project Management System

Handles project creation, template processing, and metadata tracking
for multi-student Docker Compose environments.
"""

import os
import json
import shutil
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from src.core.template_processor import TemplateProcessor, create_template_context
from src.core.docker_compose_manager import DockerComposeManager, create_docker_compose_config
from src.core.database_manager import DatabaseManager, create_database_config
from src.core.dockerfile_manager import DockerfileManager, create_dockerfile_config
from src.config.readme_manager import ReadmeManager, create_readme_config
from src.config.setup_script_manager import SetupScriptManager, create_setup_script_config
from src.core.port_assignment import PortAssignment


@dataclass
class ProjectConfig:
    """Project configuration and metadata"""
    project_name: str
    template_type: str
    username: str
    created_at: str
    port_assignment: Dict[str, Any]
    services: List[str]
    ports_used: List[int]
    has_common_project: bool
    project_path: str
    status: str = "active"
    last_updated: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProjectManager:
    """Manages project creation and lifecycle"""
    
    def __init__(self, base_dir: Optional[str] = None, templates_dir: str = "templates"):
        """
        Initialize project manager
        
        Args:
            base_dir: Base directory for projects (default: ~/dockeredServices)
            templates_dir: Directory containing template files
        """
        self.base_dir = base_dir or os.path.expanduser("~/dockeredServices")
        self.templates_dir = templates_dir
        
        # Initialize component managers
        self.template_processor = TemplateProcessor(templates_dir)
        self.docker_compose_manager = DockerComposeManager(templates_dir)
        self.database_manager = DatabaseManager(templates_dir)
        self.dockerfile_manager = DockerfileManager(templates_dir)
        self.readme_manager = ReadmeManager(templates_dir)
        self.setup_script_manager = SetupScriptManager(templates_dir)
        
        # Project configuration file name
        self.config_file = ".project-config.json"
        
        # Ensure base directory exists
        os.makedirs(self.base_dir, exist_ok=True)
    
    def create_project(self, project_name: str, template_type: str, username: str,
                      port_assignment: PortAssignment, has_common_project: bool = False,
                      custom_options: Optional[Dict[str, Any]] = None) -> ProjectConfig:
        """
        Create a new project with all necessary files and configurations
        
        Args:
            project_name: Name of the project
            template_type: Type of template (common, rag, agent)
            username: Student's login ID
            port_assignment: Student's port assignment
            has_common_project: Whether a common project exists
            custom_options: Custom project options
            
        Returns:
            ProjectConfig object with project metadata
        """
        # Validate inputs
        if not project_name or not project_name.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Project name must be alphanumeric (with hyphens/underscores)")
        
        if template_type not in ['common', 'rag', 'agent']:
            raise ValueError(f"Invalid template type: {template_type}")
        
        # Create project directory
        project_path = os.path.join(self.base_dir, project_name)
        
        if os.path.exists(project_path):
            raise FileExistsError(f"Project '{project_name}' already exists at {project_path}")
        
        try:
            # Create project directory structure
            self._create_project_structure(project_path, template_type)
            
            # Generate all project files
            generated_files = self._generate_project_files(
                project_path, project_name, template_type, username,
                port_assignment, has_common_project, custom_options or {}
            )
            
            # Determine services and ports used
            services = self._get_project_services(template_type, has_common_project)
            ports_used = self._get_ports_used(generated_files, port_assignment)
            
            # Create project configuration
            project_config = ProjectConfig(
                project_name=project_name,
                template_type=template_type,
                username=username,
                created_at=datetime.now().isoformat(),
                port_assignment=asdict(port_assignment),
                services=services,
                ports_used=ports_used,
                has_common_project=has_common_project,
                project_path=project_path,
                metadata={
                    "generated_files": list(generated_files.keys()),
                    "custom_options": custom_options or {},
                    "template_version": "1.0.0"
                }
            )
            
            # Save project configuration
            self._save_project_config(project_path, project_config)
            
            print(f"✅ Project '{project_name}' created successfully!")
            print(f"   Location: {project_path}")
            print(f"   Template: {template_type}")
            print(f"   Services: {', '.join(services)}")
            print(f"   Ports used: {len(ports_used)} of {port_assignment.total_ports}")
            
            return project_config
            
        except Exception as e:
            # Clean up on failure
            if os.path.exists(project_path):
                shutil.rmtree(project_path, ignore_errors=True)
            raise RuntimeError(f"Failed to create project '{project_name}': {e}")
    
    def _create_project_structure(self, project_path: str, template_type: str):
        """Create the basic project directory structure"""
        # Create main project directory
        os.makedirs(project_path, exist_ok=True)
        
        # Create subdirectories based on template type
        directories = ["database"]
        
        if template_type in ['rag', 'agent']:
            directories.extend(["backend", "frontend"])
        
        if template_type == 'common':
            directories.extend(["observability"])
        
        # Create all directories
        for directory in directories:
            os.makedirs(os.path.join(project_path, directory), exist_ok=True)
    
    def _generate_project_files(self, project_path: str, project_name: str,
                               template_type: str, username: str,
                               port_assignment: PortAssignment, has_common_project: bool,
                               custom_options: Dict[str, Any]) -> Dict[str, str]:
        """Generate all project files from templates"""
        generated_files = {}
        
        # 1. Generate Docker Compose file
        try:
            compose_config = create_docker_compose_config(
                username=username,
                project_name=project_name,
                template_type=template_type,
                port_assignment=port_assignment,
                output_dir=project_path,
                has_common_project=has_common_project
            )
            
            compose_file = self.docker_compose_manager.create_docker_compose_file(compose_config)
            generated_files["docker-compose.yml"] = compose_file
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to generate Docker Compose file: {e}")
        
        # 2. Generate database initialization scripts
        try:
            db_config = create_database_config(
                username=username,
                project_name=project_name,
                template_type=template_type,
                port_assignment=port_assignment,
                database_type="all",
                output_dir=project_path
            )
            
            db_files = self.database_manager.create_database_init_files(db_config)
            generated_files.update(db_files)
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to generate database files: {e}")
        
        # 3. Generate Dockerfiles (for rag and agent projects)
        if template_type in ['rag', 'agent']:
            try:
                dockerfile_config = create_dockerfile_config(
                    username=username,
                    project_name=project_name,
                    template_type=template_type,
                    service_type="all",
                    port_assignment=port_assignment,
                    output_dir=project_path,
                    target_stage="development"
                )
                
                dockerfile_files = self.dockerfile_manager.create_dockerfile_files(dockerfile_config)
                generated_files.update(dockerfile_files)
                
            except Exception as e:
                print(f"⚠️  Warning: Failed to generate Dockerfiles: {e}")
        
        # 4. Generate README file
        try:
            readme_content = self._generate_readme(
                project_name, template_type, username, port_assignment, has_common_project
            )
            
            readme_path = os.path.join(project_path, "README.md")
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            generated_files["README.md"] = readme_path
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to generate README: {e}")
        
        # 5. Generate setup script
        try:
            setup_content = self._generate_setup_script(
                project_name, template_type, username, port_assignment, has_common_project
            )
            
            setup_path = os.path.join(project_path, "setup.sh")
            with open(setup_path, 'w', encoding='utf-8') as f:
                f.write(setup_content)
            
            # Make setup script executable
            os.chmod(setup_path, 0o755)
            
            generated_files["setup.sh"] = setup_path
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to generate setup script: {e}")
        
        # 6. Copy observability configuration files (for common projects)
        if template_type == 'common':
            try:
                observability_files = self._copy_observability_configs(project_path)
                generated_files.update(observability_files)
            except Exception as e:
                print(f"⚠️  Warning: Failed to copy observability configs: {e}")
        
        # 7. Validate generated files match docker-compose expectations
        try:
            validation_issues = self._validate_project_files(project_path, template_type)
            if validation_issues:
                print(f"⚠️  Project validation warnings:")
                for issue in validation_issues[:3]:
                    print(f"  - {issue}")
        except Exception as e:
            print(f"⚠️  Warning: Failed to validate project files: {e}")
        
        return generated_files
    
    def _generate_readme(self, project_name: str, template_type: str, username: str,
                        port_assignment: PortAssignment, has_common_project: bool) -> str:
        """Generate README content from template using README manager"""
        try:
            # Create README configuration
            readme_config = create_readme_config(
                username=username,
                project_name=project_name,
                template_type=template_type,
                port_assignment=port_assignment,
                output_dir=".",  # Temporary directory, content will be returned
                has_common_project=has_common_project
            )
            
            # Generate README content using the README manager
            template_path = self.readme_manager._get_readme_template_path(template_type)
            variables = self.readme_manager._generate_readme_variables(readme_config)
            return self.readme_manager._process_readme_template(template_path, variables)
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to generate README with README manager: {e}")
            # Fallback to basic README generation
            return self._generate_basic_readme(project_name, template_type, username, port_assignment)
    
    def _generate_basic_readme(self, project_name: str, template_type: str,
                              username: str, port_assignment: PortAssignment) -> str:
        """Generate a basic README when no template is available"""
        ports = port_assignment.all_ports
        
        readme_content = f"""# {project_name} - {username}

## Project Information

- **Project Name**: {project_name}
- **Template Type**: {template_type}
- **Student**: {username}
- **Created**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Port Assignments

Your allocated ports: {len(ports)} total

"""
        
        if port_assignment.has_two_segments:
            readme_content += f"""- Segment 1: {port_assignment.segment1_start}-{port_assignment.segment1_end}
- Segment 2: {port_assignment.segment2_start}-{port_assignment.segment2_end}
"""
        else:
            readme_content += f"- Port Range: {port_assignment.segment1_start}-{port_assignment.segment1_end}\n"
        
        readme_content += f"""
## Quick Start

1. **Start the services:**
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

## Services

"""
        
        if template_type == 'common':
            readme_content += """- PostgreSQL Database
- MongoDB Database  
- Redis Cache
- ChromaDB Vector Database
- Jaeger Tracing
- Prometheus Metrics
- Grafana Dashboards
"""
        elif template_type == 'rag':
            readme_content += """- Backend API (RAG Processing)
- Frontend Interface (Chat UI)
- PostgreSQL Database (with pgvector)
- Redis Cache
- ChromaDB Vector Database
"""
        elif template_type == 'agent':
            readme_content += """- Agent Backend (AI Orchestration)
- Agent Frontend (Management UI)
- Agent Worker (Background Processing)
- PostgreSQL Database (with pgvector)
- Redis Cache
- ChromaDB Vector Database
"""
        
        readme_content += f"""
## Development

See the setup.sh script for initialization commands and the docker-compose.yml file for service configuration.

For more information, check the project documentation or contact your instructor.
"""
        
        return readme_content
    
    def _generate_setup_script(self, project_name: str, template_type: str, username: str,
                              port_assignment: PortAssignment, has_common_project: bool) -> str:
        """Generate setup script content using setup script manager"""
        try:
            # Get project services
            services = self._get_project_services(template_type, has_common_project)
            
            # Create setup script configuration
            setup_config = create_setup_script_config(
                username=username,
                project_name=project_name,
                template_type=template_type,
                port_assignment=port_assignment,
                output_dir=".",  # Temporary directory, content will be returned
                services=services,
                has_common_project=has_common_project
            )
            
            # Generate setup script content using the setup script manager
            return self.setup_script_manager._generate_setup_script_content(setup_config)
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to generate setup script with setup script manager: {e}")
            # Fallback to basic setup script generation
            return self._generate_basic_setup_script(project_name, template_type, username, port_assignment, has_common_project)
    
    def _generate_basic_setup_script(self, project_name: str, template_type: str, username: str,
                                   port_assignment: PortAssignment, has_common_project: bool) -> str:
        """Generate basic setup script as fallback"""
        setup_content = f"""#!/bin/bash
# Setup script for {project_name} - {username}
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

set -e  # Exit on any error

echo "🚀 Setting up {project_name} ({template_type} project)"
echo "Student: {username}"
echo "Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

echo "✅ Docker and Docker Compose are available"

"""
        
        if has_common_project and template_type != 'common':
            setup_content += f"""
# Check if common project is running
echo "🔍 Checking for common project..."
if docker network ls | grep -q "{username}-network"; then
    echo "✅ Common project network found"
else
    echo "⚠️  Common project network not found. Make sure to start the common project first:"
    echo "   cd ../common && docker-compose up -d"
fi

"""
        
        setup_content += """
# Initialize database if needed
if [ -f "database/init.sql" ]; then
    echo "📊 Database initialization script found"
fi

if [ -f "database/init.js" ]; then
    echo "📊 MongoDB initialization script found"
fi

# Build and start services
echo "🔧 Building and starting services..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
docker-compose ps

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Check service status: docker-compose ps"
echo "  2. View logs: docker-compose logs -f"
echo "  3. Access your services at the assigned ports"
echo ""
echo "📖 For more information, see README.md"
"""
        
        return setup_content
    
    def _get_project_services(self, template_type: str, has_common_project: bool) -> List[str]:
        """Get list of services for a project type"""
        if template_type == 'common':
            return ['postgres', 'mongodb', 'redis', 'chromadb', 'jaeger', 'prometheus', 'grafana']
        elif template_type == 'rag':
            services = ['backend', 'frontend']
            if not has_common_project:
                services.extend(['postgres', 'redis', 'chromadb'])
            return services
        elif template_type == 'agent':
            services = ['agent-backend', 'agent-frontend', 'agent-worker']
            if not has_common_project:
                services.extend(['postgres', 'redis', 'chromadb'])
            return services
        else:
            return []
    
    def _get_ports_used(self, generated_files: Dict[str, str], port_assignment: PortAssignment) -> List[int]:
        """Extract ports used from generated files"""
        ports_used = []
        
        # Extract ports from docker-compose.yml if it exists
        compose_file = generated_files.get("docker-compose.yml")
        if compose_file and os.path.exists(compose_file):
            try:
                port_mappings = self.docker_compose_manager.extract_port_mappings(
                    open(compose_file, 'r').read()
                )
                
                for host_port, _, _ in port_mappings:
                    if host_port in port_assignment.all_ports:
                        ports_used.append(host_port)
                        
            except Exception:
                pass  # Ignore errors in port extraction
        
        return sorted(list(set(ports_used)))
    
    def _save_project_config(self, project_path: str, config: ProjectConfig):
        """Save project configuration to file"""
        config_path = os.path.join(project_path, self.config_file)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(config), f, indent=2, default=str)
    
    def load_project_config(self, project_path: str) -> Optional[ProjectConfig]:
        """Load project configuration from file"""
        config_path = os.path.join(project_path, self.config_file)
        
        if not os.path.exists(config_path):
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return ProjectConfig(**data)
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to load project config: {e}")
            return None
    
    def list_projects(self, username: Optional[str] = None) -> List[ProjectConfig]:
        """List all projects, optionally filtered by username"""
        projects = []
        
        if not os.path.exists(self.base_dir):
            return projects
        
        for item in os.listdir(self.base_dir):
            project_path = os.path.join(self.base_dir, item)
            
            if os.path.isdir(project_path):
                config = self.load_project_config(project_path)
                
                if config and (username is None or config.username == username):
                    projects.append(config)
        
        return sorted(projects, key=lambda p: p.created_at, reverse=True)
    
    def get_project_status(self, project_name: str) -> Dict[str, Any]:
        """Get detailed status information for a project"""
        project_path = os.path.join(self.base_dir, project_name)
        
        if not os.path.exists(project_path):
            return {"error": f"Project '{project_name}' not found"}
        
        config = self.load_project_config(project_path)
        
        if not config:
            return {"error": f"Project configuration not found for '{project_name}'"}
        
        # Check if docker-compose.yml exists and get service info
        compose_file = os.path.join(project_path, "docker-compose.yml")
        service_info = {}
        
        if os.path.exists(compose_file):
            try:
                with open(compose_file, 'r') as f:
                    compose_content = f.read()
                
                service_info = self.docker_compose_manager.get_service_info(compose_content)
                
            except Exception as e:
                service_info = {"error": f"Failed to read compose file: {e}"}
        
        return {
            "project_config": asdict(config),
            "service_info": service_info,
            "project_path": project_path,
            "files_exist": {
                "docker-compose.yml": os.path.exists(os.path.join(project_path, "docker-compose.yml")),
                "README.md": os.path.exists(os.path.join(project_path, "README.md")),
                "setup.sh": os.path.exists(os.path.join(project_path, "setup.sh")),
                "database/init.sql": os.path.exists(os.path.join(project_path, "database/init.sql")),
                "database/init.js": os.path.exists(os.path.join(project_path, "database/init.js"))
            }
        }
    
    def project_exists(self, project_name: str) -> bool:
        """Check if a project already exists"""
        project_path = os.path.join(self.base_dir, project_name)
        return os.path.exists(project_path)
    
    def validate_project(self, project_name: str) -> List[str]:
        """Validate a project and return list of issues"""
        issues = []
        project_path = os.path.join(self.base_dir, project_name)
        
        if not os.path.exists(project_path):
            issues.append(f"Project directory not found: {project_path}")
            return issues
        
        # Check for required files
        required_files = ["docker-compose.yml", "README.md", self.config_file]
        
        for file_name in required_files:
            file_path = os.path.join(project_path, file_name)
            if not os.path.exists(file_path):
                issues.append(f"Missing required file: {file_name}")
        
        # Validate docker-compose.yml if it exists
        compose_file = os.path.join(project_path, "docker-compose.yml")
        if os.path.exists(compose_file):
            try:
                with open(compose_file, 'r') as f:
                    compose_content = f.read()
                
                compose_warnings = self.docker_compose_manager.validate_docker_compose(compose_content)
                issues.extend([f"Docker Compose: {w}" for w in compose_warnings])
                
            except Exception as e:
                issues.append(f"Failed to validate docker-compose.yml: {e}")
        
        return issues
    
    def copy_project(self, source_project: str, destination_project: str, username: str,
                    port_assignment: PortAssignment, custom_options: Optional[Dict[str, Any]] = None) -> ProjectConfig:
        """
        Copy an existing project with automatic port reassignment
        
        Args:
            source_project: Name of the source project to copy
            destination_project: Name of the new project
            username: Student's login ID
            port_assignment: Student's port assignment
            custom_options: Custom project options
            
        Returns:
            ProjectConfig object with new project metadata
        """
        # Validate inputs
        import re
        if not destination_project or not re.match(r'^[a-zA-Z0-9_-]+$', destination_project):
            raise ValueError("Destination project name must be alphanumeric (with hyphens/underscores)")
        
        source_path = os.path.join(self.base_dir, source_project)
        destination_path = os.path.join(self.base_dir, destination_project)
        
        # Check source project exists
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source project '{source_project}' not found")
        
        # Check destination doesn't exist
        if os.path.exists(destination_path):
            raise FileExistsError(f"Destination project '{destination_project}' already exists")
        
        # Load source project configuration
        source_config = self.load_project_config(source_path)
        if not source_config:
            raise ValueError(f"Source project '{source_project}' has no valid configuration")
        
        try:
            print(f"📋 Copying project '{source_project}' to '{destination_project}'")
            print(f"   Source: {source_path}")
            print(f"   Destination: {destination_path}")
            
            # Copy project directory structure
            shutil.copytree(source_path, destination_path)
            
            # Update project files with new configuration
            updated_files = self._update_copied_project_files(
                destination_path, source_project, destination_project,
                username, port_assignment, source_config, custom_options or {}
            )
            
            # Determine services and ports used
            services = self._get_project_services(source_config.template_type, source_config.has_common_project)
            ports_used = self._get_ports_used_from_assignment(port_assignment, len(source_config.ports_used))
            
            # Create new project configuration
            new_config = ProjectConfig(
                project_name=destination_project,
                template_type=source_config.template_type,
                username=username,
                created_at=datetime.now().isoformat(),
                port_assignment=asdict(port_assignment),
                services=services,
                ports_used=ports_used,
                has_common_project=source_config.has_common_project,
                project_path=destination_path,
                metadata={
                    "copied_from": source_project,
                    "updated_files": list(updated_files.keys()),
                    "custom_options": custom_options or {},
                    "template_version": "1.0.0"
                }
            )
            
            # Save new project configuration
            self._save_project_config(destination_path, new_config)
            
            print(f"✅ Project copied successfully!")
            print(f"   Template: {new_config.template_type}")
            print(f"   Services: {', '.join(services)}")
            print(f"   Ports reassigned: {len(ports_used)} ports")
            print(f"   Files updated: {len(updated_files)}")
            
            return new_config
            
        except Exception as e:
            # Clean up on failure
            if os.path.exists(destination_path):
                shutil.rmtree(destination_path, ignore_errors=True)
            raise RuntimeError(f"Failed to copy project '{source_project}': {e}")
    
    def _update_copied_project_files(self, project_path: str, source_name: str, dest_name: str,
                                   username: str, port_assignment: PortAssignment,
                                   source_config: ProjectConfig, custom_options: Dict[str, Any]) -> Dict[str, str]:
        """Update files in copied project with new configuration"""
        updated_files = {}
        
        # Create port mapping from old to new
        old_ports = source_config.ports_used
        new_ports = self._get_ports_used_from_assignment(port_assignment, len(old_ports))
        port_mapping = dict(zip(old_ports, new_ports)) if old_ports else {}
        
        # Files to update
        files_to_update = [
            "docker-compose.yml",
            "README.md",
            "setup.sh",
            "database/init.sql",
            "database/init.js"
        ]
        
        for file_name in files_to_update:
            file_path = os.path.join(project_path, file_name)
            
            if os.path.exists(file_path):
                try:
                    # Read original content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Update content
                    updated_content = self._update_file_content(
                        content, source_name, dest_name, username,
                        source_config.username, port_mapping
                    )
                    
                    # Write updated content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    
                    updated_files[file_name] = file_path
                    
                except Exception as e:
                    print(f"⚠️  Warning: Failed to update {file_name}: {e}")
        
        return updated_files
    
    def _update_file_content(self, content: str, source_name: str, dest_name: str,
                           new_username: str, old_username: str, port_mapping: Dict[int, int]) -> str:
        """Update file content with new project configuration"""
        updated_content = content
        
        # Replace project names
        updated_content = updated_content.replace(source_name, dest_name)
        
        # Replace usernames
        updated_content = updated_content.replace(old_username, new_username)
        
        # Replace ports
        for old_port, new_port in port_mapping.items():
            # Replace port mappings in various formats
            updated_content = updated_content.replace(f'"{old_port}:', f'"{new_port}:')
            updated_content = updated_content.replace(f':{old_port}', f':{new_port}')
            updated_content = updated_content.replace(f'localhost:{old_port}', f'localhost:{new_port}')
            updated_content = updated_content.replace(f'port {old_port}', f'port {new_port}')
            updated_content = updated_content.replace(f'Port: {old_port}', f'Port: {new_port}')
        
        # Update container names (replace old username with new username in container names)
        import re
        
        # Pattern for container names like "old_username-service-name"
        container_pattern = rf'{re.escape(old_username)}-([a-zA-Z0-9-]+)'
        updated_content = re.sub(container_pattern, rf'{new_username}-\1', updated_content)
        
        # Update network names
        network_pattern = rf'{re.escape(old_username)}-([a-zA-Z0-9-]*network[a-zA-Z0-9-]*)'
        updated_content = re.sub(network_pattern, rf'{new_username}-\1', updated_content)
        
        # Update volume names
        volume_pattern = rf'{re.escape(old_username)}-([a-zA-Z0-9-]*data[a-zA-Z0-9-]*)'
        updated_content = re.sub(volume_pattern, rf'{new_username}-\1', updated_content)
        
        # Update database credentials
        updated_content = updated_content.replace(f'{old_username}_user', f'{new_username}_user')
        updated_content = updated_content.replace(f'{old_username}_admin', f'{new_username}_admin')
        updated_content = updated_content.replace(f'{old_username}_password', f'{new_username}_password')
        updated_content = updated_content.replace(f'{old_username}_redis', f'{new_username}_redis')
        
        # Update paths and references
        updated_content = updated_content.replace(f'/{old_username}/', f'/{new_username}/')
        updated_content = updated_content.replace(f'{old_username}/', f'{new_username}/')
        
        return updated_content
    
    def _get_ports_used_from_assignment(self, port_assignment: PortAssignment, num_ports: int) -> List[int]:
        """Get the first N ports from port assignment"""
        available_ports = port_assignment.all_ports
        return available_ports[:min(num_ports, len(available_ports))]
    
    def validate_copy_operation(self, source_project: str, destination_project: str,
                              port_assignment: PortAssignment) -> List[str]:
        """
        Validate a project copy operation
        
        Args:
            source_project: Name of source project
            destination_project: Name of destination project
            port_assignment: Target port assignment
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check project name validity first
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', destination_project):
            issues.append("Destination project name must be alphanumeric (with hyphens/underscores)")
        
        # Check destination project
        destination_path = os.path.join(self.base_dir, destination_project)
        if os.path.exists(destination_path):
            issues.append(f"Destination project '{destination_project}' already exists")
        
        # Check source project
        source_path = os.path.join(self.base_dir, source_project)
        if not os.path.exists(source_path):
            issues.append(f"Source project '{source_project}' does not exist")
            return issues
        
        # Load source configuration
        source_config = self.load_project_config(source_path)
        if not source_config:
            issues.append(f"Source project '{source_project}' has invalid configuration")
            return issues
        
        # Check port availability
        required_ports = len(source_config.ports_used)
        available_ports = len(port_assignment.all_ports)
        
        if required_ports > available_ports:
            issues.append(
                f"Insufficient ports: need {required_ports}, have {available_ports}"
            )
        
        return issues
    
    def get_copy_preview(self, source_project: str, destination_project: str,
                        username: str, port_assignment: PortAssignment) -> Dict[str, Any]:
        """
        Get preview information for a project copy operation
        
        Args:
            source_project: Name of source project
            destination_project: Name of destination project
            username: Target username
            port_assignment: Target port assignment
            
        Returns:
            Dictionary with copy preview information
        """
        source_path = os.path.join(self.base_dir, source_project)
        source_config = self.load_project_config(source_path)
        
        if not source_config:
            return {"error": f"Source project '{source_project}' not found or invalid"}
        
        # Calculate port mapping
        old_ports = source_config.ports_used
        new_ports = self._get_ports_used_from_assignment(port_assignment, len(old_ports))
        port_mapping = dict(zip(old_ports, new_ports)) if old_ports else {}
        
        # Get files that will be updated
        files_to_update = []
        for file_name in ["docker-compose.yml", "README.md", "setup.sh", "database/init.sql", "database/init.js"]:
            file_path = os.path.join(source_path, file_name)
            if os.path.exists(file_path):
                files_to_update.append(file_name)
        
        return {
            "source_project": source_project,
            "destination_project": destination_project,
            "source_config": {
                "template_type": source_config.template_type,
                "username": source_config.username,
                "services": source_config.services,
                "ports_used": source_config.ports_used,
                "has_common_project": source_config.has_common_project
            },
            "target_config": {
                "username": username,
                "ports_assigned": new_ports,
                "port_mapping": port_mapping
            },
            "files_to_update": files_to_update,
            "validation_issues": self.validate_copy_operation(source_project, destination_project, port_assignment)
        }
    
    def _copy_observability_configs(self, project_path: str) -> Dict[str, str]:
        """
        Copy observability configuration files from templates to project
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary of copied files
        """
        copied_files = {}
        
        try:
            from src.config.file_paths import get_observability_config_paths
            
            # Get the correct paths for observability configs
            config_paths = get_observability_config_paths('common')
            
            for config_type, relative_path in config_paths.items():
                # Create full destination path
                dest_path = os.path.join(project_path, relative_path)
                
                # Ensure destination directory exists
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # Determine source file name
                if config_type == 'prometheus':
                    source_file = "prometheus.yml"
                elif config_type == 'otel_collector':
                    source_file = "otel-collector-config.yaml"
                else:
                    continue
                
                # Source: templates/observability/filename
                source_path = os.path.join(self.templates_dir, "observability", source_file)
                
                if os.path.exists(source_path):
                    try:
                        shutil.copy2(source_path, dest_path)
                        copied_files[relative_path] = dest_path
                        print(f"✓ Copied observability config: {source_file} → {relative_path}")
                    except Exception as e:
                        print(f"⚠️  Warning: Failed to copy {source_file}: {e}")
                else:
                    print(f"⚠️  Warning: Observability template not found: {source_path}")
        
        except Exception as e:
            print(f"⚠️  Warning: Failed to use centralized paths, falling back: {e}")
            # Fallback to original implementation
            return self._copy_observability_configs_fallback(project_path)
        
        return copied_files
    
    def _copy_observability_configs_fallback(self, project_path: str) -> Dict[str, str]:
        """Fallback observability config copying (original implementation)"""
        copied_files = {}
        observability_dir = os.path.join(project_path, "observability")
        os.makedirs(observability_dir, exist_ok=True)
        
        config_files = ["prometheus.yml", "otel-collector-config.yaml"]
        
        for config_file in config_files:
            source_path = os.path.join(self.templates_dir, "observability", config_file)
            dest_path = os.path.join(observability_dir, config_file)
            
            if os.path.exists(source_path):
                try:
                    shutil.copy2(source_path, dest_path)
                    copied_files[f"observability/{config_file}"] = dest_path
                    print(f"✓ Copied observability config: {config_file}")
                except Exception as e:
                    print(f"⚠️  Warning: Failed to copy {config_file}: {e}")
        
        return copied_files
    
    def _validate_project_files(self, project_path: str, template_type: str) -> List[str]:
        """
        Validate that generated files match docker-compose expectations
        
        Args:
            project_path: Path to the project directory
            template_type: Type of template used
            
        Returns:
            List of validation issues
        """
        issues = []
        
        try:
            from src.config.file_paths import get_all_output_paths, get_database_file_paths
            
            # Get expected files from centralized configuration
            all_paths = get_all_output_paths(template_type)
            database_paths = get_database_file_paths(template_type)
            
            # Check database files (most critical)
            for db_path in database_paths:
                file_path = os.path.join(project_path, db_path)
                
                if not os.path.exists(file_path):
                    issues.append(f"Missing critical database file: {db_path}")
                elif os.path.isdir(file_path):
                    issues.append(f"Expected file but found directory: {db_path}")
            
            # Check observability files for common template
            if template_type == 'common':
                observability_files = ['prometheus_config', 'otel_collector_config']
                for file_type in observability_files:
                    if file_type in all_paths:
                        file_path = os.path.join(project_path, all_paths[file_type])
                        
                        if not os.path.exists(file_path):
                            issues.append(f"Missing observability file: {all_paths[file_type]}")
                        elif os.path.isdir(file_path):
                            issues.append(f"Expected file but found directory: {all_paths[file_type]}")
        
        except Exception as e:
            # Fallback to hardcoded validation
            print(f"⚠️  Using fallback validation: {e}")
            expected_files = {
                'common': ['database/postgresql/init.sql', 'database/mongodb/init.js'],
                'rag': ['database/init.sql'],
                'agent': ['database/init.sql']
            }
            
            if template_type in expected_files:
                for expected_file in expected_files[template_type]:
                    file_path = os.path.join(project_path, expected_file)
                    
                    if not os.path.exists(file_path):
                        issues.append(f"Missing expected file: {expected_file}")
                    elif os.path.isdir(file_path):
                        issues.append(f"Expected file but found directory: {expected_file}")
        
        return issues


# Convenience functions
def create_project(project_name: str, template_type: str, username: str,
                  port_assignment: PortAssignment, has_common_project: bool = False,
                  base_dir: Optional[str] = None) -> ProjectConfig:
    """Create a new project with default settings"""
    manager = ProjectManager(base_dir)
    return manager.create_project(
        project_name=project_name,
        template_type=template_type,
        username=username,
        port_assignment=port_assignment,
        has_common_project=has_common_project
    )


def list_user_projects(username: str, base_dir: Optional[str] = None) -> List[ProjectConfig]:
    """List all projects for a specific user"""
    manager = ProjectManager(base_dir)
    return manager.list_projects(username)


def get_project_info(project_name: str, base_dir: Optional[str] = None) -> Dict[str, Any]:
    """Get detailed information about a project"""
    manager = ProjectManager(base_dir)
    return manager.get_project_status(project_name)


def copy_project(source_project: str, destination_project: str, username: str,
                port_assignment: PortAssignment, base_dir: Optional[str] = None) -> ProjectConfig:
    """Copy an existing project with default settings"""
    manager = ProjectManager(base_dir)
    return manager.copy_project(
        source_project=source_project,
        destination_project=destination_project,
        username=username,
        port_assignment=port_assignment
    )