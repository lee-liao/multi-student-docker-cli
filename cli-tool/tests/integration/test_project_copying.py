#!/usr/bin/env python3
"""
Test script for project copying system
"""

import os
import sys
import tempfile
import shutil
from src.core.project_manager import ProjectManager
from src.core.port_assignment import PortAssignment


def test_project_copying():
    """Test project copying functionality"""
    print("🧪 Testing Project Copying")
    print("=" * 30)
    
    # Create test port assignments
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4100,
        segment2_start=8000,
        segment2_end=8100
    )
    
    bob_assignment = PortAssignment(
        login_id="Bob",
        segment1_start=5000,
        segment1_end=5100,
        segment2_start=9000,
        segment2_end=9100
    )
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ProjectManager(base_dir=temp_dir, templates_dir="templates")
        
        # Test 1: Create source project
        print("\n1. Creating source project for copying...")
        
        try:
            source_config = manager.create_project(
                project_name="source-rag",
                template_type="rag",
                username="Emma",
                port_assignment=emma_assignment,
                has_common_project=False
            )
            
            print("✅ Source project created successfully")
            
        except Exception as e:
            print(f"❌ Failed to create source project: {e}")
            return False
        
        # Test 2: Copy project with different user
        print("\n2. Testing project copy with different user...")
        
        try:
            copied_config = manager.copy_project(
                source_project="source-rag",
                destination_project="copied-rag",
                username="Bob",
                port_assignment=bob_assignment
            )
            
            if (copied_config and 
                copied_config.project_name == "copied-rag" and
                copied_config.username == "Bob"):
                print("✅ Project copied successfully")
                print(f"   Source ports: {source_config.ports_used}")
                print(f"   Copied ports: {copied_config.ports_used}")
                
                # Verify files were updated
                copied_compose_path = os.path.join(copied_config.project_path, "docker-compose.yml")
                if os.path.exists(copied_compose_path):
                    with open(copied_compose_path, 'r') as f:
                        compose_content = f.read()
                    
                    # Check that usernames were updated
                    if "Bob-" in compose_content and "Emma-" not in compose_content:
                        print("✅ Container names updated correctly")
                    else:
                        print("❌ Container names not updated properly")
                        return False
                    
                    # Check that ports were updated
                    if str(copied_config.ports_used[0]) in compose_content:
                        print("✅ Ports updated correctly")
                    else:
                        print("❌ Ports not updated properly")
                        return False
                        
            else:
                print("❌ Project copy failed")
                return False
                
        except Exception as e:
            print(f"❌ Project copy failed: {e}")
            return False
        
        # Test 3: Copy validation
        print("\n3. Testing copy validation...")
        
        try:
            # Test copying to existing destination
            issues = manager.validate_copy_operation(
                source_project="source-rag",
                destination_project="copied-rag",  # Already exists
                port_assignment=bob_assignment
            )
            
            if issues and any("already exists" in issue for issue in issues):
                print("✅ Correctly detected existing destination")
            else:
                print("❌ Failed to detect existing destination")
                return False
            
            # Test copying non-existent source
            issues = manager.validate_copy_operation(
                source_project="non-existent",
                destination_project="new-project",
                port_assignment=bob_assignment
            )
            
            if issues and any("does not exist" in issue for issue in issues):
                print("✅ Correctly detected non-existent source")
            else:
                print("❌ Failed to detect non-existent source")
                return False
                
        except Exception as e:
            print(f"❌ Copy validation failed: {e}")
            return False
        
        # Test 4: Copy preview
        print("\n4. Testing copy preview...")
        
        try:
            preview = manager.get_copy_preview(
                source_project="source-rag",
                destination_project="preview-test",
                username="Bob",
                port_assignment=bob_assignment
            )
            
            if (preview and 
                "source_config" in preview and
                "target_config" in preview and
                "port_mapping" in preview["target_config"]):
                print("✅ Copy preview generated successfully")
                print(f"   Files to update: {len(preview['files_to_update'])}")
                print(f"   Port mappings: {len(preview['target_config']['port_mapping'])}")
            else:
                print("❌ Copy preview generation failed")
                return False
                
        except Exception as e:
            print(f"❌ Copy preview failed: {e}")
            return False
    
    print("\n🎉 All project copying tests passed!")
    return True


