#!/usr/bin/env python3
"""
Comprehensive Test Suite for Error Handling System
Tests custom exceptions, error recovery, logging, and CLI integration.
"""

import unittest
import tempfile
import os
import json
import logging
from unittest.mock import patch, MagicMock
from io import StringIO

from src.utils.error_handling import (
    ExitCode,
    ErrorContext,
    CLIError,
    InvalidArgumentError,
    PermissionError,
    ResourceUnavailableError,
    ProjectError,
    DockerError,
    PortAssignmentError,
    TemplateError,
    ErrorRecoveryManager,
    ErrorHandler,
    handle_cli_error
)
from src.security.secure_logger import SecureLogger, SensitiveDataSanitizer


class TestExitCodes(unittest.TestCase):
    """Test exit code enumeration"""
    
    def test_exit_code_values(self):
        """Test exit code values match requirements"""
        self.assertEqual(ExitCode.SUCCESS, 0)
        self.assertEqual(ExitCode.GENERAL_ERROR, 1)
        self.assertEqual(ExitCode.INVALID_ARGUMENTS, 2)
        self.assertEqual(ExitCode.PERMISSION_DENIED, 3)
        self.assertEqual(ExitCode.RESOURCE_UNAVAILABLE, 4)


class TestErrorContext(unittest.TestCase):
    """Test error context data structure"""
    
    def test_error_context_creation(self):
        """Test creating error context with all fields"""
        context = ErrorContext(
            operation="test_operation",
            user_id="test_user",
            project_name="test_project",
            system_info={"platform": "test"},
            timestamp="2023-01-01T00:00:00",
            recovery_suggestions=["suggestion1", "suggestion2"]
        )
        
        self.assertEqual(context.operation, "test_operation")
        self.assertEqual(context.user_id, "test_user")
        self.assertEqual(context.project_name, "test_project")
        self.assertEqual(context.system_info["platform"], "test")
        self.assertEqual(len(context.recovery_suggestions), 2)
    
    def test_error_context_minimal(self):
        """Test creating minimal error context"""
        context = ErrorContext(operation="minimal_op")
        
        self.assertEqual(context.operation, "minimal_op")
        self.assertIsNone(context.user_id)
        self.assertIsNone(context.project_name)
        self.assertIsNone(context.system_info)
        self.assertIsNone(context.recovery_suggestions)


class TestCLIError(unittest.TestCase):
    """Test base CLI error class"""
    
    def test_cli_error_creation(self):
        """Test creating CLI error with all parameters"""
        context = ErrorContext(operation="test_op", user_id="test_user")
        cause = ValueError("Original error")
        
        error = CLIError(
            message="Test error message",
            exit_code=ExitCode.INVALID_ARGUMENTS,
            context=context,
            cause=cause
        )
        
        self.assertEqual(error.message, "Test error message")
        self.assertEqual(error.exit_code, ExitCode.INVALID_ARGUMENTS)
        self.assertEqual(error.context.operation, "test_op")
        self.assertEqual(error.cause, cause)
        self.assertIsNotNone(error.timestamp)
    
    def test_cli_error_to_dict(self):
        """Test converting CLI error to dictionary"""
        context = ErrorContext(
            operation="test_op",
            user_id="test_user",
            recovery_suggestions=["Try again", "Check logs"]
        )
        
        error = CLIError("Test message", ExitCode.GENERAL_ERROR, context)
        error_dict = error.to_dict()
        
        self.assertEqual(error_dict["error_type"], "CLIError")
        self.assertEqual(error_dict["message"], "Test message")
        self.assertEqual(error_dict["exit_code"], 1)
        self.assertIn("timestamp", error_dict)
        self.assertEqual(error_dict["context"]["operation"], "test_op")
        self.assertEqual(len(error_dict["context"]["recovery_suggestions"]), 2)
    
    def test_cli_error_user_message(self):
        """Test user-friendly error message generation"""
        context = ErrorContext(
            operation="test_op",
            recovery_suggestions=["Solution 1", "Solution 2"]
        )
        
        error = CLIError("Something went wrong", context=context)
        user_message = error.get_user_message()
        
        self.assertIn("❌ Something went wrong", user_message)
        self.assertIn("💡 Suggested solutions:", user_message)
        self.assertIn("1. Solution 1", user_message)
        self.assertIn("2. Solution 2", user_message)


