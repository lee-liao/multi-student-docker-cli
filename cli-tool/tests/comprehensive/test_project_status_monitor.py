#!/usr/bin/env python3
"""
Test Suite for Project Status Monitor
Tests project scanning, port usage tracking, container status monitoring,
and comprehensive status reporting functionality.
"""

import unittest
import tempfile
import os
import shutil
import json
from unittest.mock import patch, MagicMock

from src.monitoring.project_status_monitor import (
    ProjectScanner,
    SystemMonitor,
    PortUsageAnalyzer,
    ProjectStatusMonitor,
    ProjectStatus,
    ContainerStatus,
    SystemStatus,
    PortUsageSummary,
    generate_status_report,
    get_project_status
)
from src.core.port_assignment import PortAssignment


class TestProjectScanner(unittest.TestCase):
    """Test project scanning functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.scanner = ProjectScanner(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_scan_empty_directory(self):
        """Test scanning empty directory"""
        projects = self.scanner.scan_projects()
        self.assertEqual(len(projects), 0)
    
    def test_scan_directory_with_projects(self):
        """Test scanning directory with Docker Compose projects"""
        # Create test projects
        project1_dir = os.path.join(self.test_dir, "project1")
        project2_dir = os.path.join(self.test_dir, "project2")
        project3_dir = os.path.join(self.test_dir, "project3")  # No compose file
        
        os.makedirs(project1_dir)
        os.makedirs(project2_dir)
        os.makedirs(project3_dir)
        
        # Project 1 with compose file
        compose1_content = """version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "8080:80"
  api:
    image: node
    ports:
      - "8081:3000"
"""
        with open(os.path.join(project1_dir, "docker-compose.yml"), 'w') as f:
            f.write(compose1_content)
        
        # Project 2 with compose file
        compose2_content = """version: '3.9'
services:
  backend:
    image: python
    ports:
      - "8082:8000"
