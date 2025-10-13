#!/usr/bin/env python3
"""
Test script for README generation system
"""

import os
import sys
import tempfile
import shutil
from src.config.readme_manager import ReadmeManager, create_readme_config, generate_readme
from src.core.port_assignment import PortAssignment


def test_readme_generation_basic():
    """Test basic README generation functionality"""
    print("🧪 Testing Basic README Generation")
    print("=" * 40)
    
    # Create test port assignment
    test_assignment = PortAssignment(
        login_id="TestUser",
        segment1_start=5200,
        segment1_end=5250,
        segment2_start=6000,
        segment2_end=6050
    )
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ReadmeManager(templates_dir="templates")
        
        # Test 1: Generate RAG README
        print("\n1. Testing RAG README generation...")
        
        try:
            config = create_readme_config(
                username="TestUser",
                project_name="test-rag",
                template_type="rag",
                port_assignment=test_assignment,
                output_dir=temp_dir,
                has_common_project=False
            )
            
            readme_path = manager.create_readme_file(config)
            
            if os.path.exists(readme_path):
                print("✅ RAG README file created")
                
                # Check content
                with open(readme_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Verify key elements
                if "TestUser" in content:
                    print("   ✅ Username substitution")
                else:
                    print("   ❌ Username substitution failed")
                    return False
                
                if "test-rag" in content:
                    print("   ✅ Project name substitution")
                else:
                    print("   ❌ Project name substitution failed")
                    return False
                
                if "5200" in content:
                    print("   ✅ Port assignment substitution")
                else:
                    print("   ❌ Port assignment substitution failed")
                    return False
                
                if "CORS Configuration" in content:
                    print("   ✅ CORS documentation included")
                else:
                    print("   ❌ CORS documentation missing")
                    return False
                
                if "Docker Commands" in content:
                    print("   ✅ Docker commands included")
                else:
                    print("   ❌ Docker commands missing")
                    return False
                
                if "Common Issues and Solutions" in content:
                    print("   ✅ Troubleshooting guide included")
                else:
                    print("   ❌ Troubleshooting guide missing")
                    return False
                    
            else:
                print("❌ RAG README file not created")
                return False
                
        except Exception as e:
            print(f"❌ RAG README generation failed: {e}")
            return False
        
        # Test 2: Generate Agent README
        print("\n2. Testing Agent README generation...")
        
        try:
            config = create_readme_config(
                username="TestUser",
                project_name="test-agent",
                template_type="agent",
                port_assignment=test_assignment,
                output_dir=temp_dir,
                has_common_project=True
            )
            
            readme_path = manager.create_readme_file(config)
            
            if os.path.exists(readme_path):
                print("✅ Agent README file created")
                
                # Check content
                with open(readme_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Verify agent-specific elements
                if "Agent Project" in content:
                    print("   ✅ Agent project title")
                else:
                    print("   ❌ Agent project title missing")
                    return False
                
                if "Agent Backend API" in content:
                    print("   ✅ Agent-specific services")
                else:
                    print("   ❌ Agent-specific services missing")
                    return False
                
                if "Shared Infrastructure Mode" in content:
                    print("   ✅ Common project mode detected")
                else:
                    print("   ❌ Common project mode not detected")
                    return False
                    
            else:
                print("❌ Agent README file not created")
                return False
                
        except Exception as e:
            print(f"❌ Agent README generation failed: {e}")
            return False
        
        # Test 3: Generate Common README
        print("\n3. Testing Common README generation...")
        
        try:
            config = create_readme_config(
                username="TestUser",
                project_name="common",
                template_type="common",
                port_assignment=test_assignment,
                output_dir=temp_dir,
                has_common_project=False
            )
            
            readme_path = manager.create_readme_file(config)
            
            if os.path.exists(readme_path):
                print("✅ Common README file created")
                
                # Check content
                with open(readme_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Verify common-specific elements
                if "Common Infrastructure" in content:
                    print("   ✅ Common infrastructure title")
                else:
                    print("   ❌ Common infrastructure title missing")
                    return False
                
                if "PostgreSQL" in content and "MongoDB" in content:
                    print("   ✅ Infrastructure services listed")
                else:
                    print("   ❌ Infrastructure services missing")
                    return False
                    
            else:
                print("❌ Common README file not created")
                return False
                
        except Exception as e:
            print(f"❌ Common README generation failed: {e}")
            return False
    
    print("\n🎉 All basic README generation tests passed!")
    return True


def test_cors_configuration():
    """Test CORS configuration generation"""
    print("\n🧪 Testing CORS Configuration Generation")
    print("=" * 45)
    
    # Create test port assignment with two segments
    test_assignment = PortAssignment(
        login_id="TestUser",
        segment1_start=4000,
        segment1_end=4010,
        segment2_start=8000,
        segment2_end=8010
    )
    
    manager = ReadmeManager(templates_dir="templates")
    
    # Test CORS generation
    cors_config = manager._generate_cors_configuration("TestUser", test_assignment.all_ports)
    
    print("\n1. Testing CORS origins generation...")
    
    if 'CORS_ORIGINS_CSR' in cors_config:
        print("✅ CSR CORS origins generated")
        print(f"   CSR: {cors_config['CORS_ORIGINS_CSR']}")
    else:
        print("❌ CSR CORS origins missing")
        return False
    
    if 'CORS_ORIGINS_SSR' in cors_config:
        print("✅ SSR CORS origins generated")
        print(f"   SSR: {cors_config['CORS_ORIGINS_SSR']}")
    else:
        print("❌ SSR CORS origins missing")
        return False
    
    # Verify CSR origins contain localhost ports
    if "localhost:8000" in cors_config['CORS_ORIGINS_CSR']:
        print("   ✅ CSR contains localhost ports")
    else:
        print("   ❌ CSR missing localhost ports")
        return False
    
    # Verify SSR origins contain container hostnames
    if "TestUser-frontend:3000" in cors_config['CORS_ORIGINS_SSR']:
        print("   ✅ SSR contains container hostnames")
    else:
        print("   ❌ SSR missing container hostnames")
        return False
    
    print("\n🎉 All CORS configuration tests passed!")
    return True


def test_template_validation():
    """Test README template validation"""
    print("\n🧪 Testing Template Validation")
    print("=" * 35)
    
    manager = ReadmeManager(templates_dir="templates")
    
    # Test 1: Validate RAG template
    print("\n1. Validating RAG template...")
    
    issues = manager.validate_readme_template("rag")
    
    if not issues:
        print("✅ RAG template validation passed")
    else:
        print("⚠️  RAG template validation issues:")
        for issue in issues:
            print(f"   - {issue}")
    
    # Test 2: Validate Agent template
    print("\n2. Validating Agent template...")
    
    issues = manager.validate_readme_template("agent")
    
    if not issues:
        print("✅ Agent template validation passed")
    else:
        print("⚠️  Agent template validation issues:")
        for issue in issues:
            print(f"   - {issue}")
    
    # Test 3: Validate Common template
    print("\n3. Validating Common template...")
    
    issues = manager.validate_readme_template("common")
    
    if not issues:
        print("✅ Common template validation passed")
    else:
        print("⚠️  Common template validation issues:")
        for issue in issues:
            print(f"   - {issue}")
    
    print("\n🎉 Template validation tests completed!")
    return True


def test_conditional_blocks():
    """Test conditional block processing"""
    print("\n🧪 Testing Conditional Block Processing")
    print("=" * 45)
    
    manager = ReadmeManager(templates_dir="templates")
    
    # Test conditional processing
    test_content = """
{{#if HAS_COMMON_PROJECT}}
This is shared mode content.
{{else}}
This is standalone mode content.
{{/if}}

{{#if HAS_TWO_SEGMENTS}}
Two segment configuration.
{{/if}}
"""
    
    # Test 1: With common project
    print("\n1. Testing with common project...")
    
    variables = {
        'HAS_COMMON_PROJECT': True,
        'HAS_TWO_SEGMENTS': False
    }
    
    result = manager._process_conditional_blocks(test_content, variables)
    
    if "shared mode content" in result and "standalone mode content" not in result:
        print("✅ Common project conditional works")
    else:
        print("❌ Common project conditional failed")
        return False
    
    if "Two segment configuration" not in result:
        print("✅ Two segments conditional works (false case)")
    else:
        print("❌ Two segments conditional failed")
        return False
    
    # Test 2: Without common project
    print("\n2. Testing without common project...")
    
    variables = {
        'HAS_COMMON_PROJECT': False,
        'HAS_TWO_SEGMENTS': True
    }
    
    result = manager._process_conditional_blocks(test_content, variables)
    
    if "standalone mode content" in result and "shared mode content" not in result:
        print("✅ Standalone conditional works")
    else:
        print("❌ Standalone conditional failed")
        return False
    
    if "Two segment configuration" in result:
        print("✅ Two segments conditional works (true case)")
    else:
        print("❌ Two segments conditional failed")
        return False
    
    print("\n🎉 All conditional block tests passed!")
    return True


def test_convenience_function():
    """Test convenience function"""
    print("\n🧪 Testing Convenience Function")
    print("=" * 35)
    
    # Create test port assignment
    test_assignment = PortAssignment(
        login_id="TestUser",
        segment1_start=5200,
        segment1_end=5250,
        segment2_start=6000,
        segment2_end=6050
    )
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            readme_path = generate_readme(
                username="TestUser",
                project_name="convenience-test",
                template_type="rag",
                port_assignment=test_assignment,
                output_dir=temp_dir,
                has_common_project=True,
                templates_dir="templates"
            )
            
            if os.path.exists(readme_path):
                print("✅ Convenience function works")
                
                with open(readme_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if "convenience-test" in content and "TestUser" in content:
                    print("   ✅ Content generated correctly")
                else:
                    print("   ❌ Content generation failed")
                    return False
            else:
                print("❌ Convenience function failed")
                return False
                
        except Exception as e:
            print(f"❌ Convenience function failed: {e}")
            return False
    
    print("\n🎉 Convenience function test passed!")
    return True


if __name__ == '__main__':
    # Change to project root directory (parent of cli-tool)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    success = True
    
    # Run tests
    success &= test_readme_generation_basic()
    success &= test_cors_configuration()
    success &= test_template_validation()
    success &= test_conditional_blocks()
    success &= test_convenience_function()
    
    if success:
        print("\n🎉 All README generation system tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some README generation tests failed!")
        sys.exit(1)