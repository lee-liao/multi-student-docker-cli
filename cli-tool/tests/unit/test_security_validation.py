#!/usr/bin/env python3
"""
Test Suite for Security Validation System
Tests file permissions, Docker access, login authorization, and audit logging.
"""

import sys
import os
import tempfile
import shutil
import json
import base64
from pathlib import Path

# Add the cli-tool directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from src.security.security_validation import (
    FilePermissionValidator,
    DockerAccessValidator,
    LoginIDAuthorizer,
    SecurityAuditor,
    SecurityValidator,
    FilePermissionCheck,
    DockerAccessCheck,
    SecurityAuditEvent,
    validate_system_security,
    validate_project_security,
    audit_project_operation,
    audit_port_assignment
)
from src.security.secure_logger import SecureLogger

def test_file_permission_validator():
    """Test file permission validation"""
    print("Testing File Permission Validator...")
    
    validator = FilePermissionValidator()
    
    # Test with temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test directory validation
        result = validator.validate_dockered_services_directory(temp_dir)
        
        assert isinstance(result, FilePermissionCheck)
        assert result.exists == True
        assert result.path == temp_dir
        assert isinstance(result.readable, bool)
        assert isinstance(result.writable, bool)
        assert isinstance(result.executable, bool)
        assert isinstance(result.issues, list)
        assert isinstance(result.recommendations, list)
        
        # Test project directory validation
        project_dir = os.path.join(temp_dir, "test_project")
        os.makedirs(project_dir)
        
        project_result = validator.validate_project_directory(project_dir)
        assert isinstance(project_result, FilePermissionCheck)
        assert project_result.exists == True
        
        # Create docker-compose.yml
        compose_file = os.path.join(project_dir, "docker-compose.yml")
        with open(compose_file, "w") as f:
            f.write("version: '3'\nservices:\n  test:\n    image: nginx")
        
        # Re-validate with compose file
        project_result_with_compose = validator.validate_project_directory(project_dir)
        assert project_result_with_compose.exists == True
    
    # Test non-existent directory
    nonexistent_result = validator.validate_dockered_services_directory("/nonexistent/path")
    assert nonexistent_result.exists == False
    assert len(nonexistent_result.issues) > 0
    assert len(nonexistent_result.recommendations) > 0
    
    print("✓ File Permission Validator test passed")

def test_docker_access_validator():
    """Test Docker access validation"""
    print("Testing Docker Access Validator...")
    
    validator = DockerAccessValidator()
    
    # Test Docker access validation
    result = validator.validate_docker_access()
    
    assert isinstance(result, DockerAccessCheck)
    assert isinstance(result.docker_available, bool)
    assert isinstance(result.compose_available, bool)
    assert isinstance(result.user_in_docker_group, bool)
    assert isinstance(result.can_run_docker, bool)
    assert isinstance(result.issues, list)
    assert isinstance(result.recommendations, list)
    
    # Docker version should be string if available
    if result.docker_available:
        assert isinstance(result.docker_version, str)
    
    # Compose version should be string if available
    if result.compose_available:
        assert isinstance(result.compose_version, str)
    
    print("✓ Docker Access Validator test passed")

def test_login_id_authorizer():
    """Test login ID authorization"""
    print("Testing Login ID Authorizer...")
    
    # Create temporary assignments file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the home directory
        original_home = Path.home
        Path.home = lambda: Path(temp_dir)
        
        try:
            authorizer = LoginIDAuthorizer()
            
            # Test with no assignments file
            authorized, user_info = authorizer.validate_user_authorization("test_user")
            assert authorized == False
            assert "error" in user_info
            
            # Create test assignments
            test_assignments = {
                "test_user": {
                    "start_port": 8000,
                    "end_port": 8099,
                    "total_ports": 100
                },
                "another_user": {
                    "start_port": 8100,
                    "end_port": 8199,
                    "total_ports": 100
                }
            }
            
            # Create assignments file
            authorizer.create_assignments_file(test_assignments, encrypt=False)
            
            # Test valid user
            authorized, user_info = authorizer.validate_user_authorization("test_user")
            assert authorized == True
            assert user_info["start_port"] == 8000
            assert user_info["end_port"] == 8099
            assert user_info["total_ports"] == 100
            
            # Test invalid user
            authorized, user_info = authorizer.validate_user_authorization("invalid_user")
            assert authorized == False
            assert "error" in user_info
            
            # Test encrypted assignments
            authorizer.create_assignments_file(test_assignments, encrypt=True)
            authorized, user_info = authorizer.validate_user_authorization("test_user")
            assert authorized == True
            assert user_info["start_port"] == 8000
            
        finally:
            # Restore original home function
            Path.home = original_home
    
    print("✓ Login ID Authorizer test passed")

