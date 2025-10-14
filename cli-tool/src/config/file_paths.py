#!/usr/bin/env python3
"""
Centralized File Path Configuration

This module defines the canonical file paths for different project templates
to ensure consistency between Docker Compose volume mounts and file generation.
"""

from typing import Dict, List

# Template file path configurations
TEMPLATE_FILE_PATHS = {
    'common': {
        # Database initialization files
        'postgresql_init': 'database/postgresql/init.sql',
        'mongodb_init': 'database/mongodb/init.js',
        
        # Observability configuration files
        'prometheus_config': 'observability/prometheus.yml',
        'otel_collector_config': 'observability/otel-collector-config.yaml',
        'grafana_datasources': 'observability/grafana/provisioning/datasources/prometheus.yml',
        
        # Docker Compose and project files
        'docker_compose': 'docker-compose.yml',
        'readme': 'README.md',
        'setup_script': 'setup.sh'
    },
    
    'rag': {
        # Database initialization files (single file for rag projects)
        'postgresql_init': 'database/init.sql',
        
        # Application files
        'backend_dockerfile': 'backend/Dockerfile',
        'frontend_dockerfile': 'frontend/Dockerfile',
        
        # Docker Compose and project files
        'docker_compose': 'docker-compose.yml',
        'readme': 'README.md',
        'setup_script': 'setup.sh'
    },
    
    'agent': {
        # Database initialization files (single file for agent projects)
        'postgresql_init': 'database/init.sql',
        
        # Application files
        'backend_dockerfile': 'backend/Dockerfile',
        'frontend_dockerfile': 'frontend/Dockerfile',
        
        # Docker Compose and project files
        'docker_compose': 'docker-compose.yml',
        'readme': 'README.md',
        'setup_script': 'setup.sh'
    }
}

# Template source paths (where templates are located)
TEMPLATE_SOURCE_PATHS = {
    'common': {
        'postgresql_init': 'common/database/postgresql/init.sql.template',
        'mongodb_init': 'common/database/mongodb/init.js.template',
        'prometheus_config': 'observability/prometheus.yml',
        'otel_collector_config': 'observability/otel-collector-config.yaml',
        'docker_compose': 'common/docker-compose.yml.template',
        'readme': 'common/README.md.template',
        'setup_script': 'common/setup.sh.template'
    },
    
    'rag': {
        'postgresql_init': 'rag/database/init.sql.template',
        'backend_dockerfile': 'rag/backend/Dockerfile.template',
        'frontend_dockerfile': 'rag/frontend/Dockerfile.template',
        'docker_compose': 'rag/docker-compose.yml.template',
        'readme': 'rag/README.md.template',
        'setup_script': 'rag/setup.sh.template'
    },
    
    'agent': {
        'postgresql_init': 'agent/database/init.sql.template',
        'backend_dockerfile': 'agent/backend/Dockerfile.template',
        'frontend_dockerfile': 'agent/frontend/Dockerfile.template',
        'docker_compose': 'agent/docker-compose.yml.template',
        'readme': 'agent/README.md.template',
        'setup_script': 'agent/setup.sh.template'
    }
}


def get_output_path(template_type: str, file_type: str) -> str:
    """
    Get the output path for a specific file type in a template
    
    Args:
        template_type: Type of template (common, rag, agent)
        file_type: Type of file (postgresql_init, mongodb_init, etc.)
        
    Returns:
        Relative path where the file should be created
        
    Raises:
        KeyError: If template_type or file_type is not found
    """
    if template_type not in TEMPLATE_FILE_PATHS:
        raise KeyError(f"Unknown template type: {template_type}")
    
    if file_type not in TEMPLATE_FILE_PATHS[template_type]:
        raise KeyError(f"Unknown file type '{file_type}' for template '{template_type}'")
    
    return TEMPLATE_FILE_PATHS[template_type][file_type]


def get_template_source_path(template_type: str, file_type: str) -> str:
    """
    Get the template source path for a specific file type
    
    Args:
        template_type: Type of template (common, rag, agent)
        file_type: Type of file (postgresql_init, mongodb_init, etc.)
        
    Returns:
        Relative path to the template file
        
    Raises:
        KeyError: If template_type or file_type is not found
    """
    if template_type not in TEMPLATE_SOURCE_PATHS:
        raise KeyError(f"Unknown template type: {template_type}")
    
    if file_type not in TEMPLATE_SOURCE_PATHS[template_type]:
        raise KeyError(f"Unknown file type '{file_type}' for template '{template_type}'")
    
    return TEMPLATE_SOURCE_PATHS[template_type][file_type]


def get_all_output_paths(template_type: str) -> Dict[str, str]:
    """
    Get all output paths for a template type
    
    Args:
        template_type: Type of template (common, rag, agent)
        
    Returns:
        Dictionary mapping file types to output paths
    """
    if template_type not in TEMPLATE_FILE_PATHS:
        raise KeyError(f"Unknown template type: {template_type}")
    
    return TEMPLATE_FILE_PATHS[template_type].copy()


def get_database_file_paths(template_type: str) -> List[str]:
    """
    Get all database-related file paths for a template type
    
    Args:
        template_type: Type of template (common, rag, agent)
        
    Returns:
        List of database file paths
    """
    paths = []
    template_paths = TEMPLATE_FILE_PATHS.get(template_type, {})
    
    for file_type, path in template_paths.items():
        if 'init' in file_type and ('postgresql' in file_type or 'mongodb' in file_type):
            paths.append(path)
    
    return paths


def validate_template_consistency() -> List[str]:
    """
    Validate that all template types have consistent file type definitions
    
    Returns:
        List of validation issues
    """
    issues = []
    
    # Check that all template types have required files
    required_files = ['docker_compose', 'readme', 'setup_script']
    
    for template_type in TEMPLATE_FILE_PATHS:
        for required_file in required_files:
            if required_file not in TEMPLATE_FILE_PATHS[template_type]:
                issues.append(f"Template '{template_type}' missing required file: {required_file}")
    
    # Check that source paths exist for all output paths
    for template_type in TEMPLATE_FILE_PATHS:
        if template_type not in TEMPLATE_SOURCE_PATHS:
            issues.append(f"No source paths defined for template type: {template_type}")
            continue
            
        for file_type in TEMPLATE_FILE_PATHS[template_type]:
            if file_type not in TEMPLATE_SOURCE_PATHS[template_type]:
                issues.append(f"No source path for {template_type}.{file_type}")
    
    return issues


# Convenience functions for common operations
def get_postgresql_init_path(template_type: str) -> str:
    """Get PostgreSQL initialization file path"""
    return get_output_path(template_type, 'postgresql_init')


def get_mongodb_init_path(template_type: str) -> str:
    """Get MongoDB initialization file path (common template only)"""
    if template_type != 'common':
        raise ValueError(f"MongoDB init file only available for 'common' template, not '{template_type}'")
    return get_output_path(template_type, 'mongodb_init')


def get_observability_config_paths(template_type: str) -> Dict[str, str]:
    """Get all observability configuration file paths"""
    if template_type != 'common':
        return {}
    
    return {
        'prometheus': get_output_path(template_type, 'prometheus_config'),
        'otel_collector': get_output_path(template_type, 'otel_collector_config')
    }