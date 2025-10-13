#!/usr/bin/env python3
"""
Comprehensive Error Handling System
Provides custom exception classes, error recovery strategies,
user-friendly error messages, and standardized exit codes.
"""

import os
import sys
import traceback
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import IntEnum
import json
from datetime import datetime


class ExitCode(IntEnum):
    """Standardized exit codes for CLI operations"""
    SUCCESS = 0              # Operation completed successfully
    GENERAL_ERROR = 1        # General error (default)
    INVALID_ARGUMENTS = 2    # Invalid command arguments or configuration
    PERMISSION_DENIED = 3    # Permission denied or unauthorized access
    RESOURCE_UNAVAILABLE = 4 # Resource unavailable (ports, disk, Docker)


@dataclass
class ErrorContext:
    """Context information for error reporting and recovery"""
    operation: str                    # Operation being performed
    user_id: Optional[str] = None    # User performing operation
    project_name: Optional[str] = None # Project involved
    system_info: Optional[Dict[str, Any]] = None # System context
    timestamp: Optional[str] = None   # When error occurred
    recovery_suggestions: List[str] = None # Suggested recovery actions


class CLIError(Exception):
    """Base CLI error with standardized exit code and context"""
    
    def __init__(self, message: str, exit_code: ExitCode = ExitCode.GENERAL_ERROR, 
                 context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
        self.context = context or ErrorContext(operation="unknown")
        self.cause = cause
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "exit_code": int(self.exit_code),
            "timestamp": self.timestamp,
            "context": {
                "operation": self.context.operation,
                "user_id": self.context.user_id,
                "project_name": self.context.project_name,
                "system_info": self.context.system_info,
                "recovery_suggestions": self.context.recovery_suggestions or []
            },
            "cause": str(self.cause) if self.cause else None
        }
    
    def get_user_message(self) -> str:
        """Get user-friendly error message with suggestions"""
        msg = f"❌ {self.message}"
        
        if self.context and self.context.recovery_suggestions:
            msg += "\n\n💡 Suggested solutions:"
            for i, suggestion in enumerate(self.context.recovery_suggestions, 1):
                msg += f"\n   {i}. {suggestion}"
        
        return msg


class InvalidArgumentError(CLIError):
    """Invalid command arguments or configuration"""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(message, ExitCode.INVALID_ARGUMENTS, context, cause)


class PermissionError(CLIError):
    """Permission denied or unauthorized access"""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(message, ExitCode.PERMISSION_DENIED, context, cause)


class ResourceUnavailableError(CLIError):
    """Resource unavailable (ports, disk space, Docker)"""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(message, ExitCode.RESOURCE_UNAVAILABLE, context, cause)


