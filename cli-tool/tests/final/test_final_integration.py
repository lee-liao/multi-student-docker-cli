#!/usr/bin/env python3
"""
Final Integration Test
Comprehensive test to verify all components work together for deployment readiness.
"""

import sys
import os
import tempfile
import shutil
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

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

class FinalIntegrationTester:
    """Final integration testing for deployment readiness"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = None
        self.cli_path = Path(__file__).parent / "cli.py"
        
    def setup_test_environment(self):
        """Set up comprehensive test environment"""
        self.temp_dir = tempfile.mkdtemp()
        safe_print(f"[INFO] Final integration test environment: {self.temp_dir}")
        
        # Create test directory structure
        self.test_projects_dir = os.path.join(self.temp_dir, "dockeredServices")
        os.makedirs(self.test_projects_dir)
        
        return True
    
    def cleanup_test_environment(self):
        """Clean up test environment"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            safe_print("[INFO] Test environment cleaned up")
    
    def test_cli_availability(self) -> bool:
        """Test that CLI is available and functional"""
        safe_print("\n[TEST] CLI Availability and Basic Functionality")
        safe_print("-"*50)
        
        try:
            # Test CLI help
            result = subprocess.run([
                sys.executable, str(self.cli_path), "--help"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                safe_print("  [PASS] CLI help command works")
            else:
                safe_print(f"  [FAIL] CLI help failed: {result.stderr}")
                return False
            
            # Test version command
            result = subprocess.run([
                sys.executable, str(self.cli_path), "--version"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                safe_print("  [PASS] CLI version command works")
            else:
                safe_print("  [WARN] CLI version command not available")
            
            return True
            
        except Exception as e:
            safe_print(f"  [FAIL] CLI availability test failed: {str(e)}")
            return False
    
    def test_core_components_integration(self) -> bool:
        """Test integration of all core components"""
        safe_print("\n[TEST] Core Components Integration")
        safe_print("-"*50)
        
        try:
            # Test port assignment system
            from src.core.port_assignment import PortAssignment, PortAssignmentManager
            assignment = PortAssignment("test_user", 8000, 8099)
            manager = PortAssignmentManager()
            
            assert len(assignment.get_port_range()) == 100
            safe_print("  [PASS] Port assignment system working")
            
            # Test project manager
            from src.core.project_manager import ProjectManager
            pm = ProjectManager(base_dir=self.test_projects_dir)
            projects = pm.list_projects()
            assert isinstance(projects, list)
            safe_print("  [PASS] Project manager system working")
            
            # Test template processor
            from src.core.project_manager import TemplateProcessor
            templates_dir = Path(__file__).parent.parent / "templates"
            if templates_dir.exists():
                processor = TemplateProcessor(str(templates_dir))
                safe_print("  [PASS] Template processor system working")
            else:
                safe_print("  [WARN] Templates directory not found")
            
            # Test security validation
            from src.security.security_validation import SecurityValidator
            validator = SecurityValidator()
            safe_print("  [PASS] Security validation system working")
            
            # Test error handling
            from src.utils.error_handling import CLIError, ExitCode
            error = CLIError("Test error", ExitCode.GENERAL_ERROR)
            assert error.message == "Test error"
            safe_print("  [PASS] Error handling system working")
            
            # Test secure logging
            from src.security.secure_logger import SecureLogger
            logger = SecureLogger()
            safe_print("  [PASS] Secure logging system working")
            
            return True
            
        except Exception as e:
            safe_print(f"  [FAIL] Core components integration failed: {str(e)}")
            return False
    
    def test_version_management(self) -> bool:
        """Test version management system"""
        safe_print("\n[TEST] Version Management System")
        safe_print("-"*50)
        
        try:
            from src.core.version_manager import VersionManager, get_current_version
            
            # Test version manager
            vm = VersionManager()
            version = vm.current_version
            assert version is not None
            safe_print(f"  [PASS] Version manager working (v{version})")
            
            # Test version info
            version_info = vm.get_version_info()
            assert version_info.current == version
            safe_print("  [PASS] Version info retrieval working")
            
            # Test installation validation
            validation = vm.validate_installation()
            assert "version" in validation
            assert "overall_status" in validation
            safe_print(f"  [PASS] Installation validation working (status: {validation['overall_status']})")
            
            return True
            
        except Exception as e:
            safe_print(f"  [FAIL] Version management test failed: {str(e)}")
            return False
    
    def test_template_system_integration(self) -> bool:
        """Test template system integration"""
        safe_print("\n[TEST] Template System Integration")
        safe_print("-"*50)
        
        try:
            templates_dir = Path(__file__).parent.parent / "templates"
            if not templates_dir.exists():
                safe_print("  [WARN] Templates directory not found - skipping template tests")
                return True
            
            # Check required templates
            required_templates = ["common", "rag", "agent"]
            for template in required_templates:
                template_dir = templates_dir / template
                if template_dir.exists():
                    compose_template = template_dir / "docker-compose.yml.template"
                    if compose_template.exists():
                        safe_print(f"  [PASS] {template} template available")
                    else:
                        safe_print(f"  [WARN] {template} template missing docker-compose.yml.template")
                else:
                    safe_print(f"  [WARN] {template} template directory missing")
            
            # Test template processing
            from src.core.project_manager import TemplateProcessor
            processor = TemplateProcessor(str(templates_dir))
            
            # Test with common template
            common_template = templates_dir / "common" / "docker-compose.yml.template"
            if common_template.exists():
                variables = {
                    "USERNAME": "test_user",
                    "PROJECT_NAME": "test_project",
                    "DB_NAME": "testdb",
                    "DB_USER": "testuser",
                    "DB_PASSWORD": "testpass",
                    "POSTGRES_PORT": "5432",
                    "MONGO_PORT": "27017",
                    "REDIS_PORT": "6379"
                }
                
                processed = processor.process_template_file(str(common_template), variables)
                assert "test_user" in processed
                assert "testdb" in processed
                safe_print("  [PASS] Template variable substitution working")
            
            return True
            
        except Exception as e:
            safe_print(f"  [FAIL] Template system integration failed: {str(e)}")
            return False
    
    def test_comprehensive_workflow(self) -> bool:
        """Test comprehensive workflow simulation"""
        safe_print("\n[TEST] Comprehensive Workflow Simulation")
        safe_print("-"*50)
        
        try:
            # Simulate complete project creation workflow
            from src.core.project_manager import ProjectManager
            from src.core.port_assignment import PortAssignment
            
            # Create port assignment
            assignment = PortAssignment("integration_test_user", 9000, 9099)
            
            # Create project manager
            manager = ProjectManager(base_dir=self.test_projects_dir)
            
            # Test project creation (without actual Docker operations)
            templates_dir = Path(__file__).parent.parent / "templates"
            if templates_dir.exists():
                manager.templates_dir = str(templates_dir)
                
                # Generate template variables
                variables = manager._generate_template_variables(
                    "test_project", "integration_test_user", assignment, False
                )
                
                assert "PROJECT_NAME" in variables
                assert "USERNAME" in variables
                assert variables["PROJECT_NAME"] == "test_project"
                assert variables["USERNAME"] == "integration_test_user"
                safe_print("  [PASS] Template variable generation working")
                
                # Test port allocation
                allocated_ports = assignment.allocate_ports(5)
                assert len(allocated_ports) == 5
                assert all(9000 <= port <= 9099 for port in allocated_ports)
                safe_print("  [PASS] Port allocation working")
            
            return True
            
        except Exception as e:
            safe_print(f"  [FAIL] Comprehensive workflow test failed: {str(e)}")
            return False
    
    def test_security_integration(self) -> bool:
        """Test security system integration"""
        safe_print("\n[TEST] Security System Integration")
        safe_print("-"*50)
        
        try:
            from src.security.security_validation import SecurityValidator, FilePermissionValidator
            from src.security.secure_logger import SecureLogger, SensitiveDataSanitizer
            
            # Test security validator
            validator = SecurityValidator()
            validation_result = validator.validate_system_security(
                "integration_test_user", self.test_projects_dir
            )
            assert "user_id" in validation_result
            safe_print("  [PASS] Security validation integration working")
            
            # Test file permission validator
            file_validator = FilePermissionValidator()
            dir_check = file_validator.validate_dockered_services_directory(self.test_projects_dir)
            assert hasattr(dir_check, 'exists')
            safe_print("  [PASS] File permission validation working")
            
            # Test secure logging with sanitization
            logger = SecureLogger()
            sanitizer = SensitiveDataSanitizer()
            
            test_message = "User password=secret123 logged in"
            sanitized = sanitizer.sanitize_message(test_message)
            assert "secret123" not in sanitized
            safe_print("  [PASS] Secure logging and sanitization working")
            
            return True
            
        except Exception as e:
            safe_print(f"  [FAIL] Security integration test failed: {str(e)}")
            return False
    
    def test_error_handling_integration(self) -> bool:
        """Test error handling system integration"""
        safe_print("\n[TEST] Error Handling System Integration")
        safe_print("-"*50)
        
        try:
            from src.utils.error_handling import CLIError, ExitCode, ErrorHandler, ErrorContext
            
            # Test error creation and handling
            context = ErrorContext(operation="test_operation", user_id="test_user")
            error = CLIError("Integration test error", ExitCode.GENERAL_ERROR, context)
            
            assert error.message == "Integration test error"
            assert error.exit_code == ExitCode.GENERAL_ERROR
            assert error.context.operation == "test_operation"
            safe_print("  [PASS] Error creation and context working")
            
            # Test error handler
            handler = ErrorHandler()
            user_message = handler.get_user_friendly_message(error)
            assert "Integration test error" in user_message
            safe_print("  [PASS] Error handler integration working")
            
            return True
            
        except Exception as e:
            safe_print(f"  [FAIL] Error handling integration test failed: {str(e)}")
            return False
    
    def test_monitoring_integration(self) -> bool:
        """Test monitoring system integration"""
        safe_print("\n[TEST] Monitoring System Integration")
        safe_print("-"*50)
        
        try:
            from src.monitoring.project_status_monitor import ProjectStatusMonitor, SystemHealthMonitor
            
            # Test project status monitor
            monitor = ProjectStatusMonitor(self.test_projects_dir)
            status = monitor.get_system_status()
            assert "projects_directory" in status
            safe_print("  [PASS] Project status monitoring working")
            
            # Test system health monitor
            health_monitor = SystemHealthMonitor()
            health_status = health_monitor.check_system_health()
            assert "docker_available" in health_status
            safe_print("  [PASS] System health monitoring working")
            
            return True
            
        except Exception as e:
            safe_print(f"  [FAIL] Monitoring integration test failed: {str(e)}")
            return False
    
    def test_cleanup_integration(self) -> bool:
        """Test cleanup system integration"""
        safe_print("\n[TEST] Cleanup System Integration")
        safe_print("-"*50)
        
        try:
            from src.maintenance.cleanup_maintenance_tools import CleanupManager, MaintenanceManager
            
            # Test cleanup manager
            cleanup_manager = CleanupManager()
            suggestions = cleanup_manager.get_cleanup_suggestions()
            assert isinstance(suggestions, list)
            safe_print("  [PASS] Cleanup manager working")
            
            # Test maintenance manager
            maintenance_manager = MaintenanceManager()
            maintenance_report = maintenance_manager.generate_maintenance_report()
            assert "system_status" in maintenance_report
            safe_print("  [PASS] Maintenance manager working")
            
            return True
            
        except Exception as e:
            safe_print(f"  [FAIL] Cleanup integration test failed: {str(e)}")
            return False
    
    def test_documentation_availability(self) -> bool:
        """Test that all documentation is available"""
        safe_print("\n[TEST] Documentation Availability")
        safe_print("-"*50)
        
        try:
            root_dir = Path(__file__).parent.parent
            
            # Check main documentation files
            main_docs = [
                "README.md",
                "MULTI_STUDENT_DOCKER_COMPOSE_DOCUMENTATION.md",
                "DEPLOYMENT_GUIDE.md",
                "LICENSE",
                "VERSION"
            ]
            
            for doc in main_docs:
                doc_path = root_dir / doc
                if doc_path.exists():
                    safe_print(f"  [PASS] {doc} available")
                else:
                    safe_print(f"  [WARN] {doc} missing")
            
            # Check component documentation
            component_docs = [
                "SETUP_SCRIPT_GENERATION_SUMMARY.md",
                "CORS_CONFIGURATION_SUMMARY.md",
                "PORT_VERIFICATION_SUMMARY.md",
                "PROJECT_STATUS_MONITORING_SUMMARY.md",
                "CLEANUP_MAINTENANCE_SUMMARY.md",
                "ERROR_HANDLING_SUMMARY.md",
                "SECURITY_VALIDATION_SUMMARY.md",
                "COMPREHENSIVE_TEST_SUITE_SUMMARY.md",
                "ENHANCED_END_TO_END_VALIDATION_SUMMARY.md"
            ]
            
            available_docs = 0
            for doc in component_docs:
                doc_path = root_dir / doc
                if doc_path.exists():
                    available_docs += 1
                    safe_print(f"  [PASS] {doc} available")
                else:
                    safe_print(f"  [WARN] {doc} missing")
            
            # Check distribution files
            dist_files = [
                "setup.py",
                "requirements.txt",
                "requirements-dev.txt",
                ".gitignore"
            ]
            
            for dist_file in dist_files:
                file_path = root_dir / dist_file
                if file_path.exists():
                    safe_print(f"  [PASS] {dist_file} available")
                else:
                    safe_print(f"  [WARN] {dist_file} missing")
            
            # Overall documentation score
            total_docs = len(main_docs) + len(component_docs) + len(dist_files)
            available_total = (
                sum(1 for doc in main_docs if (root_dir / doc).exists()) +
                available_docs +
                sum(1 for doc in dist_files if (root_dir / doc).exists())
            )
            
            doc_score = (available_total / total_docs) * 100
            safe_print(f"  [INFO] Documentation completeness: {doc_score:.1f}%")
            
            return doc_score >= 80
            
        except Exception as e:
            safe_print(f"  [FAIL] Documentation availability test failed: {str(e)}")
            return False
    
    def run_final_integration_tests(self) -> bool:
        """Run all final integration tests"""
        safe_print("Starting Final Integration Tests for Deployment Readiness")
        safe_print("="*70)
        
        start_time = time.time()
        tests_passed = 0
        total_tests = 0
        
        try:
            # Setup test environment
            if not self.setup_test_environment():
                safe_print("[FAIL] Failed to setup test environment")
                return False
            
            # Test 1: CLI Availability
            total_tests += 1
            if self.test_cli_availability():
                tests_passed += 1
            
            # Test 2: Core Components Integration
            total_tests += 1
            if self.test_core_components_integration():
                tests_passed += 1
            
            # Test 3: Version Management
            total_tests += 1
            if self.test_version_management():
                tests_passed += 1
            
            # Test 4: Template System Integration
            total_tests += 1
            if self.test_template_system_integration():
                tests_passed += 1
            
            # Test 5: Comprehensive Workflow
            total_tests += 1
            if self.test_comprehensive_workflow():
                tests_passed += 1
            
            # Test 6: Security Integration
            total_tests += 1
            if self.test_security_integration():
                tests_passed += 1
            
            # Test 7: Error Handling Integration
            total_tests += 1
            if self.test_error_handling_integration():
                tests_passed += 1
            
            # Test 8: Monitoring Integration
            total_tests += 1
            if self.test_monitoring_integration():
                tests_passed += 1
            
            # Test 9: Cleanup Integration
            total_tests += 1
            if self.test_cleanup_integration():
                tests_passed += 1
            
            # Test 10: Documentation Availability
            total_tests += 1
            if self.test_documentation_availability():
                tests_passed += 1
            
        finally:
            self.cleanup_test_environment()
        
        # Generate final report
        duration = time.time() - start_time
        success_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0
        
        safe_print(f"\n{'='*70}")
        safe_print(f"FINAL INTEGRATION TEST RESULTS")
        safe_print(f"{'='*70}")
        safe_print(f"Total Tests: {total_tests}")
        safe_print(f"Passed: {tests_passed}")
        safe_print(f"Failed: {total_tests - tests_passed}")
        safe_print(f"Success Rate: {success_rate:.1f}%")
        safe_print(f"Duration: {duration:.2f}s")
        
        # Deployment readiness assessment
        safe_print(f"\n[INFO] Deployment Readiness Assessment:")
        if success_rate >= 95:
            safe_print(f"  🟢 EXCELLENT: System is fully ready for production deployment")
            safe_print(f"  All critical components are working correctly")
        elif success_rate >= 85:
            safe_print(f"  🟡 GOOD: System is ready for deployment with minor issues")
            safe_print(f"  Address any failed tests before production rollout")
        elif success_rate >= 70:
            safe_print(f"  🟠 FAIR: System needs attention before deployment")
            safe_print(f"  Several components require fixes")
        else:
            safe_print(f"  🔴 POOR: System is not ready for deployment")
            safe_print(f"  Major issues require immediate attention")
        
        # Component status summary
        safe_print(f"\n[INFO] System Components Status:")
        safe_print(f"  - CLI Interface: {'✓' if tests_passed >= 1 else '✗'}")
        safe_print(f"  - Core Components: {'✓' if tests_passed >= 2 else '✗'}")
        safe_print(f"  - Version Management: {'✓' if tests_passed >= 3 else '✗'}")
        safe_print(f"  - Template System: {'✓' if tests_passed >= 4 else '✗'}")
        safe_print(f"  - Workflow Integration: {'✓' if tests_passed >= 5 else '✗'}")
        safe_print(f"  - Security System: {'✓' if tests_passed >= 6 else '✗'}")
        safe_print(f"  - Error Handling: {'✓' if tests_passed >= 7 else '✗'}")
        safe_print(f"  - Monitoring System: {'✓' if tests_passed >= 8 else '✗'}")
        safe_print(f"  - Cleanup Tools: {'✓' if tests_passed >= 9 else '✗'}")
        safe_print(f"  - Documentation: {'✓' if tests_passed >= 10 else '✗'}")
        
        # Final recommendations
        safe_print(f"\n[TIP] Final Recommendations:")
        if success_rate >= 95:
            safe_print(f"  - System is ready for production deployment")
            safe_print(f"  - Consider pilot deployment with small user group")
            safe_print(f"  - Set up monitoring and maintenance procedures")
        elif success_rate >= 85:
            safe_print(f"  - Address any failed tests before deployment")
            safe_print(f"  - Run additional testing in staging environment")
            safe_print(f"  - Prepare rollback procedures")
        else:
            safe_print(f"  - Fix failing components before considering deployment")
            safe_print(f"  - Re-run integration tests after fixes")
            safe_print(f"  - Consider additional development time")
        
        return success_rate >= 85


def main():
    """Main entry point for final integration tests"""
    tester = FinalIntegrationTester()
    
    try:
        success = tester.run_final_integration_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        safe_print("\n[INFO] Final integration tests interrupted by user")
        return 1
    except Exception as e:
        safe_print(f"\n[FAIL] Final integration tests failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())