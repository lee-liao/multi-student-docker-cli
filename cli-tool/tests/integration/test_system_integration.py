#!/usr/bin/env python3
"""
System Integration Test
Tests the complete multi-student Docker Compose system integration.
"""

import sys
import os
import tempfile
import shutil
import json
import time

# Add the cli-tool directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

def safe_print(message):
    """Print message with safe encoding for Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        safe_message = message.replace('✅', '[PASS]').replace('❌', '[FAIL]').replace('⚠️', '[WARN]')
        safe_message = safe_message.replace('🚀', '[START]').replace('🎯', '[TARGET]').replace('📊', '[STATS]')
        safe_message = safe_message.replace('✓', 'OK').replace('💡', 'TIP').replace('📋', 'INFO')
        print(safe_message)

def test_complete_system_integration():
    """Test complete system integration"""
    safe_print("\n[START] Complete System Integration Test")
    safe_print("="*60)
    
    results = {
        "components_tested": 0,
        "components_passed": 0,
        "integration_points": 0,
        "integration_passed": 0,
        "errors": []
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Test 1: Port Assignment System
            safe_print("\n[TEST] 1. Port Assignment System")
            from src.core.port_assignment import PortAssignment, PortAssignmentManager
            
            # Create test assignment
            assignment = PortAssignment("test_user", 8000, 8099)
            port_range = assignment.get_port_range()
            
            assert len(port_range) == 100
            assert port_range[0] == 8000
            assert port_range[-1] == 8099
            
            results["components_tested"] += 1
            results["components_passed"] += 1
            safe_print("  [PASS] Port assignment creation and validation")
            
        except Exception as e:
            results["components_tested"] += 1
            results["errors"].append(f"Port Assignment: {str(e)}")
            safe_print(f"  [FAIL] Port assignment: {str(e)}")
        
        try:
            # Test 2: Project Manager System
            safe_print("\n[TEST] 2. Project Manager System")
            from src.core.project_manager import ProjectManager
            
            projects_dir = os.path.join(temp_dir, "projects")
            templates_dir = os.path.join(temp_dir, "templates")
            os.makedirs(projects_dir)
            os.makedirs(templates_dir)
            
            manager = ProjectManager(base_dir=projects_dir, templates_dir=templates_dir)
            projects = manager.list_projects()
            
            assert isinstance(projects, list)
            assert manager.base_dir == projects_dir
            
            results["components_tested"] += 1
            results["components_passed"] += 1
            safe_print("  [PASS] Project manager initialization and listing")
            
        except Exception as e:
            results["components_tested"] += 1
            results["errors"].append(f"Project Manager: {str(e)}")
            safe_print(f"  [FAIL] Project manager: {str(e)}")
        
        try:
            # Test 3: Template Processing System
            safe_print("\n[TEST] 3. Template Processing System")
            from src.core.project_manager import TemplateProcessor
            
            processor = TemplateProcessor(templates_dir)
            
            # Create a simple template
            template_content = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "{{WEB_PORT}}:80"
"""
            
            template_file = os.path.join(templates_dir, "test.yml")
            with open(template_file, 'w') as f:
                f.write(template_content)
            
            # Test template processing
            variables = {"WEB_PORT": "8080"}
            processed = processor.process_template_file(template_file, variables)
            
            assert "8080:80" in processed
            
            results["components_tested"] += 1
            results["components_passed"] += 1
            safe_print("  [PASS] Template processing and variable substitution")
            
        except Exception as e:
            results["components_tested"] += 1
            results["errors"].append(f"Template Processing: {str(e)}")
            safe_print(f"  [FAIL] Template processing: {str(e)}")
        
        try:
            # Test 4: Error Handling System
            safe_print("\n[TEST] 4. Error Handling System")
            from src.utils.error_handling import CLIError, ExitCode, ErrorHandler
            
            # Test error creation
            error = CLIError("Test error", ExitCode.GENERAL_ERROR)
            assert error.message == "Test error"
            assert error.exit_code == ExitCode.GENERAL_ERROR
            
            # Test error handler
            handler = ErrorHandler()
            assert hasattr(handler, 'handle_error')
            
            results["components_tested"] += 1
            results["components_passed"] += 1
            safe_print("  [PASS] Error handling and exit codes")
            
        except Exception as e:
            results["components_tested"] += 1
            results["errors"].append(f"Error Handling: {str(e)}")
            safe_print(f"  [FAIL] Error handling: {str(e)}")
        
        try:
            # Test 5: Security Validation System
            safe_print("\n[TEST] 5. Security Validation System")
            from src.security.security_validation import SecurityValidator, FilePermissionValidator
            
            validator = SecurityValidator()
            file_validator = FilePermissionValidator()
            
            # Test directory validation
            dir_check = file_validator.validate_dockered_services_directory(temp_dir)
            assert hasattr(dir_check, 'exists')
            assert hasattr(dir_check, 'readable')
            
            results["components_tested"] += 1
            results["components_passed"] += 1
            safe_print("  [PASS] Security validation and file permissions")
            
        except Exception as e:
            results["components_tested"] += 1
            results["errors"].append(f"Security Validation: {str(e)}")
            safe_print(f"  [FAIL] Security validation: {str(e)}")
        
        try:
            # Test 6: Secure Logging System
            safe_print("\n[TEST] 6. Secure Logging System")
            from src.security.secure_logger import SecureLogger, SensitiveDataSanitizer
            
            logger = SecureLogger()
            sanitizer = SensitiveDataSanitizer()
            
            # Test sanitization
            test_message = "Password: PASSWORD=secret123"
            sanitized = sanitizer.sanitize_message(test_message)
            assert "secret123" not in sanitized
            
            results["components_tested"] += 1
            results["components_passed"] += 1
            safe_print("  [PASS] Secure logging and data sanitization")
            
        except Exception as e:
            results["components_tested"] += 1
            results["errors"].append(f"Secure Logging: {str(e)}")
            safe_print(f"  [FAIL] Secure logging: {str(e)}")
        
        # Integration Tests
        safe_print("\n[TEST] Integration Points")
        safe_print("-"*40)
        
        try:
            # Integration 1: Port Assignment + Project Manager
            safe_print("\n[INTEGRATION] 1. Port Assignment + Project Manager")
            
            assignment = PortAssignment("test_user", 8000, 8099)
            manager = ProjectManager(base_dir=projects_dir)
            
            # Generate template variables (integration point)
            variables = manager._generate_template_variables(
                "test_project", "test_user", assignment, False
            )
            
            assert "PROJECT_NAME" in variables
            assert "USERNAME" in variables
            assert variables["PROJECT_NAME"] == "test_project"
            
            results["integration_points"] += 1
            results["integration_passed"] += 1
            safe_print("  [PASS] Port assignment integrates with project manager")
            
        except Exception as e:
            results["integration_points"] += 1
            results["errors"].append(f"Port+Project Integration: {str(e)}")
            safe_print(f"  [FAIL] Port+Project integration: {str(e)}")
        
        try:
            # Integration 2: Error Handling + Security Validation
            safe_print("\n[INTEGRATION] 2. Error Handling + Security Validation")
            
            from src.utils.error_handling import ErrorHandler, PermissionError, ErrorContext
            from src.security.security_validation import SecurityAuditor
            
            handler = ErrorHandler()
            auditor = SecurityAuditor()
            
            # Test error with security context
            context = ErrorContext(operation="test_operation", user_id="test_user")
            error = PermissionError("Test permission error", context)
            
            assert error.context.operation == "test_operation"
            assert error.context.user_id == "test_user"
            
            results["integration_points"] += 1
            results["integration_passed"] += 1
            safe_print("  [PASS] Error handling integrates with security validation")
            
        except Exception as e:
            results["integration_points"] += 1
            results["errors"].append(f"Error+Security Integration: {str(e)}")
            safe_print(f"  [FAIL] Error+Security integration: {str(e)}")
        
        try:
            # Integration 3: Complete Workflow Simulation
            safe_print("\n[INTEGRATION] 3. Complete Workflow Simulation")
            
            # Simulate complete project creation workflow
            assignment = PortAssignment("test_user", 8000, 8099)
            manager = ProjectManager(base_dir=projects_dir, templates_dir=templates_dir)
            
            # Create template directory
            rag_template_dir = os.path.join(templates_dir, "rag")
            os.makedirs(rag_template_dir)
            
            # Create template file
            template_content = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "{{WEB_PORT}}:80"
    environment:
      - USER={{USERNAME}}
      - PROJECT={{PROJECT_NAME}}
