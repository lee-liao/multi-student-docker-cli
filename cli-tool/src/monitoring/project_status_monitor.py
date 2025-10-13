#!/usr/bin/env python3
"""
Project Status and Monitoring System

Handles scanning of student projects, port usage tracking,
container status monitoring, and comprehensive status reporting.
"""

import os
import json
import subprocess
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from src.core.port_assignment import PortAssignment
from src.monitoring.port_verification_system import DockerComposeParser, PortMapping


@dataclass
class ContainerStatus:
    """Container status information"""
    name: str
    image: str
    status: str  # running, exited, created, etc.
    state: str   # up, down, restarting, etc.
    ports: List[str]
    created: Optional[str] = None
    started: Optional[str] = None
    health: Optional[str] = None  # healthy, unhealthy, starting, none


@dataclass
class ProjectStatus:
    """Project status information"""
    name: str
    path: str
    has_compose_file: bool
    is_running: bool
    container_count: int
    containers: List[ContainerStatus]
    port_mappings: List[PortMapping]
    ports_used: List[int]
    last_modified: Optional[str] = None
    compose_version: Optional[str] = None
    networks: List[str] = None
    volumes: List[str] = None


@dataclass
class SystemStatus:
    """Overall system status"""
    docker_available: bool
    docker_version: Optional[str]
    compose_available: bool
    compose_version: Optional[str]
    total_containers: int
    running_containers: int
    total_networks: int
    total_volumes: int
    disk_usage: Optional[Dict[str, Any]] = None


@dataclass
class PortUsageSummary:
    """Port usage summary across all projects"""
    total_assigned_ports: int
    total_used_ports: int
    available_ports: int
    usage_percentage: float
    port_ranges: List[str]
    projects_by_port_usage: List[Tuple[str, int]]
    unused_ports: List[int]
    port_conflicts: List[Dict[str, Any]]


@dataclass
class MonitoringReport:
    """Complete monitoring report"""
    timestamp: str
    username: str
    system_status: SystemStatus
    port_usage: PortUsageSummary
    projects: List[ProjectStatus]
    total_projects: int
    running_projects: int
    warnings: List[str]
    recommendations: List[str]


