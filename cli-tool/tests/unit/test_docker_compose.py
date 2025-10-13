#!/usr/bin/env python3
"""
Test script for Docker Compose template system
"""

import os
import sys
import tempfile
import yaml
from src.core.docker_compose_manager import (
    DockerComposeManager, create_docker_compose_config,
    generate_common_docker_compose, generate_rag_docker_compose
)
from src.core.port_assignment import PortAssignment


def test_docker_compose_generation():
    """Test Docker Compose file generation"""
    print("🧪 Testing Docker Compose Generation")
    print("=" * 40)
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4100,
        segment2_start=8000,
        segment2_end=8100
    )
    
    manager = DockerComposeManager("templates")
    
    # Test 1: Generate common project Docker Compose
    print("\n1. Testing common project Docker Compose generation...")
    
    try:
        config = create_docker_compose_config(
            username="Emma",
            project_name="common",
            template_type="common",
            port_assignment=emma_assignment,
            output_dir="test_output",
            has_common_project=False
        )
        
        compose_content = manager.generate_docker_compose(config)
        
        # Check that content is generated
        if compose_content and "version:" in compose_content:
            print("✅ Common Docker Compose generated successfully")
            
            # Check for student-specific naming
            if "Emma-postgres" in compose_content and "Emma-network" in compose_content:
                print("✅ Student-specific naming applied correctly")
            else:
                print("❌ Student-specific naming not applied")
                return False
                
        else:
            print("❌ Common Docker Compose generation failed")
            return False
            
    except Exception as e:
        print(f"❌ Common Docker Compose generation failed: {e}")
        return False
    
    # Test 2: Generate RAG project Docker Compose (standalone)
    print("\n2. Testing RAG project Docker Compose (standalone mode)...")
    
    try:
        config = create_docker_compose_config(
            username="Emma",
            project_name="rag",
            template_type="rag",
            port_assignment=emma_assignment,
            output_dir="test_output",
            has_common_project=False
        )
        
        compose_content = manager.generate_docker_compose(config)
        
        # Check for standalone features
        if ("Emma-rag-postgres" in compose_content and 
            "Emma-rag-network" in compose_content):
            print("✅ RAG standalone Docker Compose generated correctly")
        else:
            print("❌ RAG standalone Docker Compose missing expected content")
            return False
            
    except Exception as e:
        print(f"❌ RAG standalone Docker Compose generation failed: {e}")
        return False
    
    # Test 3: Generate RAG project Docker Compose (shared mode)
    print("\n3. Testing RAG project Docker Compose (shared mode)...")
    
    try:
        config = create_docker_compose_config(
            username="Emma",
            project_name="rag",
            template_type="rag",
            port_assignment=emma_assignment,
            output_dir="test_output",
            has_common_project=True
        )
        
        compose_content = manager.generate_docker_compose(config)
        
        # Check for shared mode features
        if ("external: true" in compose_content and 
            "Emma-rag-backend" in compose_content):
            print("✅ RAG shared Docker Compose generated correctly")
        else:
            print("❌ RAG shared Docker Compose missing expected content")
            return False
            
    except Exception as e:
        print(f"❌ RAG shared Docker Compose generation failed: {e}")
        return False
    
    print("\n🎉 All Docker Compose generation tests passed!")
    return True


def test_docker_compose_validation():
    """Test Docker Compose validation functionality"""
    print("\n🧪 Testing Docker Compose Validation")
    print("=" * 40)
    
    manager = DockerComposeManager("templates")
    
    # Test 1: Valid Docker Compose
    print("\n1. Testing valid Docker Compose validation...")
    
    valid_compose = """
version: '3.8'
services:
  test-service:
    image: nginx
    container_name: Emma-test-service
    ports:
      - "4001:80"
    networks:
      - Emma-network
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost"]
      interval: 30s
      timeout: 10s
      retries: 3
networks:
  Emma-network:
    name: Emma-network
    driver: bridge
"""
    
    try:
        warnings = manager.validate_docker_compose(valid_compose)
        
        if not warnings:
            print("✅ Valid Docker Compose passed validation")
        else:
            print(f"⚠️  Valid Docker Compose has {len(warnings)} warnings:")
            for warning in warnings[:3]:
                print(f"  - {warning}")
            
    except Exception as e:
        print(f"❌ Valid Docker Compose validation failed: {e}")
        return False
    
    # Test 2: Invalid Docker Compose
    print("\n2. Testing invalid Docker Compose validation...")
    
    invalid_compose = """
version: '3.8'
services:
  bad-service:
    image: nginx
    # Missing container_name, networks, resource limits
    ports:
      - "4001:80"
"""
    
    try:
        warnings = manager.validate_docker_compose(invalid_compose)
        
        if warnings:
            print(f"✅ Invalid Docker Compose correctly detected {len(warnings)} issues")
            print(f"   Sample issues: {warnings[0] if warnings else 'None'}")
        else:
            print("❌ Invalid Docker Compose should have validation issues")
            return False
            
    except Exception as e:
        print(f"❌ Invalid Docker Compose validation failed: {e}")
        return False
    
    print("\n🎉 All Docker Compose validation tests passed!")
    return True


