#!/usr/bin/env python3
"""
Multi-Student Docker Compose CLI Tool

Main entry point for the CLI tool that manages Docker Compose projects
for multiple students with isolated port assignments.
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, Any, Optional, List

from src.security.secure_logger import SecureLogger
from src.core.port_assignment import get_current_user_assignment, PortAssignmentManager
from src.core.project_manager import ProjectManager
from src.maintenance.cleanup_maintenance_tools import (
    MaintenanceManager, 
    perform_cleanup, 
    get_cleanup_suggestions,
    CleanupResult,
    MaintenanceReport
)
from src.utils.error_handling import (
    ExitCode,
    ErrorContext,
    CLIError,
    InvalidArgumentError,
    PermissionError,
    ResourceUnavailableError,
    ProjectError,
    DockerError,
    PortAssignmentError,
    TemplateError,
    ErrorHandler,
    handle_cli_error
)
from src.security.security_validation import (
    SecurityValidator,
    validate_system_security,
    validate_project_security,
    audit_project_operation,
    audit_port_assignment
)


class CLIError(Exception):
    """Base CLI error with exit code"""
    exit_code = 1


class InvalidArgumentError(CLIError):
    """Invalid command arguments"""
    exit_code = 2


class PermissionError(CLIError):
    """Permission denied (unauthorized user, file access)"""
    exit_code = 3


class ResourceUnavailableError(CLIError):
    """Resource unavailable (ports, disk space, Docker)"""
    exit_code = 4


class DockerComposeCLI:
    """Main CLI application class"""
    
    def __init__(self):
        self.logger = SecureLogger()
        self.user_assignment = None
        self.dockered_services_dir = os.path.expanduser("~/dockeredServices")
        self.error_handler = ErrorHandler(self.logger.logger)
        self.security_validator = SecurityValidator(self.logger)
    
    def setup_logging(self, verbose: bool = False, quiet: bool = False):
        """Setup logging configuration"""
        if quiet:
            level = logging.ERROR
        elif verbose:
            level = logging.DEBUG
        else:
            level = logging.INFO
        
        self.logger.setup_logging(level)
    
    def ensure_user_authorized(self):
        """Ensure current user is authorized and load their assignment"""
        try:
            self.user_assignment = get_current_user_assignment()
            self.logger.info(f"User '{self.user_assignment.login_id}' authorized with {self.user_assignment.total_ports} ports")
        except Exception as e:
            context = ErrorContext(
                operation="user_authorization",
                recovery_suggestions=[
                    "Check if you are logged in to the system",
                    "Verify your user account is properly configured",
                    "Contact administrator if authorization continues to fail"
                ]
            )
            raise PermissionError(f"Authorization failed: {e}", context)
    
    def ensure_dockered_services_dir(self):
        """Ensure ~/dockeredServices directory exists"""
        if not os.path.exists(self.dockered_services_dir):
            os.makedirs(self.dockered_services_dir)
            self.logger.info(f"Created dockeredServices directory: {self.dockered_services_dir}")
    
    def cmd_create_project(self, args) -> int:
        """Create a new Docker Compose project"""
        self.logger.info(f"Creating project '{args.project_name}' with template '{args.template}'")
        
        from src.core.project_manager import ProjectManager
        
        try:
            # Initialize project manager
            base_dir = args.base_dir or os.path.expanduser("~/dockeredServices")
            manager = ProjectManager(base_dir=base_dir, templates_dir="templates")
            
            # Check if project already exists
            if manager.project_exists(args.project_name):
                print(f"❌ Project '{args.project_name}' already exists")
                return 1
            
            # Determine shared mode
            has_common_project = args.shared_mode
            if not has_common_project and args.template in ['rag', 'agent']:
                # Check if common project exists and offer shared mode
                common_project_path = os.path.join(base_dir, "common")
                if os.path.exists(common_project_path):
                    has_common_project = self._prompt_shared_mode(args.template, args.project_name)
            
            # Create the project
            print(f"\n🚀 Creating {args.template} project: {args.project_name}")
            print(f"   Mode: {'Shared infrastructure' if has_common_project else 'Self-contained'}")
            print(f"   Owner: {self.user_assignment.login_id}")
            
            project_config = manager.create_project(
                project_name=args.project_name,
                template_type=args.template,
                username=self.user_assignment.login_id,
                port_assignment=self.user_assignment,
                has_common_project=has_common_project
            )
            
            # Show next steps
            self._show_project_next_steps(args.project_name, project_config.project_path, has_common_project)
            
            # Audit log successful project creation
            audit_project_operation(
                operation="create_project",
                user_id=self.user_assignment.login_id,
                project_name=args.project_name,
                success=True,
                details={
                    "template": args.template,
                    "shared_mode": has_common_project,
                    "project_path": project_config.project_path,
                    "ports_assigned": project_config.port_assignment
                }
            )
            
            return 0
            
        except FileExistsError as e:
            print(f"❌ {e}")
            # Audit log failed project creation
            audit_project_operation(
                operation="create_project",
                user_id=self.user_assignment.login_id if self.user_assignment else "unknown",
                project_name=args.project_name,
                success=False,
                details={"error": "project_already_exists", "message": str(e)}
            )
            return 1
        except ValueError as e:
            print(f"❌ Invalid configuration: {e}")
            # Audit log failed project creation
            audit_project_operation(
                operation="create_project",
                user_id=self.user_assignment.login_id if self.user_assignment else "unknown",
                project_name=args.project_name,
                success=False,
                details={"error": "invalid_configuration", "message": str(e)}
            )
            return 1
        except Exception as e:
            print(f"❌ Failed to create project: {e}")
            self.logger.error(f"Project creation failed: {e}")
            # Audit log failed project creation
            audit_project_operation(
                operation="create_project",
                user_id=self.user_assignment.login_id if self.user_assignment else "unknown",
                project_name=args.project_name,
                success=False,
                details={"error": "general_failure", "message": str(e)}
            )
            return 1
    
    def _prompt_shared_mode(self, template_type: str, project_name: str) -> bool:
        """Prompt user for shared vs standalone mode"""
        print(f"\n🔍 Found existing 'common' infrastructure project")
        print(f"📊 Deployment Mode Options:")
        print(f"")
        print(f"   1. Shared Infrastructure (RECOMMENDED)")
        print(f"      ✅ Connect to existing common services")
        print(f"      ✅ Resource efficient - only {template_type} services")
        print(f"      ✅ Saves ports and memory")
        print(f"")
        print(f"   2. Self-Contained")
        print(f"      ⚠️  Includes all infrastructure services")
        print(f"      ⚠️  Uses more ports and resources")
        print(f"")
        
        while True:
            choice = input("Choose deployment mode (1=shared/2=self-contained) [1]: ").strip()
            if choice == "" or choice == "1":
                return True
            elif choice == "2":
                return False
            else:
                print("Please enter 1 or 2 (or press Enter for shared mode)")
    
    def _show_project_next_steps(self, project_name: str, project_path: str, has_common_project: bool):
        """Show next steps after project creation"""
        print(f"\n🎉 Next Steps:")
        print(f"")
        print(f"1. Navigate to your project:")
        print(f"   cd {project_path}")
        print(f"")
        
        if has_common_project:
            print(f"2. Ensure common infrastructure is running:")
            print(f"   cd ../common && ./setup.sh")
            print(f"")
            print(f"3. Start your {project_name} services:")
            print(f"   ./setup.sh")
        else:
            print(f"2. Run the setup script (handles everything automatically):")
            print(f"   ./setup.sh")
        
        print(f"")
        print(f"The setup script will:")
        print(f"   • Validate ports and Docker")
        print(f"   • Start all services with proper isolation")
        print(f"   • Run health checks")
        print(f"   • Show you service URLs and next steps")
        print(f"")
        print(f"📚 See README.md in the project directory for detailed instructions.")

    def _show_common_project_next_steps(self, project_path: str):
        """Show next steps after common project creation"""
        print(f"\n🎉 Common Infrastructure Next Steps:")
        print(f"")
        print(f"1. Navigate to common project:")
        print(f"   cd {project_path}")
        print(f"")
        print(f"2. Start shared infrastructure services:")
        print(f"   docker-compose up -d")
        print(f"")
        print(f"3. Verify all services are healthy:")
        print(f"   docker-compose ps")
        print(f"")
        print(f"4. Access services (using your assigned ports):")
        if len(self.user_assignment.all_ports) > 6:
            print(f"   📊 Grafana: http://localhost:{self.user_assignment.all_ports[6]}")
        if len(self.user_assignment.all_ports) > 4:
            print(f"   🔍 Jaeger: http://localhost:{self.user_assignment.all_ports[4]}")
        if len(self.user_assignment.all_ports) > 5:
            print(f"   📈 Prometheus: http://localhost:{self.user_assignment.all_ports[5]}")
        print(f"")
        print(f"5. Now create application projects that use this infrastructure:")
        print(f"   python cli.py create-project my-rag --template rag")
        print(f"   python cli.py create-project my-agent --template agent")
        print(f"")
        print(f"📚 See README.md in the common directory for service connection details.")

    def _detect_common_project(self) -> Optional[Dict[str, Any]]:
        """Detect existing common project and return its status"""
        common_project_path = os.path.join(self.dockered_services_dir, "common")
        
        if not os.path.exists(common_project_path):
            return None
            
        try:
            # Load project configuration
            manager = ProjectManager(base_dir=self.dockered_services_dir)
            config = manager.load_project_config(common_project_path)
            
            if config and config.template_type == "common":
                # Check if services are running
                compose_file = os.path.join(common_project_path, "docker-compose.yml")
                running_services = []
                
                if os.path.exists(compose_file):
                    try:
                        # Check running containers
                        import subprocess
                        result = subprocess.run(
                            ["docker-compose", "ps", "--services", "--filter", "status=running"],
                            cwd=common_project_path,
                            capture_output=True,
                            text=True
                        )
                        if result.returncode == 0:
                            running_services = result.stdout.strip().split('\n') if result.stdout.strip() else []
                    except Exception:
                        pass  # Docker not available or other error
                
                return {
                    "config": config,
                    "path": common_project_path,
                    "running_services": running_services,
                    "total_services": len(config.services),
                    "is_running": len(running_services) > 0
                }
        except Exception:
            pass
            
        return None

    def _show_common_project_guidance(self, project_type: str):
        """Show guidance for connecting to common project services"""
        common_info = self._detect_common_project()
        
        if not common_info:
            print(f"\n💡 No 'common' infrastructure project found")
            print(f"")
            print(f"📊 Recommended approach for resource efficiency:")
            print(f"   1. Create shared infrastructure: python cli.py create-project common --template common")
            print(f"   2. Create your {project_type} project: python cli.py create-project my-{project_type} --template {project_type}")
            return False
            
        config = common_info["config"]
        is_running = common_info["is_running"]
        running_count = len(common_info["running_services"])
        total_count = common_info["total_services"]
        
        print(f"\n🔍 Found existing 'common' infrastructure project")
        print(f"   📍 Location: {common_info['path']}")
        print(f"   📊 Services: {running_count}/{total_count} running")
        print(f"   🌐 Network: {config.username}-network")
        
        if is_running:
            print(f"   ✅ Status: Active")
        else:
            print(f"   ⚠️  Status: Stopped")
            print(f"")
            print(f"💡 To start common services:")
            print(f"   cd {common_info['path']} && docker-compose up -d")
            
        return True
    
    def _create_application_project(self, args) -> int:
        """Create application project with shared infrastructure option"""
        common_info = self._detect_common_project()
        
        if common_info:
            # Common project exists - show status and offer choice
            config = common_info["config"]
            is_running = common_info["is_running"]
            running_count = len(common_info["running_services"])
            total_count = common_info["total_services"]
            
            print(f"\n🔍 Found existing 'common' infrastructure project")
            print(f"   📍 Location: {common_info['path']}")
            print(f"   📊 Services: {running_count}/{total_count} running")
            print(f"   🌐 Network: {config.username}-network")
            
            if not is_running:
                print(f"   ⚠️  Status: Stopped (can be started later)")
            else:
                print(f"   ✅ Status: Active and ready")
            
            print(f"")
            print(f"📊 Resource Usage Comparison:")
            print(f"")
            print(f"   Option 1: Connect to shared infrastructure (RECOMMENDED)")
            print(f"   ✅ Uses existing databases and services from 'common' project")
            print(f"   ✅ Resource efficient - only creates {args.template} backend/frontend")
            print(f"   ✅ Saves ~6-8 ports, reduces memory usage")
            print(f"   ✅ Shared monitoring and observability")
            print(f"")
            print(f"   Option 2: Create self-contained project")
            print(f"   ⚠️  Creates separate database, Redis, and monitoring services")
            print(f"   ⚠️  Uses ~10-15 ports (you have {len(self.user_assignment.all_ports)} total)")
            print(f"   ⚠️  Higher memory and CPU usage")
            print(f"   ⚠️  Duplicate infrastructure services")
            print(f"")
            
            while True:
                choice = input("Choose deployment mode (1=shared/2=self-contained) [1]: ").strip()
                if choice == "" or choice == "1":
                    print(f"✅ Creating {args.project_name} project in shared mode")
                    return self._create_shared_project(args)
                elif choice == "2":
                    print(f"⚠️  Creating {args.project_name} project in self-contained mode")
                    return self._create_standalone_project(args)
                else:
                    print("Please enter 1 or 2 (or press Enter for default)")
        else:
            # No common project - suggest creating one first
            print(f"\n💡 No 'common' infrastructure project found")
            print(f"")
            print(f"📊 Recommended approach for resource efficiency:")
            print(f"   1. Create shared infrastructure: cli create-project common --template common")
            print(f"   2. Create your {args.template} project: cli create-project {args.project_name} --template {args.template}")
            print(f"")
            print(f"🔄 Alternative: Create self-contained project now")
            print(f"   ⚠️  Will include all services (database, cache, monitoring)")
            print(f"   ⚠️  Uses more ports and resources")
            print(f"")
            
            while True:
                choice = input("Choose: (1=create common first/2=self-contained now/3=cancel) [1]: ").strip()
                if choice == "" or choice == "1":
                    print(f"🏗️  Creating 'common' infrastructure project first...")
                    # Create common project first
                    common_result = self._create_common_project()
                    if common_result == 0:
                        print(f"✅ Common project created successfully")
                        print(f"🔗 Now creating {args.project_name} project in shared mode")
                        return self._create_shared_project(args)
                    else:
                        print(f"❌ Failed to create common project")
                        return common_result
                elif choice == "2":
                    print(f"⚠️  Creating {args.project_name} project in self-contained mode")
                    return self._create_standalone_project(args)
                elif choice == "3":
                    print(f"Operation cancelled")
                    return 0
                else:
                    print("Please enter 1, 2, or 3 (or press Enter for default)")
    
    def _create_standard_project(self, args) -> int:
        """Create standard project (common, custom, etc.)"""
        if args.template == 'common':
            return self._create_common_project()
        else:
            # TODO: Implement other template types
            print(f"Creating standard project: {args.project_name} with template {args.template}")
            return 0
    
    def _create_common_project(self) -> int:
        """Create common infrastructure project"""
        try:
            print(f"🏗️  Creating common infrastructure project...")
            print(f"   📦 PostgreSQL, MongoDB, Redis, ChromaDB")
            print(f"   📊 Jaeger, Prometheus, Grafana")
            print(f"   👤 Owner: {self.user_assignment.login_id}")
            print(f"   🌐 Shared network: {self.user_assignment.login_id}-network")
            
            # Create the common project
            project_config = create_project(
                project_name="common",
                template_type="common",
                username=self.user_assignment.login_id,
                port_assignment=self.user_assignment,
                has_common_project=False,  # Common project doesn't depend on itself
                base_dir=self.dockered_services_dir
            )
            
            print(f"✅ Common project created successfully!")
            print(f"   Location: {project_config.project_path}")
            print(f"   Services: {', '.join(project_config.services)}")
            print(f"   Ports used: {len(project_config.ports_used)} of {len(self.user_assignment.all_ports)}")
            
            # Show next steps for common project
            self._show_common_project_next_steps(project_config.project_path)
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to create common project: {e}")
            return 1
    
    def _create_shared_project(self, args) -> int:
        """Create application project that connects to common infrastructure"""
        try:
            print(f"🔗 Creating {args.project_name} project (shared mode)...")
            print(f"   📱 {args.template.upper()} backend and frontend only")
            print(f"   🔌 Connects to existing common infrastructure")
            print(f"   👤 Owner: {self.user_assignment.login_id}")
            print(f"   🌐 Uses shared network: {self.user_assignment.login_id}-network")
            
            # Create the project in shared mode
            project_config = create_project(
                project_name=args.project_name,
                template_type=args.template,
                username=self.user_assignment.login_id,
                port_assignment=self.user_assignment,
                has_common_project=True,  # This project uses common infrastructure
                base_dir=self.dockered_services_dir
            )
            
            print(f"✅ {args.template.upper()} project created successfully!")
            print(f"   Location: {project_config.project_path}")
            print(f"   Services: {', '.join(project_config.services)}")
            print(f"   Ports used: {len(project_config.ports_used)} additional ports")
            
            # Show next steps for shared project
            self._show_project_next_steps(args.project_name, project_config.project_path, True)
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to create {args.template} project: {e}")
            return 1
    
    def _create_standalone_project(self, args) -> int:
        """Create self-contained project with all services"""
        try:
            print(f"🏗️  Creating {args.project_name} project (self-contained mode)...")
            print(f"   📦 Includes database, cache, and monitoring services")
            print(f"   📱 {args.template.upper()} backend and frontend")
            print(f"   👤 Owner: {self.user_assignment.login_id}")
            print(f"   🌐 Own network: {self.user_assignment.login_id}-{args.project_name}-network")
            
            # Create the project in standalone mode (no common project)
            project_config = create_project(
                project_name=args.project_name,
                template_type=args.template,
                username=self.user_assignment.login_id,
                port_assignment=self.user_assignment,
                has_common_project=False,  # Standalone project includes all services
                base_dir=self.dockered_services_dir
            )
            
            print(f"✅ {args.template.upper()} project created successfully!")
            print(f"   Location: {project_config.project_path}")
            print(f"   Services: {', '.join(project_config.services)}")
            print(f"   Ports used: {len(project_config.ports_used)} of {len(self.user_assignment.all_ports)}")
            
            # Show next steps for standalone project
            self._show_project_next_steps(args.project_name, project_config.project_path, False)
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to create {args.template} project: {e}")
            return 1
    
    def cmd_copy_project(self, args) -> int:
        """Copy an existing project with new port assignments"""
        self.logger.info(f"Copying project '{args.source}' to '{args.destination}'")
        
        from src.core.project_manager import ProjectManager
        
        try:
            # Initialize project manager
            manager = ProjectManager(base_dir=self.dockered_services_dir, templates_dir="templates")
            
            # Get copy preview
            preview = manager.get_copy_preview(
                source_project=args.source,
                destination_project=args.destination,
                username=self.user_assignment.login_id,
                port_assignment=self.user_assignment
            )
            
            if "error" in preview:
                print(f"❌ {preview['error']}")
                return 1
            
            # Check for validation issues
            if preview["validation_issues"]:
                print("❌ Copy validation failed:")
                for issue in preview["validation_issues"]:
                    print(f"   - {issue}")
                return 1
            
            # Show copy preview
            print(f"📋 Copy Preview:")
            print(f"   Source: {args.source} ({preview['source_config']['template_type']})")
            print(f"   Destination: {args.destination}")
            print(f"   Owner: {self.user_assignment.login_id}")
            print(f"   Services: {', '.join(preview['source_config']['services'])}")
            print(f"   Files to update: {len(preview['files_to_update'])}")
            
            # Show port mapping
            if preview["target_config"]["port_mapping"]:
                print(f"\n🔄 Port Reassignment:")
                for old_port, new_port in preview["target_config"]["port_mapping"].items():
                    print(f"   {old_port} → {new_port}")
            
            # Confirm copy operation
            if not args.force:
                print(f"\n⚠️  This will create a new project '{args.destination}' based on '{args.source}'")
                print(f"   All files will be updated with new ports and configuration.")
                
                confirm = input("Continue with copy operation? (y/N): ").strip().lower()
                if confirm not in ['y', 'yes']:
                    print("Copy operation cancelled.")
                    return 0
            
            # Perform the copy
            print(f"\n🚀 Copying project...")
            
            project_config = manager.copy_project(
                source_project=args.source,
                destination_project=args.destination,
                username=self.user_assignment.login_id,
                port_assignment=self.user_assignment
            )
            
            # Show success information
            print(f"\n📋 Copy Summary:")
            print(f"   Source: {args.source}")
            print(f"   Destination: {project_config.project_name}")
            print(f"   Location: {project_config.project_path}")
            print(f"   Template: {project_config.template_type}")
            print(f"   Services: {', '.join(project_config.services)}")
            print(f"   Ports assigned: {len(project_config.ports_used)} ports")
            
            if project_config.ports_used:
                print(f"   Port range: {min(project_config.ports_used)}-{max(project_config.ports_used)}")
            
            # Show next steps
            print(f"\n🚀 Next Steps:")
            print(f"   1. Navigate to project: cd {project_config.project_path}")
            print(f"   2. Review configuration: cat README.md")
            print(f"   3. Initialize project: ./setup.sh")
            print(f"   4. Start services: docker-compose up -d")
            
            return 0
            
        except FileNotFoundError as e:
            print(f"❌ Source project not found: {e}")
            return 1
        except FileExistsError as e:
            print(f"❌ Destination already exists: {e}")
            return 1
        except ValueError as e:
            print(f"❌ Invalid configuration: {e}")
            return 1
        except Exception as e:
            print(f"❌ Failed to copy project: {e}")
            self.logger.error(f"Project copy failed: {e}")
            return 1
    
    def cmd_list_projects(self, args) -> int:
        """List all projects for current user"""
        self.logger.info("Listing projects")
        
        from src.core.project_manager import ProjectManager
        
        try:
            # Initialize project manager
            manager = ProjectManager(base_dir=self.dockered_services_dir, templates_dir="templates")
            
            # Get projects for current user
            projects = manager.list_projects(username=self.user_assignment.login_id)
            
            if args.json:
                # Convert to JSON-serializable format
                projects_data = []
                for project in projects:
                    project_data = {
                        "name": project.project_name,
                        "template_type": project.template_type,
                        "status": project.status,
                        "created_at": project.created_at,
                        "updated_at": project.last_updated,
                        "ports_used": project.ports_used,
                        "total_ports_allocated": project.port_assignment.get('total_ports', 0),
                        "has_common_project": project.has_common_project,
                        "path": project.project_path
                    }
                    projects_data.append(project_data)
                
                print(json.dumps({"projects": projects_data}, indent=2))
            else:
                if projects:
                    print(f"📁 Projects for {self.user_assignment.login_id}:")
                    print(f"   Base directory: {self.dockered_services_dir}")
                    print(f"")
                    
                    for i, project in enumerate(projects, 1):
                        # Calculate project age
                        from datetime import datetime
                        try:
                            created = datetime.fromisoformat(project.created_at.replace('Z', '+00:00'))
                            age_days = (datetime.now() - created.replace(tzinfo=None)).days
                            age_str = f"{age_days}d ago" if age_days > 0 else "today"
                        except:
                            age_str = "unknown"
                        
                        print(f"   {i}. {project.project_name}")
                        print(f"      Template: {project.template_type}")
                        print(f"      Mode: {'Shared' if project.has_common_project else 'Standalone'}")
                        ports_display = f"{len(project.ports_used)} used"
                        if project.ports_used:
                            ports_display += f" ({project.ports_used[0]}-{project.ports_used[-1]})"
                        print(f"      Ports: {ports_display}")
                        print(f"      Created: {age_str}")
                        print(f"      Status: {project.status}")
                        print(f"")
                else:
                    print("📭 No projects found.")
                    print(f"   Create your first project with: cli create-project <name>")
            
            return 0
            
        except Exception as e:
            if args.json:
                print(json.dumps({"error": str(e)}))
            else:
                print(f"❌ Error listing projects: {e}")
            return 1
        
        return 0
    
    def cmd_show_ports(self, args) -> int:
        """Show port assignments for current user"""
        self.logger.info("Showing port assignments")
        
        if args.json:
            port_info = {
                "login_id": self.user_assignment.login_id,
                "segment1": {
                    "start": self.user_assignment.segment1_start,
                    "end": self.user_assignment.segment1_end,
                    "ports": list(self.user_assignment.segment1_range)
                },
                "total_ports": self.user_assignment.total_ports,
                "has_two_segments": self.user_assignment.has_two_segments
            }
            
            if self.user_assignment.has_two_segments:
                port_info["segment2"] = {
                    "start": self.user_assignment.segment2_start,
                    "end": self.user_assignment.segment2_end,
                    "ports": list(self.user_assignment.segment2_range)
                }
            
            print(json.dumps(port_info, indent=2))
        else:
            print(f"Port Assignment for {self.user_assignment.login_id}:")
            print(f"  Segment 1: {self.user_assignment.segment1_start}-{self.user_assignment.segment1_end}")
            
            if self.user_assignment.has_two_segments:
                print(f"  Segment 2: {self.user_assignment.segment2_start}-{self.user_assignment.segment2_end}")
            
            print(f"  Total ports: {self.user_assignment.total_ports}")
            print(f"  All ports: {self.user_assignment.all_ports[:10]}{'...' if len(self.user_assignment.all_ports) > 10 else ''}")
        
        return 0
    
    def cmd_verify_ports(self, args) -> int:
        """Verify port usage in a project"""
        self.logger.info(f"Verifying ports for project '{args.project_name}'")
        
        try:
            from src.monitoring.port_verification_system import PortVerificationSystem, verify_all_projects
            
            # Get user assignment
            if not self.user_assignment:
                print("❌ Unable to get port assignment. Please check your login credentials.")
                return 3
            
            verifier = PortVerificationSystem()
            
            if args.project_name == "all":
                # Verify all projects
                print(f"🔍 Verifying all projects in {self.dockered_services_dir}")
                print("")
                
                results, cross_conflicts = verify_all_projects(
                    self.dockered_services_dir, 
                    self.user_assignment, 
                    self.user_assignment.login_id
                )
                
                if not results:
                    print("📂 No projects found with docker-compose.yml files")
                    print(f"   Projects should be in: {self.dockered_services_dir}")
                    return 0
                
                if args.json:
                    # JSON output
                    json_output = self._format_verification_json(results, cross_conflicts)
                    print(json.dumps(json_output, indent=2))
                else:
                    # Generate and display report
                    report = verifier.generate_verification_report(results, cross_conflicts)
                    print(report)
                
                # Return appropriate exit code
                all_valid = all(r.is_valid for r in results.values()) and len(cross_conflicts) == 0
                return 0 if all_valid else 1
                
            else:
                # Verify specific project
                project_dir = os.path.join(self.dockered_services_dir, args.project_name)
                
                if not os.path.exists(project_dir):
                    print(f"❌ Project '{args.project_name}' not found")
                    print(f"   Expected location: {project_dir}")
                    return 1
                
                print(f"🔍 Verifying project: {args.project_name}")
                print("")
                
                result = verifier.verify_project_ports(
                    project_dir, 
                    self.user_assignment, 
                    self.user_assignment.login_id
                )
                
                if args.json:
                    # JSON output
                    json_output = self._format_single_verification_json(args.project_name, result)
                    print(json.dumps(json_output, indent=2))
                else:
                    # Display results
                    self._display_verification_result(args.project_name, result)
                
                return 0 if result.is_valid else 1
                
        except Exception as e:
            self.logger.error(f"Port verification failed: {e}")
            print(f"❌ Port verification failed: {e}")
            return 1
    
    def _display_verification_result(self, project_name: str, result) -> None:
        """Display verification result for a single project"""
        # Header
        status_icon = "✅" if result.is_valid else "❌"
        print(f"{status_icon} Project: {project_name}")
        print(f"   Ports used: {result.total_ports_used}")
        print("")
        
        # Port assignment info
        range_info = result.assigned_range_info
        print(f"🎯 Your assigned port ranges:")
        print(f"   {range_info['formatted_ranges']}")
        print(f"   Total available: {range_info['total_ports']} ports")
        print("")
        
        # Port mappings
        if result.port_mappings:
            print("📋 Port mappings:")
            for mapping in result.port_mappings:
                print(f"   {mapping.service_name}: {mapping.host_port} → {mapping.container_port}")
            print("")
        
        # Conflicts and issues
        if result.conflicts:
            error_conflicts = [c for c in result.conflicts if c.severity == "error"]
            warning_conflicts = [c for c in result.conflicts if c.severity == "warning"]
            
            if error_conflicts:
                print("❌ Errors:")
                for conflict in error_conflicts:
                    print(f"   {conflict.service_name}: {conflict.description}")
                    if conflict.suggestion:
                        print(f"      💡 {conflict.suggestion}")
                print("")
            
            if warning_conflicts:
                print("⚠️  Warnings:")
                for conflict in warning_conflicts:
                    print(f"   {conflict.service_name}: {conflict.description}")
                    if conflict.suggestion:
                        print(f"      💡 {conflict.suggestion}")
                print("")
        
        # Suggestions
        if result.suggestions:
            print("💡 Suggestions:")
            for suggestion in result.suggestions:
                print(f"   • {suggestion}")
            print("")
    
    def _format_verification_json(self, results: Dict, cross_conflicts: List) -> Dict[str, Any]:
        """Format verification results as JSON"""
        json_results = {}
        
        for project_name, result in results.items():
            json_results[project_name] = {
                'is_valid': result.is_valid,
                'total_ports_used': result.total_ports_used,
                'port_mappings': [
                    {
                        'service_name': m.service_name,
                        'host_port': m.host_port,
                        'container_port': m.container_port,
                        'protocol': m.protocol
                    }
                    for m in result.port_mappings
                ],
                'conflicts': [
                    {
                        'port': c.port,
                        'service_name': c.service_name,
                        'issue_type': c.issue_type,
                        'description': c.description,
                        'suggestion': c.suggestion,
                        'severity': c.severity
                    }
                    for c in result.conflicts
                ],
                'warnings': result.warnings,
                'suggestions': result.suggestions
            }
        
        return {
            'summary': {
                'total_projects': len(results),
                'valid_projects': sum(1 for r in results.values() if r.is_valid),
                'total_ports_used': sum(r.total_ports_used for r in results.values()),
                'has_cross_project_conflicts': len(cross_conflicts) > 0
            },
            'cross_project_conflicts': [
                {
                    'port': c.port,
                    'services': c.service_name,
                    'issue_type': c.issue_type,
                    'description': c.description,
                    'suggestion': c.suggestion,
                    'severity': c.severity
                }
                for c in cross_conflicts
            ],
            'projects': json_results,
            'assigned_range_info': results[next(iter(results))].assigned_range_info if results else {}
        }
    
    def _format_single_verification_json(self, project_name: str, result) -> Dict[str, Any]:
        """Format single project verification result as JSON"""
        return {
            'project_name': project_name,
            'is_valid': result.is_valid,
            'total_ports_used': result.total_ports_used,
            'port_mappings': [
                {
                    'service_name': m.service_name,
                    'host_port': m.host_port,
                    'container_port': m.container_port,
                    'protocol': m.protocol
                }
                for m in result.port_mappings
            ],
            'conflicts': [
                {
                    'port': c.port,
                    'service_name': c.service_name,
                    'issue_type': c.issue_type,
                    'description': c.description,
                    'suggestion': c.suggestion,
                    'severity': c.severity
                }
                for c in result.conflicts
            ],
            'warnings': result.warnings,
            'suggestions': result.suggestions,
            'assigned_range_info': result.assigned_range_info
        }
    
    def cmd_status(self, args) -> int:
        """Show comprehensive system and project status"""
        self.logger.info("Showing system status")
        
        try:
            from src.monitoring.project_status_monitor import ProjectStatusMonitor
            
            # Get user assignment
            if not self.user_assignment:
                print("❌ Unable to get port assignment. Please check your login credentials.")
                return 3
            
            # Generate comprehensive monitoring report
            monitor = ProjectStatusMonitor(self.dockered_services_dir)
            report = monitor.generate_monitoring_report(
                self.user_assignment, 
                self.user_assignment.login_id
            )
            
            if args.json:
                # JSON output for automation
                json_output = self._format_status_json(report)
                print(json.dumps(json_output, indent=2))
            else:
                # Human-readable output
                formatted_report = monitor.format_status_report(report, detailed=True)
                print(formatted_report)
            
            # Return appropriate exit code
            has_warnings = len(report.warnings) > 0
            return 1 if has_warnings else 0
            
        except Exception as e:
            self.logger.error(f"Status check failed: {e}")
            print(f"❌ Status check failed: {e}")
            return 1
    
    def _format_status_json(self, report) -> Dict[str, Any]:
        """Format monitoring report as JSON"""
        return {
            'timestamp': report.timestamp,
            'username': report.username,
            'system_status': {
                'docker_available': report.system_status.docker_available,
                'docker_version': report.system_status.docker_version,
                'compose_available': report.system_status.compose_available,
                'compose_version': report.system_status.compose_version,
                'total_containers': report.system_status.total_containers,
                'running_containers': report.system_status.running_containers,
                'total_networks': report.system_status.total_networks,
                'total_volumes': report.system_status.total_volumes,
                'disk_usage': report.system_status.disk_usage
            },
            'port_usage': {
                'total_assigned_ports': report.port_usage.total_assigned_ports,
                'total_used_ports': report.port_usage.total_used_ports,
                'available_ports': report.port_usage.available_ports,
                'usage_percentage': report.port_usage.usage_percentage,
                'port_ranges': report.port_usage.port_ranges,
                'projects_by_port_usage': report.port_usage.projects_by_port_usage,
                'unused_ports': report.port_usage.unused_ports,
                'port_conflicts': report.port_usage.port_conflicts
            },
            'projects': [
                {
                    'name': p.name,
                    'path': p.path,
                    'has_compose_file': p.has_compose_file,
                    'is_running': p.is_running,
                    'container_count': p.container_count,
                    'ports_used': p.ports_used,
                    'last_modified': p.last_modified,
                    'compose_version': p.compose_version,
                    'containers': [
                        {
                            'name': c.name,
                            'image': c.image,
                            'status': c.status,
                            'state': c.state,
                            'ports': c.ports,
                            'health': c.health
                        }
                        for c in p.containers
                    ]
                }
                for p in report.projects
            ],
            'summary': {
                'total_projects': report.total_projects,
                'running_projects': report.running_projects,
                'warnings': report.warnings,
                'recommendations': report.recommendations
            }
        }
    
    def cmd_project_status(self, args) -> int:
        """Show detailed project status and monitoring"""
        self.logger.info(f"Showing project status for: {args.project_name or 'all projects'}")
        
        try:
            from src.monitoring.project_status_monitor import ProjectStatusMonitor, get_project_status
            
            # Get user assignment
            if not self.user_assignment:
                print("❌ Unable to get port assignment. Please check your login credentials.")
                return 3
            
            if args.project_name:
                # Show status for specific project
                project_status = get_project_status(args.project_name, self.dockered_services_dir)
                
                if not project_status:
                    print(f"❌ Project '{args.project_name}' not found")
                    print(f"   Expected location: {os.path.join(self.dockered_services_dir, args.project_name)}")
                    return 1
                
                if args.json:
                    # JSON output for specific project
                    json_output = self._format_project_status_json(project_status)
                    print(json.dumps(json_output, indent=2))
                else:
                    # Human-readable output for specific project
                    self._display_project_status(project_status, args.detailed)
                
                return 0
            else:
                # Show status for all projects
                monitor = ProjectStatusMonitor(self.dockered_services_dir)
                report = monitor.generate_monitoring_report(
                    self.user_assignment, 
                    self.user_assignment.login_id
                )
                
                if args.json:
                    # JSON output for all projects
                    json_output = self._format_status_json(report)
                    print(json.dumps(json_output, indent=2))
                else:
                    # Human-readable output for all projects
                    formatted_report = monitor.format_status_report(report, detailed=args.detailed)
                    print(formatted_report)
                
                # Return appropriate exit code
                has_warnings = len(report.warnings) > 0
                return 1 if has_warnings else 0
                
        except Exception as e:
            self.logger.error(f"Project status check failed: {e}")
            print(f"❌ Project status check failed: {e}")
            return 1
    
    def _display_project_status(self, project_status, detailed: bool = False) -> None:
        """Display status for a single project"""
        # Header
        status_icon = "🟢" if project_status.is_running else "🔴" if project_status.container_count > 0 else "⚪"
        print(f"{status_icon} Project: {project_status.name}")
        print(f"   Path: {project_status.path}")
        print(f"   Compose file: {'✅' if project_status.has_compose_file else '❌'}")
        print(f"   Status: {'Running' if project_status.is_running else 'Stopped' if project_status.container_count > 0 else 'Not started'}")
        print("")
        
        # Container information
        if project_status.containers:
            print(f"📦 Containers ({len(project_status.containers)}):")
            for container in project_status.containers:
                status_icon = "🟢" if container.status == "running" else "🔴" if container.status == "exited" else "⚪"
                print(f"   {status_icon} {container.name}")
                print(f"      Image: {container.image}")
                print(f"      Status: {container.status}")
                
                if detailed:
                    print(f"      State: {container.state}")
                    if container.ports:
                        print(f"      Ports: {', '.join(container.ports)}")
                    if container.health:
                        print(f"      Health: {container.health}")
                    if container.created:
                        print(f"      Created: {container.created}")
            print("")
        
        # Port information
        if project_status.ports_used:
            ports_str = ', '.join(map(str, sorted(project_status.ports_used)))
            print(f"🔌 Ports used: {ports_str}")
            print("")
        
        # Additional information
        if detailed:
            if project_status.compose_version:
                print(f"📄 Compose version: {project_status.compose_version}")
            
            if project_status.last_modified:
                print(f"📅 Last modified: {project_status.last_modified}")
            
            if project_status.networks:
                print(f"🌐 Networks: {', '.join(project_status.networks)}")
            
            if project_status.volumes:
                print(f"💾 Volumes: {', '.join(project_status.volumes)}")
            
            print("")
    
    def _format_project_status_json(self, project_status) -> Dict[str, Any]:
        """Format single project status as JSON"""
        return {
            'name': project_status.name,
            'path': project_status.path,
            'has_compose_file': project_status.has_compose_file,
            'is_running': project_status.is_running,
            'container_count': project_status.container_count,
            'ports_used': project_status.ports_used,
            'last_modified': project_status.last_modified,
            'compose_version': project_status.compose_version,
            'networks': project_status.networks,
            'volumes': project_status.volumes,
            'containers': [
                {
                    'name': c.name,
                    'image': c.image,
                    'status': c.status,
                    'state': c.state,
                    'ports': c.ports,
                    'created': c.created,
                    'started': c.started,
                    'health': c.health
                }
                for c in project_status.containers
            ],
            'port_mappings': [
                {
                    'service_name': m.service_name,
                    'host_port': m.host_port,
                    'container_port': m.container_port,
                    'protocol': m.protocol
                }
                for m in project_status.port_mappings
            ]
        }
    
    def cmd_remove_project(self, args) -> int:
        """Remove project with proper cleanup of containers, networks, and volumes"""
        self.logger.info(f"Removing project '{args.project_name}' (force={args.force}, dry_run={args.dry_run})")
        
        try:
            from src.maintenance.cleanup_maintenance_tools import ProjectRemovalTool
            
            if args.dry_run:
                print(f"🔍 Dry run: Would remove project '{args.project_name}'")
                print("   This would:")
                print("   • Stop and remove all containers")
                print("   • Remove associated networks")
                if args.force:
                    print("   • Remove associated volumes (--force specified)")
                else:
                    print("   • Warn about volumes with data (use --force to remove)")
                print("   • Remove project directory")
                print("")
                print("Use without --dry-run to actually perform the removal.")
                return 0
            
            # Confirm removal unless force is specified
            if not args.force:
                print(f"⚠️  This will permanently remove project '{args.project_name}' and all its resources.")
                print("   • All containers will be stopped and removed")
                print("   • All networks will be removed")
                print("   • All volumes will be preserved (use --force to remove volumes)")
                print("   • Project directory will be deleted")
                print("")
                
                try:
                    response = input("Are you sure you want to continue? (y/N): ").strip().lower()
                    if response not in ['y', 'yes']:
                        print("❌ Project removal cancelled.")
                        return 0
                except (KeyboardInterrupt, EOFError):
                    print("\n❌ Project removal cancelled.")
                    return 0
            
            # Perform removal
            removal_tool = ProjectRemovalTool(self.dockered_services_dir)
            result = removal_tool.remove_project(args.project_name, args.force)
            
            if result.success:
                print(f"✅ Successfully removed project '{args.project_name}'")
                print(f"   Items removed: {result.items_removed}")
                if result.space_freed:
                    print(f"   Space freed: {result.space_freed}")
                
                if result.warnings:
                    print("\n⚠️  Warnings:")
                    for warning in result.warnings:
                        print(f"   • {warning}")
                
                return 0
            else:
                print(f"❌ Failed to remove project '{args.project_name}'")
                if result.errors:
                    for error in result.errors:
                        print(f"   • {error}")
                return 1
                
        except Exception as e:
            self.logger.error(f"Project removal failed: {e}")
            print(f"❌ Project removal failed: {e}")
            return 1
    
    def cmd_health_check(self, args) -> int:
        """Check Docker system health"""
        self.logger.info("Performing system health check")
        
        try:
            from src.maintenance.cleanup_maintenance_tools import SystemHealthChecker
            
            print("🔍 Performing Docker system health check...")
            print("")
            
            checker = SystemHealthChecker()
            health_results = checker.check_system_health()
            
            if args.json:
                import json
                print(json.dumps(health_results, indent=2))
                return 0 if health_results['overall_status'] == 'healthy' else 1
            
            # Display human-readable results
            status_icon = "✅" if health_results['overall_status'] == 'healthy' else "❌"
            print(f"{status_icon} Overall Status: {health_results['overall_status'].title()}")
            print(f"📅 Checked: {health_results['timestamp']}")
            print("")
            
            # Display individual checks
            print("🔍 Health Checks:")
            for check_name, check_result in health_results['checks'].items():
                check_icon = "✅" if check_result['status'] else "❌"
                check_title = check_name.replace('_', ' ').title()
                print(f"   {check_icon} {check_title}: {check_result['message']}")
                
                # Show additional details for failed checks
                if not check_result['status'] and 'error' in check_result.get('details', {}):
                    print(f"      Error: {check_result['details']['error']}")
            
            print("")
            
            # Display warnings
            if health_results['warnings']:
                print("⚠️  Warnings:")
                for warning in health_results['warnings']:
                    print(f"   • {warning}")
                print("")
            
            # Display errors
            if health_results['errors']:
                print("❌ Errors:")
                for error in health_results['errors']:
                    print(f"   • {error}")
                print("")
            
            # Display recommendations
            if health_results['recommendations']:
                print("💡 Recommendations:")
                for recommendation in health_results['recommendations']:
                    print(f"   • {recommendation}")
                print("")
            
            return 0 if health_results['overall_status'] == 'healthy' else 1
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            print(f"❌ Health check failed: {e}")
            return 1
    
    def cmd_cleanup(self, args) -> int:
        """Clean up unused Docker resources"""
        self.logger.info(f"Cleaning up Docker resources (dry_run={args.dry_run})")
        
        try:
            # Determine operations to perform
            operations = []
            
            # Always include basic cleanup
            operations.append("cleanup_containers")
            operations.append("cleanup_images")
            
            # Add optional operations
            if hasattr(args, 'volumes') and args.volumes:
                operations.append("cleanup_volumes")
            
            if hasattr(args, 'networks') and getattr(args, 'networks', True):
                operations.append("cleanup_networks")
            
            if hasattr(args, 'all') and args.all:
                operations.extend(["cleanup_volumes", "cleanup_networks", "cleanup_system"])
            
            # Perform cleanup
            report = perform_cleanup(
                operations=operations,
                project_filter=getattr(args, 'project', None),
                base_dir=self.dockered_services_dir,
                dry_run=args.dry_run
            )
            
            # Print results
            self._print_cleanup_report(report, args.dry_run)
            
            # Return success if all operations succeeded
            failed_ops = [op for op in report.operations_performed if not op.success]
            return 0 if len(failed_ops) == 0 else 1
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            print(f"❌ Cleanup failed: {e}")
            return 1
            print(f"❌ Cleanup failed: {e}")
            return 1
    
    def cmd_optimize_ports(self, args) -> int:
        """Analyze and optimize port usage"""
        self.logger.info("Analyzing port usage for optimization")
        
        try:
            from src.maintenance.cleanup_maintenance_tools import PortOptimizationTool
            from src.monitoring.project_status_monitor import ProjectStatusMonitor
            
            # Get user assignment
            if not self.user_assignment:
                print("❌ Unable to get port assignment. Please check your login credentials.")
                return 3
            
            # Get current projects
            monitor = ProjectStatusMonitor(self.dockered_services_dir)
            report = monitor.generate_monitoring_report(
                self.user_assignment, 
                self.user_assignment.login_id
            )
            
            # Analyze port optimization
            optimizer = PortOptimizationTool()
            analysis = optimizer.analyze_port_optimization(report.projects, self.user_assignment)
            
            if args.json:
                import json
                print(json.dumps(analysis, indent=2))
                return 0
            
            # Display human-readable analysis
            print("🔌 Port Usage Optimization Analysis")
            print("=" * 50)
            print(f"👤 User: {self.user_assignment.login_id}")
            print(f"📊 Port Usage: {analysis['used_ports']}/{analysis['total_ports']} ({analysis['usage_percentage']:.1f}%)")
            print(f"🆓 Available: {analysis['available_ports']} ports")
            print("")
            
            # Usage status
            if analysis['usage_percentage'] > 90:
                print("🚨 CRITICAL: Port usage is very high!")
            elif analysis['usage_percentage'] > 80:
                print("⚠️  WARNING: Port usage is high")
            elif analysis['usage_percentage'] > 60:
                print("📊 MODERATE: Port usage is moderate")
            else:
                print("✅ HEALTHY: Port usage is low")
            
            print("")
            
            # Stopped projects analysis
            if analysis['stopped_projects'] > 0:
                print(f"🔴 Stopped Projects: {analysis['stopped_projects']} projects using {analysis['potential_savings']} ports")
                print("   These projects could be removed to free up ports")
                print("")
            
            # High usage projects
            if analysis['high_usage_projects']:
                print("📈 High Port Usage Projects:")
                for project_name, port_count in analysis['high_usage_projects']:
                    print(f"   • {project_name}: {port_count} ports")
                print("")
            
            # Suggestions
            if analysis['suggestions']:
                print("💡 Optimization Suggestions:")
                for suggestion in analysis['suggestions']:
                    type_icon = {
                        'critical': '🚨',
                        'warning': '⚠️',
                        'optimization': '🔧',
                        'review': '📋'
                    }.get(suggestion['type'], '💡')
                    
                    print(f"   {type_icon} {suggestion['message']}")
                    print(f"      Action: {suggestion['action']}")
                print("")
            
            # Recommendations
            if analysis['recommendations']:
                print("🎯 Recommendations:")
                for recommendation in analysis['recommendations']:
                    print(f"   • {recommendation}")
                print("")
            
            # Return appropriate exit code
            return 1 if analysis['usage_percentage'] > 90 else 0
            
        except Exception as e:
            self.logger.error(f"Port optimization analysis failed: {e}")
            print(f"❌ Port optimization analysis failed: {e}")
            return 1

    def cmd_common_status(self, args) -> int:
        """Show common infrastructure status"""
        self.logger.info("Showing common infrastructure status")
        
        try:
            common_info = self._detect_common_project()
            
            if not common_info:
                if args.json:
                    print(json.dumps({
                        "exists": False,
                        "message": "No common infrastructure project found"
                    }, indent=2))
                else:
                    print("❌ No common infrastructure project found")
                    print("")
                    print("💡 Create one with:")
                    print("   python cli.py create-project common --template common")
                return 1
            
            config = common_info["config"]
            is_running = common_info["is_running"]
            running_services = common_info["running_services"]
            
            if args.json:
                print(json.dumps({
                    "exists": True,
                    "path": common_info["path"],
                    "owner": config.username,
                    "created_at": config.created_at,
                    "services": {
                        "total": len(config.services),
                        "running": len(running_services),
                        "list": config.services,
                        "running_list": running_services
                    },
                    "ports_used": config.ports_used,
                    "is_running": is_running,
                    "network": f"{config.username}-network"
                }, indent=2))
            else:
                print(f"🏗️  Common Infrastructure Status")
                print(f"")
                print(f"📍 Location: {common_info['path']}")
                print(f"👤 Owner: {config.username}")
                print(f"📅 Created: {config.created_at}")
                print(f"🌐 Network: {config.username}-network")
                print(f"")
                print(f"📊 Services ({len(running_services)}/{len(config.services)} running):")
                
                for service in config.services:
                    status = "🟢" if service in running_services else "🔴"
                    print(f"   {status} {service}")
                
                print(f"")
                print(f"🔌 Ports used: {config.ports_used}")
                
                if not is_running:
                    print(f"")
                    print(f"💡 To start common services:")
                    print(f"   cd {common_info['path']} && docker-compose up -d")
                else:
                    print(f"")
                    print(f"✅ Common infrastructure is running and ready for application projects")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Failed to get common status: {e}")
            if args.json:
                print(json.dumps({"error": str(e)}, indent=2))
            else:
                print(f"❌ Failed to get common status: {e}")
            return 1
    
    def cmd_version_info(self, args) -> int:
        """Show port assignment file version information"""
        self.logger.info("Showing port assignment file version information")
        
        from src.core.port_assignment import PortAssignmentManager
        manager = PortAssignmentManager()
        
        try:
            # Get available versions
            available_versions = manager.list_available_versions()
            
            if not available_versions:
                if args.json:
                    print(json.dumps({"error": "No encrypted port assignment files found"}))
                else:
                    print("❌ No encrypted port assignment files found")
                    print("   Expected files like: student-port-assignments-v1.0.enc")
                return 1
            
            # Load current assignment to get detailed metadata
            manager.load_assignments()
            metadata = manager.get_metadata()
            
            version_info = {
                "current_version": metadata.get('version', 'unknown'),
                "current_file": os.path.basename(manager.encrypted_file_path) if manager.encrypted_file_path else None,
                "created_at": metadata.get('created_at', 'unknown'),
                "total_assignments": metadata.get('total_assignments', 0),
                "available_versions": [
                    {
                        "version": version,
                        "file": os.path.basename(file_path),
                        "size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    }
                    for version, file_path in available_versions
                ]
            }
            
            if args.json:
                print(json.dumps(version_info, indent=2))
            else:
                print(f"📄 Port Assignment File Information")
                print(f"=" * 40)
                print(f"Current Version: {version_info['current_version']}")
                print(f"Current File: {version_info['current_file']}")
                print(f"Created: {version_info['created_at']}")
                print(f"Total Students: {version_info['total_assignments']}")
                
                print(f"\n📋 Available Versions:")
                for i, ver_info in enumerate(version_info['available_versions']):
                    current_marker = " (current)" if ver_info['version'] == version_info['current_version'] else ""
                    size_kb = ver_info['size_bytes'] / 1024
                    print(f"  {i+1}. {ver_info['version']}{current_marker}")
                    print(f"     File: {ver_info['file']}")
                    print(f"     Size: {size_kb:.1f} KB")
            
            return 0
            
        except Exception as e:
            if args.json:
                print(json.dumps({"error": str(e)}))
            else:
                print(f"❌ Error reading port assignment file: {e}")
            return 1
    
    def cmd_template_info(self, args) -> int:
        """Show template information and validation"""
        self.logger.info(f"Showing template information for {args.template_type}")
        
        from src.core.template_processor import TemplateProcessor, create_template_context
        
        try:
            # Create a sample context for validation
            context = create_template_context(
                username=self.user_assignment.login_id,
                project_name="sample",
                template_type=args.template_type,
                port_assignment=self.user_assignment,
                has_common_project=(args.template_type != 'common')
            )
            
            processor = TemplateProcessor("templates")
            
            # Get template dependencies
            dependencies = processor.get_template_dependencies(args.template_type)
            
            template_info = {
                "template_type": args.template_type,
                "dependencies": dependencies,
                "available_templates": [],
                "validation_results": {}
            }
            
            # Check which templates actually exist
            for dep in dependencies:
                template_path = os.path.join("templates", dep)
                if os.path.exists(template_path):
                    template_info["available_templates"].append(dep)
                    
                    # Get required placeholders
                    placeholders = processor.get_required_placeholders(template_path)
                    
                    template_info[f"{dep}_placeholders"] = placeholders
            
            # Validate templates if requested
            if args.validate:
                validation_results = processor.validate_all_templates(context)
                template_info["validation_results"] = validation_results
            
            # Show interdependencies if requested
            if args.show_dependencies:
                warning = processor.show_interdependency_warning(args.template_type)
                template_info["interdependency_warning"] = warning
            
            if args.json:
                print(json.dumps(template_info, indent=2))
            else:
                print(f"📄 Template Information: {args.template_type}")
                print("=" * 50)
                
                print(f"\n📋 Template Dependencies ({len(dependencies)} total):")
                for i, dep in enumerate(dependencies, 1):
                    exists = dep in template_info["available_templates"]
                    status = "✅" if exists else "❌"
                    print(f"  {i}. {status} {dep}")
                    
                    if exists and f"{dep}_placeholders" in template_info:
                        placeholders = template_info[f"{dep}_placeholders"]
                        if placeholders:
                            print(f"     Placeholders: {', '.join(placeholders[:5])}")
                            if len(placeholders) > 5:
                                print(f"     ... and {len(placeholders) - 5} more")
                
                if args.validate and template_info["validation_results"]:
                    print(f"\n⚠️  Validation Issues:")
                    for template_file, warnings in template_info["validation_results"].items():
                        print(f"  {template_file}:")
                        for warning in warnings:
                            print(f"    - {warning}")
                elif args.validate:
                    print(f"\n✅ All templates validate successfully")
                
                if args.show_dependencies:
                    print(template_info["interdependency_warning"])
            
            return 0
            
        except Exception as e:
            if args.json:
                print(json.dumps({"error": str(e)}))
            else:
                print(f"❌ Error analyzing templates: {e}")
            return 1
    
    def cmd_generate_compose(self, args) -> int:
        """Generate Docker Compose file from template"""
        self.logger.info(f"Generating Docker Compose for {args.template_type} project: {args.project_name}")
        
        from src.core.docker_compose_manager import DockerComposeManager, create_docker_compose_config
        
        try:
            # Create Docker Compose manager
            manager = DockerComposeManager("templates")
            
            # Create configuration
            config = create_docker_compose_config(
                username=self.user_assignment.login_id,
                project_name=args.project_name,
                template_type=args.template_type,
                port_assignment=self.user_assignment,
                output_dir=args.output_dir,
                has_common_project=args.shared_mode
            )
            
            # Generate Docker Compose file
            output_path = manager.create_docker_compose_file(config)
            
            print(f"✅ Docker Compose file generated successfully:")
            print(f"   File: {output_path}")
            print(f"   Template: {args.template_type}")
            print(f"   Project: {args.project_name}")
            print(f"   Mode: {'Shared' if args.shared_mode else 'Standalone'}")
            
            # Show port assignments
            compose_content = ""
            with open(output_path, 'r') as f:
                compose_content = f.read()
            
            port_mappings = manager.extract_port_mappings(compose_content)
            if port_mappings:
                print(f"\n📊 Port Assignments:")
                for host_port, container_port, service_name in port_mappings:
                    print(f"   {service_name}: localhost:{host_port} -> {container_port}")
            
            # Validate if requested
            if args.validate:
                print(f"\n🔍 Validation Results:")
                
                # Docker Compose validation
                warnings = manager.validate_docker_compose(compose_content)
                if warnings:
                    print(f"   ⚠️  {len(warnings)} validation warnings:")
                    for warning in warnings[:3]:
                        print(f"     - {warning}")
                    if len(warnings) > 3:
                        print(f"     ... and {len(warnings) - 3} more")
                else:
                    print(f"   ✅ Docker Compose validation passed")
                
                # Port conflict validation
                port_warnings = manager.check_port_conflicts(compose_content, self.user_assignment)
                if port_warnings:
                    print(f"   ⚠️  {len(port_warnings)} port conflicts:")
                    for warning in port_warnings[:3]:
                        print(f"     - {warning}")
                    if len(port_warnings) > 3:
                        print(f"     ... and {len(port_warnings) - 3} more")
                else:
                    print(f"   ✅ Port conflict validation passed")
            
            # Show service information
            service_info = manager.get_service_info(compose_content)
            print(f"\n📋 Service Summary:")
            print(f"   Services: {len(service_info['services'])}")
            print(f"   Networks: {len(service_info['networks'])}")
            print(f"   Volumes: {len(service_info['volumes'])}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Error generating Docker Compose: {e}")
            self.logger.error(f"Docker Compose generation failed: {e}")
            return 1
    
    def cmd_generate_database(self, args) -> int:
        """Generate database initialization scripts"""
        self.logger.info(f"Generating database scripts for {args.template_type} project: {args.project_name}")
        
        from src.core.database_manager import DatabaseManager, create_database_config
        
        try:
            # Create database manager
            manager = DatabaseManager("templates")
            
            # Get supported databases for this template type
            supported_dbs = manager.get_supported_databases(args.template_type)
            
            if not supported_dbs:
                print(f"❌ No database support for template type: {args.template_type}")
                return 1
            
            print(f"📊 Template Type: {args.template_type}")
            print(f"📊 Supported Databases: {', '.join(supported_dbs)}")
            
            # Filter databases based on user selection
            if args.database_type == 'all':
                target_dbs = supported_dbs
            elif args.database_type in supported_dbs:
                target_dbs = [args.database_type]
            else:
                print(f"❌ Database type '{args.database_type}' not supported for {args.template_type} projects")
                print(f"   Supported types: {', '.join(supported_dbs)}")
                return 1
            
            created_files = {}
            
            # Generate scripts for each target database
            for db_type in target_dbs:
                print(f"\n🔧 Generating {db_type.upper()} initialization script...")
                
                # Create configuration
                config = create_database_config(
                    username=self.user_assignment.login_id,
                    project_name=args.project_name,
                    template_type=args.template_type,
                    port_assignment=self.user_assignment,
                    database_type=db_type,
                    output_dir=args.output_dir
                )
                
                try:
                    # Generate script
                    script_content = manager.generate_database_init_script(config)
                    
                    # Determine output file
                    if db_type == 'postgresql':
                        output_file = os.path.join(args.output_dir, 'database', 'init.sql')
                    elif db_type == 'mongodb':
                        output_file = os.path.join(args.output_dir, 'database', 'init.js')
                    
                    # Create directory
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    
                    # Write file
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(script_content)
                    
                    created_files[db_type] = output_file
                    
                    print(f"✅ {db_type.upper()} script created: {output_file}")
                    
                    # Validate if requested
                    if args.validate:
                        warnings = manager.validate_database_script(script_content, db_type)
                        if warnings:
                            print(f"   ⚠️  {len(warnings)} validation warnings:")
                            for warning in warnings[:3]:
                                print(f"     - {warning}")
                            if len(warnings) > 3:
                                print(f"     ... and {len(warnings) - 3} more")
                        else:
                            print(f"   ✅ Validation passed")
                    
                except Exception as e:
                    print(f"   ❌ Failed to generate {db_type} script: {e}")
            
            # Show summary
            print(f"\n📋 Generation Summary:")
            print(f"   Project: {args.project_name}")
            print(f"   Template: {args.template_type}")
            print(f"   Files created: {len(created_files)}")
            
            for db_type, file_path in created_files.items():
                file_size = os.path.getsize(file_path) / 1024
                print(f"   - {db_type.upper()}: {os.path.basename(file_path)} ({file_size:.1f} KB)")
            
            # Show connection information if requested
            if args.show_connection_info:
                print(f"\n🔗 Database Connection Information:")
                
                config = create_database_config(
                    username=self.user_assignment.login_id,
                    project_name=args.project_name,
                    template_type=args.template_type,
                    port_assignment=self.user_assignment,
                    database_type='all',
                    output_dir=args.output_dir
                )
                
                conn_info = manager.get_database_connection_info(config)
                
                for db_type, db_info in conn_info['databases'].items():
                    if db_type in [db.lower() for db in target_dbs]:
                        print(f"\n   {db_type.upper()}:")
                        print(f"     Host: {db_info['host']}")
                        print(f"     Port: {db_info['port']}")
                        print(f"     Database: {db_info['database']}")
                        print(f"     Username: {db_info['username']}")
                        print(f"     Connection URL: {db_info['connection_url']}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Error generating database scripts: {e}")
            self.logger.error(f"Database script generation failed: {e}")
            return 1
    
    def cmd_generate_dockerfile(self, args) -> int:
        """Generate Dockerfile templates"""
        self.logger.info(f"Generating Dockerfiles for {args.template_type} project: {args.project_name}")
        
        from src.core.dockerfile_manager import DockerfileManager, create_dockerfile_config
        
        try:
            # Create Dockerfile manager
            manager = DockerfileManager("templates")
            
            # Get supported services for this template type
            supported_services = manager.get_supported_services(args.template_type)
            
            if not supported_services:
                print(f"❌ No service support for template type: {args.template_type}")
                return 1
            
            print(f"📊 Template Type: {args.template_type}")
            print(f"📊 Supported Services: {', '.join(supported_services)}")
            
            # Filter services based on user selection
            if args.service_type == 'all':
                target_services = supported_services
            elif args.service_type in supported_services:
                target_services = [args.service_type]
            else:
                print(f"❌ Service type '{args.service_type}' not supported for {args.template_type} projects")
                print(f"   Supported types: {', '.join(supported_services)}")
                return 1
            
            created_files = {}
            
            # Generate Dockerfiles for each target service
            for service_type in target_services:
                print(f"\n🔧 Generating {service_type.upper()} Dockerfile...")
                
                # Create configuration
                config = create_dockerfile_config(
                    username=self.user_assignment.login_id,
                    project_name=args.project_name,
                    template_type=args.template_type,
                    service_type=service_type,
                    port_assignment=self.user_assignment,
                    output_dir=args.output_dir,
                    target_stage=args.target_stage
                )
                
                try:
                    # Generate Dockerfile
                    dockerfile_content = manager.generate_dockerfile(config)
                    
                    # Determine output file
                    output_file = os.path.join(args.output_dir, service_type, 'Dockerfile')
                    
                    # Create directory
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    
                    # Write file
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(dockerfile_content)
                    
                    created_files[service_type] = output_file
                    
                    print(f"✅ {service_type.upper()} Dockerfile created: {output_file}")
                    
                    # Validate if requested
                    if args.validate:
                        warnings = manager.validate_dockerfile(dockerfile_content, service_type)
                        if warnings:
                            print(f"   ⚠️  {len(warnings)} validation warnings:")
                            for warning in warnings[:3]:
                                print(f"     - {warning}")
                            if len(warnings) > 3:
                                print(f"     ... and {len(warnings) - 3} more")
                        else:
                            print(f"   ✅ Validation passed")
                    
                except Exception as e:
                    print(f"   ❌ Failed to generate {service_type} Dockerfile: {e}")
            
            # Show summary
            print(f"\n📋 Generation Summary:")
            print(f"   Project: {args.project_name}")
            print(f"   Template: {args.template_type}")
            print(f"   Target Stage: {args.target_stage}")
            print(f"   Files created: {len(created_files)}")
            
            for service_type, file_path in created_files.items():
                file_size = os.path.getsize(file_path) / 1024
                print(f"   - {service_type.upper()}: {os.path.basename(file_path)} ({file_size:.1f} KB)")
            
            # Show build information if requested
            if args.show_build_info:
                print(f"\n🔨 Docker Build Information:")
                
                for service_type in target_services:
                    if service_type in created_files:
                        config = create_dockerfile_config(
                            username=self.user_assignment.login_id,
                            project_name=args.project_name,
                            template_type=args.template_type,
                            service_type=service_type,
                            port_assignment=self.user_assignment,
                            output_dir=args.output_dir,
                            target_stage=args.target_stage
                        )
                        
                        build_info = manager.get_build_info(config)
                        
                        print(f"\n   {service_type.upper()}:")
                        print(f"     Image Name: {build_info['image_name']}")
                        print(f"     Build Context: {build_info['build_context']}")
                        print(f"     Dockerfile: {build_info['dockerfile_path']}")
                        print(f"     Ports: {build_info['ports']}")
                        print(f"     Build Command:")
                        print(f"       docker build -t {build_info['image_name']}:{build_info['image_tag']} \\")
                        print(f"         --target {args.target_stage} \\")
                        print(f"         -f {build_info['dockerfile_path']} \\")
                        print(f"         {build_info['build_context']}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Error generating Dockerfiles: {e}")
            self.logger.error(f"Dockerfile generation failed: {e}")
            return 1
    
    def run(self, args: list = None) -> int:
        """Main entry point"""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        try:
            # Setup logging
            self.setup_logging(parsed_args.verbose, parsed_args.quiet)
            
            # Ensure user is authorized
            self.ensure_user_authorized()
            
            # Ensure dockeredServices directory exists
            self.ensure_dockered_services_dir()
            
            # Route to appropriate command handler
            if hasattr(parsed_args, 'func'):
                return parsed_args.func(parsed_args)
            else:
                parser.print_help()
                return 0
                
        except CLIError as e:
            return self.error_handler.handle_error(
                e, 
                operation=getattr(parsed_args, 'func', lambda x: None).__name__ if hasattr(parsed_args, 'func') else "unknown",
                user_id=self.user_assignment.login_id if self.user_assignment else None,
                json_output=getattr(parsed_args, 'json', False)
            )
        except Exception as e:
            return self.error_handler.handle_error(
                e,
                operation=getattr(parsed_args, 'func', lambda x: None).__name__ if hasattr(parsed_args, 'func') else "unknown",
                user_id=self.user_assignment.login_id if self.user_assignment else None,
                json_output=getattr(parsed_args, 'json', False)
            )
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create command line argument parser"""
        parser = argparse.ArgumentParser(
            description="Multi-Student Docker Compose Management Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  cli create-project rag --template rag
  cli copy-project rag agent
  cli list-projects
  cli show-ports
  cli verify-ports rag
  cli status --json
  cli version-info
  cli template-info rag --validate --show-dependencies
  cli generate-compose rag my-rag-project --validate
  cli generate-database rag my-rag --validate --show-connection-info
  cli generate-dockerfile rag my-rag --validate --show-build-info

For more help on a specific command:
  cli <command> --help
            """
        )
        
        # Global flags
        parser.add_argument('--verbose', '-v', action='store_true', 
                          help='Increase verbosity (show debug messages)')
        parser.add_argument('--quiet', '-q', action='store_true',
                          help='Suppress output except errors')
        parser.add_argument('--json', action='store_true',
                          help='Output structured JSON data')
        
        # Subcommands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # create-project command
        create_parser = subparsers.add_parser('create-project', help='Create new Docker Compose project')
        create_parser.add_argument('project_name', help='Name of the project to create')
        create_parser.add_argument('--template', default='rag', 
                                 choices=['common', 'rag', 'agent'],
                                 help='Project template to use (default: rag)')
        create_parser.add_argument('--shared-mode', action='store_true', 
                                 help='Use shared infrastructure mode (requires common project)')
        create_parser.add_argument('--base-dir', 
                                 help='Base directory for projects (default: ~/dockeredServices)')
        create_parser.set_defaults(func=self.cmd_create_project)
        
        # copy-project command
        copy_parser = subparsers.add_parser('copy-project', help='Copy existing project')
        copy_parser.add_argument('source', help='Source project name')
        copy_parser.add_argument('destination', help='Destination project name')
        copy_parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
        copy_parser.set_defaults(func=self.cmd_copy_project)
        
        # list-projects command
        list_parser = subparsers.add_parser('list-projects', help='List all projects')
        list_parser.add_argument('--json', action='store_true', help='Output JSON format')
        list_parser.set_defaults(func=self.cmd_list_projects)
        
        # show-ports command
        ports_parser = subparsers.add_parser('show-ports', help='Show assigned port ranges')
        ports_parser.add_argument('--json', action='store_true', help='Output JSON format')
        ports_parser.set_defaults(func=self.cmd_show_ports)
        
        # verify-ports command
        verify_parser = subparsers.add_parser('verify-ports', help='Verify port usage in project(s)')
        verify_parser.add_argument('project_name', help='Project name to verify (use "all" for all projects)')
        verify_parser.add_argument('--json', action='store_true', help='Output JSON format')
        verify_parser.set_defaults(func=self.cmd_verify_ports)
        
        # status command
        status_parser = subparsers.add_parser('status', help='Show comprehensive system and project status')
        status_parser.add_argument('--json', action='store_true', help='Output JSON format')
        status_parser.set_defaults(func=self.cmd_status)
        
        # project-status command
        project_status_parser = subparsers.add_parser('project-status', help='Show detailed project status and monitoring')
        project_status_parser.add_argument('project_name', nargs='?', help='Specific project name (optional)')
        project_status_parser.add_argument('--json', action='store_true', help='Output JSON format')
        project_status_parser.add_argument('--detailed', action='store_true', help='Show detailed container information')
        project_status_parser.set_defaults(func=self.cmd_project_status)
        
        # common-status command
        common_parser = subparsers.add_parser('common-status', help='Show common infrastructure status')
        common_parser.add_argument('--json', action='store_true', help='Output JSON format')
        common_parser.set_defaults(func=self.cmd_common_status)
        
        # template-info command
        template_parser = subparsers.add_parser('template-info', help='Show template information and validation')
        template_parser.add_argument('template_type', choices=['common', 'rag', 'agent'], help='Template type to analyze')
        template_parser.add_argument('--validate', action='store_true', help='Validate templates for missing variables')
        template_parser.add_argument('--show-dependencies', action='store_true', help='Show template interdependencies')
        template_parser.add_argument('--json', action='store_true', help='Output JSON format')
        template_parser.set_defaults(func=self.cmd_template_info)
        
        # generate-compose command
        compose_parser = subparsers.add_parser('generate-compose', help='Generate Docker Compose file from template')
        compose_parser.add_argument('template_type', choices=['common', 'rag', 'agent'], help='Template type to generate')
        compose_parser.add_argument('project_name', help='Name of the project')
        compose_parser.add_argument('--output-dir', default='.', help='Output directory (default: current directory)')
        compose_parser.add_argument('--shared-mode', action='store_true', help='Use shared infrastructure mode')
        compose_parser.add_argument('--validate', action='store_true', help='Validate generated Docker Compose')
        compose_parser.set_defaults(func=self.cmd_generate_compose)
        
        # generate-database command
        db_parser = subparsers.add_parser('generate-database', help='Generate database initialization scripts')
        db_parser.add_argument('template_type', choices=['common', 'rag', 'agent'], help='Template type to generate')
        db_parser.add_argument('project_name', help='Name of the project')
        db_parser.add_argument('--database-type', choices=['postgresql', 'mongodb', 'all'], default='all', 
                              help='Database type to generate (default: all supported)')
        db_parser.add_argument('--output-dir', default='.', help='Output directory (default: current directory)')
        db_parser.add_argument('--validate', action='store_true', help='Validate generated database scripts')
        db_parser.add_argument('--show-connection-info', action='store_true', help='Show database connection information')
        db_parser.set_defaults(func=self.cmd_generate_database)
        
        # generate-dockerfile command
        dockerfile_parser = subparsers.add_parser('generate-dockerfile', help='Generate Dockerfile templates')
        dockerfile_parser.add_argument('template_type', choices=['common', 'rag', 'agent'], help='Template type to generate')
        dockerfile_parser.add_argument('project_name', help='Name of the project')
        dockerfile_parser.add_argument('--output-dir', help='Output directory for generated files')
        dockerfile_parser.set_defaults(func=self.cmd_generate_dockerfile)
        
        # remove-project command
        remove_parser = subparsers.add_parser('remove-project', help='Remove project with proper cleanup')
        remove_parser.add_argument('project_name', help='Name of the project to remove')
        remove_parser.add_argument('--force', action='store_true', help='Force removal even if containers are running')
        remove_parser.add_argument('--dry-run', action='store_true', help='Show what would be removed without actually doing it')
        remove_parser.set_defaults(func=self.cmd_remove_project)
        
        # health-check command
        health_parser = subparsers.add_parser('health-check', help='Check Docker system health')
        health_parser.add_argument('--json', action='store_true', help='Output JSON format')
        health_parser.set_defaults(func=self.cmd_health_check)
        
        # cleanup command
        cleanup_parser = subparsers.add_parser('cleanup', help='Clean up unused Docker resources')
        cleanup_parser.add_argument('--dry-run', action='store_true', help='Show what would be cleaned without actually doing it')
        cleanup_parser.add_argument('--volumes', action='store_true', help='Also clean unused volumes')
        cleanup_parser.add_argument('--networks', action='store_true', help='Also clean unused networks (default: True)')
        cleanup_parser.add_argument('--all', action='store_true', help='Clean all unused resources (containers, volumes, networks)')
        cleanup_parser.add_argument('--project', help='Filter cleanup to specific project')
        cleanup_parser.set_defaults(func=self.cmd_cleanup)
        
        # optimize-ports command
        optimize_parser = subparsers.add_parser('optimize-ports', help='Analyze and optimize port usage')
        optimize_parser.add_argument('--json', action='store_true', help='Output JSON format')
        optimize_parser.set_defaults(func=self.cmd_optimize_ports)
        
        # maintenance command
        maintenance_parser = subparsers.add_parser('maintenance', help='Perform system maintenance operations')
        maintenance_parser.add_argument('--operations', nargs='+', 
                                      choices=['containers', 'images', 'networks', 'volumes', 'system', 'stopped-projects'],
                                      help='Specific operations to perform')
        maintenance_parser.add_argument('--project', help='Filter operations to specific project')
        maintenance_parser.add_argument('--suggestions', action='store_true', help='Get cleanup suggestions only')
        maintenance_parser.add_argument('--auto-cleanup', action='store_true', help='Perform automatic cleanup based on suggestions')
        maintenance_parser.add_argument('--dry-run', action='store_true', help='Show what would be done without doing it')
        maintenance_parser.add_argument('--json', action='store_true', help='Output JSON format')
        maintenance_parser.set_defaults(func=self.cmd_maintenance)
        
        # security-check command
        security_parser = subparsers.add_parser('security-check', help='Validate system security and permissions')
        security_parser.add_argument('--project', help='Check security for specific project')
        security_parser.add_argument('--fix', action='store_true', help='Attempt to fix common security issues')
        security_parser.add_argument('--json', action='store_true', help='Output JSON format')
        security_parser.set_defaults(func=self.cmd_security_check)
        
        return parser


    def cmd_maintenance(self, args) -> int:
        """Perform system maintenance operations"""
        self.logger.info(f"Performing maintenance operations")
        
        try:
            # Get user assignment
            if not self.user_assignment:
                print("❌ Unable to get port assignment. Please check your login credentials.")
                return 3
            
            # Handle suggestions only
            if args.suggestions:
                suggestions = get_cleanup_suggestions(self.user_assignment, self.dockered_services_dir)
                self._print_cleanup_suggestions(suggestions, args.json)
                return 0
            
            # Handle auto-cleanup
            if args.auto_cleanup:
                suggestions = get_cleanup_suggestions(self.user_assignment, self.dockered_services_dir)
                if not suggestions:
                    print("✅ System appears clean - no automatic cleanup needed")
                    return 0
                
                # Perform safe automatic cleanup
                operations = ["cleanup_containers", "cleanup_networks"]
                print("🤖 Performing automatic cleanup based on system analysis...")
            else:
                # Use specified operations or default set
                if args.operations:
                    operation_map = {
                        'containers': 'cleanup_containers',
                        'images': 'cleanup_images', 
                        'networks': 'cleanup_networks',
                        'volumes': 'cleanup_volumes',
                        'system': 'cleanup_system',
                        'stopped-projects': 'cleanup_stopped_projects'
                    }
                    operations = [operation_map[op] for op in args.operations if op in operation_map]
                else:
                    operations = ["cleanup_containers", "cleanup_images", "cleanup_networks"]
            
            # Perform maintenance
            report = perform_cleanup(
                operations=operations,
                project_filter=args.project,
                base_dir=self.dockered_services_dir,
                dry_run=args.dry_run
            )
            
            # Print results
            if args.json:
                self._print_maintenance_report_json(report)
            else:
                self._print_cleanup_report(report, args.dry_run)
            
            # Return success if all operations succeeded
            failed_ops = [op for op in report.operations_performed if not op.success]
            return 0 if len(failed_ops) == 0 else 1
            
        except Exception as e:
            self.logger.error(f"Maintenance failed: {e}")
            print(f"❌ Maintenance failed: {e}")
            return 1
    
    def _print_cleanup_report(self, report: MaintenanceReport, dry_run: bool = False):
        """Print cleanup report in human-readable format"""
        mode = "🔍 DRY RUN" if dry_run else "🧹 CLEANUP"
        print(f"\n{mode} Maintenance Report")
        print(f"User: {report.username}")
        print(f"Generated: {report.timestamp}")
        
        # Operations Summary
        successful_ops = [op for op in report.operations_performed if op.success]
        failed_ops = [op for op in report.operations_performed if not op.success]
        
        print(f"\n📊 Operations Summary")
        print(f"Total Operations: {len(report.operations_performed)}")
        print(f"Successful: {len(successful_ops)}")
        print(f"Failed: {len(failed_ops)}")
        
        if report.total_space_freed:
            print(f"Total Space Freed: {report.total_space_freed}")
        
        # Operation Details
        print(f"\n🔧 Operation Details")
        for op in report.operations_performed:
            status = "✅" if op.success else "❌"
            print(f"  {status} {op.operation}: {op.items_removed} items")
            
            if op.space_freed:
                print(f"    Space freed: {op.space_freed}")
                
            if op.errors:
                for error in op.errors:
                    print(f"    ❌ {error}")
                    
            if op.warnings:
                for warning in op.warnings:
                    print(f"    ⚠️  {warning}")
                    
            if op.details and not dry_run:
                if 'message' in op.details:
                    print(f"    ℹ️  {op.details['message']}")
        
        # System Health Comparison
        if report.system_health_before and report.system_health_after:
            print(f"\n📈 System Health Changes")
            before = report.system_health_before
            after = report.system_health_after
            
            if 'total_containers' in before and 'total_containers' in after:
                container_change = before['total_containers'] - after['total_containers']
                if container_change > 0:
                    print(f"  Containers: {before['total_containers']} → {after['total_containers']} (-{container_change})")
                elif container_change < 0:
                    print(f"  Containers: {before['total_containers']} → {after['total_containers']} (+{abs(container_change)})")
                else:
                    print(f"  Containers: {after['total_containers']} (no change)")
        
        # Recommendations
        if report.recommendations:
            print(f"\n💡 Recommendations")
            for rec in report.recommendations:
                print(f"  • {rec}")
        
        # Warnings
        if report.warnings:
            print(f"\n⚠️  Warnings")
            for warning in report.warnings:
                print(f"  • {warning}")
    
    def _print_cleanup_suggestions(self, suggestions: List[str], json_output: bool = False):
        """Print cleanup suggestions"""
        if json_output:
            import json
            print(json.dumps({"suggestions": suggestions}, indent=2))
            return
        
        print(f"\n💡 Cleanup Suggestions")
        
        if not suggestions:
            print("  ✅ System appears clean - no suggestions at this time")
            return
        
        print(f"Found {len(suggestions)} suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
        
        print(f"\n🔧 To act on these suggestions:")
        print(f"  • Run cleanup: python cli.py cleanup --volumes --networks")
        print(f"  • Auto cleanup: python cli.py maintenance --auto-cleanup")
        print(f"  • Dry run first: python cli.py maintenance --dry-run")
    
    def _print_maintenance_report_json(self, report: MaintenanceReport):
        """Print maintenance report in JSON format"""
        import json
        
        # Convert to JSON-serializable format
        report_dict = {
            "timestamp": report.timestamp,
            "username": report.username,
            "total_space_freed": report.total_space_freed,
            "operations_performed": [
                {
                    "operation": op.operation,
                    "success": op.success,
                    "items_removed": op.items_removed,
                    "space_freed": op.space_freed,
                    "errors": op.errors,
                    "warnings": op.warnings,
                    "details": op.details
                }
                for op in report.operations_performed
            ],
            "recommendations": report.recommendations,
            "warnings": report.warnings,
            "system_health_before": report.system_health_before,
            "system_health_after": report.system_health_after
        }
        
        print(json.dumps(report_dict, indent=2))
    
    def cmd_security_check(self, args) -> int:
        """Validate system security and permissions"""
        self.logger.info("Performing security validation")
        
        try:
            # Get user assignment
            if not self.user_assignment:
                print("❌ Unable to get user assignment. Please check your login credentials.")
                return 3
            
            if args.project:
                # Validate specific project security
                project_path = os.path.join(self.dockered_services_dir, args.project)
                results = validate_project_security(self.user_assignment.login_id, project_path)
                
                if args.json:
                    print(json.dumps(results, indent=2))
                else:
                    self._print_project_security_results(results)
                
                return 0 if results["status"] == "PASS" else 1
            else:
                # Validate system security
                results = validate_system_security(self.user_assignment.login_id, self.dockered_services_dir)
                
                if args.json:
                    print(json.dumps(results, indent=2))
                else:
                    self._print_system_security_results(results, args.fix)
                
                return 0 if results["overall_status"] == "PASS" else 1
                
        except Exception as e:
            self.logger.error(f"Security check failed: {e}")
            print(f"❌ Security check failed: {e}")
            return 1
    
    def _print_system_security_results(self, results: Dict[str, Any], fix_issues: bool = False):
        """Print system security validation results"""
        print(f"\n🛡️  System Security Validation")
        print(f"User: {results['user_id']}")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Overall Status: {'✅ PASS' if results['overall_status'] == 'PASS' else '❌ FAIL'}")
        
        # Print validation details
        print(f"\n📋 Security Validations:")
        
        for validation_name, validation_data in results["validations"].items():
            status_icon = "✅" if validation_data["status"] == "PASS" else "❌"
            print(f"  {status_icon} {validation_name.replace('_', ' ').title()}: {validation_data['status']}")
            
            if validation_data["status"] == "FAIL" and "issues" in validation_data:
                for issue in validation_data["issues"]:
                    print(f"    • {issue}")
        
        # Print critical issues
        if results["critical_issues"]:
            print(f"\n🚨 Critical Issues ({len(results['critical_issues'])}):")
            for issue in results["critical_issues"]:
                print(f"  • {issue}")
        
        # Print recommendations
        if results["recommendations"]:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(results["recommendations"], 1):
                print(f"  {i}. {rec}")
        
        # Show fix suggestions if requested
        if fix_issues and results["recommendations"]:
            print(f"\n🔧 To fix these issues automatically:")
            print(f"  • Run: python cli.py security-check --fix")
            print(f"  • Or follow the recommendations above manually")
    
    def _print_project_security_results(self, results: Dict[str, Any]):
        """Print project security validation results"""
        print(f"\n🛡️  Project Security Validation")
        print(f"User: {results['user_id']}")
        print(f"Project: {results['project_path']}")
        print(f"Status: {'✅ PASS' if results['status'] == 'PASS' else '❌ FAIL'}")
        
        # Print permission details
        if "permissions" in results:
            perms = results["permissions"]
            print(f"\n📁 Directory Permissions:")
            print(f"  Path: {perms['path']}")
            print(f"  Owner: {perms['owner']}")
            print(f"  Group: {perms['group']}")
            print(f"  Permissions: {perms['permissions']}")
            print(f"  Readable: {'✅' if perms['readable'] else '❌'}")
            print(f"  Writable: {'✅' if perms['writable'] else '❌'}")
            print(f"  Executable: {'✅' if perms['executable'] else '❌'}")
        
        # Print issues
        if results["issues"]:
            print(f"\n🚨 Issues Found:")
            for issue in results["issues"]:
                print(f"  • {issue}")
        
        # Print recommendations
        if results["recommendations"]:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(results["recommendations"], 1):
                print(f"  {i}. {rec}")


def main():
    """Main entry point for CLI tool"""
    cli = DockerComposeCLI()
    return cli.run()


if __name__ == '__main__':
    sys.exit(main())