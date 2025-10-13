#!/usr/bin/env python3
"""
Security Validation and Authorization System
Provides file permission validation, login ID authorization checking,
and enhanced security logging for the multi-student Docker environment.
"""

import os
import stat
import hashlib
import json
import base64
import platform
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import subprocess

# Cross-platform imports
try:
    import pwd
    import grp
    HAS_UNIX_MODULES = True
except ImportError:
    # Windows doesn't have pwd/grp modules
    HAS_UNIX_MODULES = False

from src.security.secure_logger import SecureLogger
from src.utils.error_handling import (
    PermissionError as CLIPermissionError,
    ResourceUnavailableError,
    ErrorContext
)


@dataclass
class FilePermissionCheck:
    """Result of file permission validation"""
    path: str
    exists: bool
    readable: bool
    writable: bool
    executable: bool
    owner: str
    group: str
    permissions: str
    issues: List[str]
    recommendations: List[str]


@dataclass
class DockerAccessCheck:
    """Result of Docker access validation"""
    docker_available: bool
    docker_version: Optional[str]
    compose_available: bool
    compose_version: Optional[str]
    user_in_docker_group: bool
    can_run_docker: bool
    issues: List[str]
    recommendations: List[str]


@dataclass
class SecurityAuditEvent:
    """Security audit event for logging"""
    event_type: str
    user_id: str
    timestamp: str
    operation: str
    resource: Optional[str]
    success: bool
    details: Dict[str, Any]
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL


