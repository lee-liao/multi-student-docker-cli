"""
Template Processing Engine

Handles template file processing with variable substitution, conditional logic,
and interdependency warnings for Docker Compose projects.
"""

import os
import re
import yaml
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from src.core.port_assignment import PortAssignment
from src.config.cors_config_manager import generate_cors_variables


@dataclass
class TemplateContext:
    """Context information for template processing"""
    username: str
    project_name: str
    template_type: str
    port_assignment: PortAssignment
    has_common_project: bool
    available_ports: List[int]
    template_variables: Dict[str, Any]


class TemplateProcessor:
    """Processes template files with variable substitution and conditional logic"""
    
    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize template processor
        
        Args:
            templates_dir: Directory containing template files
        """
        self.templates_dir = templates_dir
        self.variable_pattern = re.compile(r'\{\{([^}]+)\}\}')
        self.conditional_pattern = re.compile(r'\{\{#(if_[^}]+)\}\}(.*?)\{\{/\1\}\}', re.DOTALL)
        self.else_pattern = re.compile(r'\{\{else\}\}')
    
    def generate_template_variables(self, context: TemplateContext) -> Dict[str, Any]:
        """
        Generate template variables from context
        
        Args:
            context: Template processing context
            
        Returns:
            Dictionary of template variables
        """
        # Get available ports from assignment
        all_ports = context.port_assignment.all_ports
        
        # Assign ports sequentially from available pool
        port_assignments = {}
        port_index = 0
        
        # Define service port assignments based on template type and mode
        if context.template_type == 'common':
            services = ['POSTGRES_PORT', 'MONGODB_PORT', 'REDIS_PORT', 
                       'CHROMADB_PORT', 'JAEGER_UI_PORT', 'PROMETHEUS_PORT', 'GRAFANA_PORT']
        elif context.has_common_project:
            # Lightweight mode - only application services
            services = ['BACKEND_PORT', 'FRONTEND_PORT']
        else:
            # Self-contained mode - all services
            services = ['POSTGRES_PORT', 'MONGODB_PORT', 'REDIS_PORT', 'CHROMADB_PORT',
                       'BACKEND_PORT', 'FRONTEND_PORT', 'JAEGER_UI_PORT', 'PROMETHEUS_PORT', 'GRAFANA_PORT']
        
        # Assign ports to services
        for service in services:
            if port_index < len(all_ports):
                port_assignments[service] = all_ports[port_index]
                port_index += 1
            else:
                port_assignments[service] = None
        
        # Generate CORS configuration using CORS manager
        cors_variables = generate_cors_variables(
            username=context.username,
            project_name=context.project_name,
            template_type=context.template_type,
            port_assignment=context.port_assignment,
            has_common_project=context.has_common_project,
            frontend_port=port_assignments.get('FRONTEND_PORT'),
            backend_port=port_assignments.get('BACKEND_PORT')
        )
        
        # Base template variables
        variables = {
            'USERNAME': context.username,
            'PROJECT_NAME': context.project_name,
            'TEMPLATE_TYPE': context.template_type,
            'HAS_COMMON_PROJECT': context.has_common_project,
            'TOTAL_PORTS': context.port_assignment.total_ports,
            'SEGMENT1_START': context.port_assignment.segment1_start,
            'SEGMENT1_END': context.port_assignment.segment1_end,
            'SEGMENT2_START': context.port_assignment.segment2_start,
            'SEGMENT2_END': context.port_assignment.segment2_end,
            'HAS_TWO_SEGMENTS': context.port_assignment.has_two_segments,
            **port_assignments,
            **cors_variables
        }
        
        # Add conditional flags
        variables.update({
            'if_common_project': context.has_common_project,
            'if_no_common_project': not context.has_common_project,
            'if_self_contained': not context.has_common_project,
            'if_shared_mode': context.has_common_project,
            'if_rag_template': context.template_type == 'rag',
            'if_agent_template': context.template_type == 'agent',
            'if_common_template': context.template_type == 'common'
        })
        
        return variables
    

    def process_template_file(self, template_path: str, variables: Dict[str, Any]) -> str:
        """
        Process a template file with variable substitution and conditional logic
        
        Args:
            template_path: Path to template file
            variables: Template variables for substitution
            
        Returns:
            Processed template content
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Process conditional blocks first (they handle their own variable substitution)
        content = self._process_conditionals(content, variables)
        
        # Process any remaining variable substitutions
        content = self._process_variables(content, variables)
        
        return content
    
    def _process_conditionals(self, content: str, variables: Dict[str, Any]) -> str:
        """Process conditional blocks in template content"""
        def replace_conditional(match):
            condition = match.group(1)
            block_content = match.group(2)
            
            # Check if condition is true - handle boolean conversion
            condition_value = variables.get(condition, False)
            if isinstance(condition_value, str):
                condition_value = condition_value.lower() in ('true', '1', 'yes')
            
            # Handle else blocks
            if '{{else}}' in block_content:
                if_part, else_part = block_content.split('{{else}}', 1)
                selected_content = if_part.strip() if condition_value else else_part.strip()
            else:
                selected_content = block_content.strip() if condition_value else ''
            
            return selected_content
        
        # Process all conditional blocks iteratively
        processed_content = content
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while self.conditional_pattern.search(processed_content) and iteration < max_iterations:
            processed_content = self.conditional_pattern.sub(replace_conditional, processed_content)
            iteration += 1
        
        return processed_content
    
    def _process_variables(self, content: str, variables: Dict[str, Any]) -> str:
        """Process variable substitutions in template content"""
        def replace_variable(match):
            var_name = match.group(1).strip()
            
            # Handle nested variable access (e.g., {{PORT.BACKEND}})
            if '.' in var_name:
                parts = var_name.split('.')
                value = variables
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return match.group(0)  # Return original if not found
                return str(value) if value is not None else ''
            
            # Simple variable substitution
            value = variables.get(var_name)
            if value is not None:
                return str(value)
            else:
                # Return original placeholder if variable not found
                return match.group(0)
        
        return self.variable_pattern.sub(replace_variable, content)
    
    def validate_template(self, template_path: str, variables: Dict[str, Any]) -> List[str]:
        """
        Validate template and check for missing variables
        
        Args:
            template_path: Path to template file
            variables: Available template variables
            
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        if not os.path.exists(template_path):
            warnings.append(f"Template file not found: {template_path}")
            return warnings
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Process conditionals first to get the actual content that will be rendered
        processed_content = self._process_conditionals(content, variables)
        
        # Find all variable references in the processed content
        variable_refs = self.variable_pattern.findall(processed_content)
        
        # Check for missing variables
        missing_vars = set()
        for var_ref in variable_refs:
            var_name = var_ref.strip()
            if '.' in var_name:
                # Handle nested access
                parts = var_name.split('.')
                value = variables
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        missing_vars.add(var_name)
                        break
            elif var_name not in variables:
                missing_vars.add(var_name)
        
        # Add warnings for missing variables
        for var_name in sorted(missing_vars):
            warnings.append(f"Missing variable: {var_name}")
        
        # Check for malformed conditional blocks
        conditional_refs = re.findall(r'\{\{#(if_[^}]+)\}\}', content)
        for condition in conditional_refs:
            if condition not in variables:
                warnings.append(f"Missing conditional variable: {condition}")
        
        # Check for unmatched conditional blocks
        open_blocks = re.findall(r'\{\{#(if_[^}]+)\}\}', content)
        close_blocks = re.findall(r'\{\{/(if_[^}]+)\}\}', content)
        
        if len(open_blocks) != len(close_blocks):
            warnings.append("Unmatched conditional blocks detected")
        
        return warnings
    
    def get_template_dependencies(self, template_type: str) -> List[str]:
        """
        Get list of template files that are interdependent
        
        Args:
            template_type: Type of template (rag, agent, common)
            
        Returns:
            List of interdependent template files
        """
        base_templates = [
            f"{template_type}/docker-compose.yml.template",
            f"{template_type}/setup.sh.template", 
            f"{template_type}/README.md.template"
        ]
        
        # Add template-specific dependencies
        if template_type in ['rag', 'agent']:
            base_templates.extend([
                f"{template_type}/backend/Dockerfile.template",
                f"{template_type}/frontend/Dockerfile.template",
                f"{template_type}/database/init.sql.template"
            ])
        elif template_type == 'common':
            base_templates.extend([
                f"{template_type}/database/postgresql/init.sql.template",
                f"{template_type}/database/mongodb/init.js.template"
            ])
        
        return base_templates
    
    def show_interdependency_warning(self, template_type: str) -> str:
        """
        Generate interdependency warning message
        
        Args:
            template_type: Type of template
            
        Returns:
            Warning message about template interdependencies
        """
        dependencies = self.get_template_dependencies(template_type)
        
        warning = f"""