class ProjectScanner:
    """Scans and analyzes Docker Compose projects"""
    
    def __init__(self, base_dir: str = None):
        """
        Initialize project scanner
        
        Args:
            base_dir: Base directory to scan (default: ~/dockeredServices)
        """
        self.base_dir = base_dir or os.path.expanduser("~/dockeredServices")
        self.parser = DockerComposeParser()
    
    def scan_projects(self) -> List[ProjectStatus]:
        """
        Scan all projects in the base directory
        
        Returns:
            List of ProjectStatus objects
        """
        projects = []
        
        if not os.path.exists(self.base_dir):
            return projects
        
        for item in os.listdir(self.base_dir):
            project_path = os.path.join(self.base_dir, item)
            
            if os.path.isdir(project_path):
                project_status = self._analyze_project(item, project_path)
                if project_status:
                    projects.append(project_status)
        
        return projects
    
    def _analyze_project(self, project_name: str, project_path: str) -> Optional[ProjectStatus]:
        """Analyze a single project directory"""
        compose_file = os.path.join(project_path, "docker-compose.yml")
        has_compose_file = os.path.exists(compose_file)
        
        if not has_compose_file:
            # Skip directories without docker-compose.yml
            return None
        
        # Parse port mappings
        port_mappings = []
        ports_used = []
        compose_version = None
        
        try:
            port_mappings = self.parser.parse_compose_file(compose_file)
            ports_used = [mapping.host_port for mapping in port_mappings]
            
            # Get compose file version
            with open(compose_file, 'r') as f:
                content = f.read()
                if 'version:' in content:
                    for line in content.split('\n'):
                        if line.strip().startswith('version:'):
                            compose_version = line.split(':')[1].strip().strip('"\'')
                            break
        except Exception:
            # Continue even if parsing fails
            pass
        
        # Get container status
        containers = self._get_container_status(project_name)
        is_running = any(c.status == 'running' for c in containers)
        
        # Get file modification time
        last_modified = None
        try:
            stat = os.stat(compose_file)
            last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
        except Exception:
            pass
        
        # Get networks and volumes
        networks = self._get_project_networks(project_name)
        volumes = self._get_project_volumes(project_name)
        
        return ProjectStatus(
            name=project_name,
            path=project_path,
            has_compose_file=has_compose_file,
            is_running=is_running,
            container_count=len(containers),
            containers=containers,
            port_mappings=port_mappings,
            ports_used=ports_used,
            last_modified=last_modified,
            compose_version=compose_version,
            networks=networks,
            volumes=volumes
        )
    
    def _get_container_status(self, project_name: str) -> List[ContainerStatus]:
        """Get container status for a project"""
        containers = []
        
        try:
            # Use docker-compose ps to get container status
            result = subprocess.run(
                ['docker-compose', 'ps', '--format', 'json'],
                cwd=os.path.join(self.base_dir, project_name),
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse JSON output (one JSON object per line)
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            container_data = json.loads(line)
                            containers.append(ContainerStatus(
                                name=container_data.get('Name', ''),
                                image=container_data.get('Image', ''),
                                status=container_data.get('State', ''),
                                state=container_data.get('Status', ''),
                                ports=container_data.get('Publishers', []),
                                created=container_data.get('CreatedAt', ''),
                                health=container_data.get('Health', '')
                            ))
                        except json.JSONDecodeError:
                            continue
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            # Fallback to docker ps if docker-compose ps fails
            try:
                result = subprocess.run(
                    ['docker', 'ps', '-a', '--filter', f'label=com.docker.compose.project={project_name}', '--format', 'json'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            try:
                                container_data = json.loads(line)
                                containers.append(ContainerStatus(
                                    name=container_data.get('Names', ''),
                                    image=container_data.get('Image', ''),
                                    status=container_data.get('State', ''),
                                    state=container_data.get('Status', ''),
                                    ports=container_data.get('Ports', '').split(', ') if container_data.get('Ports') else [],
                                    created=container_data.get('CreatedAt', '')
                                ))
                            except json.JSONDecodeError:
                                continue
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                pass
        
        return containers
    
    def _get_project_networks(self, project_name: str) -> List[str]:
        """Get networks associated with a project"""
        networks = []
        
        try:
            result = subprocess.run(
                ['docker', 'network', 'ls', '--filter', f'label=com.docker.compose.project={project_name}', '--format', '{{.Name}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                networks = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        
        return networks
    
    def _get_project_volumes(self, project_name: str) -> List[str]:
        """Get volumes associated with a project"""
        volumes = []
        
        try:
            result = subprocess.run(
                ['docker', 'volume', 'ls', '--filter', f'label=com.docker.compose.project={project_name}', '--format', '{{.Name}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                volumes = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        
        return volumes


class SystemMonitor:
    """Monitors Docker system status"""
    
    def get_system_status(self) -> SystemStatus:
        """Get overall Docker system status"""
        docker_available = self._check_docker_available()
        docker_version = self._get_docker_version() if docker_available else None
        compose_available = self._check_compose_available()
        compose_version = self._get_compose_version() if compose_available else None
        
        # Get container statistics
        total_containers = 0
        running_containers = 0
        
        if docker_available:
            total_containers, running_containers = self._get_container_stats()
        
        # Get network and volume counts
        total_networks = self._get_network_count() if docker_available else 0
        total_volumes = self._get_volume_count() if docker_available else 0
        
        # Get disk usage
        disk_usage = self._get_disk_usage() if docker_available else None
        
        return SystemStatus(
            docker_available=docker_available,
            docker_version=docker_version,
            compose_available=compose_available,
            compose_version=compose_version,
            total_containers=total_containers,
            running_containers=running_containers,
            total_networks=total_networks,
            total_volumes=total_volumes,
            disk_usage=disk_usage
        )
    
    def _check_docker_available(self) -> bool:
        """Check if Docker is available and running"""
        try:
            result = subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _get_docker_version(self) -> Optional[str]:
        """Get Docker version"""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        return None
    
    def _check_compose_available(self) -> bool:
        """Check if Docker Compose is available"""
        try:
            result = subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _get_compose_version(self) -> Optional[str]:
        """Get Docker Compose version"""
        try:
            result = subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        return None
    
    def _get_container_stats(self) -> Tuple[int, int]:
        """Get container statistics"""
        total = 0
        running = 0
        
        try:
            # Get total containers
            result = subprocess.run(
                ['docker', 'ps', '-a', '--format', '{{.Status}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                statuses = result.stdout.strip().split('\n')
                total = len([s for s in statuses if s.strip()])
                running = len([s for s in statuses if s.strip().startswith('Up')])
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        
        return total, running
    
    def _get_network_count(self) -> int:
        """Get total network count"""
        try:
            result = subprocess.run(
                ['docker', 'network', 'ls', '--format', '{{.Name}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                networks = result.stdout.strip().split('\n')
                return len([n for n in networks if n.strip()])
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        
        return 0
    
    def _get_volume_count(self) -> int:
        """Get total volume count"""
        try:
            result = subprocess.run(
                ['docker', 'volume', 'ls', '--format', '{{.Name}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                volumes = result.stdout.strip().split('\n')
                return len([v for v in volumes if v.strip()])
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        
        return 0
    
    def _get_disk_usage(self) -> Optional[Dict[str, Any]]:
        """Get Docker disk usage information"""
        try:
            result = subprocess.run(
                ['docker', 'system', 'df', '--format', 'json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError):
            pass
        
        return None


class PortUsageAnalyzer:
    """Analyzes port usage across projects"""
    
    def analyze_port_usage(self, projects: List[ProjectStatus], 
                          port_assignment: PortAssignment) -> PortUsageSummary:
        """
        Analyze port usage across all projects
        
        Args:
            projects: List of project statuses
            port_assignment: Student's port assignment
            
        Returns:
            PortUsageSummary with detailed analysis
        """
        assigned_ports = set(port_assignment.all_ports)
        used_ports = set()
        projects_by_usage = []
        port_conflicts = []
        
        # Collect used ports from all projects
        port_to_projects = {}
        
        for project in projects:
            project_ports = set(project.ports_used)
            used_ports.update(project_ports)
            
            if project_ports:
                projects_by_usage.append((project.name, len(project_ports)))
            
            # Track which projects use which ports (for conflict detection)
            for port in project_ports:
                if port not in port_to_projects:
                    port_to_projects[port] = []
                port_to_projects[port].append(project.name)
        
        # Find port conflicts (ports used by multiple projects)
        for port, project_list in port_to_projects.items():
            if len(project_list) > 1:
                port_conflicts.append({
                    'port': port,
                    'projects': project_list,
                    'conflict_type': 'multiple_projects'
                })
        
        # Calculate statistics
        total_assigned = len(assigned_ports)
        total_used = len(used_ports)
        available_ports = total_assigned - total_used
        usage_percentage = (total_used / total_assigned * 100) if total_assigned > 0 else 0
        
        # Get unused ports
        unused_ports = sorted(list(assigned_ports - used_ports))
        
        # Format port ranges
        port_ranges = []
        if port_assignment.segment1_start and port_assignment.segment1_end:
            port_ranges.append(f"{port_assignment.segment1_start}-{port_assignment.segment1_end}")
        if port_assignment.has_two_segments and port_assignment.segment2_start and port_assignment.segment2_end:
            port_ranges.append(f"{port_assignment.segment2_start}-{port_assignment.segment2_end}")
        
        # Sort projects by port usage (descending)
        projects_by_usage.sort(key=lambda x: x[1], reverse=True)
        
        return PortUsageSummary(
            total_assigned_ports=total_assigned,
            total_used_ports=total_used,
            available_ports=available_ports,
            usage_percentage=usage_percentage,
            port_ranges=port_ranges,
            projects_by_port_usage=projects_by_usage,
            unused_ports=unused_ports,
            port_conflicts=port_conflicts
        )


class ProjectStatusMonitor:
    """Main project status and monitoring system"""
    
    def __init__(self, base_dir: str = None):
        """
        Initialize project status monitor
        
        Args:
            base_dir: Base directory for projects (default: ~/dockeredServices)
        """
        self.base_dir = base_dir or os.path.expanduser("~/dockeredServices")
        self.scanner = ProjectScanner(self.base_dir)
        self.system_monitor = SystemMonitor()
        self.port_analyzer = PortUsageAnalyzer()
    
    def generate_monitoring_report(self, port_assignment: PortAssignment, 
                                 username: str) -> MonitoringReport:
        """
        Generate comprehensive monitoring report
        
        Args:
            port_assignment: Student's port assignment
            username: Student's username
            
        Returns:
            Complete monitoring report
        """
        # Scan all projects
        projects = self.scanner.scan_projects()
        
        # Get system status
        system_status = self.system_monitor.get_system_status()
        
        # Analyze port usage
        port_usage = self.port_analyzer.analyze_port_usage(projects, port_assignment)
        
        # Calculate summary statistics
        total_projects = len(projects)
        running_projects = len([p for p in projects if p.is_running])
        
        # Generate warnings and recommendations
        warnings = self._generate_warnings(projects, port_usage, system_status)
        recommendations = self._generate_recommendations(projects, port_usage, system_status)
        
        return MonitoringReport(
            timestamp=datetime.now().isoformat(),
            username=username,
            system_status=system_status,
            port_usage=port_usage,
            projects=projects,
            total_projects=total_projects,
            running_projects=running_projects,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def _generate_warnings(self, projects: List[ProjectStatus], 
                          port_usage: PortUsageSummary, 
                          system_status: SystemStatus) -> List[str]:
        """Generate warning messages"""
        warnings = []
        
        # System warnings
        if not system_status.docker_available:
            warnings.append("Docker is not available or not running")
        
        if not system_status.compose_available:
            warnings.append("Docker Compose is not available")
        
        # Port usage warnings
        if port_usage.usage_percentage > 80:
            warnings.append(f"High port usage: {port_usage.usage_percentage:.1f}% of allocated ports in use")
        
        if port_usage.port_conflicts:
            warnings.append(f"Port conflicts detected: {len(port_usage.port_conflicts)} ports used by multiple projects")
        
        # Project warnings
        failed_projects = [p for p in projects if p.has_compose_file and not p.is_running and p.container_count > 0]
        if failed_projects:
            warnings.append(f"{len(failed_projects)} projects have stopped containers")
        
        return warnings
    
    def _generate_recommendations(self, projects: List[ProjectStatus], 
                                port_usage: PortUsageSummary, 
                                system_status: SystemStatus) -> List[str]:
        """Generate recommendation messages"""
        recommendations = []
        
        # Port usage recommendations
        if port_usage.usage_percentage > 90:
            recommendations.append("Consider stopping unused projects to free up ports")
            
            # Suggest specific projects to stop
            stopped_projects = [p for p in projects if not p.is_running and p.ports_used]
            if stopped_projects:
                project_names = [p.name for p in stopped_projects[:3]]
                recommendations.append(f"Consider removing stopped projects: {', '.join(project_names)}")
        
        if port_usage.port_conflicts:
            recommendations.append("Resolve port conflicts by updating docker-compose.yml files")
        
        # System recommendations
        if system_status.docker_available and system_status.total_containers > 20:
            recommendations.append("Consider cleaning up unused containers: docker container prune")
        
        if system_status.total_volumes > 10:
            recommendations.append("Consider cleaning up unused volumes: docker volume prune")
        
        # Project recommendations
        if not projects:
            recommendations.append("No projects found. Create your first project with: python cli.py create-project")
        
        return recommendations
    
    def format_status_report(self, report: MonitoringReport, detailed: bool = True) -> str:
        """
        Format monitoring report as human-readable text
        
        Args:
            report: Monitoring report to format
            detailed: Whether to include detailed information
            
        Returns:
            Formatted report string
        """
        lines = []
        
        # Header
        lines.append("📊 Project Status and Monitoring Report")
        lines.append("=" * 50)
        lines.append(f"👤 User: {report.username}")
        lines.append(f"📅 Generated: {report.timestamp}")
        lines.append("")
        
        # System Status
        lines.append("🖥️  System Status:")
        lines.append(f"   Docker: {'✅ Available' if report.system_status.docker_available else '❌ Not Available'}")
        if report.system_status.docker_version:
            lines.append(f"   Version: {report.system_status.docker_version}")
        
        lines.append(f"   Compose: {'✅ Available' if report.system_status.compose_available else '❌ Not Available'}")
        if report.system_status.compose_version:
            lines.append(f"   Version: {report.system_status.compose_version}")
        
        lines.append(f"   Containers: {report.system_status.running_containers}/{report.system_status.total_containers} running")
        lines.append("")
        
        # Port Usage Summary
        lines.append("🔌 Port Usage Summary:")
        lines.append(f"   Assigned: {report.port_usage.total_assigned_ports} ports ({', '.join(report.port_usage.port_ranges)})")
        lines.append(f"   Used: {report.port_usage.total_used_ports} ports ({report.port_usage.usage_percentage:.1f}%)")
        lines.append(f"   Available: {report.port_usage.available_ports} ports")
        
        if report.port_usage.port_conflicts:
            lines.append(f"   ⚠️  Conflicts: {len(report.port_usage.port_conflicts)} ports")
        
        lines.append("")
        
        # Project Summary
        lines.append("📋 Project Summary:")
        lines.append(f"   Total: {report.total_projects} projects")
        lines.append(f"   Running: {report.running_projects} projects")
        lines.append("")
        
        # Project Details
        if report.projects:
            lines.append("📁 Projects:")
            for project in report.projects:
                status_icon = "🟢" if project.is_running else "🔴" if project.container_count > 0 else "⚪"
                lines.append(f"   {status_icon} {project.name}")
                lines.append(f"      Containers: {project.container_count} ({'running' if project.is_running else 'stopped'})")
                
                if project.ports_used:
                    ports_str = ', '.join(map(str, sorted(project.ports_used)))
                    lines.append(f"      Ports: {ports_str}")
                
                if detailed and project.containers:
                    for container in project.containers:
                        lines.append(f"         • {container.name}: {container.status}")
            
            lines.append("")
        
        # Port Usage by Project
        if report.port_usage.projects_by_port_usage:
            lines.append("📊 Port Usage by Project:")
            for project_name, port_count in report.port_usage.projects_by_port_usage:
                lines.append(f"   {project_name}: {port_count} ports")
            lines.append("")
        
        # Warnings
        if report.warnings:
            lines.append("⚠️  Warnings:")
            for warning in report.warnings:
                lines.append(f"   • {warning}")
            lines.append("")
        
        # Recommendations
        if report.recommendations:
            lines.append("💡 Recommendations:")
            for recommendation in report.recommendations:
                lines.append(f"   • {recommendation}")
            lines.append("")
        
        return "\n".join(lines)


def generate_status_report(port_assignment: PortAssignment, username: str, 
                          base_dir: str = None) -> MonitoringReport:
    """
    Convenience function to generate status report
    
    Args:
        port_assignment: Student's port assignment
        username: Student's username
        base_dir: Base directory for projects
        
    Returns:
        MonitoringReport
    """
    monitor = ProjectStatusMonitor(base_dir)
    return monitor.generate_monitoring_report(port_assignment, username)


def get_project_status(project_name: str, base_dir: str = None) -> Optional[ProjectStatus]:
    """
    Get status for a specific project
    
    Args:
        project_name: Name of the project
        base_dir: Base directory for projects
        
    Returns:
        ProjectStatus or None if not found
    """
    scanner = ProjectScanner(base_dir)
    projects = scanner.scan_projects()
    
    for project in projects:
        if project.name == project_name:
            return project
    
    return None