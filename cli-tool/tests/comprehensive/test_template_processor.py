#!/usr/bin/env python3
"""
Test script for template processing engine
"""

import os
import sys
import tempfile
from src.core.template_processor import TemplateProcessor, create_template_context
from src.core.port_assignment import PortAssignment


def test_template_processing():
    """Test template processing functionality"""
    print("🧪 Testing Template Processing Engine")
    print("=" * 40)
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4100,
        segment2_start=8000,
        segment2_end=8100
    )
    
    # Test 1: Variable substitution
    print("\n1. Testing variable substitution...")
    
    processor = TemplateProcessor()
    
    test_template = """
Project: {{PROJECT_NAME}}
User: {{USERNAME}}
Backend Port: {{BACKEND_PORT}}
Total Ports: {{TOTAL_PORTS}}
"""
    
    variables = {
        'PROJECT_NAME': 'rag',
        'USERNAME': 'Emma',
        'BACKEND_PORT': 8001,
        'TOTAL_PORTS': 202
    }
    
    result = processor._process_variables(test_template, variables)
    
    if "Project: rag" in result and "User: Emma" in result and "Backend Port: 8001" in result:
        print("✅ Variable substitution works")
    else:
        print(f"❌ Variable substitution failed: {result}")
        return False
    
    # Test 2: Conditional processing
    print("\n2. Testing conditional processing...")
    
    test_conditional = """
{{#if_common_project}}
Using shared infrastructure
Database: {{USERNAME}}-postgres
{{else}}
Using self-contained setup
Database: {{USERNAME}}-rag-postgres
{{/if_common_project}}
"""
    
    # Test with common project
    variables_with_common = {
        'USERNAME': 'Emma',
        'if_common_project': True
    }
    
    result_shared = processor._process_conditionals(test_conditional, variables_with_common)
    result_shared = processor._process_variables(result_shared, variables_with_common)
    
    if "Using shared infrastructure" in result_shared and "Emma-postgres" in result_shared:
        print("✅ Conditional processing (shared mode) works")
    else:
        print(f"❌ Conditional processing (shared) failed: {result_shared}")
        return False
    
    # Test without common project
    variables_no_common = {
        'USERNAME': 'Emma',
        'if_common_project': False
    }
    
    result_standalone = processor._process_conditionals(test_conditional, variables_no_common)
    result_standalone = processor._process_variables(result_standalone, variables_no_common)
    
    if "Using self-contained setup" in result_standalone and "Emma-rag-postgres" in result_standalone:
        print("✅ Conditional processing (standalone mode) works")
    else:
        print(f"❌ Conditional processing (standalone) failed: {result_standalone}")
        return False
    
    # Test 3: Template variable generation
    print("\n3. Testing template variable generation...")
    
    # Test shared mode context
    shared_context = create_template_context(
        username="Emma",
        project_name="rag", 
        template_type="rag",
        port_assignment=emma_assignment,
        has_common_project=True
    )
    
    shared_vars = processor.generate_template_variables(shared_context)
    
    if (shared_vars['USERNAME'] == 'Emma' and 
        shared_vars['PROJECT_NAME'] == 'rag' and
        shared_vars['HAS_COMMON_PROJECT'] == True and
        'BACKEND_PORT' in shared_vars):
        print("✅ Template variable generation (shared mode) works")
    else:
        print(f"❌ Template variable generation (shared) failed")
        return False
    
    # Test standalone mode context
    standalone_context = create_template_context(
        username="Emma",
        project_name="rag",
        template_type="rag", 
        port_assignment=emma_assignment,
        has_common_project=False
    )
    
    standalone_vars = processor.generate_template_variables(standalone_context)
    
    if (standalone_vars['HAS_COMMON_PROJECT'] == False and
        'POSTGRES_PORT' in standalone_vars and
        'BACKEND_PORT' in standalone_vars):
        print("✅ Template variable generation (standalone mode) works")
    else:
        print(f"❌ Template variable generation (standalone) failed")
        return False
    
    # Test 4: CORS origins generation
    print("\n4. Testing CORS origins generation...")
    
    if ('CORS_ORIGINS_CSR' in shared_vars and 
        'CORS_ORIGINS_SSR' in shared_vars and
        'localhost' in shared_vars['CORS_ORIGINS_CSR']):
        print("✅ CORS origins generation works")
        print(f"   CSR: {shared_vars['CORS_ORIGINS_CSR']}")
        print(f"   SSR: {shared_vars['CORS_ORIGINS_SSR']}")
    else:
        print(f"❌ CORS origins generation failed")
        return False
    
    # Test 5: Template interdependency warnings
    print("\n5. Testing interdependency warnings...")
    
    warning = processor.show_interdependency_warning('rag')
    
    if "TEMPLATE INTERDEPENDENCY WARNING" in warning and "docker-compose.yml" in warning:
        print("✅ Interdependency warnings work")
    else:
        print(f"❌ Interdependency warnings failed")
        return False
    
    print("\n🎉 All template processing tests passed!")
    return True