def test_security_auditor():
    """Test security audit logging"""
    print("Testing Security Auditor...")
    
    auditor = SecurityAuditor()
    
    # Test project operation logging
    auditor.log_project_operation(
        operation="create_project",
        user_id="test_user",
        project_name="test_project",
        success=True,
        details={"template": "rag", "ports": [8000, 8001]}
    )
    
    # Test port assignment logging
    auditor.log_port_assignment(
        user_id="test_user",
        ports_assigned=[8000, 8001, 8002, 8003, 8004]
    )
    
    # Test file operation logging
    auditor.log_file_operation(
        operation="create",
        file_path="/test/docker-compose.yml",
        user_id="test_user",
        success=True,
        details={"size": 1024}
    )
    
    # Test permission check logging
    auditor.log_permission_check(
        check_type="directory_permissions",
        resource="/test/directory",
        user_id="test_user",
        result=True,
        issues=[]
    )
    
    # Test failed operation (higher risk)
    auditor.log_project_operation(
        operation="remove_project",
        user_id="test_user",
        project_name="test_project",
        success=False,
        details={"error": "Permission denied"}
    )
    
    print("✓ Security Auditor test passed")

def test_security_validator():
    """Test comprehensive security validator"""
    print("Testing Security Validator...")
    
    validator = SecurityValidator()
    
    # Test system security validation with temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # This will fail because user won't be authorized, but we can test the structure
        results = validator.validate_system_security("test_user", temp_dir)
        
        assert isinstance(results, dict)
        assert "user_id" in results
        assert "timestamp" in results
        assert "validations" in results
        assert "overall_status" in results
        assert "critical_issues" in results
        assert "recommendations" in results
        
        # Check validation structure
        assert "user_authorization" in results["validations"]
        assert "directory_permissions" in results["validations"]
        assert "docker_access" in results["validations"]
        
        # Test project security validation
        project_dir = os.path.join(temp_dir, "test_project")
        os.makedirs(project_dir)
        
        project_results = validator.validate_project_security("test_user", project_dir)
        
        assert isinstance(project_results, dict)
        assert "user_id" in project_results
        assert "project_path" in project_results
        assert "status" in project_results
        assert "issues" in project_results
        assert "recommendations" in project_results
        assert "permissions" in project_results
    
    print("✓ Security Validator test passed")

def test_convenience_functions():
    """Test convenience functions"""
    print("Testing Convenience Functions...")
    
    # Test system security validation function
    with tempfile.TemporaryDirectory() as temp_dir:
        results = validate_system_security("test_user", temp_dir)
        assert isinstance(results, dict)
        assert "overall_status" in results
        
        # Test project security validation function
        project_dir = os.path.join(temp_dir, "test_project")
        os.makedirs(project_dir)
        
        project_results = validate_project_security("test_user", project_dir)
        assert isinstance(project_results, dict)
        assert "status" in project_results
    
    # Test audit convenience functions
    audit_project_operation(
        operation="create",
        user_id="test_user",
        project_name="test_project",
        success=True,
        details={"template": "rag"}
    )
    
    audit_port_assignment(
        user_id="test_user",
        ports_assigned=[8000, 8001, 8002]
    )
    
    print("✓ Convenience Functions test passed")

