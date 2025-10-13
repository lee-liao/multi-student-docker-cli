#!/usr/bin/env python3
"""
Test script for enhanced template processing engine features
"""

import os
import sys
import tempfile
from src.core.template_processor import TemplateProcessor, create_template_context
from src.core.port_assignment import PortAssignment
from cli import DockerComposeCLI


def test_template_validation():
    """Test template validation functionality"""
    print("🧪 Testing Template Validation")
    print("=" * 35)
    
    processor = TemplateProcessor("templates")
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4100,
        segment2_start=8000,
        segment2_end=8100
    )
    
    # Test 1: Validate existing templates
    print("\n1. Testing validation of existing templates...")
    
    context = create_template_context(
        username="Emma",
        project_name="rag",
        template_type="rag",
        port_assignment=emma_assignment,
        has_common_project=False
    )
    
    try:
        validation_results = processor.validate_all_templates(context)
        
        if not validation_results:
            print("✅ All existing templates validate successfully")
        else:
            print("⚠️  Some templates have validation issues:")
            for template_file, warnings in validation_results.items():
                print(f"  {template_file}: {len(warnings)} issues")
                for warning in warnings[:3]:  # Show first 3 warnings
                    print(f"    - {warning}")
        
    except Exception as e:
        print(f"❌ Template validation failed: {e}")
        return False
    
    # Test 2: Test placeholder detection
    print("\n2. Testing placeholder detection...")
    
    rag_template = "templates/rag/docker-compose.yml.template"
    if os.path.exists(rag_template):
        try:
            placeholders = processor.get_required_placeholders(rag_template)
            
            if placeholders:
                print(f"✅ Found {len(placeholders)} placeholders in RAG template")
                print(f"   Sample placeholders: {', '.join(placeholders[:5])}")
                if len(placeholders) > 5:
                    print(f"   ... and {len(placeholders) - 5} more")
            else:
                print("⚠️  No placeholders found in RAG template")
                
        except Exception as e:
            print(f"❌ Placeholder detection failed: {e}")
            return False
    else:
        print("⚠️  RAG template not found, skipping placeholder test")
    
    print("\n🎉 All template validation tests passed!")
    return True


def test_cli_template_commands():
    """Test CLI template-related commands"""
    print("\n🧪 Testing CLI Template Commands")
    print("=" * 35)
    
    # Save original USER env var
    original_user = os.environ.get('USER')
    
    try:
        # Set test user
        os.environ['USER'] = 'Emma'
        
        cli = DockerComposeCLI()
        
        # Test 1: Template-info command for RAG
        print("\n1. Testing template-info command for RAG...")
        try:
            result = cli.run(['template-info', 'rag'])
            if result == 0:
                print("✅ Template-info RAG command successful")
            else:
                print(f"❌ Template-info RAG command failed with exit code {result}")
                return False
        except Exception as e:
            print(f"❌ Template-info RAG command failed: {e}")
            return False
        
        # Test 2: Template-info with validation
        print("\n2. Testing template-info with validation...")
        try:
            result = cli.run(['template-info', 'rag', '--validate'])
            if result == 0:
                print("✅ Template-info with validation successful")
            else:
                print(f"❌ Template-info validation failed with exit code {result}")
                return False
        except Exception as e:
            print(f"❌ Template-info validation failed: {e}")
            return False
        
        print("\n🎉 All CLI template command tests passed!")
        return True
        
    finally:
        # Restore original USER env var
        if original_user:
            os.environ['USER'] = original_user
        elif 'USER' in os.environ:
            del os.environ['USER']


def test_variable_generation_flexibility():
    """Test flexible variable generation from port segments"""
    print("\n🧪 Testing Flexible Variable Generation")
    print("=" * 42)
    
    processor = TemplateProcessor("templates")
    
    # Test 1: Single segment assignment
    print("\n1. Testing single segment port assignment...")
    
    single_segment = PortAssignment(
        login_id="TestUser",
        segment1_start=5000,
        segment1_end=5200,
        segment2_start=None,
        segment2_end=None
    )
    
    context = create_template_context(
        username="TestUser",
        project_name="test",
        template_type="rag",
        port_assignment=single_segment,
        has_common_project=False
    )
    
    try:
        variables = processor.generate_template_variables(context)
        
        if (variables['HAS_TWO_SEGMENTS'] == False and
            variables['SEGMENT1_START'] == 5000 and
            variables['SEGMENT1_END'] == 5200 and
            'BACKEND_PORT' in variables):
            print("✅ Single segment variable generation works")
            print(f"   Port range: {variables['SEGMENT1_START']}-{variables['SEGMENT1_END']}")
            print(f"   Backend port: {variables['BACKEND_PORT']}")
        else:
            print("❌ Single segment variable generation failed")
            return False
            
    except Exception as e:
        print(f"❌ Single segment test failed: {e}")
        return False
    
    # Test 2: CORS origins generation
    print("\n2. Testing CORS origins generation...")
    
    try:
        cors_csr = variables['CORS_ORIGINS_CSR']
        cors_ssr = variables['CORS_ORIGINS_SSR']
        
        if (cors_csr and cors_ssr and
            'localhost' in cors_csr and
            'TestUser-frontend' in cors_ssr):
            print("✅ CORS origins generation works")
            print(f"   CSR origins: {cors_csr[:50]}...")
            print(f"   SSR origins: {cors_ssr[:50]}...")
        else:
            print("❌ CORS origins generation failed")
            return False
            
    except Exception as e:
        print(f"❌ CORS origins test failed: {e}")
        return False
    
    print("\n🎉 All flexible variable generation tests passed!")
    return True


if __name__ == '__main__':
    # Change to cli-tool directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    success = True
    
    # Run tests
    success &= test_template_validation()
    success &= test_cli_template_commands()
    success &= test_variable_generation_flexibility()
    
    if success:
        print("\n🎉 All enhanced template processing tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some enhanced template processing tests failed!")
        sys.exit(1)