class ProjectError(CLIError):
    """Project-related errors"""
    
    def __init__(self, message: str, project_name: str, exit_code: ExitCode = ExitCode.GENERAL_ERROR, 
                 context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        if context:
            context.project_name = project_name
        else:
            context = ErrorContext(operation="project_operation", project_name=project_name)
        super().__init__(message, exit_code, context, cause)


class DockerError(CLIError):
    """Docker-related errors"""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(message, ExitCode.RESOURCE_UNAVAILABLE, context, cause)


class PortAssignmentError(CLIError):
    """Port assignment and management errors"""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(message, ExitCode.RESOURCE_UNAVAILABLE, context, cause)


class TemplateError(CLIError):
    """Template processing errors"""
    
    def __init__(self, message: str, template_name: str = None, context: Optional[ErrorContext] = None, 
                 cause: Optional[Exception] = None):
        if context:
            context.operation = f"template_processing:{template_name}" if template_name else "template_processing"
        else:
            context = ErrorContext(operation=f"template_processing:{template_name}" if template_name else "template_processing")
        super().__init__(message, ExitCode.GENERAL_ERROR, context, cause)


class ErrorRecoveryManager:
    """Manages error recovery strategies and suggestions"""
    
    def __init__(self):
        self.recovery_strategies = {
            # Docker-related errors
            "docker_not_running": [
                "Start Docker Desktop or Docker daemon",
                "Check if Docker service is running: 'systemctl status docker' (Linux) or 'docker version'",
                "Restart Docker service if needed"
            ],
            "docker_permission": [
                "Add your user to the docker group: 'sudo usermod -aG docker $USER'",
                "Log out and log back in for group changes to take effect",
                "Try running with sudo (not recommended for regular use)"
            ],
            "docker_compose_not_found": [
                "Install Docker Compose: 'pip install docker-compose' or use Docker Desktop",
                "Check if docker-compose is in PATH: 'which docker-compose'",
                "Use 'docker compose' (newer syntax) instead of 'docker-compose'"
            ],
            
            # Port-related errors
            "port_conflict": [
                "Check which process is using the port: 'netstat -tulpn | grep <port>'",
                "Stop the conflicting service or choose a different port",
                "Use the port verification tool: 'python cli.py verify-ports all'"
            ],
            "port_exhaustion": [
                "Clean up stopped projects: 'python cli.py cleanup --dry-run'",
                "Remove unused projects to free up ports",
                "Contact administrator if you need more ports"
            ],
            
            # Project-related errors
            "project_not_found": [
                "Check project name spelling and case sensitivity",
                "List available projects: 'python cli.py list-projects'",
                "Verify project location in ~/dockeredServices/"
            ],
            "project_already_exists": [
                "Choose a different project name",
                "Remove existing project if no longer needed: 'python cli.py remove-project <name>'",
                "Copy from existing project: 'python cli.py copy-project <source> <new-name>'"
            ],
            
            # Permission errors
            "file_permission": [
                "Check file permissions: 'ls -la <file>'",
                "Ensure you have write access to ~/dockeredServices/",
                "Check if files are owned by another user"
            ],
            "directory_permission": [
                "Check directory permissions: 'ls -ld <directory>'",
                "Create directory if it doesn't exist: 'mkdir -p ~/dockeredServices'",
                "Ensure proper ownership: 'chown -R $USER:$USER ~/dockeredServices'"
            ],
            
            # Template errors
            "template_not_found": [
                "Check available templates: 'python cli.py template-info <type>'",
                "Verify template files exist in templates/ directory",
                "Use supported template types: common, rag, agent"
            ],
            "template_variable_missing": [
                "Check template variable definitions",
                "Verify all required variables are provided",
                "Use template validation: 'python cli.py template-info <type> --validate'"
            ],
            
            # System resource errors
            "disk_space": [
                "Check available disk space: 'df -h'",
                "Clean up Docker resources: 'python cli.py cleanup --all --dry-run'",
                "Remove unused Docker images: 'docker image prune -a'"
            ],
            "memory_limit": [
                "Check system memory usage: 'free -h'",
                "Stop unnecessary containers: 'docker ps' and 'docker stop <container>'",
                "Increase Docker memory limits in Docker Desktop settings"
            ]
        }
    
    def get_recovery_suggestions(self, error_type: str, context: Optional[ErrorContext] = None) -> List[str]:
        """Get recovery suggestions for specific error type"""
        suggestions = self.recovery_strategies.get(error_type, [])
        
        # Add context-specific suggestions
        if context:
            if context.project_name and error_type == "project_not_found":
                suggestions.append(f"Create new project: 'python cli.py create-project {context.project_name}'")
            
            if context.user_id and "permission" in error_type:
                suggestions.append(f"Verify user '{context.user_id}' has proper permissions")
        
        return suggestions
    
    def enhance_error_context(self, error: CLIError, additional_context: Dict[str, Any] = None) -> CLIError:
        """Enhance error with additional context and recovery suggestions"""
        if not error.context:
            error.context = ErrorContext(operation="unknown")
        
        # Add system information
        if not error.context.system_info:
            error.context.system_info = self._get_system_info()
        
        # Add additional context
        if additional_context:
            if not error.context.system_info:
                error.context.system_info = {}
            error.context.system_info.update(additional_context)
        
        # Add recovery suggestions based on error type
        error_type = self._classify_error(error)
        if not error.context.recovery_suggestions:
            error.context.recovery_suggestions = self.get_recovery_suggestions(error_type, error.context)
        
        return error
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Collect system information for error context"""
        import platform
        import shutil
        
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Check Docker availability
        try:
            docker_path = shutil.which("docker")
            info["docker_available"] = docker_path is not None
            info["docker_path"] = docker_path
            
            if docker_path:
                import subprocess
                try:
                    result = subprocess.run(["docker", "version", "--format", "json"], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        docker_info = json.loads(result.stdout)
                        info["docker_version"] = docker_info.get("Client", {}).get("Version", "unknown")
                except:
                    info["docker_version"] = "unavailable"
        except:
            info["docker_available"] = False
        
        # Check Docker Compose availability
        try:
            compose_path = shutil.which("docker-compose")
            info["docker_compose_available"] = compose_path is not None
            info["docker_compose_path"] = compose_path
        except:
            info["docker_compose_available"] = False
        
        # Check disk space
        try:
            home_dir = os.path.expanduser("~")
            stat = shutil.disk_usage(home_dir)
            info["disk_space"] = {
                "total": stat.total,
                "used": stat.used,
                "free": stat.free,
                "free_gb": round(stat.free / (1024**3), 2)
            }
        except:
            info["disk_space"] = "unavailable"
        
        return info
    
    def _classify_error(self, error: CLIError) -> str:
        """Classify error to determine appropriate recovery strategy"""
        message_lower = error.message.lower()
        
        # Docker-related errors
        if "docker" in message_lower:
            if "not found" in message_lower or "command not found" in message_lower:
                return "docker_not_running"
            elif "permission" in message_lower or "denied" in message_lower:
                return "docker_permission"
            elif "compose" in message_lower:
                return "docker_compose_not_found"
        
        # Port-related errors
        if "port" in message_lower:
            if "conflict" in message_lower or "already in use" in message_lower:
                return "port_conflict"
            elif "exhausted" in message_lower or "no available" in message_lower:
                return "port_exhaustion"
        
        # Project-related errors
        if "project" in message_lower:
            if "not found" in message_lower or "does not exist" in message_lower:
                return "project_not_found"
            elif "already exists" in message_lower:
                return "project_already_exists"
        
        # Permission errors
        if "permission" in message_lower or "denied" in message_lower:
            if "file" in message_lower:
                return "file_permission"
            elif "directory" in message_lower:
                return "directory_permission"
        
        # Template errors
        if "template" in message_lower:
            if "not found" in message_lower:
                return "template_not_found"
            elif "variable" in message_lower or "missing" in message_lower:
                return "template_variable_missing"
        
        # Resource errors
        if "disk" in message_lower or "space" in message_lower:
            return "disk_space"
        elif "memory" in message_lower:
            return "memory_limit"
        
        return "general"


class ErrorHandler:
    """Central error handling and reporting system"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.recovery_manager = ErrorRecoveryManager()
    
    def handle_error(self, error: Exception, operation: str = "unknown", 
                    user_id: str = None, project_name: str = None,
                    json_output: bool = False) -> int:
        """
        Handle error with appropriate logging, user messaging, and exit code
        Returns appropriate exit code
        """
        # Convert to CLIError if needed
        if not isinstance(error, CLIError):
            cli_error = self._convert_to_cli_error(error, operation, user_id, project_name)
        else:
            cli_error = error
        
        # Enhance with context and recovery suggestions
        cli_error = self.recovery_manager.enhance_error_context(cli_error)
        
        # Log the error
        self._log_error(cli_error)
        
        # Output user message
        if json_output:
            print(json.dumps(cli_error.to_dict(), indent=2))
        else:
            print(cli_error.get_user_message())
        
        return int(cli_error.exit_code)
    
    def _convert_to_cli_error(self, error: Exception, operation: str, 
                            user_id: str = None, project_name: str = None) -> CLIError:
        """Convert standard exception to CLIError"""
        context = ErrorContext(
            operation=operation,
            user_id=user_id,
            project_name=project_name
        )
        
        error_message = str(error)
        
        # Classify based on exception type and message
        if isinstance(error, FileNotFoundError):
            if "project" in error_message.lower():
                return ProjectError(f"Project not found: {error_message}", 
                                  project_name or "unknown", ExitCode.GENERAL_ERROR, context, error)
            else:
                return CLIError(f"File not found: {error_message}", ExitCode.GENERAL_ERROR, context, error)
        
        elif isinstance(error, PermissionError):
            return PermissionError(f"Permission denied: {error_message}", context, error)
        
        elif isinstance(error, ValueError):
            return InvalidArgumentError(f"Invalid value: {error_message}", context, error)
        
        elif isinstance(error, OSError):
            if "docker" in error_message.lower():
                return DockerError(f"Docker error: {error_message}", context, error)
            else:
                return ResourceUnavailableError(f"System error: {error_message}", context, error)
        
        else:
            return CLIError(f"Unexpected error: {error_message}", ExitCode.GENERAL_ERROR, context, error)
    
    def _log_error(self, error: CLIError):
        """Log error with full context"""
        log_data = {
            "timestamp": error.timestamp,
            "error_type": error.__class__.__name__,
            "message": error.message,
            "exit_code": int(error.exit_code),
            "operation": error.context.operation if error.context else "unknown",
            "user_id": error.context.user_id if error.context else None,
            "project_name": error.context.project_name if error.context else None,
            "system_info": error.context.system_info if error.context else None
        }
        
        # Log with appropriate level
        if error.exit_code == ExitCode.SUCCESS:
            self.logger.info(f"Operation completed: {json.dumps(log_data)}")
        elif error.exit_code in [ExitCode.INVALID_ARGUMENTS, ExitCode.PERMISSION_DENIED]:
            self.logger.warning(f"User error: {json.dumps(log_data)}")
        else:
            self.logger.error(f"System error: {json.dumps(log_data)}")
        
        # Log stack trace if available
        if error.cause:
            self.logger.debug(f"Stack trace: {traceback.format_exception(type(error.cause), error.cause, error.cause.__traceback__)}")


def handle_cli_error(func):
    """Decorator for CLI command functions to handle errors consistently"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CLIError as e:
            handler = ErrorHandler()
            return handler.handle_error(e)
        except Exception as e:
            handler = ErrorHandler()
            return handler.handle_error(e, operation=func.__name__)
    
    return wrapper


# Convenience functions for common error scenarios
def raise_docker_error(message: str, context: ErrorContext = None):
    """Raise Docker-related error with appropriate context"""
    raise DockerError(message, context)


def raise_port_error(message: str, context: ErrorContext = None):
    """Raise port assignment error with appropriate context"""
    raise PortAssignmentError(message, context)


def raise_project_error(message: str, project_name: str, context: ErrorContext = None):
    """Raise project-related error with appropriate context"""
    raise ProjectError(message, project_name, context=context)


def raise_permission_error(message: str, context: ErrorContext = None):
    """Raise permission error with appropriate context"""
    raise PermissionError(message, context)


def raise_invalid_argument_error(message: str, context: ErrorContext = None):
    """Raise invalid argument error with appropriate context"""
    raise InvalidArgumentError(message, context)


def raise_resource_error(message: str, context: ErrorContext = None):
    """Raise resource unavailable error with appropriate context"""
    raise ResourceUnavailableError(message, context)