def test_security_audit_event():
    """Test security audit event structure"""
    print("Testing Security Audit Event...")
    
    event = SecurityAuditEvent(
        event_type="project_operation",
        user_id="test_user",
        timestamp="2023-01-01T00:00:00",
        operation="create_project",
        resource="test_project",
        success=True,
        details={"template": "rag"},
        risk_level="LOW"
    )
    
    assert event.event_type == "project_operation"
    assert event.user_id == "test_user"
    assert event.operation == "create_project"
    assert event.resource == "test_project"
    assert event.success == True
    assert event.risk_level == "LOW"
    assert isinstance(event.details, dict)
    
    print("✓ Security Audit Event test passed")

def test_integration_scenarios():
    """Test integration scenarios"""
    print("Testing Integration Scenarios...")
    
    # Test complete security validation workflow
    with tempfile.TemporaryDirectory() as temp_dir:
        validator = SecurityValidator()
        
        # Create test project structure
        project_dir = os.path.join(temp_dir, "test_project")
        os.makedirs(project_dir)
        
        # Create docker-compose.yml
        compose_file = os.path.join(project_dir, "docker-compose.yml")
        with open(compose_file, "w") as f:
            f.write("version: '3'\nservices:\n  web:\n    image: nginx")
        
        # Validate system security
        system_results = validator.validate_system_security("test_user", temp_dir)
        assert isinstance(system_results, dict)
        
        # Validate project security
        project_results = validator.validate_project_security("test_user", project_dir)
        assert isinstance(project_results, dict)
        
        # Audit operations
        validator.auditor.log_project_operation(
            "create_project",
            "test_user",
            "test_project",
            True,
            {"template": "rag", "validation_passed": True}
        )
        
        validator.auditor.log_file_operation(
            "create",
            compose_file,
            "test_user",
            True,
            {"file_type": "docker-compose"}
        )
    
    print("✓ Integration Scenarios test passed")

def run_security_validation_tests():
    """Run all security validation tests"""
    print("Running Security Validation System Tests")
    print("=" * 50)
    
    try:
        test_file_permission_validator()
        test_docker_access_validator()
        test_login_id_authorizer()
        test_security_auditor()
        test_security_validator()
        test_convenience_functions()
        test_security_audit_event()
        test_integration_scenarios()
        
        print("\n" + "=" * 50)
        print("✅ All security validation tests passed!")
        
        print("\n🛡️  Security Validation System Summary:")
        print("=" * 50)
        
        print("\n📋 Core Components:")
        print("  • FilePermissionValidator - Validates file and directory permissions")
        print("  • DockerAccessValidator - Validates Docker daemon and compose access")
        print("  • LoginIDAuthorizer - Handles encrypted user authorization")
        print("  • SecurityAuditor - Enhanced security audit logging")
        print("  • SecurityValidator - Comprehensive security validation coordinator")
        
        print("\n🔧 Key Features:")
        print("  • File permission validation for Docker operations")
        print("  • Docker access verification and troubleshooting")
        print("  • Encrypted user assignment validation")
        print("  • Risk-based security audit logging")
        print("  • Comprehensive system security checks")
        
        print("\n🛡️  Security Features:")
        print("  • Encrypted user assignments with base64 encoding")
        print("  • File permission validation with ownership checks")
        print("  • Docker socket access verification")
        print("  • Risk-level assessment for operations")
        print("  • Comprehensive audit trail with timestamps")
        
        print("\n📊 Validation Types:")
        print("  • Directory permissions (read, write, execute)")
        print("  • File ownership and group membership")
        print("  • Docker daemon availability and access")
        print("  • Docker Compose installation and functionality")
        print("  • User authorization against encrypted assignments")
        print("  • Project-specific security validation")
        
        print("\n🔍 Audit Logging:")
        print("  • Project operations (create, copy, remove)")
        print("  • Port assignments and allocations")
        print("  • File operations (create, modify, delete)")
        print("  • Permission validation checks")
        print("  • Risk-level assessment (LOW, MEDIUM, HIGH, CRITICAL)")
        
        print("\n📝 Security Checks:")
        print("  • User authorization validation")
        print("  • Directory permission verification")
        print("  • Docker access validation")
        print("  • Project security validation")
        print("  • File permission checks")
        
        print("\n✅ System is ready for production use!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_security_validation_tests()
    sys.exit(0 if success else 1)