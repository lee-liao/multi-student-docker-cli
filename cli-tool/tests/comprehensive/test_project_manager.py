#!/usr/bin/env python3
"""
Test script for project management system
"""

import os
import sys
import tempfile
import shutil
import json
from src.core.project_manager import (
    ProjectManager, create_project, list_user_projects, get_project_info
)
from src.core.port_assignment import PortAssignment


def test_project_creation():
    """Test project creation functionality"""
    print("🧪 Testing Project Creation")
    print("=" * 30)
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4100,
        segment2_start=8000,
        segment2_end=8100
    )
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ProjectManager(base_dir=temp_dir, templates_dir="templates")
        
        # Test 1: Create RAG project
        print("\n1. Testing RAG project creation...")
        
        try:
            project_config = manager.create_project(
                project_name="my-rag-project",
                template_type="rag",
                username="Emma",
                port_assignment=emma_assignment,
                has_common_project=False
            )
            
            if project_config and project_config.project_name == "my-rag-project":
                print("✅ RAG project created successfully")
                print(f"   Services: {', '.join(project_config.services)}")
                print(f"   Ports used: {len(project_config.ports_used)}")
                
                # Check if files were created
                project_path = project_config.project_path
                expected_files = ["docker-compose.yml", "README.md", "setup.sh", ".project-config.json"]
                
                for file_name in expected_files:
                    file_path = os.path.join(project_path, file_name)
                    if os.path.exists(file_path):
                        print(f"   ✅ {file_name}")
                    else:
                        print(f"   ❌ {file_name} missing")
                        return False
                        
            else:
                print("❌ RAG project creation failed")
                return False
                
        except Exception as e:
            print(f"❌ RAG project creation failed: {e}")
            return False
        
        # Test 2: Create common project
        print("\n2. Testing common project creation...")
        
        try:
            project_config = manager.create_project(
                project_name="common-infrastructure",
                template_type="common",
                username="Emma",
                port_assignment=emma_assignment,
                has_common_project=False
            )
            
            if (project_config and 
                project_config.template_type == "common" and
                len(project_config.services) >= 5):  # Should have multiple services
                print("✅ Common project created successfully")
                print(f"   Services: {len(project_config.services)} total")
            else:
                print("❌ Common project creation failed")
                return False
                
        except Exception as e:
            print(f"❌ Common project creation failed: {e}")
            return False
        
        # Test 3: Create agent project with common dependency
        print("\n3. Testing agent project with common dependency...")
        
        try:
            project_config = manager.create_project(
                project_name="my-agent-system",
                template_type="agent",
                username="Emma",
                port_assignment=emma_assignment,
                has_common_project=True
            )
            
            if (project_config and 
                project_config.has_common_project == True and
                project_config.template_type == "agent"):
                print("✅ Agent project with common dependency created successfully")
            else:
                print("❌ Agent project creation failed")
                return False
                
        except Exception as e:
            print(f"❌ Agent project creation failed: {e}")
            return False
    
    print("\n🎉 All project creation tests passed!")
    return True


def test_project_listing():
    """Test project listing functionality"""
    print("\n🧪 Testing Project Listing")
    print("=" * 30)
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4100,
        segment2_start=8000,
        segment2_end=8100
    )
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ProjectManager(base_dir=temp_dir, templates_dir="templates")
        
        # Create multiple projects
        projects_to_create = [
            ("project1", "rag", "Emma"),
            ("project2", "agent", "Emma"),
            ("project3", "common", "Bob")
        ]
        
        created_projects = []
        
        for project_name, template_type, username in projects_to_create:
            try:
                config = manager.create_project(
                    project_name=project_name,
                    template_type=template_type,
                    username=username,
                    port_assignment=emma_assignment,
                    has_common_project=False
                )
                created_projects.append(config)
                
            except Exception as e:
                print(f"⚠️  Failed to create {project_name}: {e}")
        
        # Test 1: List all projects
        print("\n1. Testing list all projects...")
        
        try:
            all_projects = manager.list_projects()
            
            if len(all_projects) == len(created_projects):
                print(f"✅ Listed {len(all_projects)} projects correctly")
            else:
                print(f"❌ Expected {len(created_projects)} projects, got {len(all_projects)}")
                return False
                
        except Exception as e:
            print(f"❌ List all projects failed: {e}")
            return False
        
        # Test 2: List projects by user
        print("\n2. Testing list projects by user...")
        
        try:
            emma_projects = manager.list_projects(username="Emma")
            bob_projects = manager.list_projects(username="Bob")
            
            if len(emma_projects) == 2 and len(bob_projects) == 1:
                print("✅ User-filtered project listing works correctly")
                print(f"   Emma: {len(emma_projects)} projects")
                print(f"   Bob: {len(bob_projects)} projects")
            else:
                print(f"❌ User filtering failed: Emma={len(emma_projects)}, Bob={len(bob_projects)}")
                return False
                
        except Exception as e:
            print(f"❌ User-filtered listing failed: {e}")
            return False
        
        # Test 3: Project status
        print("\n3. Testing project status...")
        
        try:
            status = manager.get_project_status("project1")
            
            if ("project_config" in status and 
                "service_info" in status and
                status["project_config"]["project_name"] == "project1"):
                print("✅ Project status retrieval works correctly")
            else:
                print("❌ Project status retrieval failed")
                return False
                
        except Exception as e:
            print(f"❌ Project status failed: {e}")
            return False
    
    print("\n🎉 All project listing tests passed!")
    return True


