#!/usr/bin/env python3
"""
Cleanup and Maintenance Tools System
Handles Docker resource cleanup, project-specific maintenance,
system optimization, and automated cleanup suggestions.
"""
import os
import subprocess
import json
import time
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from src.core.port_assignment import PortAssignment
from src.monitoring.project_status_monitor import ProjectStatusMonitor, ProjectStatus

@dataclass
class CleanupResult:
    """Result of a cleanup operation"""
    operation: str
    success: bool
    items_removed: int
    space_freed: Optional[str] = None
    errors: List[str] = None
    warnings: List[str] = None
    details: Optional[Dict[str, Any]] = None

@dataclass
class MaintenanceReport:
    """Maintenance operation report"""
    timestamp: str
    username: str
    operations_performed: List[CleanupResult]
    total_space_freed: Optional[str]
    recommendations: List[str]
    warnings: List[str]
    system_health_before: Dict[str, Any]
    system_health_after: Dict[str, Any]

class DockerResourceCleaner:
    """Handles Docker resource cleanup operations"""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize Docker resource cleaner
        Args:
            dry_run: If True, only show what would be cleaned without actually doing it
        """
        self.dry_run = dry_run
    
    def cleanup_containers(self, project_filter: Optional[str] = None, 
                          stopped_only: bool = True) -> CleanupResult:
        """
        Clean up Docker containers
        Args:
            project_filter: Only clean containers from specific project
            stopped_only: Only clean stopped containers (safer)
        Returns:
            CleanupResult with operation details
        """
        try:
            # Get containers to clean
            containers = self._get_containers_to_clean(project_filter, stopped_only)
            if not containers:
                return CleanupResult(
                    operation="container_cleanup",
                    success=True,
                    items_removed=0,
                    details={"message": "No containers to clean"}
                )
            
            if self.dry_run:
                return CleanupResult(
                    operation="container_cleanup",
                    success=True,
                    items_removed=len(containers),
                    details={
                        "dry_run": True,
                        "containers_to_remove": containers,
                        "message": f"Would remove {len(containers)} containers"
                    }
                )
            
            # Remove containers
            removed_count = 0
            errors = []
            for container in containers:
                try:
                    result = subprocess.run(
                        ['docker', 'rm', container['id']],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        removed_count += 1
                    else:
                        errors.append(f"Failed to remove container {container['name']}: {result.stderr}")
                except subprocess.TimeoutExpired:
                    errors.append(f"Timeout removing container {container['name']}")
                except Exception as e:
                    errors.append(f"Error removing container {container['name']}: {str(e)}")
            
            return CleanupResult(
                operation="container_cleanup",
                success=len(errors) == 0,
                items_removed=removed_count,
                errors=errors if errors else None,
                details={
                    "total_found": len(containers),
                    "successfully_removed": removed_count,
                    "failed": len(containers) - removed_count
                }
            )
        except Exception as e:
            return CleanupResult(
                operation="container_cleanup",
                success=False,
                items_removed=0,
                errors=[f"Container cleanup failed: {str(e)}"]
            )
    
    def cleanup_images(self, unused_only: bool = True, 
                      dangling_only: bool = False) -> CleanupResult:
        """
        Clean up Docker images
        Args:
            unused_only: Only remove unused images
            dangling_only: Only remove dangling images (safer)
        Returns:
            CleanupResult with operation details
        """
        try:
            if dangling_only:
                # Clean only dangling images (safest)
                cmd = ['docker', 'image', 'prune', '-f']
                operation_name = "dangling_image_cleanup"
            elif unused_only:
                # Clean unused images
                cmd = ['docker', 'image', 'prune', '-a', '-f']
                operation_name = "unused_image_cleanup"
            else:
                # This would be very aggressive - not recommended
                return CleanupResult(
                    operation="image_cleanup",
                    success=False,
                    items_removed=0,
                    errors=["Aggressive image cleanup not supported for safety"]
                )
            
            if self.dry_run:
                # Get images that would be removed
                images_info = self._get_images_info(dangling_only, unused_only)
                return CleanupResult(
                    operation=operation_name,
                    success=True,
                    items_removed=images_info['count'],
                    space_freed=images_info['size'],
                    details={
                        "dry_run": True,
                        "message": f"Would remove {images_info['count']} images, freeing {images_info['size']}"
                    }
                )
            
            # Execute cleanup
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout for image cleanup
            )
            
            if result.returncode == 0:
                # Parse output to get space freed
                space_freed = self._parse_prune_output(result.stdout)
                return CleanupResult(
                    operation=operation_name,
                    success=True,
                    items_removed=space_freed['count'],
                    space_freed=space_freed['size'],
                    details={"output": result.stdout.strip()}
                )
            else:
                return CleanupResult(
                    operation=operation_name,
                    success=False,
                    items_removed=0,
                    errors=[f"Image cleanup failed: {result.stderr}"]
                )
        except subprocess.TimeoutExpired:
            return CleanupResult(
                operation="image_cleanup",
                success=False,
                items_removed=0,
                errors=["Image cleanup timed out after 5 minutes"]
            )
        except Exception as e:
            return CleanupResult(
                operation="image_cleanup",
                success=False,
                items_removed=0,
                errors=[f"Image cleanup failed: {str(e)}"]
            )
    
    def cleanup_networks(self, project_filter: Optional[str] = None) -> CleanupResult:
        """
        Clean up unused Docker networks
        Args:
            project_filter: Only clean networks from specific project
        Returns:
            CleanupResult with operation details
        """
        try:
            if self.dry_run:
                networks_info = self._get_unused_networks(project_filter)
                return CleanupResult(
                    operation="network_cleanup",
                    success=True,
                    items_removed=len(networks_info),
                    details={
                        "dry_run": True,
                        "networks_to_remove": networks_info,
                        "message": f"Would remove {len(networks_info)} unused networks"
                    }
                )
            
            # Clean unused networks
            cmd = ['docker', 'network', 'prune', '-f']
            if project_filter:
                # For project-specific cleanup, we need to handle manually
                return self._cleanup_project_networks(project_filter)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # Parse output
                space_info = self._parse_prune_output(result.stdout)
                return CleanupResult(
                    operation="network_cleanup",
                    success=True,
                    items_removed=space_info['count'],
                    details={"output": result.stdout.strip()}
                )
            else:
                return CleanupResult(
                    operation="network_cleanup",
                    success=False,
                    items_removed=0,
                    errors=[f"Network cleanup failed: {result.stderr}"]
                )
        except Exception as e:
            return CleanupResult(
                operation="network_cleanup",
                success=False,
                items_removed=0,
                errors=[f"Network cleanup failed: {str(e)}"]
            )
    
    def cleanup_volumes(self, project_filter: Optional[str] = None,
                       unused_only: bool = True) -> CleanupResult:
        """
        Clean up Docker volumes
        Args:
            project_filter: Only clean volumes from specific project
            unused_only: Only clean unused volumes (safer)
        Returns:
            CleanupResult with operation details
        """
        try:
            if self.dry_run:
                volumes_info = self._get_unused_volumes(project_filter)
                return CleanupResult(
                    operation="volume_cleanup",
                    success=True,
                    items_removed=len(volumes_info),
                    details={
                        "dry_run": True,
                        "volumes_to_remove": volumes_info,
                        "message": f"Would remove {len(volumes_info)} unused volumes"
                    }
                )
            
            if not unused_only:
                return CleanupResult(
                    operation="volume_cleanup",
                    success=False,
                    items_removed=0,
                    errors=["Aggressive volume cleanup not supported for safety - data loss risk"]
                )
            
            # Clean unused volumes
            cmd = ['docker', 'volume', 'prune', '-f']
            if project_filter:
                return self._cleanup_project_volumes(project_filter)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                space_info = self._parse_prune_output(result.stdout)
                return CleanupResult(
                    operation="volume_cleanup",
                    success=True,
                    items_removed=space_info['count'],
                    space_freed=space_info['size'],
                    details={"output": result.stdout.strip()}
                )
            else:
                return CleanupResult(
                    operation="volume_cleanup",
                    success=False,
                    items_removed=0,
                    errors=[f"Volume cleanup failed: {result.stderr}"]
                )
        except Exception as e:
            return CleanupResult(
                operation="volume_cleanup",
                success=False,
                items_removed=0,
                errors=[f"Volume cleanup failed: {str(e)}"]
            )
    
    def cleanup_system(self) -> CleanupResult:
        """
        Comprehensive Docker system cleanup
        Returns:
            CleanupResult with operation details
        """
        try:
            if self.dry_run:
                return CleanupResult(
                    operation="system_cleanup",
                    success=True,
                    items_removed=0,
                    details={
                        "dry_run": True,
                        "message": "Would perform comprehensive system cleanup"
                    }
                )
            
            # Docker system prune (removes stopped containers, unused networks, dangling images)
            result = subprocess.run(
                ['docker', 'system', 'prune', '-f'],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if result.returncode == 0:
                space_info = self._parse_prune_output(result.stdout)
                return CleanupResult(
                    operation="system_cleanup",
                    success=True,
                    items_removed=space_info['count'],
                    space_freed=space_info['size'],
                    details={"output": result.stdout.strip()}
                )
            else:
                return CleanupResult(
                    operation="system_cleanup",
                    success=False,
                    items_removed=0,
                    errors=[f"System cleanup failed: {result.stderr}"]
                )
        except subprocess.TimeoutExpired:
            return CleanupResult(
                operation="system_cleanup",
                success=False,
                items_removed=0,
                errors=["System cleanup timed out after 10 minutes"]
            )
        except Exception as e:
            return CleanupResult(
                operation="system_cleanup",
                success=False,
                items_removed=0,
                errors=[f"System cleanup failed: {str(e)}"]
            )
    
    def _get_containers_to_clean(self, project_filter: Optional[str], 
                               stopped_only: bool) -> List[Dict[str, str]]:
        """Get list of containers to clean"""
        try:
            cmd = ['docker', 'ps', '-a', '--format', 'json']
            if stopped_only:
                cmd = ['docker', 'ps', '-a', '--filter', 'status=exited', '--format', 'json']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return []
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        container = json.loads(line)
                        # Apply project filter if specified
                        if project_filter:
                            labels = container.get('Labels', '')
                            if f'com.docker.compose.project={project_filter}' not in labels:
                                continue
                        
                        containers.append({
                            'id': container.get('ID', ''),
                            'name': container.get('Names', ''),
                            'status': container.get('Status', ''),
                            'image': container.get('Image', '')
                        })
                    except json.JSONDecodeError:
                        continue
            
            return containers
        except Exception:
            return []
    
    def _get_images_info(self, dangling_only: bool, unused_only: bool) -> Dict[str, Any]:
        """Get information about images that would be cleaned"""
        try:
            if dangling_only:
                cmd = ['docker', 'images', '-f', 'dangling=true', '--format', 'json']
            else:
                cmd = ['docker', 'images', '--format', 'json']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {'count': 0, 'size': '0B'}
            
            count = 0
            total_size = 0
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        image = json.loads(line)
                        count += 1
                        # Size parsing would be complex, so we'll estimate
                        size_str = image.get('Size', '0B')
                        total_size += self._parse_size_string(size_str)
                    except json.JSONDecodeError:
                        continue
            
            return {
                'count': count,
                'size': self._format_size(total_size)
            }
        except Exception:
            return {'count': 0, 'size': '0B'}
    
    def _get_unused_networks(self, project_filter: Optional[str]) -> List[str]:
        """Get list of unused networks"""
        try:
            cmd = ['docker', 'network', 'ls', '--filter', 'dangling=true', '--format', '{{.Name}}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return []
            
            networks = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            if project_filter:
                # Filter by project
                filtered_networks = []
                for network in networks:
                    if project_filter in network:
                        filtered_networks.append(network)
                return filtered_networks
            
            return networks
        except Exception:
            return []
    
    def _get_unused_volumes(self, project_filter: Optional[str]) -> List[str]:
        """Get list of unused volumes"""
        try:
            cmd = ['docker', 'volume', 'ls', '-f', 'dangling=true', '--format', '{{.Name}}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return []
            
            volumes = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            if project_filter:
                # Filter by project
                filtered_volumes = []
                for volume in volumes:
                    if project_filter in volume:
                        filtered_volumes.append(volume)
                return filtered_volumes
            
            return volumes
        except Exception:
            return []
    
    def _cleanup_project_networks(self, project_name: str) -> CleanupResult:
        """Clean up networks for a specific project"""
        try:
            # Get project networks
            cmd = ['docker', 'network', 'ls', '--filter', f'label=com.docker.compose.project={project_name}', '--format', '{{.Name}}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return CleanupResult(
                    operation="project_network_cleanup",
                    success=False,
                    items_removed=0,
                    errors=[f"Failed to list project networks: {result.stderr}"]
                )
            
            networks = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            if not networks:
                return CleanupResult(
                    operation="project_network_cleanup",
                    success=True,
                    items_removed=0,
                    details={"message": f"No networks found for project {project_name}"}
                )
            
            # Remove networks
            removed_count = 0
            errors = []
            for network in networks:
                try:
                    result = subprocess.run(
                        ['docker', 'network', 'rm', network],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        removed_count += 1
                    else:
                        errors.append(f"Failed to remove network {network}: {result.stderr}")
                except Exception as e:
                    errors.append(f"Error removing network {network}: {str(e)}")
            
            return CleanupResult(
                operation="project_network_cleanup",
                success=len(errors) == 0,
                items_removed=removed_count,
                errors=errors if errors else None
            )
        except Exception as e:
            return CleanupResult(
                operation="project_network_cleanup",
                success=False,
                items_removed=0,
                errors=[f"Project network cleanup failed: {str(e)}"]
            )
    
    def _cleanup_project_volumes(self, project_name: str) -> CleanupResult:
        """Clean up volumes for a specific project"""
        try:
            # Get project volumes
            cmd = ['docker', 'volume', 'ls', '--filter', f'label=com.docker.compose.project={project_name}', '--format', '{{.Name}}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return CleanupResult(
                    operation="project_volume_cleanup",
                    success=False,
                    items_removed=0,
                    errors=[f"Failed to list project volumes: {result.stderr}"]
                )
            
            volumes = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            if not volumes:
                return CleanupResult(
                    operation="project_volume_cleanup",
                    success=True,
                    items_removed=0,
                    details={"message": f"No volumes found for project {project_name}"}
                )
            
            # Remove volumes
            removed_count = 0
            errors = []
            for volume in volumes:
                try:
                    result = subprocess.run(
                        ['docker', 'volume', 'rm', volume],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        removed_count += 1
                    else:
                        errors.append(f"Failed to remove volume {volume}: {result.stderr}")
                except Exception as e:
                    errors.append(f"Error removing volume {volume}: {str(e)}")
            
            return CleanupResult(
                operation="project_volume_cleanup",
                success=len(errors) == 0,
                items_removed=removed_count,
                errors=errors if errors else None
            )
        except Exception as e:
            return CleanupResult(
                operation="project_volume_cleanup",
                success=False,
                items_removed=0,
                errors=[f"Project volume cleanup failed: {str(e)}"]
            )
    
    def _parse_prune_output(self, output: str) -> Dict[str, Any]:
        """Parse Docker prune command output"""
        lines = output.strip().split('\n')
        count = 0
        size = "0B"
        
        for line in lines:
            if "Total reclaimed space:" in line:
                size = line.split(":")[-1].strip()
            elif "deleted" in line.lower() or "removed" in line.lower():
                # Try to extract count from various output formats
                words = line.split()
                for word in words:
                    if word.isdigit():
                        count = int(word)
                        break
        
        return {'count': count, 'size': size}
    
    def _parse_size_string(self, size_str: str) -> int:
        """Parse size string to bytes"""
        if not size_str or size_str == "0B":
            return 0
        
        # Simple size parsing - would need more robust implementation
        size_str = size_str.upper()
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024**2,
            'GB': 1024**3,
            'TB': 1024**4
        }
        
        for unit, multiplier in multipliers.items():
            if size_str.endswith(unit):
                try:
                    number = float(size_str[:-len(unit)])
                    return int(number * multiplier)
                except ValueError:
                    return 0
        return 0
    
    def _format_size(self, bytes_size: int) -> str:
        """Format bytes to human readable size"""
        if bytes_size == 0:
            return "0B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(bytes_size)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.1f}{units[unit_index]}"

class ProjectCleaner:
    """Handles project-specific cleanup operations"""
    
    def __init__(self, base_dir: str = None, dry_run: bool = False):
        """
        Initialize project cleaner
        Args:
            base_dir: Base directory for projects
            dry_run: If True, only show what would be cleaned
        """
        self.base_dir = base_dir or os.path.expanduser("~/dockeredServices")
        self.dry_run = dry_run
        self.docker_cleaner = DockerResourceCleaner(dry_run)
    
    def cleanup_project(self, project_name: str, 
                       remove_containers: bool = True,
                       remove_images: bool = False,
                       remove_volumes: bool = False,
                       remove_networks: bool = True,
                       remove_project_dir: bool = False) -> List[CleanupResult]:
        """
        Clean up a specific project
        Args:
            project_name: Name of the project to clean
            remove_containers: Remove project containers
            remove_images: Remove project images (dangerous)
            remove_volumes: Remove project volumes (data loss)
            remove_networks: Remove project networks
            remove_project_dir: Remove project directory (complete removal)
        Returns:
            List of CleanupResult objects
        """
        results = []
        
        # Verify project exists
        project_path = os.path.join(self.base_dir, project_name)
        if not os.path.exists(project_path):
            results.append(CleanupResult(
                operation="project_verification",
                success=False,
                items_removed=0,
                errors=[f"Project '{project_name}' not found at {project_path}"]
            ))
            return results
        
        # Stop project first (safer)
        stop_result = self._stop_project(project_name)
        results.append(stop_result)
        
        # Clean containers
        if remove_containers:
            container_result = self.docker_cleaner.cleanup_containers(
                project_filter=project_name,
                stopped_only=True
            )
            results.append(container_result)
        
        # Clean networks
        if remove_networks:
            network_result = self.docker_cleaner._cleanup_project_networks(project_name)
            results.append(network_result)
        
        # Clean volumes (dangerous - data loss)
        if remove_volumes:
            volume_result = self.docker_cleaner._cleanup_project_volumes(project_name)
            results.append(volume_result)
        
        # Clean images (very dangerous - may affect other projects)
        if remove_images:
            results.append(CleanupResult(
                operation="project_image_cleanup",
                success=False,
                items_removed=0,
                warnings=["Project-specific image cleanup not supported - too dangerous"],
                details={"message": "Use 'docker image prune' manually if needed"}
            ))
        
        # Remove project directory (complete removal)
        if remove_project_dir:
            dir_result = self._remove_project_directory(project_name, project_path)
            results.append(dir_result)
        
        return results
    
    def cleanup_stopped_projects(self) -> List[CleanupResult]:
        """
        Clean up all stopped projects
        Returns:
            List of CleanupResult objects
        """
        results = []
        try:
            # Get project status
            monitor = ProjectStatusMonitor(self.base_dir)
            projects = monitor.scanner.scan_projects()
            
            stopped_projects = [p for p in projects if not p.is_running and p.container_count > 0]
            
            if not stopped_projects:
                results.append(CleanupResult(
                    operation="stopped_projects_cleanup",
                    success=True,
                    items_removed=0,
                    details={"message": "No stopped projects found"}
                ))
                return results
            
            # Clean each stopped project
            for project in stopped_projects:
                project_results = self.cleanup_project(
                    project.name,
                    remove_containers=True,
                    remove_networks=True,
                    remove_volumes=False,  # Keep data by default
                    remove_project_dir=False
                )
                results.extend(project_results)
            
            return results
        except Exception as e:
            results.append(CleanupResult(
                operation="stopped_projects_cleanup",
                success=False,
                items_removed=0,
                errors=[f"Failed to cleanup stopped projects: {str(e)}"]
            ))
            return results
    
    def _stop_project(self, project_name: str) -> CleanupResult:
        """Stop a project using docker-compose"""
        try:
            project_path = os.path.join(self.base_dir, project_name)
            
            if self.dry_run:
                return CleanupResult(
                    operation="project_stop",
                    success=True,
                    items_removed=0,
                    details={
                        "dry_run": True,
                        "message": f"Would stop project {project_name}"
                    }
                )
            
            result = subprocess.run(
                ['docker-compose', 'down'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return CleanupResult(
                    operation="project_stop",
                    success=True,
                    items_removed=1,
                    details={"message": f"Successfully stopped project {project_name}"}
                )
            else:
                return CleanupResult(
                    operation="project_stop",
                    success=False,
                    items_removed=0,
                    errors=[f"Failed to stop project {project_name}: {result.stderr}"]
                )
        except subprocess.TimeoutExpired:
            return CleanupResult(
                operation="project_stop",
                success=False,
                items_removed=0,
                errors=[f"Timeout stopping project {project_name}"]
            )
        except Exception as e:
            return CleanupResult(
                operation="project_stop",
                success=False,
                items_removed=0,
                errors=[f"Error stopping project {project_name}: {str(e)}"]
            )
    
    def _remove_project_directory(self, project_name: str, project_path: str) -> CleanupResult:
        """Remove project directory completely"""
        try:
            if self.dry_run:
                return CleanupResult(
                    operation="project_directory_removal",
                    success=True,
                    items_removed=1,
                    details={
                        "dry_run": True,
                        "message": f"Would remove project directory {project_path}"
                    }
                )
            
            # Calculate directory size before removal
            dir_size = self._get_directory_size(project_path)
            
            # Remove directory
            import shutil
            shutil.rmtree(project_path)
            
            return CleanupResult(
                operation="project_directory_removal",
                success=True,
                items_removed=1,
                space_freed=self.docker_cleaner._format_size(dir_size),
                details={"message": f"Removed project directory {project_path}"}
            )
        except Exception as e:
            return CleanupResult(
                operation="project_directory_removal",
                success=False,
                items_removed=0,
                errors=[f"Failed to remove project directory: {str(e)}"]
            )
    
    def _get_directory_size(self, path: str) -> int:
        """Get total size of directory in bytes"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, IOError):
                        continue
        except Exception:
            pass
        return total_size

