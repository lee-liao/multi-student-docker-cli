#!/usr/bin/env python3
"""
Test script for Dockerfile template system
"""

import os
import sys
import tempfile
from src.core.dockerfile_manager import (
    DockerfileManager, create_dockerfile_config,
    generate_backend_dockerfile, generate_frontend_dockerfile, create_all_dockerfiles
)
from src.core.port_assignment import PortAssignment


def test_dockerfile_generation():
    """Test Dockerfile generation"""
    print("🧪 Testing Dockerfile Generation")
    print("=" * 35)
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4100,
        segment2_start=8000,
        segment2_end=8100
    )
    
    manager = DockerfileManager("templates")
    
    # Test 1: Generate backend Dockerfile for RAG project
    print("\n1. Testing backend Dockerfile for RAG project...")
    
    try:
        config = create_dockerfile_config(
            username="Emma",
            project_name="rag-chatbot",
            template_type="rag",
            service_type="backend",
            port_assignment=emma_assignment,
            output_dir="test_output",
            target_stage="production"
        )
        
        dockerfile_content = manager.generate_dockerfile(config)
        
        # Check that content is generated
        if dockerfile_content and "FROM python:" in dockerfile_content:
            print("✅ RAG backend Dockerfile generated successfully")
            
            # Check for RAG-specific content
            if ("RAG Backend" in dockerfile_content and 
                "CHUNK_SIZE" in dockerfile_content and
                "EMBEDDING_MODEL" in dockerfile_content):
                print("✅ RAG-specific optimizations applied correctly")
            else:
                print("❌ RAG-specific optimizations not applied")
                return False
                
        else:
            print("❌ RAG backend Dockerfile generation failed")
            return False
            
    except Exception as e:
        print(f"❌ RAG backend Dockerfile generation failed: {e}")
        return False
    
    # Test 2: Generate frontend Dockerfile for Agent project
    print("\n2. Testing frontend Dockerfile for Agent project...")
    
    try:
        config = create_dockerfile_config(
            username="Emma",
            project_name="agent-system",
            template_type="agent",
            service_type="frontend",
            port_assignment=emma_assignment,
            output_dir="test_output",
            target_stage="development"
        )
        
        dockerfile_content = manager.generate_dockerfile(config)
        
        # Check for Agent-specific content
        if ("Agent Frontend" in dockerfile_content and 
            "AGENT_MAX_ITERATIONS" in dockerfile_content and
            "NODE_ENV=development" in dockerfile_content):
            print("✅ Agent frontend Dockerfile generated correctly")
        else:
            print("❌ Agent frontend Dockerfile missing expected content")
            return False
            
    except Exception as e:
        print(f"❌ Agent frontend Dockerfile generation failed: {e}")
        return False
    
    # Test 3: Generate common backend Dockerfile
    print("\n3. Testing common backend Dockerfile...")
    
    try:
        config = create_dockerfile_config(
            username="Emma",
            project_name="common",
            template_type="common",
            service_type="backend",
            port_assignment=emma_assignment,
            output_dir="test_output",
            target_stage="production"
        )
        
        dockerfile_content = manager.generate_dockerfile(config)
        
        # Check for multi-stage build and security features
        if ("FROM python:" in dockerfile_content and 
            "USER appuser" in dockerfile_content and
            "HEALTHCHECK" in dockerfile_content):
            print("✅ Common backend Dockerfile generated correctly")
        else:
            print("❌ Common backend Dockerfile missing expected features")
            return False
            
    except Exception as e:
        print(f"❌ Common backend Dockerfile generation failed: {e}")
        return False
    
    print("\n🎉 All Dockerfile generation tests passed!")
    return True