"""
        with open(os.path.join(project2_dir, "docker-compose.yml"), 'w') as f:
            f.write(compose2_content)
        
        # Project 3 has no compose file (should be ignored)
        
        projects = self.scanner.scan_projects()
        
        # Should find 2 projects (project3 ignored due to no compose file)
        self.assertEqual(len(projects), 2)
        
        project_names = [p.name for p in projects]
        self.assertIn("project1", project_names)
        self.assertIn("project2", project_names)
        self.assertNotIn("project3", project_names)
        
        # Check project1 details
        project1 = next(p for p in projects if p.name == "project1")
        self.assertTrue(project1.has_compose_file)
        self.assertEqual(len(project1.port_mappings), 2)
        self.assertEqual(set(project1.ports_used), {8080, 8081})
        self.assertEqual(project1.compose_version, "'3.8'")
        
        # Check project2 details
        project2 = next(p for p in projects if p.name == "project2")
        self.assertTrue(project2.has_compose_file)
        self.assertEqual(len(project2.port_mappings), 1)
        self.assertEqual(project2.ports_used, [8082])
        self.assertEqual(project2.compose_version, "'3.9'")
    
    def test_scan_nonexistent_directory(self):
        """Test scanning nonexistent directory"""
        scanner = ProjectScanner("/nonexistent/directory")
        projects = scanner.scan_projects()
        self.assertEqual(len(projects), 0)
    
    @patch('subprocess.run')
    def test_get_container_status_with_docker_compose(self, mock_run):
        """Test getting container status using docker-compose"""
        # Mock docker-compose ps output
        mock_output = """{"Name": "project1_web_1", "Image": "nginx", "State": "running", "Status": "Up 5 minutes", "Publishers": ["8080:80/tcp"]}
{"Name": "project1_api_1", "Image": "node", "State": "exited", "Status": "Exited (0) 2 minutes ago", "Publishers": []}"""
        
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
        
        containers = self.scanner._get_container_status("project1")
        
        self.assertEqual(len(containers), 2)
        
        web_container = containers[0]
        self.assertEqual(web_container.name, "project1_web_1")
        self.assertEqual(web_container.image, "nginx")
        self.assertEqual(web_container.status, "running")
        self.assertEqual(web_container.ports, ["8080:80/tcp"])
        
        api_container = containers[1]
        self.assertEqual(api_container.name, "project1_api_1")
        self.assertEqual(api_container.status, "exited")
    
    @patch('subprocess.run')
    def test_get_container_status_fallback_to_docker(self, mock_run):
        """Test fallback to docker ps when docker-compose fails"""
        # First call (docker-compose) fails, second call (docker) succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),  # docker-compose fails
            MagicMock(returncode=0, stdout='{"Names": "project1_web_1", "Image": "nginx", "State": "running", "Status": "Up 5 minutes"}')  # docker succeeds
        ]
        
        containers = self.scanner._get_container_status("project1")
        
        self.assertEqual(len(containers), 1)
        self.assertEqual(containers[0].name, "project1_web_1")
        self.assertEqual(containers[0].image, "nginx")
        self.assertEqual(containers[0].status, "running")


class TestSystemMonitor(unittest.TestCase):
    """Test system monitoring functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.monitor = SystemMonitor()
    
    @patch('subprocess.run')
    def test_check_docker_available_success(self, mock_run):
        """Test Docker availability check when Docker is available"""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.monitor._check_docker_available()
        self.assertTrue(result)
        
        mock_run.assert_called_with(['docker', 'info'], capture_output=True, text=True, timeout=5)
    
    @patch('subprocess.run')
    def test_check_docker_available_failure(self, mock_run):
        """Test Docker availability check when Docker is not available"""
        mock_run.return_value = MagicMock(returncode=1)
        
        result = self.monitor._check_docker_available()
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_get_docker_version(self, mock_run):
        """Test getting Docker version"""
        mock_run.return_value = MagicMock(returncode=0, stdout="Docker version 20.10.8, build 3967b7d")
        
        version = self.monitor._get_docker_version()
        self.assertEqual(version, "Docker version 20.10.8, build 3967b7d")
    
    @patch('subprocess.run')
    def test_get_container_stats(self, mock_run):
        """Test getting container statistics"""
        mock_run.return_value = MagicMock(returncode=0, stdout="Up 5 minutes\nExited (0) 2 minutes ago\nUp 1 hour\n")
        
        total, running = self.monitor._get_container_stats()
        self.assertEqual(total, 3)
        self.assertEqual(running, 2)  # Two containers with "Up" status
    
    @patch('subprocess.run')
    def test_get_system_status_complete(self, mock_run):
        """Test getting complete system status"""
        # Mock all subprocess calls
        mock_run.side_effect = [
            MagicMock(returncode=0),  # docker info
            MagicMock(returncode=0, stdout="Docker version 20.10.8"),  # docker --version
            MagicMock(returncode=0, stdout="docker-compose version 1.29.2"),  # docker-compose --version
            MagicMock(returncode=0, stdout="Up 5 minutes\nUp 1 hour\n"),  # docker ps -a
            MagicMock(returncode=0, stdout="bridge\nhost\n"),  # docker network ls
            MagicMock(returncode=0, stdout="vol1\nvol2\nvol3\n"),  # docker volume ls
            MagicMock(returncode=0, stdout='{"Images": [{"Size": 1000000}]}')  # docker system df
        ]
        
        status = self.monitor.get_system_status()
        
        self.assertTrue(status.docker_available)
        self.assertEqual(status.docker_version, "Docker version 20.10.8")
        self.assertTrue(status.compose_available)
        self.assertEqual(status.total_containers, 2)
        self.assertEqual(status.running_containers, 2)
        self.assertEqual(status.total_networks, 2)
        self.assertEqual(status.total_volumes, 3)