def test_port_conflict_detection():
    """Test port conflict detection"""
    print("\n🧪 Testing Port Conflict Detection")
    print("=" * 40)
    
    manager = DockerComposeManager("templates")
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4010,  # Small range for testing
        segment2_start=None,
        segment2_end=None
    )
    
    # Test 1: Valid port usage
    print("\n1. Testing valid port usage...")
    
    valid_ports_compose = """
version: '3.8'
services:
  service1:
    image: nginx
    ports:
      - "4001:80"
  service2:
    image: redis
    ports:
      - "4002:6379"
"""
    
    try:
        warnings = manager.check_port_conflicts(valid_ports_compose, emma_assignment)
        
        if not warnings:
            print("✅ Valid port usage passed conflict detection")
        else:
            print(f"⚠️  Valid port usage has {len(warnings)} warnings")
            
    except Exception as e:
        print(f"❌ Valid port conflict detection failed: {e}")
        return False
    
    # Test 2: Port conflicts
    print("\n2. Testing port conflict detection...")
    
    conflict_compose = """
version: '3.8'
services:
  service1:
    image: nginx
    ports:
      - "5000:80"  # Outside allocated range
  service2:
    image: redis
    ports:
      - "4001:6379"
  service3:
    image: postgres
    ports:
      - "4001:5432"  # Duplicate port
"""
    
    try:
        warnings = manager.check_port_conflicts(conflict_compose, emma_assignment)
        
        if warnings:
            print(f"✅ Port conflicts correctly detected {len(warnings)} issues")
            print(f"   Sample issues: {warnings[0] if warnings else 'None'}")
        else:
            print("❌ Port conflicts should have been detected")
            return False
            
    except Exception as e:
        print(f"❌ Port conflict detection failed: {e}")
        return False
    
    print("\n🎉 All port conflict detection tests passed!")
    return True


def test_service_info_extraction():
    """Test service information extraction"""
    print("\n🧪 Testing Service Info Extraction")
    print("=" * 40)
    
    manager = DockerComposeManager("templates")
    
    # Test with sample Docker Compose
    sample_compose = """
version: '3.8'
services:
  postgres:
    image: postgres:13
    container_name: Emma-postgres
    ports:
      - "4001:5432"
    networks:
      - Emma-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]
    deploy:
      resources:
        limits:
          memory: 512M
  backend:
    build: ./backend
    container_name: Emma-backend
    ports:
      - "4002:8000"
    networks:
      - Emma-network
networks:
  Emma-network:
    name: Emma-network
volumes:
  postgres_data:
    name: Emma-postgres-data
"""
    
    try:
        service_info = manager.get_service_info(sample_compose)
        
        # Check extracted information
        if (len(service_info["services"]) == 2 and
            len(service_info["networks"]) == 1 and
            len(service_info["volumes"]) == 1 and
            len(service_info["port_mappings"]) == 2):
            print("✅ Service information extracted correctly")
            print(f"   Services: {len(service_info['services'])}")
            print(f"   Networks: {len(service_info['networks'])}")
            print(f"   Volumes: {len(service_info['volumes'])}")
            print(f"   Port mappings: {len(service_info['port_mappings'])}")
        else:
            print("❌ Service information extraction incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Service info extraction failed: {e}")
        return False
    
    print("\n🎉 All service info extraction tests passed!")
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
    
    # Test 1: Generate common Docker Compose
    print("\n1. Testing generate_common_docker_compose...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            output_path = generate_common_docker_compose(
                username="Emma",
                port_assignment=emma_assignment,
                output_dir=temp_dir
            )
            
            if os.path.exists(output_path):
                print("✅ Common Docker Compose file created successfully")
                
                # Check file content
                with open(output_path, 'r') as f:
                    content = f.read()
                    if "Emma-postgres" in content and "Emma-network" in content:
                        print("✅ Common Docker Compose content is correct")
                    else:
                        print("❌ Common Docker Compose content is incorrect")
                        return False
            else:
                print("❌ Common Docker Compose file not created")
                return False
                
        except Exception as e:
            print(f"❌ generate_common_docker_compose failed: {e}")
            return False
    
    # Test 2: Generate RAG Docker Compose
    print("\n2. Testing generate_rag_docker_compose...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            output_path = generate_rag_docker_compose(
                username="Emma",
                port_assignment=emma_assignment,
                output_dir=temp_dir,
                has_common_project=False
            )
            
            if os.path.exists(output_path):
                print("✅ RAG Docker Compose file created successfully")
                
                # Check file content
                with open(output_path, 'r') as f:
                    content = f.read()
                    if "Emma-rag-backend" in content:
                        print("✅ RAG Docker Compose content is correct")
                    else:
                        print("❌ RAG Docker Compose content is incorrect")
                        return False
            else:
                print("❌ RAG Docker Compose file not created")
                return False
                
        except Exception as e:
            print(f"❌ generate_rag_docker_compose failed: {e}")
            return False
    
    print("\n🎉 All convenience function tests passed!")
    return True


if __name__ == '__main__':
    # Change to project root directory (parent of cli-tool)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    success = True
    
    # Run tests
    success &= test_docker_compose_generation()
    success &= test_docker_compose_validation()
    success &= test_port_conflict_detection()
    success &= test_service_info_extraction()
    success &= test_convenience_functions()
    
    if success:
        print("\n🎉 All Docker Compose template system tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some Docker Compose tests failed!")
        sys.exit(1)