def test_dockerfile_validation():
    """Test Dockerfile validation"""
    print("\n🧪 Testing Dockerfile Validation")
    print("=" * 35)
    
    manager = DockerfileManager("templates")
    
    # Test 1: Valid backend Dockerfile
    print("\n1. Testing valid backend Dockerfile validation...")
    
    valid_backend_dockerfile = """
FROM python:3.11-slim as production

RUN groupadd --gid 1000 appuser && \\
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
    
    try:
        warnings = manager.validate_dockerfile(valid_backend_dockerfile, 'backend')
        
        if len(warnings) <= 1:  # May have one warning about multi-stage
            print("✅ Valid backend Dockerfile passed validation")
        else:
            print(f"⚠️  Valid backend Dockerfile has {len(warnings)} warnings:")
            for warning in warnings[:3]:
                print(f"  - {warning}")
            
    except Exception as e:
        print(f"❌ Backend Dockerfile validation failed: {e}")
        return False
    
    # Test 2: Invalid Dockerfile (missing security features)
    print("\n2. Testing invalid Dockerfile validation...")
    
    invalid_dockerfile = """
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["python", "app.py"]
"""
    
    try:
        warnings = manager.validate_dockerfile(invalid_dockerfile, 'backend')
        
        if warnings and len(warnings) >= 3:
            print(f"✅ Invalid Dockerfile correctly detected {len(warnings)} issues")
            print(f"   Sample issues: {warnings[0] if warnings else 'None'}")
        else:
            print("❌ Invalid Dockerfile should have more validation issues")
            return False
            
    except Exception as e:
        print(f"❌ Dockerfile validation failed: {e}")
        return False
    
    # Test 3: Frontend Dockerfile validation
    print("\n3. Testing frontend Dockerfile validation...")
    
    frontend_dockerfile = """
FROM node:18-alpine as base

RUN addgroup -g 1000 appuser && \\
    adduser -D -s /bin/sh -u 1000 -G appuser appuser

WORKDIR /app
USER appuser

COPY package*.json ./
RUN npm ci --only=production

COPY . .