class FilePermissionValidator:
    """Validates file and directory permissions for Docker operations"""
    
    def __init__(self, logger: SecureLogger = None):
        self.logger = logger or SecureLogger()
    
    def validate_dockered_services_directory(self, base_dir: str) -> FilePermissionCheck:
        """
        Validate permissions for the main dockeredServices directory
        Args:
            base_dir: Path to dockeredServices directory
        Returns:
            FilePermissionCheck with validation results
        """
        path = Path(base_dir)
        issues = []
        recommendations = []
        
        # Check if directory exists
        if not path.exists():
            issues.append("Directory does not exist")
            recommendations.append(f"Create directory: mkdir -p {base_dir}")
            return FilePermissionCheck(
                path=str(path),
                exists=False,
                readable=False,
                writable=False,
                executable=False,
                owner="unknown",
                group="unknown",
                permissions="000",
                issues=issues,
                recommendations=recommendations
            )
        
        # Get file stats
        stat_info = path.stat()
        permissions = oct(stat_info.st_mode)[-3:]
        
        # Get owner and group info (cross-platform)
        if HAS_UNIX_MODULES:
            try:
                owner = pwd.getpwuid(stat_info.st_uid).pw_name
            except KeyError:
                owner = str(stat_info.st_uid)
            
            try:
                group = grp.getgrgid(stat_info.st_gid).gr_name
            except KeyError:
                group = str(stat_info.st_gid)
        else:
            # Windows - use environment variables
            owner = os.getenv('USERNAME', 'unknown')
            group = 'users'  # Default group on Windows
        
        # Check permissions
        readable = os.access(path, os.R_OK)
        writable = os.access(path, os.W_OK)
        executable = os.access(path, os.X_OK)
        
        # Validate requirements
        if not readable:
            issues.append("Directory is not readable")
            recommendations.append(f"Fix permissions: chmod +r {base_dir}")
        
        if not writable:
            issues.append("Directory is not writable")
            recommendations.append(f"Fix permissions: chmod +w {base_dir}")
        
        if not executable:
            issues.append("Directory is not executable (cannot enter)")
            recommendations.append(f"Fix permissions: chmod +x {base_dir}")
        
        # Check if owned by current user
        current_user = os.getenv('USER', 'unknown')
        if owner != current_user:
            issues.append(f"Directory owned by {owner}, not current user {current_user}")
            recommendations.append(f"Change ownership: chown -R {current_user}:{current_user} {base_dir}")
        
        # Check permissions are appropriate (at least 755)
        perm_value = int(permissions, 8)
        if perm_value < 0o755:
            issues.append(f"Permissions too restrictive: {permissions}")
            recommendations.append(f"Set appropriate permissions: chmod 755 {base_dir}")
        
        return FilePermissionCheck(
            path=str(path),
            exists=True,
            readable=readable,
            writable=writable,
            executable=executable,
            owner=owner,
            group=group,
            permissions=permissions,
            issues=issues,
            recommendations=recommendations
        )
    
    def validate_project_directory(self, project_path: str) -> FilePermissionCheck:
        """
        Validate permissions for a specific project directory
        Args:
            project_path: Path to project directory
        Returns:
            FilePermissionCheck with validation results
        """
        path = Path(project_path)
        issues = []
        recommendations = []
        
        if not path.exists():
            issues.append("Project directory does not exist")
            recommendations.append(f"Create project directory: mkdir -p {project_path}")
            return FilePermissionCheck(
                path=str(path),
                exists=False,
                readable=False,
                writable=False,
                executable=False,
                owner="unknown",
                group="unknown",
                permissions="000",
                issues=issues,
                recommendations=recommendations
            )
        
        # Similar validation as dockered services directory
        stat_info = path.stat()
        permissions = oct(stat_info.st_mode)[-3:]
        
        if HAS_UNIX_MODULES:
            try:
                owner = pwd.getpwuid(stat_info.st_uid).pw_name
            except KeyError:
                owner = str(stat_info.st_uid)
            
            try:
                group = grp.getgrgid(stat_info.st_gid).gr_name
            except KeyError:
                group = str(stat_info.st_gid)
        else:
            owner = os.getenv('USERNAME', 'unknown')
            group = 'users'
        
        readable = os.access(path, os.R_OK)
        writable = os.access(path, os.W_OK)
        executable = os.access(path, os.X_OK)
        
        # Validate project-specific requirements
        if not readable or not writable or not executable:
            issues.append("Insufficient permissions for project operations")
            recommendations.append(f"Fix permissions: chmod 755 {project_path}")
        
        # Check for docker-compose.yml permissions
        compose_file = path / "docker-compose.yml"
        if compose_file.exists():
            if not os.access(compose_file, os.R_OK):
                issues.append("docker-compose.yml is not readable")
                recommendations.append(f"Fix file permissions: chmod 644 {compose_file}")
        
        return FilePermissionCheck(
            path=str(path),
            exists=True,
            readable=readable,
            writable=writable,
            executable=executable,
            owner=owner,
            group=group,
            permissions=permissions,
            issues=issues,
            recommendations=recommendations
        )
    
    def validate_docker_socket_access(self) -> FilePermissionCheck:
        """
        Validate access to Docker socket
        Returns:
            FilePermissionCheck for Docker socket access
        """
        # Docker socket path is different on Windows
        if platform.system() == "Windows":
            # On Windows, Docker uses named pipes, not sockets
            issues = []
            recommendations = []
            
            # Check if Docker Desktop is running by trying docker command
            try:
                result = subprocess.run(['docker', 'version'], capture_output=True, timeout=5)
                if result.returncode == 0:
                    return FilePermissionCheck(
                        path="docker_desktop",
                        exists=True,
                        readable=True,
                        writable=True,
                        executable=False,
                        owner=os.getenv('USERNAME', 'unknown'),
                        group='users',
                        permissions="777",
                        issues=[],
                        recommendations=[]
                    )
                else:
                    issues.append("Docker Desktop not accessible")
                    recommendations.append("Start Docker Desktop")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                issues.append("Docker not found or not running")
                recommendations.append("Install and start Docker Desktop")
            
            return FilePermissionCheck(
                path="docker_desktop",
                exists=False,
                readable=False,
                writable=False,
                executable=False,
                owner="unknown",
                group="unknown",
                permissions="000",
                issues=issues,
                recommendations=recommendations
            )
        
        # Unix/Linux Docker socket validation
        docker_socket = Path("/var/run/docker.sock")
        issues = []
        recommendations = []
        
        if not docker_socket.exists():
            issues.append("Docker socket does not exist")
            recommendations.append("Start Docker daemon")
            return FilePermissionCheck(
                path=str(docker_socket),
                exists=False,
                readable=False,
                writable=False,
                executable=False,
                owner="unknown",
                group="unknown",
                permissions="000",
                issues=issues,
                recommendations=recommendations
            )
        
        # Check socket permissions
        stat_info = docker_socket.stat()
        permissions = oct(stat_info.st_mode)[-3:]
        
        if HAS_UNIX_MODULES:
            try:
                owner = pwd.getpwuid(stat_info.st_uid).pw_name
            except KeyError:
                owner = str(stat_info.st_uid)
            
            try:
                group = grp.getgrgid(stat_info.st_gid).gr_name
            except KeyError:
                group = str(stat_info.st_gid)
        else:
            owner = os.getenv('USERNAME', 'unknown')
            group = 'users'
        
        readable = os.access(docker_socket, os.R_OK)
        writable = os.access(docker_socket, os.W_OK)
        
        # Check if current user can access Docker socket
        if not readable or not writable:
            current_user = os.getenv('USER', 'unknown')
            issues.append(f"User {current_user} cannot access Docker socket")
            recommendations.append(f"Add user to docker group: sudo usermod -aG docker {current_user}")
            recommendations.append("Log out and log back in for group changes to take effect")
        
        return FilePermissionCheck(
            path=str(docker_socket),
            exists=True,
            readable=readable,
            writable=writable,
            executable=False,  # Not applicable for socket
            owner=owner,
            group=group,
            permissions=permissions,
            issues=issues,
            recommendations=recommendations
        )


