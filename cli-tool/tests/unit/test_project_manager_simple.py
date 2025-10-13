#!/usr/bin/env python3
"""
Simple Project Manager Tests
Tests core project management functionality.
"""

import sys
import os
import tempfile
import shutil

# Add the cli-tool directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from src.core.project_manager import ProjectManager, ProjectConfig
from src.core.port_assignment import PortAssignment

def test_project_manager_initialization():
    """Test project manager initialization"""
    print("Testing Project Manager Initialization...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        projects_dir = os.path.join(temp_dir, "projects")
        templates_dir = os.path.join(temp_dir, "templates")
        
        # Create directories
        os.makedirs(projects_dir)
        os.makedirs(templates_dir)
        
        # Initialize project manager
        manager = ProjectManager(base_dir=projects_dir, templates_dir=templates_dir)
        
        assert manager.base_dir == projects_dir
        assert manager.templates_dir == templates_dir
        assert os.path.exists(projects_dir)
    
    print("✓ Project Manager Initialization test passed")

def test_project_existence_check():
    """Test project existence checking"""
    print("Testing Project Existence Check...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        projects_dir = os.path.join(temp_dir, "projects")
        os.makedirs(projects_dir)
        
        manager = ProjectManager(base_dir=projects_dir)
        
        # Test non-existent project
        assert not manager.project_exists("nonexistent_project")
        
        # Create a project directory
        test_project_dir = os.path.join(projects_dir, "test_project")
        os.makedirs(test_project_dir)
        
        # Test existing project
        assert manager.project_exists("test_project")
    
    print("✓ Project Existence Check test passed")

def test_project_listing():
    """Test project listing functionality"""
    print("Testing Project Listing...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        projects_dir = os.path.join(temp_dir, "projects")
        os.makedirs(projects_dir)
        
        manager = ProjectManager(base_dir=projects_dir)
        
        # Test empty directory
        projects = manager.list_projects()
        assert len(projects) == 0
        
        # Create some test projects
        for project_name in ["project1", "project2", "project3"]:
            project_dir = os.path.join(projects_dir, project_name)
            os.makedirs(project_dir)
            
            # Create docker-compose.yml to make it a valid project
            compose_file = os.path.join(project_dir, "docker-compose.yml")
            with open(compose_file, 'w') as f:
                f.write("version: '3.8'\nservices:\n  web:\n    image: nginx")
        
        # Test project listing
        projects = manager.list_projects()
        assert len(projects) == 3
        
        project_names = [p.name for p in projects]
        assert "project1" in project_names
        assert "project2" in project_names
        assert "project3" in project_names
    
    print("✓ Project Listing test passed")

def test_template_availability():
    """Test template availability checking"""
    print("Testing Template Availability...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        templates_dir = os.path.join(temp_dir, "templates")
        os.makedirs(templates_dir)
        
        manager = ProjectManager(templates_dir=templates_dir)
        
        # Test empty templates directory
        templates = manager.get_available_templates()
        assert len(templates) == 0
        
        # Create some template directories
        for template_name in ["rag", "agent", "common"]:
            template_dir = os.path.join(templates_dir, template_name)
            os.makedirs(template_dir)
            
            # Create a template file
            template_file = os.path.join(template_dir, "docker-compose.yml.template")
            with open(template_file, 'w') as f:
                f.write("version: '3.8'\nservices:\n  web:\n    image: nginx")
        
        # Test template availability
        templates = manager.get_available_templates()
        assert len(templates) == 3
        assert "rag" in templates
        assert "agent" in templates
        assert "common" in templates
    
    print("✓ Template Availability test passed")

def test_project_config():
    """Test project configuration handling"""
    print("Testing Project Configuration...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test ProjectConfig creation
        config = ProjectConfig(
            project_name="test_project",
            template_type="rag",
            username="test_user",
            project_path=os.path.join(temp_dir, "test_project"),
            port_assignments={"web": 8080, "api": 8081},
            has_common_project=True
        )
        
        assert config.project_name == "test_project"
        assert config.template_type == "rag"
        assert config.username == "test_user"
        assert config.port_assignments["web"] == 8080
        assert config.has_common_project == True
        
        # Test config serialization
        config_dict = config.to_dict()
        assert config_dict["project_name"] == "test_project"
        assert config_dict["template_type"] == "rag"
        assert config_dict["port_assignments"]["web"] == 8080
    
    print("✓ Project Configuration test passed")

def test_template_variable_generation():
    """Test template variable generation"""
    print("Testing Template Variable Generation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ProjectManager(base_dir=temp_dir)
        
        # Create port assignment
        port_assignment = PortAssignment("test_user", 8000, 8099)
        
        # Generate template variables
        variables = manager._generate_template_variables(
            project_name="test_project",
            username="test_user",
            port_assignment=port_assignment,
            has_common_project=False
        )
        
        # Verify required variables
        assert "PROJECT_NAME" in variables
        assert "USERNAME" in variables
        assert "USER_ID" in variables
        assert variables["PROJECT_NAME"] == "test_project"
        assert variables["USERNAME"] == "test_user"
        assert variables["USER_ID"] == "test_user"
        
        # Verify port variables
        assert "WEB_PORT" in variables
        assert "API_PORT" in variables
        assert isinstance(variables["WEB_PORT"], int)
        assert isinstance(variables["API_PORT"], int)
        
        # Verify ports are in range
        assert 8000 <= variables["WEB_PORT"] <= 8099
        assert 8000 <= variables["API_PORT"] <= 8099
    
    print("✓ Template Variable Generation test passed")

def test_project_validation():
    """Test project validation functionality"""
    print("Testing Project Validation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        projects_dir = os.path.join(temp_dir, "projects")
        os.makedirs(projects_dir)
        
        manager = ProjectManager(base_dir=projects_dir)
        
        # Create a valid project
        valid_project_dir = os.path.join(projects_dir, "valid_project")
        os.makedirs(valid_project_dir)
        
        compose_content = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "8080:80"
"""
        
        compose_file = os.path.join(valid_project_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        # Test project validation
        is_valid = manager.validate_project("valid_project")
        assert is_valid
        
        # Test invalid project (no docker-compose.yml)
        invalid_project_dir = os.path.join(projects_dir, "invalid_project")
        os.makedirs(invalid_project_dir)
        
        is_invalid = manager.validate_project("invalid_project")
        assert not is_invalid
    
    print("✓ Project Validation test passed")

def run_project_manager_tests():
    """Run all project manager tests"""
    print("Running Project Manager Tests")
    print("=" * 50)
    
    try:
        test_project_manager_initialization()
        test_project_existence_check()
        test_project_listing()
        test_template_availability()
        test_project_config()
        test_template_variable_generation()
        test_project_validation()
        
        print("\n" + "=" * 50)
        print("✅ All project manager tests passed!")
        
        print("\n📁 Project Manager System Summary:")
        print("=" * 50)
        
        print("\n📋 Core Components Tested:")
        print("  • ProjectManager - Main project management class")
        print("  • ProjectConfig - Project configuration handling")
        print("  • Project existence and validation")
        print("  • Template availability and processing")
        print("  • Variable generation for templates")
        
        print("\n🔧 Key Features Validated:")
        print("  • Project directory management")
        print("  • Template discovery and validation")
        print("  • Project listing and filtering")
        print("  • Configuration serialization")
        print("  • Template variable generation")
        print("  • Project validation")
        
        print("\n✅ Project manager system is working correctly!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_project_manager_tests()
    sys.exit(0 if success else 1)