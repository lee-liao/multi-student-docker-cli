#!/usr/bin/env python3
"""
Database Initialization Template System

Manages database initialization templates for PostgreSQL and MongoDB
with project-specific schema generation and student-specific credentials.
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from src.core.template_processor import TemplateProcessor, create_template_context
from src.core.port_assignment import PortAssignment


@dataclass
class DatabaseConfig:
    """Configuration for database initialization"""
    username: str
    project_name: str
    template_type: str
    port_assignment: PortAssignment
    database_type: str  # 'postgresql' or 'mongodb'
    output_dir: str
    custom_variables: Dict[str, Any]


class DatabaseManager:
    """Manages database initialization template system"""
    
    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize database manager
        
        Args:
            templates_dir: Directory containing template files
        """
        self.templates_dir = templates_dir
        self.template_processor = TemplateProcessor(templates_dir)
        
        # Database type mappings
        self.db_type_mappings = {
            'common': ['postgresql', 'mongodb'],
            'rag': ['postgresql'],
            'agent': ['postgresql']
        }
        
        # Template file mappings
        self.template_files = {
            'postgresql': {
                'common': 'common/database/postgresql/init.sql.template',
                'rag': 'rag/database/init.sql.template',
                'agent': 'agent/database/init.sql.template'
            },
            'mongodb': {
                'common': 'common/database/mongodb/init.js.template',
                'rag': None,  # RAG uses PostgreSQL only
                'agent': None  # Agent uses PostgreSQL only
            }
        }
    
    def get_supported_databases(self, template_type: str) -> List[str]:
        """
        Get list of supported databases for a template type
        
        Args:
            template_type: Type of template (common, rag, agent)
            
        Returns:
            List of supported database types
        """
        return self.db_type_mappings.get(template_type, [])
    
    def generate_database_init_script(self, config: DatabaseConfig) -> str:
        """
        Generate database initialization script from template
        
        Args:
            config: Database configuration
            
        Returns:
            Generated initialization script content
        """
        # Get template file path
        template_file = self.template_files.get(config.database_type, {}).get(config.template_type)
        
        if not template_file:
            raise ValueError(
                f"No {config.database_type} template available for {config.template_type} projects"
            )
        
        template_path = os.path.join(self.templates_dir, template_file)
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Database template not found: {template_path}")
        
        # Create template context
        context = create_template_context(
            username=config.username,
            project_name=config.project_name,
            template_type=config.template_type,
            port_assignment=config.port_assignment,
            has_common_project=False  # Database init is always standalone
        )
        
        # Generate template variables
        variables = self.template_processor.generate_template_variables(context)
        
        # Add database-specific variables
        variables.update(self._generate_database_variables(config))
        
        # Add custom variables
        variables.update(config.custom_variables)
        
        # Process template
        return self.template_processor.process_template_file(template_path, variables)
    
    def _generate_database_variables(self, config: DatabaseConfig) -> Dict[str, Any]:
        """Generate database-specific template variables"""
        variables = {
            'DATABASE_TYPE': config.database_type,
            'CURRENT_TIMESTAMP': datetime.now().isoformat(),
            'DATABASE_NAME': self._get_database_name(config.template_type),
            'USER_PASSWORD': f"{config.username}_password_2024",
            'REDIS_PASSWORD': f"{config.username}_redis_2024"
        }
        
        # Add database-specific configurations
        if config.database_type == 'postgresql':
            variables.update({
                'POSTGRES_DB': self._get_database_name(config.template_type),
                'POSTGRES_USER': f"{config.username}_user",
                'POSTGRES_PASSWORD': f"{config.username}_password_2024",
                'VECTOR_DIMENSION': 1536,  # OpenAI embedding dimension
                'MAX_CONNECTIONS': 100,
                'SHARED_BUFFERS': '256MB'
            })
        elif config.database_type == 'mongodb':
            variables.update({
                'MONGO_INITDB_ROOT_USERNAME': f"{config.username}_admin",
                'MONGO_INITDB_ROOT_PASSWORD': f"{config.username}_password_2024",
                'MONGO_INITDB_DATABASE': self._get_database_name(config.template_type),
                'APP_USERNAME': f"{config.username}_app",
                'APP_PASSWORD': f"{config.username}_password_2024"
            })
        
        return variables
    
    def _get_database_name(self, template_type: str) -> str:
        """Get database name based on template type"""
        db_names = {
            'common': 'shared_db',
            'rag': 'rag_chatbot',
            'agent': 'agent_system'
        }
        return db_names.get(template_type, 'default_db')
    
    def validate_database_script(self, script_content: str, database_type: str) -> List[str]:
        """
        Validate database initialization script
        
        Args:
            script_content: Database script content
            database_type: Type of database (postgresql, mongodb)
            
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        if database_type == 'postgresql':
            warnings.extend(self._validate_postgresql_script(script_content))
        elif database_type == 'mongodb':
            warnings.extend(self._validate_mongodb_script(script_content))
        else:
            warnings.append(f"Unknown database type: {database_type}")
        
        return warnings
    
    def _validate_postgresql_script(self, script_content: str) -> List[str]:
        """Validate PostgreSQL script"""
        warnings = []
        
        # Check for required extensions
        required_extensions = ['uuid-ossp', 'vector']
        for ext in required_extensions:
            if f'CREATE EXTENSION IF NOT EXISTS "{ext}"' not in script_content:
                warnings.append(f"Missing required extension: {ext}")
        
        # Check for basic SQL structure
        if 'CREATE TABLE' not in script_content:
            warnings.append("No CREATE TABLE statements found")
        
        if 'CREATE INDEX' not in script_content:
            warnings.append("No CREATE INDEX statements found - performance may be impacted")
        
        # Check for security considerations
        if 'GRANT' not in script_content:
            warnings.append("No GRANT statements found - permissions may not be set correctly")
        
        # Check for vector operations (if using pgvector)
        if 'vector(' in script_content and 'ivfflat' not in script_content:
            warnings.append("Vector columns found but no vector indexes - search performance may be poor")
        
        return warnings
    
    def _validate_mongodb_script(self, script_content: str) -> List[str]:
        """Validate MongoDB script"""
        warnings = []
        
        # Check for basic MongoDB operations
        if 'createCollection' not in script_content:
            warnings.append("No createCollection statements found")
        
        if 'createIndex' not in script_content:
            warnings.append("No createIndex statements found - performance may be impacted")
        
        if 'createUser' not in script_content:
            warnings.append("No createUser statements found - authentication may not work")
        
        # Check for validation schemas
        if '$jsonSchema' not in script_content:
            warnings.append("No validation schemas found - data integrity may be compromised")
        
        return warnings
    
    def create_database_init_files(self, config: DatabaseConfig) -> Dict[str, str]:
        """
        Create database initialization files for a project
        
        Args:
            config: Database configuration
            
        Returns:
            Dictionary mapping file paths to their content
        """
        supported_dbs = self.get_supported_databases(config.template_type)
        created_files = {}
        
        for db_type in supported_dbs:
            if config.database_type == 'all' or config.database_type == db_type:
                # Create config for this database type
                db_config = DatabaseConfig(
                    username=config.username,
                    project_name=config.project_name,
                    template_type=config.template_type,
                    port_assignment=config.port_assignment,
                    database_type=db_type,
                    output_dir=config.output_dir,
                    custom_variables=config.custom_variables
                )
                
                try:
                    # Generate script content
                    script_content = self.generate_database_init_script(db_config)
                    
                    # Validate script
                    warnings = self.validate_database_script(script_content, db_type)
                    if warnings:
                        print(f"⚠️  {db_type.upper()} validation warnings:")
                        for warning in warnings[:3]:
                            print(f"  - {warning}")
                        if len(warnings) > 3:
                            print(f"  ... and {len(warnings) - 3} more warnings")
                    
                    # Determine output file path using centralized configuration
                    from src.config.file_paths import get_output_path
                    
                    try:
                        if db_type == 'postgresql':
                            relative_path = get_output_path(config.template_type, 'postgresql_init')
                        elif db_type == 'mongodb':
                            relative_path = get_output_path(config.template_type, 'mongodb_init')
                        
                        output_file = os.path.join(config.output_dir, relative_path)
                    except KeyError as e:
                        # Fallback to old behavior if path not defined
                        print(f"⚠️  Using fallback path for {db_type} in {config.template_type}: {e}")
                        if db_type == 'postgresql':
                            output_file = os.path.join(config.output_dir, 'database', 'init.sql')
                        elif db_type == 'mongodb':
                            output_file = os.path.join(config.output_dir, 'database', 'init.js')
                    
                    # Create directory if it doesn't exist
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    
                    # Write file
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(script_content)
                    
                    created_files[output_file] = script_content
                    
                except Exception as e:
                    print(f"⚠️  Failed to create {db_type} initialization script: {e}")
        
        return created_files
    
    def get_database_connection_info(self, config: DatabaseConfig) -> Dict[str, Any]:
        """
        Get database connection information for a configuration
        
        Args:
            config: Database configuration
            
        Returns:
            Dictionary with connection information
        """
        connection_info = {
            'username': config.username,
            'project_name': config.project_name,
            'template_type': config.template_type,
            'databases': {}
        }
        
        supported_dbs = self.get_supported_databases(config.template_type)
        
        for db_type in supported_dbs:
            if db_type == 'postgresql':
                port = None
                for port_val in config.port_assignment.all_ports:
                    # Use first available port for PostgreSQL
                    port = port_val
                    break
                
                connection_info['databases']['postgresql'] = {
                    'host': 'localhost',
                    'port': port,
                    'database': self._get_database_name(config.template_type),
                    'username': f"{config.username}_user",
                    'password': f"{config.username}_password_2024",
                    'connection_url': f"postgresql://{config.username}_user:{config.username}_password_2024@localhost:{port}/{self._get_database_name(config.template_type)}"
                }
            
            elif db_type == 'mongodb':
                port = None
                for port_val in config.port_assignment.all_ports[1:]:  # Skip first port (used by PostgreSQL)
                    port = port_val
                    break
                
                connection_info['databases']['mongodb'] = {
                    'host': 'localhost',
                    'port': port,
                    'database': self._get_database_name(config.template_type),
                    'username': f"{config.username}_admin",
                    'password': f"{config.username}_password_2024",
                    'connection_url': f"mongodb://{config.username}_admin:{config.username}_password_2024@localhost:{port}/{self._get_database_name(config.template_type)}"
                }
        
        return connection_info


def create_database_config(username: str, project_name: str, template_type: str,
                         port_assignment: PortAssignment, database_type: str,
                         output_dir: str, custom_variables: Optional[Dict[str, Any]] = None) -> DatabaseConfig:
    """
    Create database configuration
    
    Args:
        username: Student's login ID
        project_name: Name of the project
        template_type: Type of template (common, rag, agent)
        port_assignment: Student's port assignment
        database_type: Type of database (postgresql, mongodb, all)
        output_dir: Output directory for generated files
        custom_variables: Custom template variables
        
    Returns:
        DatabaseConfig object
    """
    return DatabaseConfig(
        username=username,
        project_name=project_name,
        template_type=template_type,
        port_assignment=port_assignment,
        database_type=database_type,
        output_dir=output_dir,
        custom_variables=custom_variables or {}
    )


# Convenience functions for common operations
def generate_postgresql_init(username: str, project_name: str, template_type: str,
                           port_assignment: PortAssignment, output_dir: str) -> str:
    """Generate PostgreSQL initialization script"""
    manager = DatabaseManager()
    config = create_database_config(
        username=username,
        project_name=project_name,
        template_type=template_type,
        port_assignment=port_assignment,
        database_type='postgresql',
        output_dir=output_dir
    )
    return manager.generate_database_init_script(config)


def generate_mongodb_init(username: str, project_name: str, template_type: str,
                        port_assignment: PortAssignment, output_dir: str) -> str:
    """Generate MongoDB initialization script"""
    manager = DatabaseManager()
    config = create_database_config(
        username=username,
        project_name=project_name,
        template_type=template_type,
        port_assignment=port_assignment,
        database_type='mongodb',
        output_dir=output_dir
    )
    return manager.generate_database_init_script(config)


def create_all_database_files(username: str, project_name: str, template_type: str,
                            port_assignment: PortAssignment, output_dir: str) -> Dict[str, str]:
    """Create all database initialization files for a project"""
    manager = DatabaseManager()
    config = create_database_config(
        username=username,
        project_name=project_name,
        template_type=template_type,
        port_assignment=port_assignment,
        database_type='all',
        output_dir=output_dir
    )
    return manager.create_database_init_files(config)