def test_project_validation():
    """Test project validation functionality"""
    print("\n🧪 Testing Project Validation")
    print("=" * 32)
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4100,
        segment2_start=8000,
        segment2_end=8100
    )
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ProjectManager(base_dir=temp_dir, templates_dir="templates")
        
        # Test 1: Validate valid project
        print("\n1. Testing validation of valid project...")
        
        try:
            # Create a valid project
            project_config = manager.create_project(
                project_name="valid-project",
                template_type="rag",
                username="Emma",
                port_assignment=emma_assignment,
                has_common_project=False
            )
            
            # Validate it
            issues = manager.validate_project("valid-project")
            
            if len(issues) == 0:
                print("✅ Valid project passes validation")
            else:
                print(f"⚠️  Valid project has {len(issues)} issues:")
                for issue in issues[:3]:
                    print(f"   - {issue}")
                
        except Exception as e:
            print(f"❌ Valid project validation failed: {e}")
            return False
        
        # Test 2: Validate non-existent project
        print("\n2. Testing validation of non-existent project...")
        
        try:
            issues = manager.validate_project("non-existent-project")
            
            if issues and "not found" in issues[0]:
                print("✅ Non-existent project correctly identified")
            else:
                print("❌ Non-existent project validation failed")
                return False
                
        except Exception as e:
            print(f"❌ Non-existent project validation failed: {e}")
            return False
        
        # Test 3: Validate project with missing files
        print("\n3. Testing validation of project with missing files...")
        
        try:
            # Create a project and then remove a required file
            project_config = manager.create_project(
                project_name="incomplete-project",
                template_type="rag",
                username="Emma",
                port_assignment=emma_assignment,
                has_common_project=False
            )
            
            # Remove README.md
            readme_path = os.path.join(project_config.project_path, "README.md")
            if os.path.exists(readme_path):
                os.remove(readme_path)
            
            # Validate
            issues = manager.validate_project("incomplete-project")
            
            if issues and any("README.md" in issue for issue in issues):
                print("✅ Missing file correctly detected")
            else:
                print("❌ Missing file not detected")
                return False
                
        except Exception as e:
            print(f"❌ Incomplete project validation failed: {e}")
            return False
    
    print("\n🎉 All project validation tests passed!")
    return True


def test_convenience_functions():
    """Test convenience functions"""
    print("\n🧪 Testing Convenience Functions")
    print("=" * 35)
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4100,
        segment2_start=8000,
        segment2_end=8100
    )
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test 1: create_project function
        print("\n1. Testing create_project convenience function...")
        
        try:
            project_config = create_project(
                project_name="convenience-test",
                template_type="rag",
                username="Emma",
                port_assignment=emma_assignment,
                has_common_project=False,
                base_dir=temp_dir
            )
            
            if project_config and project_config.project_name == "convenience-test":
                print("✅ create_project convenience function works")
            else:
                print("❌ create_project convenience function failed")
                return False
                
        except Exception as e:
            print(f"❌ create_project convenience function failed: {e}")
            return False
        
        # Test 2: list_user_projects function
        print("\n2. Testing list_user_projects convenience function...")
        
        try:
            projects = list_user_projects("Emma", base_dir=temp_dir)
            
            if len(projects) >= 1:
                print(f"✅ list_user_projects works ({len(projects)} projects found)")
            else:
                print("❌ list_user_projects failed")
                return False
                
        except Exception as e:
            print(f"❌ list_user_projects failed: {e}")
            return False
        
        # Test 3: get_project_info function
        print("\n3. Testing get_project_info convenience function...")
        
        try:
            info = get_project_info("convenience-test", base_dir=temp_dir)
            
            if ("project_config" in info and 
                info["project_config"]["project_name"] == "convenience-test"):
                print("✅ get_project_info works correctly")
            else:
                print("❌ get_project_info failed")
                return False
                
        except Exception as e:
            print(f"❌ get_project_info failed: {e}")
            return False
    
    print("\n🎉 All convenience function tests passed!")
    return True


def test_project_config_persistence():
    """Test project configuration persistence"""
    print("\n🧪 Testing Project Config Persistence")
    print("=" * 40)
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4100,
        segment2_start=8000,
        segment2_end=8100
    )
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ProjectManager(base_dir=temp_dir, templates_dir="templates")
        
        # Test 1: Create project and check config file
        print("\n1. Testing config file creation...")
        
        try:
            project_config = manager.create_project(
                project_name="config-test",
                template_type="rag",
                username="Emma",
                port_assignment=emma_assignment,
                has_common_project=False
            )
            
            # Check if config file exists
            config_file = os.path.join(project_config.project_path, ".project-config.json")
            
            if os.path.exists(config_file):
                print("✅ Project config file created")
                
                # Check config file content
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                if (config_data["project_name"] == "config-test" and
                    config_data["username"] == "Emma"):
                    print("✅ Config file contains correct data")
                else:
                    print("❌ Config file data incorrect")
                    return False
                    
            else:
                print("❌ Project config file not created")
                return False
                
        except Exception as e:
            print(f"❌ Config file creation failed: {e}")
            return False
        
        # Test 2: Load config from file
        print("\n2. Testing config file loading...")
        
        try:
            loaded_config = manager.load_project_config(project_config.project_path)
            
            if (loaded_config and 
                loaded_config.project_name == project_config.project_name and
                loaded_config.username == project_config.username):
                print("✅ Config file loaded correctly")
            else:
                print("❌ Config file loading failed")
                return False
                
        except Exception as e:
            print(f"❌ Config file loading failed: {e}")
            return False
    
    print("\n🎉 All config persistence tests passed!")
    return True


if __name__ == '__main__':
    # Change to project root directory (parent of cli-tool)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    success = True
    
    # Run tests
    success &= test_project_creation()
    success &= test_project_listing()
    success &= test_project_validation()
    success &= test_convenience_functions()
    success &= test_project_config_persistence()
    
    if success:
        print("\n🎉 All project management system tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some project management tests failed!")
        sys.exit(1)