"""
Secure Logger

Comprehensive logging system that automatically sanitizes sensitive data,
supports multiple verbosity levels, log rotation, and audit logging.
"""

import logging
import logging.handlers
import os
import re
import json
import platform
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


class SensitiveDataSanitizer:
    """Sanitizes sensitive data from log messages"""
    
    # Patterns for detecting sensitive data
    SENSITIVE_PATTERNS = [
        # Environment variables
        (r'PASSWORD=[\w\-!@#$%^&*()+=]+', 'PASSWORD=***'),
        (r'API_KEY=[\w\-]+', 'API_KEY=***'),
        (r'SECRET=[\w\-!@#$%^&*()+=]+', 'SECRET=***'),
        (r'TOKEN=[\w\-\.]+', 'TOKEN=***'),
        (r'POSTGRES_PASSWORD=[\w\-!@#$%^&*()+=]+', 'POSTGRES_PASSWORD=***'),
        (r'REDIS_PASSWORD=[\w\-!@#$%^&*()+=]+', 'REDIS_PASSWORD=***'),
        (r'OPENAI_API_KEY=sk-[\w\-]+', 'OPENAI_API_KEY=sk-***'),
        (r'ANTHROPIC_API_KEY=sk-ant-[\w\-]+', 'ANTHROPIC_API_KEY=sk-ant-***'),
        (r'JWT_SECRET=[\w\-!@#$%^&*()+=]+', 'JWT_SECRET=***'),
        
        # Connection strings
        (r'://[^:]+:[^@]+@', '://***:***@'),
        (r'postgresql://[^:]+:[^@]+@', 'postgresql://***:***@'),
        (r'mongodb://[^:]+:[^@]+@', 'mongodb://***:***@'),
        (r'redis://[^:]+:[^@]+@', 'redis://***:***@'),
        
        # JSON/YAML values
        (r'"password"\s*:\s*"[^"]*"', '"password": "***"'),
        (r'"secret"\s*:\s*"[^"]*"', '"secret": "***"'),
        (r'"api_key"\s*:\s*"[^"]*"', '"api_key": "***"'),
        (r'"token"\s*:\s*"[^"]*"', '"token": "***"'),
        
        # Command line arguments
        (r'--password\s+\S+', '--password ***'),
        (r'--secret\s+\S+', '--secret ***'),
        (r'--api-key\s+\S+', '--api-key ***'),
        (r'-p\s+\S+', '-p ***'),
    ]
    
    # Keywords that indicate sensitive data in dictionary keys
    SENSITIVE_KEYWORDS = [
        'password', 'secret', 'key', 'token', 'auth', 'credential',
        'pass', 'pwd', 'jwt', 'api_key', 'access_key', 'private_key',
        'client_secret', 'auth_token', 'session_key'
    ]
    
    def sanitize_message(self, message: str) -> str:
        """Sanitize sensitive data from log message"""
        sanitized = message
        
        # Apply regex patterns
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data from dictionary"""
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key indicates sensitive data
            if any(keyword in key_lower for keyword in self.SENSITIVE_KEYWORDS):
                sanitized[key] = "***"
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [self.sanitize_dict(item) if isinstance(item, dict) else item for item in value]
            elif isinstance(value, str):
                sanitized[key] = self.sanitize_message(value)
            else:
                sanitized[key] = value
        
        return sanitized


class SecureFormatter(logging.Formatter):
    """Custom formatter that sanitizes sensitive data"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sanitizer = SensitiveDataSanitizer()
    
    def format(self, record):
        # Sanitize the message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self.sanitizer.sanitize_message(record.msg)
        
        # Sanitize arguments
        if hasattr(record, 'args') and record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(self.sanitizer.sanitize_message(arg))
                elif isinstance(arg, dict):
                    sanitized_args.append(self.sanitizer.sanitize_dict(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        return super().format(record)


class SecureLogger:
    """Comprehensive secure logging system"""
    
    def __init__(self):
        self.logger = None
        self.log_dir = Path.home() / ".dockeredServices" / ".logs"
        self.sanitizer = SensitiveDataSanitizer()
        self.audit_logger = None
        
        # Log file settings
        self.max_log_size = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5
        
    def setup_logging(self, level: int = logging.INFO, quiet: bool = False, verbose: bool = False):
        """Setup comprehensive logging configuration"""
        # Determine log level
        if verbose:
            level = logging.DEBUG
        elif quiet:
            level = logging.ERROR
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create main logger
        self.logger = logging.getLogger('docker_compose_cli')
        self.logger.setLevel(logging.DEBUG)  # Always capture all levels to file
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler (respects quiet/verbose flags)
        if not quiet or level <= logging.ERROR:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_formatter = SecureFormatter(
                '%(levelname)s: %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        # File handler with rotation
        log_file = self.log_dir / "cli.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_log_size,
            backupCount=self.backup_count
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = SecureFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Setup audit logging
        self._setup_audit_logging()
        
        # Log startup information
        self._log_startup_info()
    
    def _setup_audit_logging(self):
        """Setup separate audit logging for security events"""
        self.audit_logger = logging.getLogger('docker_compose_cli.audit')
        self.audit_logger.setLevel(logging.INFO)
        
        # Audit log file
        audit_file = self.log_dir / "audit.log"
        audit_handler = logging.handlers.RotatingFileHandler(
            audit_file,
            maxBytes=self.max_log_size,
            backupCount=self.backup_count
        )
        audit_formatter = SecureFormatter(
            '%(asctime)s - AUDIT - %(message)s'
        )
        audit_handler.setFormatter(audit_formatter)
        self.audit_logger.addHandler(audit_handler)
    
    def _log_startup_info(self):
        """Log system information at startup"""
        startup_info = {
            "event": "cli_startup",
            "timestamp": datetime.now().isoformat(),
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "user": os.getenv('USER', 'unknown'),
            "working_directory": os.getcwd(),
            "log_directory": str(self.log_dir)
        }
        
        self.info(f"CLI startup: {json.dumps(startup_info)}")
    
    def debug(self, message: str, extra_data: Dict[str, Any] = None):
        """Log debug message with optional structured data"""
        if self.logger:
            if extra_data:
                sanitized_data = self.sanitizer.sanitize_dict(extra_data)
                self.logger.debug(f"{message} | Data: {json.dumps(sanitized_data)}")
            else:
                self.logger.debug(message)
    
    def info(self, message: str, extra_data: Dict[str, Any] = None):
        """Log info message with optional structured data"""
        if self.logger:
            if extra_data:
                sanitized_data = self.sanitizer.sanitize_dict(extra_data)
                self.logger.info(f"{message} | Data: {json.dumps(sanitized_data)}")
            else:
                self.logger.info(message)
    
    def warning(self, message: str, extra_data: Dict[str, Any] = None):
        """Log warning message with optional structured data"""
        if self.logger:
            if extra_data:
                sanitized_data = self.sanitizer.sanitize_dict(extra_data)
                self.logger.warning(f"{message} | Data: {json.dumps(sanitized_data)}")
            else:
                self.logger.warning(message)
    
    def error(self, message: str, extra_data: Dict[str, Any] = None, exc_info: bool = False):
        """Log error message with optional structured data and exception info"""
        if self.logger:
            if extra_data:
                sanitized_data = self.sanitizer.sanitize_dict(extra_data)
                self.logger.error(f"{message} | Data: {json.dumps(sanitized_data)}", exc_info=exc_info)
            else:
                self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str, extra_data: Dict[str, Any] = None, exc_info: bool = False):
        """Log critical message with optional structured data and exception info"""
        if self.logger:
            if extra_data:
                sanitized_data = self.sanitizer.sanitize_dict(extra_data)
                self.logger.critical(f"{message} | Data: {json.dumps(sanitized_data)}", exc_info=exc_info)
            else:
                self.logger.critical(message, exc_info=exc_info)
    
    def audit(self, event: str, user_id: str = None, project_name: str = None, 
             details: Dict[str, Any] = None):
        """Log audit event for security and compliance"""
        if not self.audit_logger:
            return
        
        audit_data = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id or os.getenv('USER', 'unknown'),
            "project_name": project_name,
            "details": self.sanitizer.sanitize_dict(details) if details else None
        }
        
        self.audit_logger.info(json.dumps(audit_data))
    
    def log_operation(self, operation: str, user_id: str = None, project_name: str = None,
                     success: bool = True, details: Dict[str, Any] = None):
        """Log operation with audit trail"""
        # Regular log
        level_method = self.info if success else self.error
        status = "SUCCESS" if success else "FAILED"
        message = f"Operation {operation} {status}"
        
        if project_name:
            message += f" for project '{project_name}'"
        if user_id:
            message += f" by user '{user_id}'"
        
        level_method(message, details)
        
        # Audit log
        audit_event = f"operation_{operation.lower().replace(' ', '_')}"
        audit_details = {
            "operation": operation,
            "success": success,
            "details": details
        }
        self.audit(audit_event, user_id, project_name, audit_details)
    
    def log_port_assignment(self, user_id: str, ports_assigned: List[int], 
                           operation: str = "port_assignment"):
        """Log port assignment operations for audit"""
        self.audit(
            event=operation,
            user_id=user_id,
            details={
                "ports_assigned": ports_assigned,
                "port_count": len(ports_assigned)
            }
        )
    
    def log_project_operation(self, operation: str, project_name: str, user_id: str = None,
                             success: bool = True, details: Dict[str, Any] = None):
        """Log project-specific operations"""
        self.log_operation(
            operation=f"project_{operation}",
            user_id=user_id,
            project_name=project_name,
            success=success,
            details=details
        )
    
    def log_file_operation(self, operation: str, file_path: str, user_id: str = None,
                          success: bool = True, details: Dict[str, Any] = None):
        """Log file operations for audit"""
        audit_details = {
            "file_path": file_path,
            "operation": operation,
            "details": details
        }
        
        self.audit(
            event="file_operation",
            user_id=user_id,
            details=audit_details
        )
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics and health information"""
        stats = {
            "log_directory": str(self.log_dir),
            "log_files": [],
            "total_size": 0
        }
        
        try:
            for log_file in self.log_dir.glob("*.log*"):
                file_stats = log_file.stat()
                stats["log_files"].append({
                    "name": log_file.name,
                    "size": file_stats.st_size,
                    "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                })
                stats["total_size"] += file_stats.st_size
            
            stats["total_size_mb"] = round(stats["total_size"] / (1024 * 1024), 2)
        except Exception as e:
            self.error(f"Failed to get log stats: {e}")
        
        return stats
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        simple_formatter = logging.Formatter('%(levelname)s: %(message)s')
        
        # File handlers with rotation
        main_log_file = os.path.join(self.log_dir, 'cli-tool.log')
        error_log_file = os.path.join(self.log_dir, 'cli-tool-error.log')
        debug_log_file = os.path.join(self.log_dir, 'cli-tool-debug.log')
        
        # Main log (INFO and above)
        main_handler = logging.FileHandler(main_log_file)
        main_handler.setLevel(logging.INFO)
        main_handler.setFormatter(detailed_formatter)
        main_handler.addFilter(self._create_sanitizing_filter())
        
        # Error log (ERROR only)
        error_handler = logging.FileHandler(error_log_file)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        error_handler.addFilter(self._create_sanitizing_filter())
        
        # Debug log (DEBUG and above) - only if debug level
        if level <= logging.DEBUG:
            debug_handler = logging.FileHandler(debug_log_file)
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(detailed_formatter)
            debug_handler.addFilter(self._create_sanitizing_filter())
            self.logger.addHandler(debug_handler)
        
        # Console handler (respects level)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(simple_formatter)
        console_handler.addFilter(self._create_sanitizing_filter())
        
        # Add handlers
        self.logger.addHandler(main_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)
        
        # Log startup
        self.logger.info(f"Secure logging initialized - Level: {logging.getLevelName(level)}")
        self.logger.debug(f"Log directory: {self.log_dir}")
    
    def _create_sanitizing_filter(self):
        """Create a logging filter that sanitizes sensitive data"""
        # Capture reference to the logger instance
        logger_instance = self
        
        class SanitizingFilter(logging.Filter):
            def filter(self, record):
                # Sanitize the message
                if hasattr(record, 'msg') and record.msg:
                    record.msg = logger_instance.sanitize_message(str(record.msg))
                
                # Sanitize args if present
                if hasattr(record, 'args') and record.args:
                    sanitized_args = []
                    for arg in record.args:
                        if isinstance(arg, str):
                            sanitized_args.append(logger_instance.sanitize_message(arg))
                        elif isinstance(arg, dict):
                            sanitized_args.append(logger_instance.sanitize_dict(arg))
                        else:
                            sanitized_args.append(arg)
                    record.args = tuple(sanitized_args)
                
                return True
        
        return SanitizingFilter()
    
    def sanitize_message(self, message: str) -> str:
        """Remove sensitive data from log messages"""
        if not isinstance(message, str):
            return message
        
        sanitized = message
        
        # Apply regex patterns
        for pattern in self.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary data by redacting sensitive keys"""
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            if self.is_sensitive_key(key):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, str):
                sanitized[key] = self.sanitize_message(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def is_sensitive_key(self, key: str) -> bool:
        """Check if a key contains sensitive data"""
        if not isinstance(key, str):
            return False
        
        key_lower = key.lower()
        return any(keyword in key_lower for keyword in self.SENSITIVE_KEYWORDS)
    
    def log_operation(self, operation: str, details: Dict[str, Any]):
        """Log operation with sanitized details"""
        sanitized_details = self.sanitize_dict(details)
        self.logger.info(f"Operation: {operation}, Details: {sanitized_details}")
    
    def log_file_modification(self, file_path: str, changes: Dict[str, Any]):
        """Log file changes without exposing sensitive content"""
        safe_changes = self.sanitize_dict(changes)
        self.logger.info(f"Modified {file_path}: {safe_changes}")
    
    def info(self, message: str, *args, **kwargs):
        """Log info message with sanitization"""
        if self.logger:
            self.logger.info(message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message with sanitization"""
        if self.logger:
            self.logger.debug(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message with sanitization"""
        if self.logger:
            self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message with sanitization"""
        if self.logger:
            self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message with sanitization"""
        if self.logger:
            self.logger.critical(message, *args, **kwargs)


# Test function for the secure logger
def test_secure_logger():
    """Test the secure logger functionality"""
    logger = SecureLogger()
    logger.setup_logging(logging.DEBUG)
    
    # Test basic logging
    logger.info("Testing secure logger")
    
    # Test sensitive data sanitization
    logger.info("Database connection: postgresql://user:secret123@localhost:5432/db")
    logger.info("API configuration: OPENAI_API_KEY=sk-abc123def456")
    logger.info("Environment: PASSWORD=mysecret TOKEN=jwt123")
    
    # Test dictionary sanitization
    config = {
        'database_url': 'postgresql://user:password@localhost/db',
        'api_key': 'secret-key-123',
        'debug': True,
        'port': 5432
    }
    logger.log_operation("test_config", config)
    
    # Test file modification logging
    changes = {
        'POSTGRES_PASSWORD': 'newsecret',
        'container_name': 'test-container',
        'ports': ['4001:5432']
    }
    logger.log_file_modification('docker-compose.yml', changes)
    
    logger.info("Secure logger test completed")


if __name__ == '__main__':
    test_secure_logger()