class TestSpecificErrors(unittest.TestCase):
    """Test specific error types"""
    
    def test_invalid_argument_error(self):
        """Test InvalidArgumentError"""
        error = InvalidArgumentError("Invalid argument provided")
        
        self.assertEqual(error.exit_code, ExitCode.INVALID_ARGUMENTS)
        self.assertIn("Invalid argument", error.message)
    
    def test_permission_error(self):
        """Test PermissionError"""
        error = PermissionError("Access denied")
        
        self.assertEqual(error.exit_code, ExitCode.PERMISSION_DENIED)
        self.assertIn("Access denied", error.message)
    
    def test_resource_unavailable_error(self):
        """Test ResourceUnavailableError"""
        error = ResourceUnavailableError("Docker not available")
        
        self.assertEqual(error.exit_code, ExitCode.RESOURCE_UNAVAILABLE)
        self.assertIn("Docker not available", error.message)
    
    def test_project_error(self):
        """Test ProjectError with project name"""
        error = ProjectError("Project not found", "test-project")
        
        self.assertEqual(error.context.project_name, "test-project")
        self.assertIn("Project not found", error.message)
    
    def test_docker_error(self):
        """Test DockerError"""
        error = DockerError("Docker daemon not running")
        
        self.assertEqual(error.exit_code, ExitCode.RESOURCE_UNAVAILABLE)
        self.assertIn("Docker daemon", error.message)
    
    def test_port_assignment_error(self):
        """Test PortAssignmentError"""
        error = PortAssignmentError("No available ports")
        
        self.assertEqual(error.exit_code, ExitCode.RESOURCE_UNAVAILABLE)
        self.assertIn("No available ports", error.message)
    
    def test_template_error(self):
        """Test TemplateError with template name"""
        error = TemplateError("Template not found", "rag")
        
        self.assertEqual(error.context.operation, "template_processing:rag")
        self.assertIn("Template not found", error.message)


class TestErrorRecoveryManager(unittest.TestCase):
    """Test error recovery management"""
    
    def setUp(self):
        """Set up test environment"""
        self.recovery_manager = ErrorRecoveryManager()
    
    def test_get_recovery_suggestions_docker(self):
        """Test recovery suggestions for Docker errors"""
        suggestions = self.recovery_manager.get_recovery_suggestions("docker_not_running")
        
        self.assertGreater(len(suggestions), 0)
        self.assertTrue(any("Docker" in suggestion for suggestion in suggestions))
    
    def test_get_recovery_suggestions_port(self):
        """Test recovery suggestions for port errors"""
        suggestions = self.recovery_manager.get_recovery_suggestions("port_conflict")
        
        self.assertGreater(len(suggestions), 0)
        self.assertTrue(any("port" in suggestion for suggestion in suggestions))
    
    def test_get_recovery_suggestions_project(self):
        """Test recovery suggestions for project errors"""
        context = ErrorContext(operation="test", project_name="test-project")
        suggestions = self.recovery_manager.get_recovery_suggestions("project_not_found", context)
        
        self.assertGreater(len(suggestions), 0)
        self.assertTrue(any("test-project" in suggestion for suggestion in suggestions))
    
    def test_enhance_error_context(self):
        """Test enhancing error with context and suggestions"""
        error = CLIError("Docker not running")
        enhanced_error = self.recovery_manager.enhance_error_context(error)
        
        self.assertIsNotNone(enhanced_error.context)
        self.assertIsNotNone(enhanced_error.context.system_info)
        self.assertIsNotNone(enhanced_error.context.recovery_suggestions)
        self.assertGreater(len(enhanced_error.context.recovery_suggestions), 0)
    
    def test_classify_error_docker(self):
        """Test error classification for Docker errors"""
        error = CLIError("Docker daemon not running")
        error_type = self.recovery_manager._classify_error(error)
        
        self.assertEqual(error_type, "docker_not_running")
    
    def test_classify_error_port(self):
        """Test error classification for port errors"""
        error = CLIError("Port 8080 already in use")
        error_type = self.recovery_manager._classify_error(error)
        
        self.assertEqual(error_type, "port_conflict")
    
    def test_classify_error_project(self):
        """Test error classification for project errors"""
        error = CLIError("Project not found")
        error_type = self.recovery_manager._classify_error(error)
        
        self.assertEqual(error_type, "project_not_found")