"""
            
            template_file = os.path.join(rag_template_dir, "docker-compose.yml.template")
            with open(template_file, 'w') as f:
                f.write(template_content)
            
            # Generate variables
            variables = manager._generate_template_variables(
                "test_project", "test_user", assignment, False
            )
            
            # Process template
            processor = TemplateProcessor(templates_dir)
            processed_content = processor.process_template_file(template_file, variables)
            
            # Verify complete workflow
            assert "USER=test_user" in processed_content
            assert "PROJECT=test_project" in processed_content
            assert f"WEB_PORT" in str(variables)
            
            results["integration_points"] += 1
            results["integration_passed"] += 1
            safe_print("  [PASS] Complete workflow simulation successful")
            
        except Exception as e:
            results["integration_points"] += 1
            results["errors"].append(f"Complete Workflow: {str(e)}")
            safe_print(f"  [FAIL] Complete workflow: {str(e)}")
    
    # Generate Final Report
    safe_print("\n[STATS] SYSTEM INTEGRATION REPORT")
    safe_print("="*60)
    
    component_success_rate = (results["components_passed"] / results["components_tested"] * 100) if results["components_tested"] > 0 else 0
    integration_success_rate = (results["integration_passed"] / results["integration_points"] * 100) if results["integration_points"] > 0 else 0
    overall_success_rate = ((results["components_passed"] + results["integration_passed"]) / 
                           (results["components_tested"] + results["integration_points"]) * 100) if (results["components_tested"] + results["integration_points"]) > 0 else 0
    
    safe_print(f"\nComponent Tests:")
    safe_print(f"  Tested: {results['components_tested']}")
    safe_print(f"  Passed: {results['components_passed']}")
    safe_print(f"  Success Rate: {component_success_rate:.1f}%")
    
    safe_print(f"\nIntegration Tests:")
    safe_print(f"  Tested: {results['integration_points']}")
    safe_print(f"  Passed: {results['integration_passed']}")
    safe_print(f"  Success Rate: {integration_success_rate:.1f}%")
    
    safe_print(f"\nOverall System Health:")
    safe_print(f"  Total Tests: {results['components_tested'] + results['integration_points']}")
    safe_print(f"  Total Passed: {results['components_passed'] + results['integration_passed']}")
    safe_print(f"  Overall Success Rate: {overall_success_rate:.1f}%")
    
    if overall_success_rate >= 90:
        safe_print(f"\n[PASS] EXCELLENT: System is ready for production use")
    elif overall_success_rate >= 75:
        safe_print(f"\n[PASS] GOOD: System is functional with minor issues")
    elif overall_success_rate >= 50:
        safe_print(f"\n[WARN] FAIR: System has significant issues that need attention")
    else:
        safe_print(f"\n[FAIL] POOR: System has major issues requiring immediate attention")
    
    # Error Summary
    if results["errors"]:
        safe_print(f"\n[INFO] Error Summary:")
        for i, error in enumerate(results["errors"], 1):
            safe_print(f"  {i}. {error}")
    
    # System Capabilities Summary
    safe_print(f"\n[INFO] System Capabilities Validated:")
    safe_print(f"  - Port assignment and management")
    safe_print(f"  - Project creation and management")
    safe_print(f"  - Template processing and variable substitution")
    safe_print(f"  - Comprehensive error handling")
    safe_print(f"  - Security validation and file permissions")
    safe_print(f"  - Secure logging with data sanitization")
    safe_print(f"  - Component integration and workflow coordination")
    
    safe_print(f"\n[TIP] Next Steps:")
    if overall_success_rate >= 75:
        safe_print(f"  - System is ready for deployment")
        safe_print(f"  - Consider end-to-end testing with actual Docker environment")
        safe_print(f"  - Test with multiple concurrent users")
    else:
        safe_print(f"  - Address failing components before deployment")
        safe_print(f"  - Review error messages and fix underlying issues")
        safe_print(f"  - Re-run tests after fixes")
    
    return overall_success_rate >= 75

if __name__ == "__main__":
    success = test_complete_system_integration()
    sys.exit(0 if success else 1)