def test_real_template_processing():
    """Test processing real template files"""
    print("\n🧪 Testing Real Template Processing")
    print("=" * 35)
    
    # Check if template files exist
    rag_template = "../templates/rag/docker-compose.yml.template"
    common_template = "../templates/common/docker-compose.yml.template"
    
    if not os.path.exists(rag_template):
        print(f"⚠️  RAG template not found: {rag_template}")
        return True  # Skip this test
    
    if not os.path.exists(common_template):
        print(f"⚠️  Common template not found: {common_template}")
        return True  # Skip this test
    
    # Create test context
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4100,
        segment2_start=8000,
        segment2_end=8100
    )
    
    processor = TemplateProcessor("../templates")
    
    # Test 1: Process RAG template in shared mode
    print("\n1. Testing RAG template (shared mode)...")
    
    shared_context = create_template_context(
        username="Emma",
        project_name="rag",
        template_type="rag",
        port_assignment=emma_assignment,
        has_common_project=True
    )
    
    try:
        variables = processor.generate_template_variables(shared_context)
        processed_content = processor.process_template_file(rag_template, variables)
        
        # Check that shared mode features are present
        if ("external: true" in processed_content and 
            "Emma-network" in processed_content and
            "Emma-rag-backend" in processed_content):
            print("✅ RAG template (shared mode) processed correctly")
        else:
            print("❌ RAG template (shared mode) missing expected content")
            return False
            
    except Exception as e:
        print(f"❌ RAG template (shared mode) processing failed: {e}")
        return False
    
    # Test 2: Process RAG template in standalone mode
    print("\n2. Testing RAG template (standalone mode)...")
    
    standalone_context = create_template_context(
        username="Emma",
        project_name="rag",
        template_type="rag",
        port_assignment=emma_assignment,
        has_common_project=False
    )
    
    try:
        variables = processor.generate_template_variables(standalone_context)
        processed_content = processor.process_template_file(rag_template, variables)
        
        # Check that standalone features are present
        if ("postgres-rag:" in processed_content and
            "Emma-rag-postgres" in processed_content and
            "Emma-rag-network" in processed_content):
            print("✅ RAG template (standalone mode) processed correctly")
        else:
            print("❌ RAG template (standalone mode) missing expected content")
            return False
            
    except Exception as e:
        print(f"❌ RAG template (standalone mode) processing failed: {e}")
        return False
    
    # Test 3: Process common template
    print("\n3. Testing common template...")
    
    common_context = create_template_context(
        username="Emma",
        project_name="common",
        template_type="common",
        port_assignment=emma_assignment,
        has_common_project=False
    )
    
    try:
        variables = processor.generate_template_variables(common_context)
        processed_content = processor.process_template_file(common_template, variables)
        
        # Check that common template features are present
        if ("Emma-postgres" in processed_content and
            "Emma-mongodb" in processed_content and
            "Emma-network" in processed_content):
            print("✅ Common template processed correctly")
        else:
            print("❌ Common template missing expected content")
            return False
            
    except Exception as e:
        print(f"❌ Common template processing failed: {e}")
        return False
    
    print("\n🎉 All real template processing tests passed!")
    return True


if __name__ == '__main__':
    # Change to cli-tool directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    success = True
    
    # Run tests
    success &= test_template_processing()
    success &= test_real_template_processing()
    
    if success:
        print("\n🎉 All template processor tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some template processor tests failed!")
        sys.exit(1)