class TestErrorHandler(unittest.TestCase):
    """Test error handler functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.logger = MagicMock()
        self.error_handler = ErrorHandler(self.logger)
    
    def test_handle_cli_error(self):
        """Test handling CLI error"""
        error = InvalidArgumentError("Invalid project name")
        
        with patch('builtins.print') as mock_print:
            exit_code = self.error_handler.handle_error(error, "create_project", "test_user")
            
            self.assertEqual(exit_code, ExitCode.INVALID_ARGUMENTS)
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            self.assertIn("❌", call_args)
            self.assertIn("Invalid project name", call_args)
    
    def test_handle_standard_exception(self):
        """Test handling standard Python exception"""
        error = FileNotFoundError("Project directory not found")
        
        with patch('builtins.print') as mock_print:
            exit_code = self.error_handler.handle_error(error, "create_project", "test_user")
            
            self.assertEqual(exit_code, ExitCode.GENERAL_ERROR)
            mock_print.assert_called_once()
    
    def test_handle_permission_exception(self):
        """Test handling permission exception"""
        error = PermissionError("Access denied to directory")
        
        with patch('builtins.print') as mock_print:
            exit_code = self.error_handler.handle_error(error, "create_project", "test_user")
            
            self.assertEqual(exit_code, ExitCode.PERMISSION_DENIED)
    
    def test_handle_error_json_output(self):
        """Test handling error with JSON output"""
        error = InvalidArgumentError("Invalid template type")
        
        with patch('builtins.print') as mock_print:
            exit_code = self.error_handler.handle_error(error, json_output=True)
            
            self.assertEqual(exit_code, ExitCode.INVALID_ARGUMENTS)
            mock_print.assert_called_once()
            
            # Check that JSON was printed
            printed_content = mock_print.call_args[0][0]
            try:
                json_data = json.loads(printed_content)
                self.assertEqual(json_data["error_type"], "InvalidArgumentError")
                self.assertEqual(json_data["exit_code"], 2)
            except json.JSONDecodeError:
                self.fail("Output was not valid JSON")
    
    def test_convert_to_cli_error_file_not_found(self):
        """Test converting FileNotFoundError to CLIError"""
        error = FileNotFoundError("Project not found")
        cli_error = self.error_handler._convert_to_cli_error(error, "test_operation")
        
        self.assertIsInstance(cli_error, CLIError)
        self.assertIn("File not found", cli_error.message)
        self.assertEqual(cli_error.exit_code, ExitCode.GENERAL_ERROR)
    
    def test_convert_to_cli_error_value_error(self):
        """Test converting ValueError to InvalidArgumentError"""
        error = ValueError("Invalid port number")
        cli_error = self.error_handler._convert_to_cli_error(error, "test_operation")
        
        self.assertIsInstance(cli_error, InvalidArgumentError)
        self.assertIn("Invalid value", cli_error.message)
        self.assertEqual(cli_error.exit_code, ExitCode.INVALID_ARGUMENTS)


class TestSensitiveDataSanitizer(unittest.TestCase):
    """Test sensitive data sanitization"""
    
    def setUp(self):
        """Set up test environment"""
        self.sanitizer = SensitiveDataSanitizer()
    
    def test_sanitize_password_env_var(self):
        """Test sanitizing password environment variables"""
        message = "Setting PASSWORD=secret123 for database"
        sanitized = self.sanitizer.sanitize_message(message)
        
        self.assertNotIn("secret123", sanitized)
        self.assertIn("PASSWORD=***", sanitized)
    
    def test_sanitize_api_key(self):
        """Test sanitizing API keys"""
        message = "Using OPENAI_API_KEY=sk-abc123def456 for requests"
        sanitized = self.sanitizer.sanitize_message(message)
        
        self.assertNotIn("sk-abc123def456", sanitized)
        self.assertIn("OPENAI_API_KEY=sk-***", sanitized)
    
    def test_sanitize_connection_string(self):
        """Test sanitizing database connection strings"""
        message = "Connecting to postgresql://user:password@localhost:5432/db"
        sanitized = self.sanitizer.sanitize_message(message)
        
        self.assertNotIn("user:password", sanitized)
        self.assertIn("://***:***@", sanitized)
    
    def test_sanitize_json_values(self):
        """Test sanitizing JSON password values"""
        message = 'Config: {"password": "secret123", "host": "localhost"}'
        sanitized = self.sanitizer.sanitize_message(message)
        
        self.assertNotIn("secret123", sanitized)
        self.assertIn('"password": "***"', sanitized)
        self.assertIn('"host": "localhost"', sanitized)
    
    def test_sanitize_dict_sensitive_keys(self):
        """Test sanitizing dictionary with sensitive keys"""
        data = {
            "password": "secret123",
            "api_key": "key123",
            "host": "localhost",
            "port": 5432,
            "nested": {
                "secret": "nested_secret",
                "name": "test"
            }
        }
        
        sanitized = self.sanitizer.sanitize_dict(data)
        
        self.assertEqual(sanitized["password"], "***")
        self.assertEqual(sanitized["api_key"], "***")
        self.assertEqual(sanitized["host"], "localhost")
        self.assertEqual(sanitized["port"], 5432)
        self.assertEqual(sanitized["nested"]["secret"], "***")
        self.assertEqual(sanitized["nested"]["name"], "test")
    
    def test_sanitize_command_line_args(self):
        """Test sanitizing command line arguments"""
        message = "Running command: docker run --password secret123 -p 5432:5432"
        sanitized = self.sanitizer.sanitize_message(message)
        
        self.assertNotIn("secret123", sanitized)
        self.assertIn("--password ***", sanitized)


class TestSecureLogger(unittest.TestCase):
    """Test secure logging functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = SecureLogger()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_logger_initialization(self):
        """Test logger initialization"""
        self.logger.setup_logging(logging.INFO)
        
        self.assertIsNotNone(self.logger.logger)
        self.assertTrue(self.logger.log_dir.exists())
    
    def test_sensitive_data_logging(self):
        """Test that sensitive data is sanitized in logs"""
        self.logger.setup_logging(logging.DEBUG)
        
        # Capture log output
        with patch.object(self.logger.logger, 'info') as mock_info:
            self.logger.info("Database password: PASSWORD=secret123")
            
            # Check that the logged message was sanitized
            mock_info.assert_called_once()
            logged_message = mock_info.call_args[0][0]
            self.assertNotIn("secret123", logged_message)
    
    def test_audit_logging(self):
        """Test audit logging functionality"""
        self.logger.setup_logging(logging.INFO)
        
        with patch.object(self.logger.audit_logger, 'info') as mock_audit:
            self.logger.audit("user_login", "test_user", "test_project", {"action": "login"})
            
            mock_audit.assert_called_once()
            logged_data = json.loads(mock_audit.call_args[0][0])
            
            self.assertEqual(logged_data["event"], "user_login")
            self.assertEqual(logged_data["user_id"], "test_user")
            self.assertEqual(logged_data["project_name"], "test_project")
    
    def test_operation_logging(self):
        """Test operation logging with audit trail"""
        self.logger.setup_logging(logging.INFO)
        
        with patch.object(self.logger, 'info') as mock_info, \
             patch.object(self.logger, 'audit') as mock_audit:
            
            self.logger.log_operation("create_project", "test_user", "test_project", True, {"template": "rag"})
            
            mock_info.assert_called_once()
            mock_audit.assert_called_once()
            
            # Check audit call
            audit_args = mock_audit.call_args
            self.assertEqual(audit_args[1]["user_id"], "test_user")
            self.assertEqual(audit_args[1]["project_name"], "test_project")


