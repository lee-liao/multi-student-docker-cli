#!/usr/bin/env python3
"""
Version Management and Update System
Handles version checking, updates, and compatibility validation.
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class VersionInfo:
    """Version information structure"""
    current: str
    latest: str
    is_outdated: bool
    update_available: bool
    compatibility_status: str
    release_notes: Optional[str] = None
    update_url: Optional[str] = None

class VersionManager:
    """Manages version checking and updates"""
    
    def __init__(self):
        self.current_version = self._get_current_version()
        self.version_file = Path(__file__).parent.parent / "VERSION"
        self.update_check_file = Path.home() / ".multi-student-docker" / "last_update_check"
        self.config_dir = Path.home() / ".multi-student-docker"
        self.config_dir.mkdir(exist_ok=True)
        
        # Update configuration
        self.update_check_interval = timedelta(days=7)  # Check weekly
        self.github_api_url = "https://api.github.com/repos/your-org/multi-student-docker-compose/releases/latest"
        self.github_releases_url = "https://github.com/your-org/multi-student-docker-compose/releases"
    
    def _get_current_version(self) -> str:
        """Get current version from VERSION file or default"""
        try:
            version_file = Path(__file__).parent.parent / "VERSION"
            if version_file.exists():
                return version_file.read_text().strip()
            return "1.0.0"
        except Exception:
            return "1.0.0"
    
    def get_version_info(self) -> VersionInfo:
        """Get comprehensive version information"""
        try:
            latest_version = self._get_latest_version()
            is_outdated = self._compare_versions(self.current_version, latest_version) < 0
            
            return VersionInfo(
                current=self.current_version,
                latest=latest_version,
                is_outdated=is_outdated,
                update_available=is_outdated,
                compatibility_status=self._check_compatibility(),
                update_url=self.github_releases_url
            )
        except Exception as e:
            return VersionInfo(
                current=self.current_version,
                latest=self.current_version,
                is_outdated=False,
                update_available=False,
                compatibility_status="unknown",
                release_notes=f"Version check failed: {str(e)}"
            )
    
    def _get_latest_version(self) -> str:
        """Get latest version from GitHub releases"""
        try:
            with urllib.request.urlopen(self.github_api_url, timeout=10) as response:
                data = json.loads(response.read().decode())
                return data.get("tag_name", "").lstrip("v")
        except (urllib.error.URLError, json.JSONDecodeError, KeyError):
            # Fallback to current version if unable to check
            return self.current_version
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings. Returns -1, 0, or 1"""
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            for v1, v2 in zip(v1_parts, v2_parts):
                if v1 < v2:
                    return -1
                elif v1 > v2:
                    return 1
            return 0
        except ValueError:
            # If version parsing fails, assume they're equal
            return 0
    
    def _check_compatibility(self) -> str:
        """Check system compatibility"""
        issues = []
        
        # Check Python version
        if sys.version_info < (3, 8):
            issues.append("Python 3.8+ required")
        
        # Check Docker availability
        if not self._check_docker():
            issues.append("Docker not available")
        
        # Check Docker Compose availability
        if not self._check_docker_compose():
            issues.append("Docker Compose not available")
        
        if not issues:
            return "compatible"
        elif len(issues) == 1 and "Docker" in issues[0]:
            return "partial"  # Can run without Docker for some operations
        else:
            return "incompatible"
    
    def _check_docker(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(['docker', 'version'], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_docker_compose(self) -> bool:
        """Check if Docker Compose is available"""
        try:
            # Try docker-compose command
            result = subprocess.run(['docker-compose', 'version'], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                return True
            
            # Try docker compose command (newer syntax)
            result = subprocess.run(['docker', 'compose', 'version'], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def should_check_for_updates(self) -> bool:
        """Check if it's time to check for updates"""
        if not self.update_check_file.exists():
            return True
        
        try:
            last_check = datetime.fromtimestamp(self.update_check_file.stat().st_mtime)
            return datetime.now() - last_check > self.update_check_interval
        except (OSError, ValueError):
            return True
    
    def mark_update_check(self):
        """Mark that we've checked for updates"""
        try:
            self.update_check_file.touch()
        except OSError:
            pass
    
    def check_for_updates(self, force: bool = False) -> Optional[VersionInfo]:
        """Check for updates if needed"""
        if not force and not self.should_check_for_updates():
            return None
        
        version_info = self.get_version_info()
        self.mark_update_check()
        
        return version_info if version_info.update_available else None
    
    def get_update_instructions(self) -> Dict[str, str]:
        """Get platform-specific update instructions"""
        return {
            "git": "git pull origin main && pip install -r requirements.txt",
            "pip": "pip install --upgrade multi-student-docker-compose",
            "manual": f"Download latest release from {self.github_releases_url}",
            "docker": "docker pull multi-student-docker-compose:latest"
        }
    
    def validate_installation(self) -> Dict[str, Any]:
        """Validate the current installation"""
        validation_results = {
            "version": self.current_version,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "python_compatible": sys.version_info >= (3, 8),
            "docker_available": self._check_docker(),
            "docker_compose_available": self._check_docker_compose(),
            "templates_available": self._check_templates(),
            "cli_executable": self._check_cli_executable(),
            "permissions_ok": self._check_permissions(),
        }
        
        validation_results["overall_status"] = self._get_overall_status(validation_results)
        return validation_results
    
    def _check_templates(self) -> bool:
        """Check if templates are available"""
        templates_dir = Path(__file__).parent.parent / "templates"
        if not templates_dir.exists():
            return False
        
        required_templates = ["common", "rag", "agent"]
        for template in required_templates:
            template_dir = templates_dir / template
            if not template_dir.exists():
                return False
            
            compose_template = template_dir / "docker-compose.yml.template"
            if not compose_template.exists():
                return False
        
        return True
    
    def _check_cli_executable(self) -> bool:
        """Check if CLI is executable"""
        cli_file = Path(__file__).parent / "cli.py"
        return cli_file.exists() and os.access(cli_file, os.R_OK)
    
    def _check_permissions(self) -> bool:
        """Check basic file permissions"""
        try:
            # Check if we can create directories in home
            test_dir = Path.home() / ".multi-student-docker-test"
            test_dir.mkdir(exist_ok=True)
            test_dir.rmdir()
            return True
        except (OSError, PermissionError):
            return False
    
    def _get_overall_status(self, results: Dict[str, Any]) -> str:
        """Get overall installation status"""
        critical_checks = [
            "python_compatible",
            "cli_executable",
            "templates_available",
            "permissions_ok"
        ]
        
        failed_critical = [check for check in critical_checks if not results.get(check, False)]
        
        if not failed_critical:
            if results.get("docker_available") and results.get("docker_compose_available"):
                return "excellent"
            else:
                return "good"  # Can run without Docker for some operations
        elif len(failed_critical) <= 2:
            return "fair"
        else:
            return "poor"

# Convenience functions
def get_current_version() -> str:
    """Get current version"""
    manager = VersionManager()
    return manager.current_version

def check_for_updates(force: bool = False) -> Optional[VersionInfo]:
    """Check for updates"""
    manager = VersionManager()
    return manager.check_for_updates(force)

def validate_installation() -> Dict[str, Any]:
    """Validate installation"""
    manager = VersionManager()
    return manager.validate_installation()

def get_version_info() -> VersionInfo:
    """Get version information"""
    manager = VersionManager()
    return manager.get_version_info()

if __name__ == "__main__":
    # Command-line interface for version management
    import argparse
    
    parser = argparse.ArgumentParser(description="Version management for Multi-Student Docker Compose CLI")
    parser.add_argument("--check", action="store_true", help="Check for updates")
    parser.add_argument("--force", action="store_true", help="Force update check")
    parser.add_argument("--validate", action="store_true", help="Validate installation")
    parser.add_argument("--version", action="store_true", help="Show version information")
    
    args = parser.parse_args()
    
    manager = VersionManager()
    
    if args.version:
        version_info = manager.get_version_info()
        print(f"Current Version: {version_info.current}")
        print(f"Latest Version: {version_info.latest}")
        print(f"Update Available: {version_info.update_available}")
        print(f"Compatibility: {version_info.compatibility_status}")
    
    elif args.validate:
        results = manager.validate_installation()
        print("Installation Validation Results:")
        print(f"Overall Status: {results['overall_status'].upper()}")
        print(f"Version: {results['version']}")
        print(f"Python: {results['python_version']} ({'✓' if results['python_compatible'] else '✗'})")
        print(f"Docker: {'✓' if results['docker_available'] else '✗'}")
        print(f"Docker Compose: {'✓' if results['docker_compose_available'] else '✗'}")
        print(f"Templates: {'✓' if results['templates_available'] else '✗'}")
        print(f"CLI Executable: {'✓' if results['cli_executable'] else '✗'}")
        print(f"Permissions: {'✓' if results['permissions_ok'] else '✗'}")
    
    elif args.check:
        update_info = manager.check_for_updates(args.force)
        if update_info:
            print(f"Update available: {update_info.latest}")
            print(f"Current version: {update_info.current}")
            print(f"Update URL: {update_info.update_url}")
        else:
            print("No updates available or check not needed")
    
    else:
        print(f"Multi-Student Docker Compose CLI v{manager.current_version}")
        print("Use --help for available options")