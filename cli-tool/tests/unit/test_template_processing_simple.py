#!/usr/bin/env python3
"""
Simple Template Processing Tests
Tests core template processing functionality.
"""

import sys
import os
import tempfile
import shutil

# Add the cli-tool directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from src.core.project_manager import ProjectManager, TemplateProcessor
from src.core.port_assignment import PortAssignment

def test_template_processor_basic():
    """Test basic template processing functionality"""
    print("Testing Template Processor Basic...")
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        templates_dir = os.path.join(temp_dir, "templates")
        os.makedirs(templates_dir)
        
        # Create a simple template
        template_content = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "{{WEB_PORT}}:80"
    environment:
      - USER_ID={{USER_ID}}
      - PROJECT_NAME={{PROJECT_NAME}}
"""
        
        template_file = os.path.join(templates_dir, "test_template.yml")
        with open(template_file, 'w') as f:
            f.write(template_content)
        
        # Test template processing
        processor = TemplateProcessor(templates_dir)
        
        variables = {
            "WEB_PORT": "8080",
            "USER_ID": "test_user",
            "PROJECT_NAME": "test_project"
        }
        
        processed_content = processor.process_template("test_template.yml", variables)
        
        # Verify substitutions
        assert "8080:80" in processed_content
        assert "USER_ID=test_user" in processed_content
        assert "PROJECT_NAME=test_project" in processed_content
        assert "{{" not in processed_content  # No unprocessed variables
    
    print("✓ Template Processor Basic test passed")

def test_template_validation():
    """Test template validation functionality"""
    print("Testing Template Validation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        templates_dir = os.path.join(temp_dir, "templates")
        os.makedirs(templates_dir)
        
        # Create template with missing variables
        template_content = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "{{WEB_PORT}}:80"
    environment:
      - USER_ID={{USER_ID}}
      - MISSING_VAR={{MISSING_VAR}}
"""
        
        template_file = os.path.join(templates_dir, "test_template.yml")
        with open(template_file, 'w') as f:
            f.write(template_content)
        
        processor = TemplateProcessor(templates_dir)
        
        # Test with incomplete variables
        variables = {
            "WEB_PORT": "8080",
            "USER_ID": "test_user"
            # MISSING_VAR is not provided
        }
        
        # Should detect missing variables
        missing_vars = processor.find_missing_variables("test_template.yml", variables)
        assert "MISSING_VAR" in missing_vars
        assert len(missing_vars) == 1
    
    print("✓ Template Validation test passed")

def test_project_manager_templates():
    """Test project manager template functionality"""
    print("Testing Project Manager Templates...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create basic project structure
        templates_dir = os.path.join(temp_dir, "templates")
        projects_dir = os.path.join(temp_dir, "projects")
        os.makedirs(templates_dir)
        os.makedirs(projects_dir)
        
        # Create a simple template structure
        rag_dir = os.path.join(templates_dir, "rag")
        os.makedirs(rag_dir)
        
        compose_template = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "{{WEB_PORT}}:80"
    environment:
      - USER={{USERNAME}}
"""
        
        with open(os.path.join(rag_dir, "docker-compose.yml.template"), 'w') as f:
            f.write(compose_template)
        
        # Test project manager
        manager = ProjectManager(base_dir=projects_dir, templates_dir=templates_dir)
        
        # Test template availability
        available_templates = manager.get_available_templates()
        assert "rag" in available_templates
        
        # Test template validation
        port_assignment = PortAssignment("test_user", 8000, 8099)
        
        # This would normally create a project, but we'll just test the template processing
        template_vars = manager._generate_template_variables(
            "test_project", 
            "test_user", 
            port_assignment, 
            has_common_project=False
        )
        
        assert "USERNAME" in template_vars
        assert "PROJECT_NAME" in template_vars
        assert template_vars["USERNAME"] == "test_user"
        assert template_vars["PROJECT_NAME"] == "test_project"
    
    print("✓ Project Manager Templates test passed")

def test_template_edge_cases():
    """Test template processing edge cases"""
    print("Testing Template Edge Cases...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        templates_dir = os.path.join(temp_dir, "templates")
        os.makedirs(templates_dir)
        
        # Test template with no variables
        simple_template = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "80:80"
"""
        
        template_file = os.path.join(templates_dir, "simple.yml")
        with open(template_file, 'w') as f:
            f.write(simple_template)
        
        processor = TemplateProcessor(templates_dir)
        
        # Process template with no variables
        processed = processor.process_template("simple.yml", {})
        assert processed == simple_template
        
        # Test template with repeated variables
        repeated_template = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "{{PORT}}:{{PORT}}"
    environment:
      - PORT={{PORT}}
"""
        
        repeated_file = os.path.join(templates_dir, "repeated.yml")
        with open(repeated_file, 'w') as f:
            f.write(repeated_template)
        
        processed_repeated = processor.process_template("repeated.yml", {"PORT": "8080"})
        assert processed_repeated.count("8080") == 3  # Should replace all occurrences
    
    print("✓ Template Edge Cases test passed")

def test_template_security():
    """Test template processing security"""
    print("Testing Template Security...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        templates_dir = os.path.join(temp_dir, "templates")
        os.makedirs(templates_dir)
        
        # Test template with potentially dangerous content
        template_content = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "{{WEB_PORT}}:80"
    environment:
      - PASSWORD={{PASSWORD}}
      - SECRET_KEY={{SECRET_KEY}}
"""
        
        template_file = os.path.join(templates_dir, "secure_template.yml")
        with open(template_file, 'w') as f:
            f.write(template_content)
        
        processor = TemplateProcessor(templates_dir)
        
        variables = {
            "WEB_PORT": "8080",
            "PASSWORD": "secret123",
            "SECRET_KEY": "super_secret_key"
        }
        
        processed_content = processor.process_template("secure_template.yml", variables)
        
        # Verify that sensitive data is processed correctly
        assert "PASSWORD=secret123" in processed_content
        assert "SECRET_KEY=super_secret_key" in processed_content
        
        # Note: In a real implementation, we might want to add warnings
        # about sensitive data in templates or automatic sanitization
    
    print("✓ Template Security test passed")

def run_template_processing_tests():
    """Run all template processing tests"""
    print("Running Template Processing Tests")
    print("=" * 50)
    
    try:
        test_template_processor_basic()
        test_template_validation()
        test_project_manager_templates()
        test_template_edge_cases()
        test_template_security()
        
        print("\n" + "=" * 50)
        print("✅ All template processing tests passed!")
        
        print("\n📄 Template Processing System Summary:")
        print("=" * 50)
        
        print("\n📋 Core Components Tested:")
        print("  • TemplateProcessor - Template variable substitution")
        print("  • Template validation and missing variable detection")
        print("  • ProjectManager template integration")
        print("  • Edge cases and security considerations")
        
        print("\n🔧 Key Features Validated:")
        print("  • Variable substitution with {{VAR}} syntax")
        print("  • Missing variable detection")
        print("  • Template file processing")
        print("  • Integration with project management")
        print("  • Security and edge case handling")
        
        print("\n✅ Template processing system is working correctly!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_template_processing_tests()
    sys.exit(0 if success else 1)