class TestHandleCliErrorDecorator(unittest.TestCase):
    """Test the handle_cli_error decorator"""
    
    def test_decorator_with_cli_error(self):
        """Test decorator handling CLI error"""
        @handle_cli_error
        def test_function():
            raise InvalidArgumentError("Test error")
        
        with patch('error_handling.ErrorHandler') as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.handle_error.return_value = ExitCode.INVALID_ARGUMENTS
            mock_handler_class.return_value = mock_handler
            
            result = test_function()
            
            self.assertEqual(result, ExitCode.INVALID_ARGUMENTS)
            mock_handler.handle_error.assert_called_once()
    
    def test_decorator_with_standard_exception(self):
        """Test decorator handling standard exception"""
        @handle_cli_error
        def test_function():
            raise ValueError("Standard error")
        
        with patch('error_handling.ErrorHandler') as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.handle_error.return_value = ExitCode.GENERAL_ERROR
            mock_handler_class.return_value = mock_handler
            
            result = test_function()
            
            self.assertEqual(result, ExitCode.GENERAL_ERROR)
            mock_handler.handle_error.assert_called_once()
    
    def test_decorator_with_success(self):
        """Test decorator with successful function"""
        @handle_cli_error
        def test_function():
            return ExitCode.SUCCESS
        
        result = test_function()
        self.assertEqual(result, ExitCode.SUCCESS)


