#!/usr/bin/env python3
"""
Port Verification System

Handles verification of Docker Compose port configurations to ensure
students are using their assigned port ranges correctly and detect conflicts.
"""

import os
import yaml
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from pathlib import Path
from src.core.port_assignment import PortAssignment


@dataclass
class PortMapping:
    """Represents a port mapping from Docker Compose"""
    service_name: str
    host_port: int
    container_port: int
    protocol: str = "tcp"
    source_line: Optional[int] = None
    raw_mapping: Optional[str] = None


@dataclass
class PortConflict:
    """Represents a port conflict or issue"""
    port: int
    service_name: str
    issue_type: str  # 'out_of_range', 'conflict', 'duplicate', 'invalid'
    description: str
    suggestion: Optional[str] = None
    severity: str = "error"  # 'error', 'warning', 'info'


@dataclass
class VerificationResult:
    """Results of port verification"""
    is_valid: bool
    total_ports_used: int
    port_mappings: List[PortMapping]
    conflicts: List[PortConflict]
    warnings: List[str]
    suggestions: List[str]
    assigned_range_info: Dict[str, Any]


class DockerComposeParser:
    """Parses Docker Compose files to extract port mappings"""
    
    def __init__(self):
        """Initialize Docker Compose parser"""
        # Regex patterns for port mapping formats
        self.port_patterns = [
            re.compile(r'^(\d+):(\d+)(?:/(tcp|udp))?$'),           # "8080:80" or "8080:80/tcp"
            re.compile(r'^(\d+):(\d+):(\d+)(?:/(tcp|udp))?$'),     # "127.0.0.1:8080:80"
            re.compile(r'^(\d+\.\d+\.\d+\.\d+):(\d+):(\d+)(?:/(tcp|udp))?$'),  # "192.168.1.1:8080:80"
        ]
    
    def parse_compose_file(self, compose_file_path: str) -> List[PortMapping]:
        """
        Parse Docker Compose file and extract port mappings
        
        Args:
            compose_file_path: Path to docker-compose.yml file
            
        Returns:
            List of PortMapping objects
        """
        if not os.path.exists(compose_file_path):
            raise FileNotFoundError(f"Docker Compose file not found: {compose_file_path}")
        
        try:
            with open(compose_file_path, 'r', encoding='utf-8') as f:
                compose_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in Docker Compose file: {e}")
        
        port_mappings = []
        
        # Extract services section
        services = compose_data.get('services', {})
        
        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                continue
            
            # Parse ports section
            ports = service_config.get('ports', [])
            if ports:
                port_mappings.extend(self._parse_ports_section(service_name, ports))
        
        return port_mappings
    
    def _parse_ports_section(self, service_name: str, ports: List) -> List[PortMapping]:
        """Parse the ports section of a service"""
        port_mappings = []
        
        for port_entry in ports:
            if isinstance(port_entry, str):
                # String format: "8080:80" or "8080:80/tcp"
                mapping = self._parse_port_string(service_name, port_entry)
                if mapping:
                    port_mappings.append(mapping)
            
            elif isinstance(port_entry, dict):
                # Object format with target, published, protocol
                mapping = self._parse_port_object(service_name, port_entry)
                if mapping:
                    port_mappings.append(mapping)
            
            elif isinstance(port_entry, int):
                # Just a port number - maps to same port
                port_mappings.append(PortMapping(
                    service_name=service_name,
                    host_port=port_entry,
                    container_port=port_entry,
                    protocol="tcp",
                    raw_mapping=str(port_entry)
                ))
        
        return port_mappings
    
    def _parse_port_string(self, service_name: str, port_string: str) -> Optional[PortMapping]:
        """Parse port string format"""
        for pattern in self.port_patterns:
            match = pattern.match(port_string.strip())
            if match:
                groups = match.groups()
                
                if len(groups) >= 2:
                    if len(groups) == 2 or groups[2] is None:
                        # Simple format: "host:container"
                        host_port = int(groups[0])
                        container_port = int(groups[1])
                        protocol = "tcp"
                    elif len(groups) == 3:
                        # Format with protocol: "host:container/tcp"
                        host_port = int(groups[0])
                        container_port = int(groups[1])
                        protocol = groups[2] or "tcp"
                    else:
                        # Format with IP: "ip:host:container"
                        host_port = int(groups[1])
                        container_port = int(groups[2])
                        protocol = groups[3] if len(groups) > 3 and groups[3] else "tcp"
                    
                    return PortMapping(
                        service_name=service_name,
                        host_port=host_port,
                        container_port=container_port,
                        protocol=protocol,
                        raw_mapping=port_string
                    )
        
        return None
    
    def _parse_port_object(self, service_name: str, port_obj: Dict) -> Optional[PortMapping]:
        """Parse port object format"""
        target = port_obj.get('target')
        published = port_obj.get('published')
        protocol = port_obj.get('protocol', 'tcp')
        
        if target is not None and published is not None:
            return PortMapping(
                service_name=service_name,
                host_port=int(published),
                container_port=int(target),
                protocol=protocol,
                raw_mapping=str(port_obj)
            )
        
        return None