class DockerAccessValidator:
    """Validates Docker access and configuration"""
    
    def __init__(self, logger: SecureLogger = None):
        self.logger = logger or SecureLogger()
    
    def validate_docker_access(self) -> DockerAccessCheck:
        """
        Comprehensive Docker access validation
        Returns:
            DockerAccessCheck with validation results
        """
        issues = []
        recommendations = []
        
        # Check Docker availability
        docker_available = False
        docker_version = None
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                docker_available = True
                docker_version = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            issues.append("Docker command not found or not responding")
            recommendations.append("Install Docker or ensure it's in PATH")
        
        # Check Docker Compose availability
        compose_available = False
        compose_version = None
        try:
            result = subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                compose_available = True
                compose_version = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Try newer docker compose syntax
            try:
                result = subprocess.run(
                    ['docker', 'compose', 'version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    compose_available = True
                    compose_version = result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                issues.append("Docker Compose not found")
                recommendations.append("Install Docker Compose or use Docker Desktop")
        
        # Check if user is in docker group (Unix/Linux only)
        user_in_docker_group = False
        current_user = os.getenv('USER') or os.getenv('USERNAME', 'unknown')
        
        if HAS_UNIX_MODULES and platform.system() != "Windows":
            try:
                docker_group = grp.getgrnam('docker')
                user_in_docker_group = current_user in docker_group.gr_mem
            except KeyError:
                issues.append("Docker group does not exist")
                recommendations.append("Ensure Docker is properly installed")
            except Exception:
                pass  # Group check failed, will be caught by Docker run test
        else:
            # On Windows, Docker Desktop handles permissions differently
            user_in_docker_group = True  # Assume true for Windows
        
        # Test if Docker can actually run
        can_run_docker = False
        if docker_available:
            try:
                result = subprocess.run(
                    ['docker', 'ps'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                can_run_docker = result.returncode == 0
                if not can_run_docker:
                    if "permission denied" in result.stderr.lower():
                        issues.append("Permission denied accessing Docker")
                        recommendations.append(f"Add user to docker group: sudo usermod -aG docker {current_user}")
                    elif "daemon" in result.stderr.lower():
                        issues.append("Docker daemon not running")
                        recommendations.append("Start Docker daemon or Docker Desktop")
                    else:
                        issues.append(f"Docker command failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                issues.append("Docker command timed out")
                recommendations.append("Check Docker daemon status")
        
        return DockerAccessCheck(
            docker_available=docker_available,
            docker_version=docker_version,
            compose_available=compose_available,
            compose_version=compose_version,
            user_in_docker_group=user_in_docker_group,
            can_run_docker=can_run_docker,
            issues=issues,
            recommendations=recommendations
        )


class LoginIDAuthorizer:
    """Handles login ID authorization against encrypted assignments"""
    
    def __init__(self, logger: SecureLogger = None):
        self.logger = logger or SecureLogger()
        self.assignments_file = Path.home() / ".dockeredServices" / ".assignments"
    
    def validate_user_authorization(self, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate user authorization against encrypted assignments
        Args:
            user_id: User login ID to validate
        Returns:
            Tuple of (authorized, user_info)
        """
        try:
            # Check if assignments file exists
            if not self.assignments_file.exists():
                self.logger.audit(
                    "authorization_check",
                    user_id,
                    details={
                        "result": "failed",
                        "reason": "assignments_file_missing",
                        "file_path": str(self.assignments_file)
                    }
                )
                return False, {"error": "Assignments file not found"}
            
            # Load and decrypt assignments
            assignments = self._load_assignments()
            if not assignments:
                self.logger.audit(
                    "authorization_check",
                    user_id,
                    details={
                        "result": "failed",
                        "reason": "assignments_load_failed"
                    }
                )
                return False, {"error": "Failed to load assignments"}
            
            # Check if user is authorized
            user_info = assignments.get(user_id)
            if not user_info:
                self.logger.audit(
                    "authorization_check",
                    user_id,
                    details={
                        "result": "failed",
                        "reason": "user_not_found"
                    }
                )
                return False, {"error": "User not authorized"}
            
            # Validate user info structure
            required_fields = ['start_port', 'end_port', 'total_ports']
            if not all(field in user_info for field in required_fields):
                self.logger.audit(
                    "authorization_check",
                    user_id,
                    details={
                        "result": "failed",
                        "reason": "invalid_user_info",
                        "missing_fields": [f for f in required_fields if f not in user_info]
                    }
                )
                return False, {"error": "Invalid user information"}
            
            # Log successful authorization
            self.logger.audit(
                "authorization_check",
                user_id,
                details={
                    "result": "success",
                    "port_range": f"{user_info['start_port']}-{user_info['end_port']}",
                    "total_ports": user_info['total_ports']
                }
            )
            
            return True, user_info
            
        except Exception as e:
            self.logger.audit(
                "authorization_check",
                user_id,
                details={
                    "result": "error",
                    "error": str(e)
                }
            )
            return False, {"error": f"Authorization check failed: {str(e)}"}
    
    def _load_assignments(self) -> Optional[Dict[str, Any]]:
        """
        Load and decrypt user assignments
        Returns:
            Dictionary of user assignments or None if failed
        """
        try:
            with open(self.assignments_file, 'r') as f:
                encrypted_data = f.read().strip()
            
            # For now, assume assignments are base64 encoded JSON
            # In production, this would use proper encryption
            try:
                decoded_data = base64.b64decode(encrypted_data).decode('utf-8')
                assignments = json.loads(decoded_data)
                return assignments
            except (ValueError, json.JSONDecodeError):
                # Try loading as plain JSON (for development)
                with open(self.assignments_file, 'r') as f:
                    assignments = json.load(f)
                return assignments
                
        except Exception as e:
            self.logger.error(f"Failed to load assignments: {e}")
            return None
    
    def create_assignments_file(self, assignments: Dict[str, Any], encrypt: bool = True):
        """
        Create encrypted assignments file
        Args:
            assignments: Dictionary of user assignments
            encrypt: Whether to encrypt the data (default: True)
        """
        try:
            # Ensure directory exists
            self.assignments_file.parent.mkdir(parents=True, exist_ok=True)
            
            if encrypt:
                # Convert to JSON and base64 encode (simple encryption for demo)
                json_data = json.dumps(assignments, indent=2)
                encrypted_data = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
                
                with open(self.assignments_file, 'w') as f:
                    f.write(encrypted_data)
            else:
                # Store as plain JSON (for development)
                with open(self.assignments_file, 'w') as f:
                    json.dump(assignments, f, indent=2)
            
            # Set restrictive permissions
            os.chmod(self.assignments_file, 0o600)
            
            self.logger.audit(
                "assignments_file_created",
                "system",
                details={
                    "file_path": str(self.assignments_file),
                    "encrypted": encrypt,
                    "user_count": len(assignments)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create assignments file: {e}")
            raise


class SecurityAuditor:
    """Enhanced security audit logging"""
    
    def __init__(self, logger: SecureLogger = None):
        self.logger = logger or SecureLogger()
    
    def log_project_operation(self, operation: str, user_id: str, project_name: str,
                            success: bool, details: Dict[str, Any] = None):
        """
        Log project operations with security context
        Args:
            operation: Operation performed (create, copy, remove, etc.)
            user_id: User performing operation
            project_name: Project involved
            success: Whether operation succeeded
            details: Additional operation details
        """
        risk_level = self._assess_risk_level(operation, success, details)
        
        event = SecurityAuditEvent(
            event_type="project_operation",
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            operation=operation,
            resource=project_name,
            success=success,
            details=details or {},
            risk_level=risk_level
        )
        
        self._log_security_event(event)
    
    def log_port_assignment(self, user_id: str, ports_assigned: List[int],
                          operation: str = "port_assignment"):
        """
        Log port assignment operations
        Args:
            user_id: User receiving port assignment
            ports_assigned: List of ports assigned
            operation: Type of port operation
        """
        event = SecurityAuditEvent(
            event_type="port_assignment",
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            operation=operation,
            resource=f"ports_{min(ports_assigned)}-{max(ports_assigned)}",
            success=True,
            details={
                "ports_assigned": ports_assigned,
                "port_count": len(ports_assigned),
                "port_range": f"{min(ports_assigned)}-{max(ports_assigned)}"
            },
            risk_level="LOW"
        )
        
        self._log_security_event(event)
    
    def log_file_operation(self, operation: str, file_path: str, user_id: str,
                         success: bool, details: Dict[str, Any] = None):
        """
        Log file operations with security implications
        Args:
            operation: File operation (create, modify, delete, etc.)
            file_path: Path to file
            user_id: User performing operation
            success: Whether operation succeeded
            details: Additional operation details
        """
        # Assess risk based on file type and operation
        risk_level = "LOW"
        if "docker-compose" in file_path.lower():
            risk_level = "MEDIUM"
        elif operation in ["delete", "modify"] and "template" in file_path.lower():
            risk_level = "HIGH"
        
        event = SecurityAuditEvent(
            event_type="file_operation",
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            operation=operation,
            resource=file_path,
            success=success,
            details=details or {},
            risk_level=risk_level
        )
        
        self._log_security_event(event)
    
    def log_permission_check(self, check_type: str, resource: str, user_id: str,
                           result: bool, issues: List[str] = None):
        """
        Log permission validation checks
        Args:
            check_type: Type of permission check
            resource: Resource being checked
            user_id: User performing check
            result: Whether check passed
            issues: List of issues found
        """
        risk_level = "HIGH" if not result else "LOW"
        
        event = SecurityAuditEvent(
            event_type="permission_check",
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            operation=check_type,
            resource=resource,
            success=result,
            details={
                "issues": issues or [],
                "issue_count": len(issues) if issues else 0
            },
            risk_level=risk_level
        )
        
        self._log_security_event(event)
    
    def _assess_risk_level(self, operation: str, success: bool, details: Dict[str, Any] = None) -> str:
        """
        Assess risk level for an operation
        Args:
            operation: Operation performed
            success: Whether operation succeeded
            details: Operation details
        Returns:
            Risk level: LOW, MEDIUM, HIGH, CRITICAL
        """
        # Failed operations are higher risk
        if not success:
            if operation in ["remove", "delete"]:
                return "HIGH"
            return "MEDIUM"
        
        # Assess based on operation type
        if operation in ["create", "copy"]:
            return "LOW"
        elif operation in ["modify", "update"]:
            return "MEDIUM"
        elif operation in ["remove", "delete"]:
            return "HIGH"
        else:
            return "LOW"
    
    def _log_security_event(self, event: SecurityAuditEvent):
        """
        Log security event to audit trail
        Args:
            event: Security audit event to log
        """
        # Log to audit trail
        self.logger.audit(
            event.event_type,
            event.user_id,
            details={
                "operation": event.operation,
                "resource": event.resource,
                "success": event.success,
                "risk_level": event.risk_level,
                "details": event.details
            }
        )
        
        # Log to main logger based on risk level
        log_message = f"Security event: {event.operation} on {event.resource} by {event.user_id}"
        
        if event.risk_level == "CRITICAL":
            self.logger.critical(log_message, extra_data=event.details)
        elif event.risk_level == "HIGH":
            self.logger.error(log_message, extra_data=event.details)
        elif event.risk_level == "MEDIUM":
            self.logger.warning(log_message, extra_data=event.details)
        else:
            self.logger.info(log_message, extra_data=event.details)


class SecurityValidator:
    """Main security validation coordinator"""
    
    def __init__(self, logger: SecureLogger = None):
        self.logger = logger or SecureLogger()
        self.file_validator = FilePermissionValidator(logger)
        self.docker_validator = DockerAccessValidator(logger)
        self.login_authorizer = LoginIDAuthorizer(logger)
        self.auditor = SecurityAuditor(logger)
    
    def validate_system_security(self, user_id: str, base_dir: str) -> Dict[str, Any]:
        """
        Comprehensive system security validation
        Args:
            user_id: User ID to validate
            base_dir: Base directory for projects
        Returns:
            Dictionary with validation results
        """
        results = {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "validations": {},
            "overall_status": "UNKNOWN",
            "critical_issues": [],
            "recommendations": []
        }
        
        # Validate user authorization
        authorized, user_info = self.login_authorizer.validate_user_authorization(user_id)
        results["validations"]["user_authorization"] = {
            "status": "PASS" if authorized else "FAIL",
            "details": user_info
        }
        if not authorized:
            results["critical_issues"].append("User not authorized")
            results["recommendations"].append("Contact administrator for access")
        
        # Validate file permissions
        dir_check = self.file_validator.validate_dockered_services_directory(base_dir)
        results["validations"]["directory_permissions"] = {
            "status": "PASS" if not dir_check.issues else "FAIL",
            "path": dir_check.path,
            "permissions": dir_check.permissions,
            "issues": dir_check.issues,
            "recommendations": dir_check.recommendations
        }
        if dir_check.issues:
            results["critical_issues"].extend(dir_check.issues)
            results["recommendations"].extend(dir_check.recommendations)
        
        # Validate Docker access
        docker_check = self.docker_validator.validate_docker_access()
        results["validations"]["docker_access"] = {
            "status": "PASS" if not docker_check.issues else "FAIL",
            "docker_available": docker_check.docker_available,
            "compose_available": docker_check.compose_available,
            "can_run_docker": docker_check.can_run_docker,
            "issues": docker_check.issues,
            "recommendations": docker_check.recommendations
        }
        if docker_check.issues:
            results["critical_issues"].extend(docker_check.issues)
            results["recommendations"].extend(docker_check.recommendations)
        
        # Determine overall status
        if results["critical_issues"]:
            results["overall_status"] = "FAIL"
        else:
            results["overall_status"] = "PASS"
        
        # Log security validation
        self.auditor.log_permission_check(
            "system_security_validation",
            base_dir,
            user_id,
            results["overall_status"] == "PASS",
            results["critical_issues"]
        )
        
        return results
    
    def validate_project_security(self, user_id: str, project_path: str) -> Dict[str, Any]:
        """
        Validate security for a specific project
        Args:
            user_id: User ID
            project_path: Path to project directory
        Returns:
            Dictionary with validation results
        """
        results = {
            "user_id": user_id,
            "project_path": project_path,
            "timestamp": datetime.now().isoformat(),
            "status": "UNKNOWN",
            "issues": [],
            "recommendations": []
        }
        
        # Validate project directory permissions
        project_check = self.file_validator.validate_project_directory(project_path)
        
        results["status"] = "PASS" if not project_check.issues else "FAIL"
        results["issues"] = project_check.issues
        results["recommendations"] = project_check.recommendations
        results["permissions"] = {
            "path": project_check.path,
            "owner": project_check.owner,
            "group": project_check.group,
            "permissions": project_check.permissions,
            "readable": project_check.readable,
            "writable": project_check.writable,
            "executable": project_check.executable
        }
        
        # Log project security validation
        self.auditor.log_permission_check(
            "project_security_validation",
            project_path,
            user_id,
            results["status"] == "PASS",
            results["issues"]
        )
        
        return results


# Convenience functions for easy integration
def validate_system_security(user_id: str, base_dir: str) -> Dict[str, Any]:
    """
    Convenience function for system security validation
    Args:
        user_id: User ID to validate
        base_dir: Base directory for projects
    Returns:
        Dictionary with validation results
    """
    validator = SecurityValidator()
    return validator.validate_system_security(user_id, base_dir)


def validate_project_security(user_id: str, project_path: str) -> Dict[str, Any]:
    """
    Convenience function for project security validation
    Args:
        user_id: User ID
        project_path: Path to project directory
    Returns:
        Dictionary with validation results
    """
    validator = SecurityValidator()
    return validator.validate_project_security(user_id, project_path)


def audit_project_operation(operation: str, user_id: str, project_name: str,
                          success: bool, details: Dict[str, Any] = None):
    """
    Convenience function for auditing project operations
    Args:
        operation: Operation performed
        user_id: User performing operation
        project_name: Project involved
        success: Whether operation succeeded
        details: Additional operation details
    """
    auditor = SecurityAuditor()
    auditor.log_project_operation(operation, user_id, project_name, success, details)


def audit_port_assignment(user_id: str, ports_assigned: List[int]):
    """
    Convenience function for auditing port assignments
    Args:
        user_id: User receiving port assignment
        ports_assigned: List of ports assigned
    """
    auditor = SecurityAuditor()
    auditor.log_port_assignment(user_id, ports_assigned)