⚠️  TEMPLATE INTERDEPENDENCY WARNING ⚠️

The following template files are interconnected:
"""
        for dep in dependencies:
            warning += f"  - {dep}\n"
        
        warning += f"""
Modifying one template may require updating others to maintain consistency.

Key interdependencies:
  • docker-compose.yml ↔ setup.sh (service names, ports)
  • docker-compose.yml ↔ README.md (port documentation)
  • setup.sh ↔ database init files (initialization logic)
  • Dockerfiles ↔ docker-compose.yml (image names, build context)

Always test the complete project after template modifications!
"""
        return warning
    
    def process_project_templates(self, context: TemplateContext, output_dir: str) -> Dict[str, str]:
        """
        Process all templates for a project and generate output files
        
        Args:
            context: Template processing context
            output_dir: Directory to write processed templates
            
        Returns:
            Dictionary mapping output file paths to their content
        """
        # Generate template variables
        variables = self.generate_template_variables(context)
        
        # Get template dependencies
        template_files = self.get_template_dependencies(context.template_type)
        
        # Process each template
        processed_files = {}
        
        for template_file in template_files:
            template_path = os.path.join(self.templates_dir, template_file)
            
            if os.path.exists(template_path):
                # Process template
                try:
                    processed_content = self.process_template_file(template_path, variables)
                    
                    # Determine output file path
                    output_file = template_file.replace('.template', '').replace(f'{context.template_type}/', '')
                    output_path = os.path.join(output_dir, output_file)
                    
                    processed_files[output_path] = processed_content
                    
                except Exception as e:
                    print(f"⚠️  Warning: Failed to process template {template_file}: {e}")
            else:
                print(f"⚠️  Warning: Template file not found: {template_path}")
        
        return processed_files
    
    def validate_all_templates(self, context: TemplateContext) -> Dict[str, List[str]]:
        """
        Validate all templates for a project type
        
        Args:
            context: Template processing context
            
        Returns:
            Dictionary mapping template files to their validation warnings
        """
        variables = self.generate_template_variables(context)
        template_files = self.get_template_dependencies(context.template_type)
        
        validation_results = {}
        
        for template_file in template_files:
            template_path = os.path.join(self.templates_dir, template_file)
            warnings = self.validate_template(template_path, variables)
            if warnings:
                validation_results[template_file] = warnings
        
        return validation_results
    
    def get_required_placeholders(self, template_path: str) -> List[str]:
        """
        Get list of all placeholders required by a template
        
        Args:
            template_path: Path to template file
            
        Returns:
            List of required placeholder names
        """
        if not os.path.exists(template_path):
            return []
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all variable references
        variable_refs = self.variable_pattern.findall(content)
        
        # Find all conditional references
        conditional_refs = re.findall(r'\{\{#(if_[^}]+)\}\}', content)
        
        # Combine and deduplicate
        all_placeholders = set()
        all_placeholders.update(var_ref.strip() for var_ref in variable_refs)
        all_placeholders.update(conditional_refs)
        
        return sorted(list(all_placeholders))


def create_template_context(username: str, project_name: str, template_type: str, 
                          port_assignment: PortAssignment, has_common_project: bool) -> TemplateContext:
    """
    Create a template processing context
    
    Args:
        username: Student's login ID
        project_name: Name of the project being created
        template_type: Type of template (rag, agent, common)
        port_assignment: Student's port assignment
        has_common_project: Whether a common project exists
        
    Returns:
        TemplateContext object
    """
    available_ports = port_assignment.all_ports
    
    return TemplateContext(
        username=username,
        project_name=project_name,
        template_type=template_type,
        port_assignment=port_assignment,
        has_common_project=has_common_project,
        available_ports=available_ports,
        template_variables={}
    )


# Convenience functions for common operations
def process_docker_compose_template(context: TemplateContext, templates_dir: str = "templates") -> str:
    """Process docker-compose.yml template"""
    processor = TemplateProcessor(templates_dir)
    template_path = os.path.join(templates_dir, f"{context.template_type}/docker-compose.yml.template")
    variables = processor.generate_template_variables(context)
    return processor.process_template_file(template_path, variables)


def process_readme_template(context: TemplateContext, templates_dir: str = "templates") -> str:
    """Process README.md template"""
    processor = TemplateProcessor(templates_dir)
    template_path = os.path.join(templates_dir, f"{context.template_type}/README.md.template")
    variables = processor.generate_template_variables(context)
    return processor.process_template_file(template_path, variables)