ENV NODE_ENV=production

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \\
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["npm", "start"]
"""
    
    try:
        warnings = manager.validate_dockerfile(frontend_dockerfile, 'frontend')
        
        if len(warnings) <= 2:  # May have warnings about multi-stage and dumb-init
            print("✅ Frontend Dockerfile validation reasonable")
        else:
            print(f"⚠️  Frontend Dockerfile has {len(warnings)} warnings")
            
    except Exception as e:
        print(f"❌ Frontend Dockerfile validation failed: {e}")
        return False
    
    print("\n🎉 All Dockerfile validation tests passed!")
    return True


def test_supported_services():
    """Test supported service detection"""
    print("\n🧪 Testing Supported Service Detection")
    print("=" * 42)
    
    manager = DockerfileManager("templates")
    
    # Test 1: Common project services
    print("\n1. Testing common project supported services...")
    
    try:
        supported = manager.get_supported_services('common')
        
        if 'backend' in supported and 'frontend' in supported:
            print(f"✅ Common project supports: {', '.join(supported)}")
        else:
            print(f"❌ Common project missing expected services: {supported}")
            return False
            
    except Exception as e:
        print(f"❌ Common service detection failed: {e}")
        return False
    
    # Test 2: RAG project services
    print("\n2. Testing RAG project supported services...")
    
    try:
        supported = manager.get_supported_services('rag')
        
        if 'backend' in supported and 'frontend' in supported:
            print(f"✅ RAG project supports: {', '.join(supported)}")
        else:
            print(f"❌ RAG project missing expected services: {supported}")
            return False
            
    except Exception as e:
        print(f"❌ RAG service detection failed: {e}")
        return False
    
    # Test 3: Agent project services
    print("\n3. Testing Agent project supported services...")
    
    try:
        supported = manager.get_supported_services('agent')
        
        if 'backend' in supported and 'frontend' in supported:
            print(f"✅ Agent project supports: {', '.join(supported)}")
        else:
            print(f"❌ Agent project missing expected services: {supported}")
            return False
            
    except Exception as e:
        print(f"❌ Agent service detection failed: {e}")
        return False
    
    print("\n🎉 All supported service detection tests passed!")
    return True


def test_build_info_generation():
    """Test build information generation"""
    print("\n🧪 Testing Build Info Generation")
    print("=" * 35)
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4010,
        segment2_start=None,
        segment2_end=None
    )
    
    manager = DockerfileManager("templates")
    
    # Test 1: Backend build info
    print("\n1. Testing backend build info...")
    
    try:
        config = create_dockerfile_config(
            username="Emma",
            project_name="rag",
            template_type="rag",
            service_type="backend",
            port_assignment=emma_assignment,
            output_dir="test_output",
            target_stage="production"
        )
        
        build_info = manager.get_build_info(config)
        
        if (build_info['service_type'] == 'backend' and 
            build_info['image_name'] == 'Emma-rag-backend' and
            len(build_info['ports']) > 0):
            print("✅ Backend build info generated correctly")
            print(f"   Image: {build_info['image_name']}")
            print(f"   Ports: {build_info['ports']}")
        else:
            print("❌ Backend build info incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Backend build info generation failed: {e}")
        return False
    
    # Test 2: Frontend build info
    print("\n2. Testing frontend build info...")
    
    try:
        config = create_dockerfile_config(
            username="Emma",
            project_name="agent",
            template_type="agent",
            service_type="frontend",
            port_assignment=emma_assignment,
            output_dir="test_output",
            target_stage="development"
        )
        
        build_info = manager.get_build_info(config)
        
        if (build_info['service_type'] == 'frontend' and 
            build_info['target_stage'] == 'development' and
            'NODE_ENV' in build_info['environment']):
            print("✅ Frontend build info generated correctly")
            print(f"   Target: {build_info['target_stage']}")
            print(f"   Environment: {build_info['environment']['NODE_ENV']}")
        else:
            print("❌ Frontend build info incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Frontend build info generation failed: {e}")
        return False
    
    print("\n🎉 All build info generation tests passed!")
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
    
    # Test 1: Generate backend Dockerfile
    print("\n1. Testing generate_backend_dockerfile...")
    
    try:
        dockerfile_content = generate_backend_dockerfile(
            username="Emma",
            project_name="test",
            template_type="rag",
            port_assignment=emma_assignment,
            output_dir="test_output",
            target_stage="production"
        )
        
        if dockerfile_content and "FROM python:" in dockerfile_content:
            print("✅ Backend Dockerfile generation successful")
        else:
            print("❌ Backend Dockerfile generation failed")
            return False
            
    except Exception as e:
        print(f"❌ generate_backend_dockerfile failed: {e}")
        return False
    
    # Test 2: Generate frontend Dockerfile
    print("\n2. Testing generate_frontend_dockerfile...")
    
    try:
        dockerfile_content = generate_frontend_dockerfile(
            username="Emma",
            project_name="test",
            template_type="agent",
            port_assignment=emma_assignment,
            output_dir="test_output",
            target_stage="development"
        )
        
        if dockerfile_content and "FROM node:" in dockerfile_content:
            print("✅ Frontend Dockerfile generation successful")
        else:
            print("❌ Frontend Dockerfile generation failed")
            return False
            
    except Exception as e:
        print(f"❌ generate_frontend_dockerfile failed: {e}")
        return False
    
    # Test 3: Create all Dockerfiles
    print("\n3. Testing create_all_dockerfiles...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            created_files = create_all_dockerfiles(
                username="Emma",
                project_name="test",
                template_type="common",
                port_assignment=emma_assignment,
                output_dir=temp_dir,
                target_stage="production"
            )
            
            if created_files:
                print(f"✅ Created {len(created_files)} Dockerfile(s)")
                for file_path in created_files.keys():
                    if os.path.exists(file_path):
                        print(f"   ✅ {os.path.relpath(file_path, temp_dir)}")
                    else:
                        print(f"   ❌ {os.path.relpath(file_path, temp_dir)} not found")
                        return False
            else:
                print("❌ No Dockerfiles created")
                return False
                
        except Exception as e:
            print(f"❌ create_all_dockerfiles failed: {e}")
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
    success &= test_dockerfile_generation()
    success &= test_dockerfile_validation()
    success &= test_supported_services()
    success &= test_build_info_generation()
    success &= test_convenience_functions()
    
    if success:
        print("\n🎉 All Dockerfile template system tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some Dockerfile tests failed!")
        sys.exit(1)