class PortVerificationSystem:
    """Main port verification system"""
    
    def __init__(self):
        """Initialize port verification system"""
        self.parser = DockerComposeParser()
    
    def verify_project_ports(self, project_dir: str, port_assignment: PortAssignment,
                           username: str) -> VerificationResult:
        """
        Verify all ports in a project directory
        
        Args:
            project_dir: Path to project directory
            port_assignment: Student's port assignment
            username: Student's username
            
        Returns:
            VerificationResult with detailed analysis
        """
        compose_file = os.path.join(project_dir, "docker-compose.yml")
        
        if not os.path.exists(compose_file):
            return VerificationResult(
                is_valid=False,
                total_ports_used=0,
                port_mappings=[],
                conflicts=[PortConflict(
                    port=0,
                    service_name="",
                    issue_type="missing_file",
                    description="docker-compose.yml file not found",
                    suggestion="Create a docker-compose.yml file in the project directory",
                    severity="error"
                )],
                warnings=["No docker-compose.yml file found"],
                suggestions=["Create a docker-compose.yml file to define your services"],
                assigned_range_info=self._get_range_info(port_assignment)
            )
        
        try:
            # Parse Docker Compose file
            port_mappings = self.parser.parse_compose_file(compose_file)
            
            # Verify port assignments
            conflicts = self._verify_port_assignments(port_mappings, port_assignment, username)
            
            # Generate warnings and suggestions
            warnings = self._generate_warnings(port_mappings, conflicts)
            suggestions = self._generate_suggestions(conflicts, port_assignment)
            
            # Determine if configuration is valid
            error_conflicts = [c for c in conflicts if c.severity == "error"]
            is_valid = len(error_conflicts) == 0
            
            return VerificationResult(
                is_valid=is_valid,
                total_ports_used=len(port_mappings),
                port_mappings=port_mappings,
                conflicts=conflicts,
                warnings=warnings,
                suggestions=suggestions,
                assigned_range_info=self._get_range_info(port_assignment)
            )
            
        except Exception as e:
            return VerificationResult(
                is_valid=False,
                total_ports_used=0,
                port_mappings=[],
                conflicts=[PortConflict(
                    port=0,
                    service_name="",
                    issue_type="parse_error",
                    description=f"Failed to parse docker-compose.yml: {str(e)}",
                    suggestion="Check docker-compose.yml syntax and format",
                    severity="error"
                )],
                warnings=[f"Failed to parse docker-compose.yml: {str(e)}"],
                suggestions=["Check docker-compose.yml syntax with 'docker-compose config'"],
                assigned_range_info=self._get_range_info(port_assignment)
            )
    
    def _verify_port_assignments(self, port_mappings: List[PortMapping],
                               port_assignment: PortAssignment, username: str) -> List[PortConflict]:
        """Verify that port assignments are within allowed ranges"""
        conflicts = []
        assigned_ports = port_assignment.all_ports
        used_ports = set()
        
        for mapping in port_mappings:
            host_port = mapping.host_port
            
            # Check for duplicate port usage
            if host_port in used_ports:
                conflicts.append(PortConflict(
                    port=host_port,
                    service_name=mapping.service_name,
                    issue_type="duplicate",
                    description=f"Port {host_port} is used by multiple services",
                    suggestion=f"Use a different port from your assigned range: {self._format_port_ranges(port_assignment)}",
                    severity="error"
                ))
            else:
                used_ports.add(host_port)
            
            # Check if port is within assigned range
            if host_port not in assigned_ports:
                conflicts.append(PortConflict(
                    port=host_port,
                    service_name=mapping.service_name,
                    issue_type="out_of_range",
                    description=f"Port {host_port} is not in your assigned range",
                    suggestion=self._suggest_alternative_port(host_port, assigned_ports, used_ports),
                    severity="error"
                ))
            
            # Check for common port conflicts
            if host_port in [22, 80, 443, 3306, 5432, 27017]:
                conflicts.append(PortConflict(
                    port=host_port,
                    service_name=mapping.service_name,
                    issue_type="system_port",
                    description=f"Port {host_port} is a common system port that may cause conflicts",
                    suggestion=f"Use a port from your assigned range: {self._format_port_ranges(port_assignment)}",
                    severity="warning"
                ))
        
        return conflicts
    
    def _suggest_alternative_port(self, invalid_port: int, assigned_ports: List[int],
                                used_ports: Set[int]) -> str:
        """Suggest an alternative port from the assigned range"""
        available_ports = [p for p in assigned_ports if p not in used_ports]
        
        if not available_ports:
            return "No available ports in your assigned range. Consider removing unused services."
        
        # Try to suggest a port close to the invalid one
        closest_port = min(available_ports, key=lambda x: abs(x - invalid_port))
        
        return f"Try using port {closest_port} instead (available in your range)"
    
    def _format_port_ranges(self, port_assignment: PortAssignment) -> str:
        """Format port ranges for display"""
        ranges = [f"{port_assignment.segment1_start}-{port_assignment.segment1_end}"]
        
        if port_assignment.has_two_segments:
            ranges.append(f"{port_assignment.segment2_start}-{port_assignment.segment2_end}")
        
        return ", ".join(ranges)
    
    def _generate_warnings(self, port_mappings: List[PortMapping],
                         conflicts: List[PortConflict]) -> List[str]:
        """Generate warning messages"""
        warnings = []
        
        # Check for high port usage
        if len(port_mappings) > 10:
            warnings.append(f"Using {len(port_mappings)} ports - consider consolidating services")
        
        # Check for warning-level conflicts
        warning_conflicts = [c for c in conflicts if c.severity == "warning"]
        for conflict in warning_conflicts:
            warnings.append(f"{conflict.service_name}: {conflict.description}")
        
        return warnings
    
    def _generate_suggestions(self, conflicts: List[PortConflict],
                           port_assignment: PortAssignment) -> List[str]:
        """Generate helpful suggestions"""
        suggestions = []
        
        error_conflicts = [c for c in conflicts if c.severity == "error"]
        
        if error_conflicts:
            suggestions.append("Fix port assignment errors before running docker-compose up")
            suggestions.append(f"Your assigned port ranges: {self._format_port_ranges(port_assignment)}")
        
        # Add specific suggestions from conflicts
        for conflict in error_conflicts:
            if conflict.suggestion:
                suggestions.append(f"{conflict.service_name}: {conflict.suggestion}")
        
        if not error_conflicts:
            suggestions.append("Port configuration looks good! You can run docker-compose up")
        
        return suggestions
    
    def _get_range_info(self, port_assignment: PortAssignment) -> Dict[str, Any]:
        """Get port assignment range information"""
        return {
            'username': port_assignment.login_id,
            'segment1_start': port_assignment.segment1_start,
            'segment1_end': port_assignment.segment1_end,
            'segment2_start': port_assignment.segment2_start,
            'segment2_end': port_assignment.segment2_end,
            'has_two_segments': port_assignment.has_two_segments,
            'total_ports': port_assignment.total_ports,
            'formatted_ranges': self._format_port_ranges(port_assignment)
        }
    
    def verify_multiple_projects(self, base_dir: str, port_assignment: PortAssignment,
                               username: str) -> Dict[str, VerificationResult]:
        """
        Verify ports across multiple projects in a directory
        
        Args:
            base_dir: Base directory containing project subdirectories
            port_assignment: Student's port assignment
            username: Student's username
            
        Returns:
            Dictionary mapping project names to verification results
        """
        results = {}
        
        if not os.path.exists(base_dir):
            return results
        
        # Find all project directories with docker-compose.yml files
        for item in os.listdir(base_dir):
            project_dir = os.path.join(base_dir, item)
            
            if os.path.isdir(project_dir):
                compose_file = os.path.join(project_dir, "docker-compose.yml")
                if os.path.exists(compose_file):
                    results[item] = self.verify_project_ports(project_dir, port_assignment, username)
        
        return results
    
    def detect_cross_project_conflicts(self, verification_results: Dict[str, VerificationResult]) -> List[PortConflict]:
        """
        Detect port conflicts across multiple projects
        
        Args:
            verification_results: Results from multiple project verifications
            
        Returns:
            List of cross-project port conflicts
        """
        conflicts = []
        port_usage = {}  # port -> [(project, service)]
        
        # Collect all port usage across projects
        for project_name, result in verification_results.items():
            for mapping in result.port_mappings:
                port = mapping.host_port
                if port not in port_usage:
                    port_usage[port] = []
                port_usage[port].append((project_name, mapping.service_name))
        
        # Find conflicts (ports used by multiple projects)
        for port, usage in port_usage.items():
            if len(usage) > 1:
                projects_services = [f"{proj}/{svc}" for proj, svc in usage]
                conflicts.append(PortConflict(
                    port=port,
                    service_name=", ".join(projects_services),
                    issue_type="cross_project_conflict",
                    description=f"Port {port} is used by multiple projects: {', '.join(projects_services)}",
                    suggestion=f"Change port assignments in one of the conflicting projects",
                    severity="error"
                ))
        
        return conflicts
    
    def generate_verification_report(self, verification_results: Dict[str, VerificationResult],
                                   cross_project_conflicts: List[PortConflict] = None) -> str:
        """
        Generate a comprehensive verification report
        
        Args:
            verification_results: Results from project verifications
            cross_project_conflicts: Cross-project conflicts (optional)
            
        Returns:
            Formatted verification report
        """
        report = []
        report.append("🔍 Port Verification Report")
        report.append("=" * 50)
        report.append("")
        
        if not verification_results:
            report.append("❌ No projects found with docker-compose.yml files")
            return "\n".join(report)
        
        # Overall summary
        total_projects = len(verification_results)
        valid_projects = sum(1 for r in verification_results.values() if r.is_valid)
        total_ports = sum(r.total_ports_used for r in verification_results.values())
        
        report.append(f"📊 Summary:")
        report.append(f"   Projects: {valid_projects}/{total_projects} valid")
        report.append(f"   Total ports used: {total_ports}")
        report.append("")
        
        # Port assignment info (from first project)
        if verification_results:
            first_result = next(iter(verification_results.values()))
            range_info = first_result.assigned_range_info
            report.append(f"🎯 Your assigned port ranges:")
            report.append(f"   {range_info['formatted_ranges']}")
            report.append(f"   Total available: {range_info['total_ports']} ports")
            report.append("")
        
        # Cross-project conflicts
        if cross_project_conflicts:
            report.append("⚠️  Cross-Project Conflicts:")
            for conflict in cross_project_conflicts:
                report.append(f"   ❌ {conflict.description}")
                if conflict.suggestion:
                    report.append(f"      💡 {conflict.suggestion}")
            report.append("")
        
        # Individual project results
        report.append("📋 Project Details:")
        for project_name, result in verification_results.items():
            status = "✅" if result.is_valid else "❌"
            report.append(f"   {status} {project_name} ({result.total_ports_used} ports)")
            
            # Show conflicts for this project
            if result.conflicts:
                for conflict in result.conflicts:
                    severity_icon = "❌" if conflict.severity == "error" else "⚠️"
                    report.append(f"      {severity_icon} {conflict.service_name}: {conflict.description}")
                    if conflict.suggestion:
                        report.append(f"         💡 {conflict.suggestion}")
            
            # Show port mappings
            if result.port_mappings:
                report.append(f"      Ports: {', '.join(str(m.host_port) for m in result.port_mappings)}")
        
        report.append("")
        
        # Suggestions
        all_suggestions = []
        for result in verification_results.values():
            all_suggestions.extend(result.suggestions)
        
        if all_suggestions:
            report.append("💡 Suggestions:")
            for suggestion in set(all_suggestions):  # Remove duplicates
                report.append(f"   • {suggestion}")
        
        return "\n".join(report)


def verify_project_ports(project_dir: str, port_assignment: PortAssignment,
                        username: str) -> VerificationResult:
    """
    Convenience function to verify ports in a single project
    
    Args:
        project_dir: Path to project directory
        port_assignment: Student's port assignment
        username: Student's username
        
    Returns:
        VerificationResult
    """
    verifier = PortVerificationSystem()
    return verifier.verify_project_ports(project_dir, port_assignment, username)


def verify_all_projects(base_dir: str, port_assignment: PortAssignment,
                       username: str) -> Tuple[Dict[str, VerificationResult], List[PortConflict]]:
    """
    Convenience function to verify all projects and detect cross-project conflicts
    
    Args:
        base_dir: Base directory containing projects
        port_assignment: Student's port assignment
        username: Student's username
        
    Returns:
        Tuple of (verification_results, cross_project_conflicts)
    """
    verifier = PortVerificationSystem()
    results = verifier.verify_multiple_projects(base_dir, port_assignment, username)
    conflicts = verifier.detect_cross_project_conflicts(results)
    return results, conflicts