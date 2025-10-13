#!/usr/bin/env python3
"""
Test Suite for Cleanup and Maintenance Tools
Tests project removal, port optimization, system health checking,
and maintenance operations.
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import patch, MagicMock

from src.maintenance.cleanup_maintenance_tools import (
    ProjectRemovalTool,
    PortOptimizationTool,
    SystemHealthChecker,
    MaintenanceTool,
    CleanupResult,
    remove_project,
    analyze_port_optimization,
    check_system_health,
    clean_unused_resources
)
from src.monitoring.project_status_monitor import ProjectStatus, ContainerStatus
from src.core.port_assignment import PortAssignment


class TestProjectRemovalTool(unittest.TestCase):
    """Test project removal functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.removal_tool = ProjectRemovalTool(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_remove_nonexistent_project(self):
        """Test removing a project that doesn't exist"""
        result = self.removal_tool.remove_project("nonexistent")
        
        self.assertFalse(result.success)
        self.assertEqual(result.items_removed, 0)
        self.assertIn("not found", result.errors[0])
    
    def test_remove_project_directory_only(self):
        """Test removing a project with only directory (no containers)"""
        # Create test project directory
        project_dir = os.path.join(self.test_dir, "test_project")
        os.makedirs(project_dir)
        
        # Create some files
        with open(os.path.join(project_dir, "docker-compose.yml"), "w") as f:
            f.write("version: '3'\nservices:\n  web:\n    image: nginx")
        
        result = self.removal_tool.remove_project("test_project")
        
        self.assertTrue(result.success)
        self.assertEqual(result.items_removed, 1)
        self.assertFalse(os.path.exists(project_dir))
    
    @patch('subprocess.run')
    def test_remove_project_with_containers(self, mock_run):
        """Test removing a project with running containers"""
        # Create test project directory
        project_dir = os.path.join(self.test_dir, "test_project")
        os.makedirs(project_dir)
        
        # Create docker-compose.yml
        with open(os.path.join(project_dir, "docker-compose.yml"), "w") as f:
            f.write("version: '3'\nservices:\n  web:\n    image: nginx")
        
        # Mock docker-compose down
        mock_run.return_value = MagicMock(returncode=0, stdout="Stopping containers...")
        
        result = self.removal_tool.remove_project("test_project", stop_containers=True)
        
        self.assertTrue(result.success)
        self.assertGreaterEqual(result.items_removed, 1)
        
        # Check that docker-compose down was called
        mock_run.assert_called_with(
            ['docker-compose', 'down'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
    
    def test_force_remove_project(self):
        """Test force removing a project"""
        # Create test project directory
        project_dir = os.path.join(self.test_dir, "test_project")
        os.makedirs(project_dir)
        
        # Create a file that might be "in use"
        test_file = os.path.join(project_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")
        
        result = self.removal_tool.remove_project("test_project", force=True)
        
        self.assertTrue(result.success)
        self.assertFalse(os.path.exists(project_dir))


class TestPortOptimizationTool(unittest.TestCase):
    """Test port optimization functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.port_assignment = PortAssignment("test_user", 8000, 8099)
        self.optimization_tool = PortOptimizationTool()
    
    def test_analyze_port_usage_no_projects(self):
        """Test port analysis with no projects"""
        analysis = self.optimization_tool.analyze_port_usage(self.port_assignment, [])
        
        self.assertEqual(analysis['total_ports'], 100)
        self.assertEqual(analysis['used_ports'], 0)
        self.assertEqual(analysis['available_ports'], 100)
        self.assertEqual(analysis['usage_percentage'], 0.0)
    
    def test_analyze_port_usage_with_projects(self):
        """Test port analysis with projects"""
        # Mock project statuses
        projects = [
            ProjectStatus("project1", "/path/to/project1", True, [
                ContainerStatus("web", "running", {"80/tcp": [{"HostPort": "8001"}]})
            ]),
            ProjectStatus("project2", "/path/to/project2", False, [
                ContainerStatus("db", "exited", {"5432/tcp": [{"HostPort": "8002"}]})
            ])
        ]
        
        analysis = self.optimization_tool.analyze_port_usage(self.port_assignment, projects)
        
        self.assertEqual(analysis['total_ports'], 100)
        self.assertEqual(analysis['used_ports'], 2)
        self.assertEqual(analysis['available_ports'], 98)
        self.assertEqual(analysis['usage_percentage'], 2.0)
    
    def test_get_optimization_suggestions_low_usage(self):
        """Test optimization suggestions for low port usage"""
        analysis = {
            'total_ports': 100,
            'used_ports': 5,
            'available_ports': 95,
            'usage_percentage': 5.0,
            'port_conflicts': [],
            'unused_ports': list(range(8005, 8100))
        }
        
        suggestions = self.optimization_tool.get_optimization_suggestions(analysis)
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        # Should suggest that usage is low
        suggestion_text = " ".join(suggestions)
        self.assertIn("low", suggestion_text.lower())
    
    def test_get_optimization_suggestions_high_usage(self):
        """Test optimization suggestions for high port usage"""
        analysis = {
            'total_ports': 100,
            'used_ports': 85,
            'available_ports': 15,
            'usage_percentage': 85.0,
            'port_conflicts': [],
            'unused_ports': list(range(8085, 8100))
        }
        
        suggestions = self.optimization_tool.get_optimization_suggestions(analysis)
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        # Should suggest cleanup or optimization
        suggestion_text = " ".join(suggestions)
        self.assertTrue(
            "cleanup" in suggestion_text.lower() or 
            "optimize" in suggestion_text.lower() or
            "high" in suggestion_text.lower()
        )


class TestSystemHealthChecker(unittest.TestCase):
    """Test system health checking functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.health_checker = SystemHealthChecker()
    
    @patch('subprocess.run')
    def test_check_docker_availability_success(self, mock_run):
        """Test Docker availability check when Docker is available"""
        mock_run.return_value = MagicMock(returncode=0, stdout="Docker version 20.10.0")
        
        result = self.health_checker.check_docker_availability()
        
        self.assertTrue(result['available'])
        self.assertIn('version', result)
        self.assertEqual(result['status'], 'healthy')
    
    @patch('subprocess.run')
    def test_check_docker_availability_failure(self, mock_run):
        """Test Docker availability check when Docker is not available"""
        mock_run.side_effect = FileNotFoundError("docker command not found")
        
        result = self.health_checker.check_docker_availability()
        
        self.assertFalse(result['available'])
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('error', result)
    
    @patch('subprocess.run')
    def test_check_system_resources(self, mock_run):
        """Test system resource checking"""
        # Mock df command for disk usage
        mock_run.return_value = MagicMock(
            returncode=0, 
            stdout="/dev/sda1    100G   50G   45G  53% /home"
        )
        
        result = self.health_checker.check_system_resources()
        
        self.assertIn('disk_usage', result)
        self.assertIn('status', result)
    
    def test_generate_health_report(self):
        """Test health report generation"""
        # Mock individual check results
        with patch.object(self.health_checker, 'check_docker_availability') as mock_docker, \
             patch.object(self.health_checker, 'check_system_resources') as mock_resources:
            
            mock_docker.return_value = {'available': True, 'status': 'healthy'}
            mock_resources.return_value = {'disk_usage': 50, 'status': 'healthy'}
            
            report = self.health_checker.generate_health_report()
            
            self.assertIn('docker', report)
            self.assertIn('system_resources', report)
            self.assertIn('overall_status', report)
            self.assertIn('timestamp', report)


class TestMaintenanceTool(unittest.TestCase):
    """Test maintenance tool functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.maintenance_tool = MaintenanceTool(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    @patch('subprocess.run')
    def test_clean_unused_docker_resources(self, mock_run):
        """Test cleaning unused Docker resources"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Deleted containers: 5\nDeleted networks: 2\nTotal reclaimed space: 1.2GB"
        )
        
        result = self.maintenance_tool.clean_unused_docker_resources()
        
        self.assertTrue(result.success)
        self.assertGreater(result.items_removed, 0)
        self.assertIn("1.2GB", result.space_freed)
    
    @patch('subprocess.run')
    def test_clean_unused_docker_resources_failure(self, mock_run):
        """Test cleaning Docker resources when command fails"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: Docker daemon not running"
        )
        
        result = self.maintenance_tool.clean_unused_docker_resources()
        
        self.assertFalse(result.success)
        self.assertEqual(result.items_removed, 0)
        self.assertIn("Docker daemon", result.errors[0])
    
    def test_cleanup_old_project_files(self):
        """Test cleanup of old project files"""
        # Create test project with old files
        project_dir = os.path.join(self.test_dir, "old_project")
        os.makedirs(project_dir)
        
        # Create some test files
        old_file = os.path.join(project_dir, "old_file.txt")
        with open(old_file, "w") as f:
            f.write("old content")
        
        # Set file modification time to be old (simulate)
        # In real implementation, this would check actual file ages
        
        result = self.maintenance_tool.cleanup_old_project_files(days_old=30)
        
        self.assertIsInstance(result, CleanupResult)
        # Note: This test is simplified - real implementation would check file ages


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    @patch('cleanup_maintenance_tools.ProjectRemovalTool')
    def test_remove_project_function(self, mock_tool_class):
        """Test remove_project convenience function"""
        mock_tool = MagicMock()
        mock_result = CleanupResult("remove_project", True, 1)
        mock_tool.remove_project.return_value = mock_result
        mock_tool_class.return_value = mock_tool
        
        result = remove_project("test_project", base_dir=self.test_dir)
        
        self.assertEqual(result, mock_result)
        mock_tool_class.assert_called_once_with(self.test_dir)
        mock_tool.remove_project.assert_called_once_with("test_project", False, False)
    
    @patch('cleanup_maintenance_tools.PortOptimizationTool')
    def test_analyze_port_optimization_function(self, mock_tool_class):
        """Test analyze_port_optimization convenience function"""
        mock_tool = MagicMock()
        mock_analysis = {'usage_percentage': 25.0}
        mock_tool.analyze_port_usage.return_value = mock_analysis
        mock_tool_class.return_value = mock_tool
        
        port_assignment = PortAssignment("test_user", 8000, 8099)
        result = analyze_port_optimization(port_assignment, [])
        
        self.assertEqual(result, mock_analysis)
        mock_tool_class.assert_called_once()
        mock_tool.analyze_port_usage.assert_called_once_with(port_assignment, [])
    
    @patch('cleanup_maintenance_tools.SystemHealthChecker')
    def test_check_system_health_function(self, mock_checker_class):
        """Test check_system_health convenience function"""
        mock_checker = MagicMock()
        mock_report = {'overall_status': 'healthy'}
        mock_checker.generate_health_report.return_value = mock_report
        mock_checker_class.return_value = mock_checker
        
        result = check_system_health()
        
        self.assertEqual(result, mock_report)
        mock_checker_class.assert_called_once()
        mock_checker.generate_health_report.assert_called_once()
    
    @patch('cleanup_maintenance_tools.MaintenanceTool')
    def test_clean_unused_resources_function(self, mock_tool_class):
        """Test clean_unused_resources convenience function"""
        mock_tool = MagicMock()
        mock_result = CleanupResult("cleanup", True, 5, space_freed="1GB")
        mock_tool.clean_unused_docker_resources.return_value = mock_result
        mock_tool_class.return_value = mock_tool
        
        result = clean_unused_resources()
        
        self.assertEqual(result, mock_result)
        mock_tool_class.assert_called_once()
        mock_tool.clean_unused_docker_resources.assert_called_once()


class TestCleanupResult(unittest.TestCase):
    """Test CleanupResult data class"""
    
    def test_cleanup_result_creation(self):
        """Test CleanupResult creation and attributes"""
        result = CleanupResult(
            operation="test_operation",
            success=True,
            items_removed=5,
            space_freed="100MB",
            errors=["Error 1"],
            warnings=["Warning 1"]
        )
        
        self.assertEqual(result.operation, "test_operation")
        self.assertTrue(result.success)
        self.assertEqual(result.items_removed, 5)
        self.assertEqual(result.space_freed, "100MB")
        self.assertEqual(result.errors, ["Error 1"])
        self.assertEqual(result.warnings, ["Warning 1"])
    
    def test_cleanup_result_minimal(self):
        """Test CleanupResult with minimal attributes"""
        result = CleanupResult(
            operation="minimal_op",
            success=False,
            items_removed=0
        )
        
        self.assertEqual(result.operation, "minimal_op")
        self.assertFalse(result.success)
        self.assertEqual(result.items_removed, 0)
        self.assertIsNone(result.space_freed)
        self.assertIsNone(result.errors)
        self.assertIsNone(result.warnings)


if __name__ == '__main__':
    unittest.main()