def run_comprehensive_tests():
    """Run all comprehensive error handling tests"""
    print("Running Comprehensive Error Handling Tests")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestExitCodes,
        TestErrorContext,
        TestCLIError,
        TestSpecificErrors,
        TestErrorRecoveryManager,
        TestErrorHandler,
        TestSensitiveDataSanitizer,
        TestSecureLogger,
        TestHandleCliErrorDecorator
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All error handling tests passed!")
        
        print("\n🛡️  Error Handling System Summary:")
        print("=" * 50)
        
        print("\n📋 Core Components:")
        print("  • Custom exception classes with standardized exit codes")
        print("  • Error recovery manager with contextual suggestions")
        print("  • Comprehensive error handler with logging integration")
        print("  • Secure logger with sensitive data sanitization")
        
        print("\n🔧 Key Features:")
        print("  • Standardized exit codes (0=success, 1=general, 2=invalid args, 3=permission, 4=resource)")
        print("  • User-friendly error messages with actionable suggestions")
        print("  • Automatic sensitive data redaction in logs")
        print("  • Context-aware error recovery strategies")
        print("  • Audit logging for security and compliance")
        
        print("\n🛡️  Safety Features:")
        print("  • Automatic sanitization of passwords, API keys, and secrets")
        print("  • Structured error context for debugging")
        print("  • Recovery suggestions based on error classification")
        print("  • Comprehensive logging with rotation")
        
        print("\n📊 Error Types Supported:")
        print("  • InvalidArgumentError - Invalid command arguments")
        print("  • PermissionError - Access denied or unauthorized")
        print("  • ResourceUnavailableError - Docker, ports, disk space")
        print("  • ProjectError - Project-specific operations")
        print("  • DockerError - Docker daemon and container issues")
        print("  • PortAssignmentError - Port allocation problems")
        print("  • TemplateError - Template processing issues")
        
        print("\n✅ System is ready for production use!")
        return True
    else:
        print(f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False


if __name__ == "__main__":
    import sys
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)