class TestPortUsageAnalyzer(unittest.TestCase):
    """Test port usage analysis functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.analyzer = PortUsageAnalyzer()
        self.port_assignment = PortAssignment(
            login_id="testuser",
            segment1_start=8000,
            segment1_end=8009
        )
    
    def test_analyze_port_usage_no_projects(self):
        """Test port usage analysis with no projects"""
        projects = []
        
        summary = self.analyzer.analyze_port_usage(projects, self.port_assignment)
        
        self.assertEqual(summary.total_assigned_ports, 10)
        self.assertEqual(summary.total_used_ports, 0)
        self.assertEqual(summary.available_ports, 10)
        self.assertEqual(summary.usage_percentage, 0.0)
        self.assertEqual(len(summary.projects_by_port_usage), 0)
        self.assertEqual(len(summary.port_conflicts), 0)
    
    def test_analyze_port_usage_with_projects(self):
        """Test port usage analysis with projects"""
        # Create mock projects
        project1 = ProjectStatus(
            name="project1",
            path="/test/project1",
            has_compose_file=True,
            is_running=True,
            container_count=2,
            containers=[],
            port_mappings=[],
            ports_used=[8000, 8001, 8002]
        )
        
        project2 = ProjectStatus(
            name="project2",
            path="/test/project2",
            has_compose_file=True,
            is_running=False,
            container_count=1,
            containers=[],
            port_mappings=[],
            ports_used=[8003, 8004]
        )
        
        projects = [project1, project2]
        
        summary = self.analyzer.analyze_port_usage(projects, self.port_assignment)
        
        self.assertEqual(summary.total_assigned_ports, 10)
        self.assertEqual(summary.total_used_ports, 5)
        self.assertEqual(summary.available_ports, 5)
        self.assertEqual(summary.usage_percentage, 50.0)
        
        # Check projects by usage (sorted by port count descending)
        self.assertEqual(len(summary.projects_by_port_usage), 2)
        self.assertEqual(summary.projects_by_port_usage[0], ("project1", 3))
        self.assertEqual(summary.projects_by_port_usage[1], ("project2", 2))
        
        # Check unused ports
        expected_unused = [8005, 8006, 8007, 8008, 8009]
        self.assertEqual(summary.unused_ports, expected_unused)
    
    def test_analyze_port_usage_with_conflicts(self):
        """Test port usage analysis with port conflicts"""
        # Create projects with conflicting ports
        project1 = ProjectStatus(
            name="project1",
            path="/test/project1",
            has_compose_file=True,
            is_running=True,
            container_count=1,
            containers=[],
            port_mappings=[],
            ports_used=[8000, 8001]
        )
        
        project2 = ProjectStatus(
            name="project2",
            path="/test/project2",
            has_compose_file=True,
            is_running=True,
            container_count=1,
            containers=[],
            port_mappings=[],
            ports_used=[8001, 8002]  # 8001 conflicts with project1
        )
        
        projects = [project1, project2]
        
        summary = self.analyzer.analyze_port_usage(projects, self.port_assignment)
        
        # Should detect one conflict
        self.assertEqual(len(summary.port_conflicts), 1)
        conflict = summary.port_conflicts[0]
        self.assertEqual(conflict['port'], 8001)
        self.assertEqual(set(conflict['projects']), {"project1", "project2"})
        self.assertEqual(conflict['conflict_type'], 'multiple_projects')


class TestProjectStatusMonitor(unittest.TestCase):
    """Test complete project status monitoring"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.monitor = ProjectStatusMonitor(self.test_dir)
        self.port_assignment = PortAssignment(
            login_id="testuser",
            segment1_start=8000,
            segment1_end=8009
        )
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    @patch('project_status_monitor.SystemMonitor.get_system_status')
    def test_generate_monitoring_report(self, mock_system_status):
        """Test generating complete monitoring report"""
        # Mock system status
        mock_system_status.return_value = SystemStatus(
            docker_available=True,
            docker_version="Docker version 20.10.8",
            compose_available=True,
            compose_version="docker-compose version 1.29.2",
            total_containers=5,
            running_containers=3,
            total_networks=2,
            total_volumes=1
        )
        
        # Create test project
        project_dir = os.path.join(self.test_dir, "test-project")
        os.makedirs(project_dir)
        
        compose_content = """version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "8000:80"
"""
        with open(os.path.join(project_dir, "docker-compose.yml"), 'w') as f:
            f.write(compose_content)
        
        report = self.monitor.generate_monitoring_report(self.port_assignment, "testuser")
        
        # Check report structure
        self.assertEqual(report.username, "testuser")
        self.assertIsNotNone(report.timestamp)
        self.assertTrue(report.system_status.docker_available)
        self.assertEqual(report.total_projects, 1)
        self.assertEqual(report.port_usage.total_assigned_ports, 10)
        self.assertEqual(report.port_usage.total_used_ports, 1)
    
    def test_generate_warnings_high_port_usage(self):
        """Test warning generation for high port usage"""
        # Create mock data with high port usage
        projects = []
        port_usage = PortUsageSummary(
            total_assigned_ports=10,
            total_used_ports=9,  # 90% usage
            available_ports=1,
            usage_percentage=90.0,
            port_ranges=["8000-8009"],
            projects_by_port_usage=[],
            unused_ports=[8009],
            port_conflicts=[]
        )
        system_status = SystemStatus(
            docker_available=True,
            docker_version="Docker version 20.10.8",
            compose_available=True,
            compose_version="docker-compose version 1.29.2",
            total_containers=5,
            running_containers=3,
            total_networks=2,
            total_volumes=1
        )
        
        warnings = self.monitor._generate_warnings(projects, port_usage, system_status)
        
        # Should warn about high port usage
        self.assertTrue(any("High port usage" in w for w in warnings))
    
    def test_generate_recommendations_cleanup(self):
        """Test recommendation generation for cleanup"""
        projects = []
        port_usage = PortUsageSummary(
            total_assigned_ports=10,
            total_used_ports=9,
            available_ports=1,
            usage_percentage=95.0,  # Very high usage
            port_ranges=["8000-8009"],
            projects_by_port_usage=[],
            unused_ports=[8009],
            port_conflicts=[]
        )
        system_status = SystemStatus(
            docker_available=True,
            docker_version="Docker version 20.10.8",
            compose_available=True,
            compose_version="docker-compose version 1.29.2",
            total_containers=25,  # Many containers
            running_containers=3,
            total_networks=2,
            total_volumes=15  # Many volumes
        )
        
        recommendations = self.monitor._generate_recommendations(projects, port_usage, system_status)
        
        # Should recommend stopping projects and cleanup
        self.assertTrue(any("stopping unused projects" in r for r in recommendations))
        self.assertTrue(any("container prune" in r for r in recommendations))
        self.assertTrue(any("volume prune" in r for r in recommendations))
    
    def test_format_status_report(self):
        """Test formatting status report as text"""
        # Create mock report
        from src.monitoring.project_status_monitor import MonitoringReport
        
        report = MonitoringReport(
            timestamp="2023-10-13T10:00:00",
            username="testuser",
            system_status=SystemStatus(
                docker_available=True,
                docker_version="Docker version 20.10.8",
                compose_available=True,
                compose_version="docker-compose version 1.29.2",
                total_containers=5,
                running_containers=3,
                total_networks=2,
                total_volumes=1
            ),
            port_usage=PortUsageSummary(
                total_assigned_ports=10,
                total_used_ports=3,
                available_ports=7,
                usage_percentage=30.0,
                port_ranges=["8000-8009"],
                projects_by_port_usage=[("project1", 3)],
                unused_ports=[8003, 8004, 8005, 8006, 8007, 8008, 8009],
                port_conflicts=[]
            ),
            projects=[
                ProjectStatus(
                    name="project1",
                    path="/test/project1",
                    has_compose_file=True,
                    is_running=True,
                    container_count=2,
                    containers=[],
                    port_mappings=[],
                    ports_used=[8000, 8001, 8002]
                )
            ],
            total_projects=1,
            running_projects=1,
            warnings=[],
            recommendations=[]
        )
        
        formatted = self.monitor.format_status_report(report)
        
        # Check key sections are present
        self.assertIn("Project Status and Monitoring Report", formatted)
        self.assertIn("testuser", formatted)
        self.assertIn("System Status", formatted)
        self.assertIn("Port Usage Summary", formatted)
        self.assertIn("Project Summary", formatted)
        self.assertIn("project1", formatted)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.port_assignment = PortAssignment(
            login_id="testuser",
            segment1_start=8000,
            segment1_end=8009
        )
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    @patch('project_status_monitor.SystemMonitor.get_system_status')
    def test_generate_status_report_function(self, mock_system_status):
        """Test convenience function for generating status report"""
        mock_system_status.return_value = SystemStatus(
            docker_available=True,
            docker_version="Docker version 20.10.8",
            compose_available=True,
            compose_version="docker-compose version 1.29.2",
            total_containers=0,
            running_containers=0,
            total_networks=0,
            total_volumes=0
        )
        
        report = generate_status_report(self.port_assignment, "testuser", self.test_dir)
        
        self.assertEqual(report.username, "testuser")
        self.assertIsNotNone(report.timestamp)
        self.assertEqual(report.total_projects, 0)  # No projects in empty directory
    
    def test_get_project_status_function(self):
        """Test convenience function for getting specific project status"""
        # Create test project
        project_dir = os.path.join(self.test_dir, "test-project")
        os.makedirs(project_dir)
        
        compose_content = """version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "8000:80"
"""
        with open(os.path.join(project_dir, "docker-compose.yml"), 'w') as f:
            f.write(compose_content)
        
        # Test existing project
        status = get_project_status("test-project", self.test_dir)
        self.assertIsNotNone(status)
        self.assertEqual(status.name, "test-project")
        self.assertTrue(status.has_compose_file)
        
        # Test non-existent project
        status = get_project_status("nonexistent", self.test_dir)
        self.assertIsNone(status)


if __name__ == '__main__':
    unittest.main()