def test_file_content_updates():
    """Test file content update functionality"""
    print("\n🧪 Testing File Content Updates")
    print("=" * 35)
    
    manager = ProjectManager()
    
    # Test 1: Port replacement
    print("\n1. Testing port replacement...")
    
    test_content = '''
    ports:
      - "4001:8000"
      - "4002:3000"
    environment:
      - API_URL=http://localhost:4001
      - FRONTEND_URL=http://localhost:4002
    '''
    
    port_mapping = {4001: 5001, 4002: 5002}
    
    try:
        updated_content = manager._update_file_content(
            test_content, "old-project", "new-project",
            "Bob", "Emma", port_mapping
        )
        
        if ("5001:8000" in updated_content and 
            "5002:3000" in updated_content and
            "localhost:5001" in updated_content and
            "localhost:5002" in updated_content):
            print("✅ Port replacement works correctly")
        else:
            print("❌ Port replacement failed")
            return False
            
    except Exception as e:
        print(f"❌ Port replacement failed: {e}")
        return False
    
    # Test 2: Username replacement
    print("\n2. Testing username replacement...")
    
    test_content = '''
    container_name: Emma-backend
    networks:
      - Emma-network
    volumes:
      - Emma-postgres-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=Emma_user
      - POSTGRES_PASSWORD=Emma_password_2024
    '''
    
    try:
        updated_content = manager._update_file_content(
            test_content, "old-project", "new-project",
            "Bob", "Emma", {}
        )
        
        if ("Bob-backend" in updated_content and 
            "Bob-network" in updated_content and
            "Bob-postgres-data" in updated_content and
            "Bob_user" in updated_content and
            "Bob_password" in updated_content):
            print("✅ Username replacement works correctly")
        else:
            print("❌ Username replacement failed")
            print(f"Updated content: {updated_content}")
            return False
            
    except Exception as e:
        print(f"❌ Username replacement failed: {e}")
        return False
    
    # Test 3: Project name replacement
    print("\n3. Testing project name replacement...")
    
    test_content = '''
    # My Old Project
    This is the old-project documentation.
    Navigate to old-project directory.
    '''
    
    try:
        updated_content = manager._update_file_content(
            test_content, "old-project", "new-project",
            "Bob", "Emma", {}
        )
        
        if ("new-project" in updated_content and "old-project" not in updated_content):
            print("✅ Project name replacement works correctly")
        else:
            print("❌ Project name replacement failed")
            return False
            
    except Exception as e:
        print(f"❌ Project name replacement failed: {e}")
        return False
    
    print("\n🎉 All file content update tests passed!")
    return True


def test_port_assignment_logic():
    """Test port assignment logic for copying"""
    print("\n🧪 Testing Port Assignment Logic")
    print("=" * 38)
    
    manager = ProjectManager()
    
    # Test 1: Port assignment from available pool
    print("\n1. Testing port assignment from available pool...")
    
    port_assignment = PortAssignment(
        login_id="TestUser",
        segment1_start=6000,
        segment1_end=6010,
        segment2_start=None,
        segment2_end=None
    )
    
    try:
        # Request 5 ports
        assigned_ports = manager._get_ports_used_from_assignment(port_assignment, 5)
        
        if (len(assigned_ports) == 5 and 
            assigned_ports == [6000, 6001, 6002, 6003, 6004]):
            print("✅ Port assignment from pool works correctly")
        else:
            print(f"❌ Port assignment failed: got {assigned_ports}")
            return False
            
    except Exception as e:
        print(f"❌ Port assignment failed: {e}")
        return False
    
    # Test 2: Port assignment with insufficient ports
    print("\n2. Testing port assignment with insufficient ports...")
    
    try:
        # Request more ports than available
        assigned_ports = manager._get_ports_used_from_assignment(port_assignment, 20)
        
        if len(assigned_ports) == 11:  # Should get all available ports
            print("✅ Correctly limited to available ports")
        else:
            print(f"❌ Port limiting failed: got {len(assigned_ports)} ports")
            return False
            
    except Exception as e:
        print(f"❌ Port assignment with insufficient ports failed: {e}")
        return False
    
    print("\n🎉 All port assignment logic tests passed!")
    return True


def test_copy_validation_edge_cases():
    """Test edge cases in copy validation"""
    print("\n🧪 Testing Copy Validation Edge Cases")
    print("=" * 42)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ProjectManager(base_dir=temp_dir, templates_dir="templates")
        
        # Create a test port assignment with limited ports
        limited_assignment = PortAssignment(
            login_id="TestUser",
            segment1_start=7000,
            segment1_end=7002,  # Only 3 ports
            segment2_start=None,
            segment2_end=None
        )
        
        # Test 1: Invalid project names
        print("\n1. Testing invalid project names...")
        
        try:
            issues = manager.validate_copy_operation(
                source_project="valid-source",
                destination_project="invalid name!",  # Invalid characters
                port_assignment=limited_assignment
            )
            
            if issues and any("alphanumeric" in issue for issue in issues):
                print("✅ Correctly detected invalid project name")
            else:
                print(f"❌ Failed to detect invalid project name. Issues: {issues}")
                return False
                
        except Exception as e:
            print(f"❌ Invalid project name validation failed: {e}")
            return False
        
        # Test 2: Create source project with many ports, then test insufficient ports
        print("\n2. Testing insufficient port allocation...")
        
        try:
            # Create source project with many services (uses many ports)
            emma_assignment = PortAssignment(
                login_id="Emma",
                segment1_start=4000,
                segment1_end=4100,
                segment2_start=8000,
                segment2_end=8100
            )
            
            source_config = manager.create_project(
                project_name="large-project",
                template_type="rag",
                username="Emma",
                port_assignment=emma_assignment,
                has_common_project=False
            )
            
            # Try to copy to user with insufficient ports
            issues = manager.validate_copy_operation(
                source_project="large-project",
                destination_project="small-copy",
                port_assignment=limited_assignment
            )
            
            if issues and any("Insufficient ports" in issue for issue in issues):
                print("✅ Correctly detected insufficient ports")
            else:
                print("❌ Failed to detect insufficient ports")
                return False
                
        except Exception as e:
            print(f"❌ Insufficient ports validation failed: {e}")
            return False
    
    print("\n🎉 All copy validation edge case tests passed!")
    return True


if __name__ == '__main__':
    # Change to project root directory (parent of cli-tool)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    success = True
    
    # Run tests
    success &= test_project_copying()
    success &= test_file_content_updates()
    success &= test_port_assignment_logic()
    success &= test_copy_validation_edge_cases()
    
    if success:
        print("\n🎉 All project copying system tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some project copying tests failed!")
        sys.exit(1)