class MaintenanceManager:
    """Main maintenance and cleanup management system"""
    
    def __init__(self, base_dir: str = None, dry_run: bool = False):
        """
        Initialize maintenance manager
        Args:
            base_dir: Base directory for projects
            dry_run: If True, only show what would be done
        """
        self.base_dir = base_dir or os.path.expanduser("~/dockeredServices")
        self.dry_run = dry_run
        self.docker_cleaner = DockerResourceCleaner(dry_run)
        self.project_cleaner = ProjectCleaner(base_dir, dry_run)
        self.monitor = ProjectStatusMonitor(base_dir)
    
    def perform_maintenance(self, operations: List[str], 
                          project_filter: Optional[str] = None) -> MaintenanceReport:
        """
        Perform maintenance operations
        Args:
            operations: List of operations to perform
            project_filter: Filter operations to specific project
        Returns:
            MaintenanceReport with results
        """
        # Get system health before
        system_health_before = self._get_system_health()
        results = []
        warnings = []
        recommendations = []
        
        # Perform requested operations
        for operation in operations:
            if operation == "cleanup_containers":
                result = self.docker_cleaner.cleanup_containers(
                    project_filter=project_filter,
                    stopped_only=True
                )
                results.append(result)
            elif operation == "cleanup_images":
                result = self.docker_cleaner.cleanup_images(
                    unused_only=True,
                    dangling_only=True
                )
                results.append(result)
            elif operation == "cleanup_networks":
                result = self.docker_cleaner.cleanup_networks(project_filter)
                results.append(result)
            elif operation == "cleanup_volumes":
                result = self.docker_cleaner.cleanup_volumes(
                    project_filter=project_filter,
                    unused_only=True
                )
                results.append(result)
            elif operation == "cleanup_system":
                result = self.docker_cleaner.cleanup_system()
                results.append(result)
            elif operation == "cleanup_stopped_projects":
                project_results = self.project_cleaner.cleanup_stopped_projects()
                results.extend(project_results)
            elif operation.startswith("cleanup_project:"):
                project_name = operation.split(":", 1)[1]
                project_results = self.project_cleaner.cleanup_project(
                    project_name,
                    remove_containers=True,
                    remove_networks=True,
                    remove_volumes=False
                )
                results.extend(project_results)
            else:
                results.append(CleanupResult(
                    operation=operation,
                    success=False,
                    items_removed=0,
                    errors=[f"Unknown operation: {operation}"]
                ))
        
        # Get system health after
        system_health_after = self._get_system_health()
        
        # Generate recommendations
        recommendations = self._generate_maintenance_recommendations(
            system_health_before, 
            system_health_after, 
            results
        )
        
        # Calculate total space freed
        total_space_freed = self._calculate_total_space_freed(results)
        
        return MaintenanceReport(
            timestamp=datetime.now().isoformat(),
            username=os.getenv('USER', 'unknown'),
            operations_performed=results,
            total_space_freed=total_space_freed,
            recommendations=recommendations,
            warnings=warnings,
            system_health_before=system_health_before,
            system_health_after=system_health_after
        )
    
    def get_cleanup_suggestions(self, port_assignment: PortAssignment) -> List[str]:
        """
        Get automated cleanup suggestions based on system analysis
        Args:
            port_assignment: Student's port assignment
        Returns:
            List of cleanup suggestions
        """
        suggestions = []
        try:
            # Get current system status
            report = self.monitor.generate_monitoring_report(port_assignment, port_assignment.login_id)
            
            # Analyze port usage
            if report.port_usage.usage_percentage > 80:
                suggestions.append("High port usage detected - consider cleaning up stopped projects")
                stopped_projects = [p for p in report.projects if not p.is_running and p.container_count > 0]
                if stopped_projects:
                    project_names = [p.name for p in stopped_projects[:3]]
                    suggestions.append(f"Stopped projects using ports: {', '.join(project_names)}")
            
            # Analyze container count
            if report.system_status.total_containers > 20:
                suggestions.append("High container count - run 'docker container prune' to clean stopped containers")
            
            # Analyze running vs stopped containers
            if report.system_status.total_containers > report.system_status.running_containers * 2:
                suggestions.append("Many stopped containers detected - cleanup recommended")
            
            # Check for unused resources
            if report.system_status.total_volumes > 10:
                suggestions.append("Many Docker volumes detected - consider 'docker volume prune' for unused volumes")
            
            if report.system_status.total_networks > 10:
                suggestions.append("Many Docker networks detected - consider 'docker network prune' for unused networks")
            
            # Project-specific suggestions
            if not report.projects:
                suggestions.append("No projects found - system appears clean")
            elif len(report.projects) > 5:
                suggestions.append("Many projects detected - consider archiving unused projects")
            
            # Disk space suggestions (if available)
            if report.system_status.disk_usage:
                # Would need to analyze disk usage data
                suggestions.append("Check Docker disk usage with 'docker system df'")
                
        except Exception as e:
            suggestions.append(f"Unable to analyze system for suggestions: {str(e)}")
        
        return suggestions
    
    def _get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics"""
        try:
            # Get Docker system info
            result = subprocess.run(
                ['docker', 'system', 'df', '--format', 'json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            health = {
                'timestamp': datetime.now().isoformat(),
                'docker_available': True,
                'disk_usage': None
            }
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    health['disk_usage'] = json.loads(result.stdout)
                except json.JSONDecodeError:
                    pass
            
            # Get container counts
            result = subprocess.run(
                ['docker', 'ps', '-a', '--format', '{{.Status}}'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                statuses = result.stdout.strip().split('\n')
                health['total_containers'] = len([s for s in statuses if s.strip()])
                health['running_containers'] = len([s for s in statuses if s.strip().startswith('Up')])
            
            return health
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'docker_available': False,
                'error': str(e)
            }
    
    def _generate_maintenance_recommendations(self, before: Dict[str, Any], 
                                           after: Dict[str, Any], 
                                           results: List[CleanupResult]) -> List[str]:
        """Generate maintenance recommendations based on results"""
        recommendations = []
        
        # Analyze cleanup results
        successful_operations = [r for r in results if r.success]
        failed_operations = [r for r in results if not r.success]
        
        if successful_operations:
            total_items = sum(r.items_removed for r in successful_operations)
            recommendations.append(f"Successfully cleaned {total_items} items")
        
        if failed_operations:
            recommendations.append(f"{len(failed_operations)} operations failed - check logs for details")
        
        # Compare system health
        if before.get('total_containers', 0) > after.get('total_containers', 0):
            containers_removed = before['total_containers'] - after['total_containers']
            recommendations.append(f"Removed {containers_removed} containers - system is cleaner")
        
        # General recommendations
        if after.get('total_containers', 0) > 15:
            recommendations.append("Consider regular cleanup to maintain system performance")
        
        if any(r.space_freed for r in results):
            recommendations.append("Disk space has been freed - system performance may improve")
        
        return recommendations
    
    def _calculate_total_space_freed(self, results: List[CleanupResult]) -> Optional[str]:
        """Calculate total space freed from all operations"""
        total_bytes = 0
        has_space_info = False
        
        for result in results:
            if result.space_freed:
                has_space_info = True
                # Parse space freed string to bytes
                bytes_freed = self.docker_cleaner._parse_size_string(result.space_freed)
                total_bytes += bytes_freed
        
        if has_space_info and total_bytes > 0:
            return self.docker_cleaner._format_size(total_bytes)
        return None

def perform_cleanup(operations: List[str], project_filter: Optional[str] = None,
                   base_dir: str = None, dry_run: bool = False) -> MaintenanceReport:
    """
    Convenience function to perform cleanup operations
    Args:
        operations: List of operations to perform
        project_filter: Filter to specific project
        base_dir: Base directory for projects
        dry_run: If True, only show what would be done
    Returns:
        MaintenanceReport with results
    """
    manager = MaintenanceManager(base_dir, dry_run)
    return manager.perform_maintenance(operations, project_filter)

def get_cleanup_suggestions(port_assignment: PortAssignment, 
                          base_dir: str = None) -> List[str]:
    """
    Convenience function to get cleanup suggestions
    Args:
        port_assignment: Student's port assignment
        base_dir: Base directory for projects
    Returns:
        List of cleanup suggestions
    """
    manager = MaintenanceManager(base_dir, dry_run=False)
    return manager.get_cleanup_suggestions(port_assignment)