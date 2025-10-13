#!/usr/bin/env python3
"""
Test Suite for Port Verification System
Tests Docker Compose parsing, port conflict detection,
and verification reporting functionality.
"""

import unittest
import tempfile
import os
import shutil
from src.monitoring.port_verification_system import (
    DockerComposeParser,
    PortVerificationSystem,
    PortMapping,
    PortConflict,
    verify_project_ports,
    verify_all_projects
)
from src.core.port_assignment import PortAssignment


class TestDockerComposeParser(unittest.TestCase):
    """Test Docker Compose file parsing"""
    
    def setUp(self):
        """Set up test environment"""
        self.parser = DockerComposeParser()
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_parse_simple_port_mappings(self):
        """Test parsing simple port mappings"""
        compose_content = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "8080:80"
      - "8443:443"
  api:
    image: node
    ports:
      - "3000:3000"
"""
        compose_file = os.path.join(self.test_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        mappings = self.parser.parse_compose_file(compose_file)
        
        self.assertEqual(len(mappings), 3)
        
        # Check web service mappings
        web_mappings = [m for m in mappings if m.service_name == "web"]
        self.assertEqual(len(web_mappings), 2)
        
        port_8080 = next(m for m in web_mappings if m.host_port == 8080)
        self.assertEqual(port_8080.container_port, 80)
        self.assertEqual(port_8080.protocol, "tcp")
        
        # Check api service mapping
        api_mappings = [m for m in mappings if m.service_name == "api"]
        self.assertEqual(len(api_mappings), 1)
        self.assertEqual(api_mappings[0].host_port, 3000)
        self.assertEqual(api_mappings[0].container_port, 3000)
    
    def test_parse_port_with_protocol(self):
        """Test parsing port mappings with protocol specification"""
        compose_content = """
version: '3.8'
services:
  dns:
    image: dns-server
    ports:
      - "5353:53/udp"
      - "8080:80/tcp"
"""
        compose_file = os.path.join(self.test_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        mappings = self.parser.parse_compose_file(compose_file)
        
        self.assertEqual(len(mappings), 2)
        
        udp_mapping = next(m for m in mappings if m.host_port == 5353)
        self.assertEqual(udp_mapping.protocol, "udp")
        self.assertEqual(udp_mapping.container_port, 53)
        
        tcp_mapping = next(m for m in mappings if m.host_port == 8080)
        self.assertEqual(tcp_mapping.protocol, "tcp")
    
    def test_parse_object_format_ports(self):
        """Test parsing object format port mappings"""
        compose_content = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - target: 80
        published: 8080
        protocol: tcp
      - target: 443
        published: 8443
        protocol: tcp
"""
        compose_file = os.path.join(self.test_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        mappings = self.parser.parse_compose_file(compose_file)
        
        self.assertEqual(len(mappings), 2)
        
        port_8080 = next(m for m in mappings if m.host_port == 8080)
        self.assertEqual(port_8080.container_port, 80)
        self.assertEqual(port_8080.protocol, "tcp")
    
    def test_parse_mixed_port_formats(self):
        """Test parsing mixed port format styles"""
        compose_content = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "8080:80"
      - target: 443
        published: 8443
      - 9000
"""
        compose_file = os.path.join(self.test_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        mappings = self.parser.parse_compose_file(compose_file)
        
        self.assertEqual(len(mappings), 3)
        
        # Check different formats were parsed correctly
        string_format = next(m for m in mappings if m.host_port == 8080)
        self.assertEqual(string_format.container_port, 80)
        
        object_format = next(m for m in mappings if m.host_port == 8443)
        self.assertEqual(object_format.container_port, 443)
        
        simple_format = next(m for m in mappings if m.host_port == 9000)
        self.assertEqual(simple_format.container_port, 9000)
    
    def test_parse_ip_specific_ports(self):
        """Test parsing IP-specific port mappings"""
        compose_content = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "127.0.0.1:8080:80"
      - "192.168.1.100:8443:443"
"""
        compose_file = os.path.join(self.test_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        mappings = self.parser.parse_compose_file(compose_file)
        
        self.assertEqual(len(mappings), 2)
        
        # IP-specific mappings should still extract host ports correctly
        port_8080 = next(m for m in mappings if m.host_port == 8080)
        self.assertEqual(port_8080.container_port, 80)
        
        port_8443 = next(m for m in mappings if m.host_port == 8443)
        self.assertEqual(port_8443.container_port, 443)
    
    def test_parse_invalid_compose_file(self):
        """Test handling of invalid Docker Compose files"""
        # Invalid YAML
        compose_file = os.path.join(self.test_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        with self.assertRaises(ValueError):
            self.parser.parse_compose_file(compose_file)
    
    def test_parse_nonexistent_file(self):
        """Test handling of nonexistent files"""
        nonexistent_file = os.path.join(self.test_dir, "nonexistent.yml")
        
        with self.assertRaises(FileNotFoundError):
            self.parser.parse_compose_file(nonexistent_file)


class TestPortVerificationSystem(unittest.TestCase):
    """Test port verification functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.verifier = PortVerificationSystem()
        self.test_dir = tempfile.mkdtemp()
        
        # Create test port assignment
        self.port_assignment = PortAssignment(
            login_id="testuser",
            segment1_start=8000,
            segment1_end=8009
        )
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_verify_valid_port_configuration(self):
        """Test verification of valid port configuration"""
        compose_content = """
version: '3.8'
services:
  backend:
    image: node
    ports:
      - "8000:3000"
  frontend:
    image: nginx
    ports:
      - "8001:80"
"""
        compose_file = os.path.join(self.test_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        result = self.verifier.verify_project_ports(self.test_dir, self.port_assignment, "testuser")
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.total_ports_used, 2)
        self.assertEqual(len(result.conflicts), 0)
        self.assertIn("Port configuration looks good", " ".join(result.suggestions))
    
    def test_verify_out_of_range_ports(self):
        """Test detection of out-of-range ports"""
        compose_content = """
version: '3.8'
services:
  backend:
    image: node
    ports:
      - "3000:3000"  # Out of range
  frontend:
    image: nginx
    ports:
      - "8001:80"    # In range
"""
        compose_file = os.path.join(self.test_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        result = self.verifier.verify_project_ports(self.test_dir, self.port_assignment, "testuser")
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.total_ports_used, 2)
        
        # Should have one out-of-range conflict
        out_of_range_conflicts = [c for c in result.conflicts if c.issue_type == "out_of_range"]
        self.assertEqual(len(out_of_range_conflicts), 1)
        self.assertEqual(out_of_range_conflicts[0].port, 3000)
        self.assertEqual(out_of_range_conflicts[0].service_name, "backend")
    
    def test_verify_duplicate_ports(self):
        """Test detection of duplicate port usage"""
        compose_content = """
version: '3.8'
services:
  backend:
    image: node
    ports:
      - "8000:3000"
  frontend:
    image: nginx
    ports:
      - "8000:80"    # Duplicate port
"""
        compose_file = os.path.join(self.test_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        result = self.verifier.verify_project_ports(self.test_dir, self.port_assignment, "testuser")
        
        self.assertFalse(result.is_valid)
        
        # Should have duplicate port conflict
        duplicate_conflicts = [c for c in result.conflicts if c.issue_type == "duplicate"]
        self.assertEqual(len(duplicate_conflicts), 1)
        self.assertEqual(duplicate_conflicts[0].port, 8000)
    
    def test_verify_system_port_warnings(self):
        """Test warnings for common system ports"""
        compose_content = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "80:80"      # System port (if in range)
  ssh:
    image: ssh-server
    ports:
      - "22:22"      # System port (if in range)
"""
        # Create port assignment that includes system ports for testing
        system_port_assignment = PortAssignment(
            login_id="testuser",
            segment1_start=20,
            segment1_end=100
        )
        
        compose_file = os.path.join(self.test_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        result = self.verifier.verify_project_ports(self.test_dir, system_port_assignment, "testuser")
        
        # Should have system port warnings
        system_port_conflicts = [c for c in result.conflicts if c.issue_type == "system_port"]
        self.assertGreater(len(system_port_conflicts), 0)
        
        # Check that warnings are generated
        self.assertGreater(len(result.warnings), 0)
    
    def test_verify_missing_compose_file(self):
        """Test handling of missing docker-compose.yml file"""
        result = self.verifier.verify_project_ports(self.test_dir, self.port_assignment, "testuser")
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.total_ports_used, 0)
        
        # Should have missing file conflict
        missing_file_conflicts = [c for c in result.conflicts if c.issue_type == "missing_file"]
        self.assertEqual(len(missing_file_conflicts), 1)
        self.assertIn("docker-compose.yml file not found", missing_file_conflicts[0].description)
    
    def test_verify_invalid_compose_syntax(self):
        """Test handling of invalid Docker Compose syntax"""
        compose_content = "invalid: yaml: [syntax"
        
        compose_file = os.path.join(self.test_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        result = self.verifier.verify_project_ports(self.test_dir, self.port_assignment, "testuser")
        
        self.assertFalse(result.is_valid)
        
        # Should have parse error conflict
        parse_error_conflicts = [c for c in result.conflicts if c.issue_type == "parse_error"]
        self.assertEqual(len(parse_error_conflicts), 1)
        self.assertIn("Failed to parse docker-compose.yml", parse_error_conflicts[0].description)
    
    def test_suggest_alternative_ports(self):
        """Test port suggestion functionality"""
        # Test with out-of-range port
        result = self.verifier._suggest_alternative_port(3000, [8000, 8001, 8002], {8000})
        self.assertIn("8001", result)  # Should suggest available port close to 3000
        
        # Test with no available ports
        result = self.verifier._suggest_alternative_port(3000, [8000], {8000})
        self.assertIn("No available ports", result)
    
    def test_format_port_ranges(self):
        """Test port range formatting"""
        # Single segment
        single_segment = PortAssignment(
            login_id="testuser",
            segment1_start=8000,
            segment1_end=8009
        )
        formatted = self.verifier._format_port_ranges(single_segment)
        self.assertEqual(formatted, "8000-8009")
        
        # Two segments
        two_segments = PortAssignment(
            login_id="testuser",
            segment1_start=4000,
            segment1_end=4099,
            segment2_start=8000,
            segment2_end=8099
        )
        formatted = self.verifier._format_port_ranges(two_segments)
        self.assertEqual(formatted, "4000-4099, 8000-8099")


class TestMultiProjectVerification(unittest.TestCase):
    """Test multi-project verification functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.verifier = PortVerificationSystem()
        self.test_dir = tempfile.mkdtemp()
        
        # Create test port assignment
        self.port_assignment = PortAssignment(
            login_id="testuser",
            segment1_start=8000,
            segment1_end=8019  # 20 ports for multiple projects
        )
        
        # Create test projects
        self.project1_dir = os.path.join(self.test_dir, "project1")
        self.project2_dir = os.path.join(self.test_dir, "project2")
        os.makedirs(self.project1_dir)
        os.makedirs(self.project2_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_verify_multiple_projects_no_conflicts(self):
        """Test verification of multiple projects without conflicts"""
        # Project 1
        compose1_content = """
version: '3.8'
services:
  backend:
    image: node
    ports:
      - "8000:3000"
  frontend:
    image: nginx
    ports:
      - "8001:80"
"""
        with open(os.path.join(self.project1_dir, "docker-compose.yml"), 'w') as f:
            f.write(compose1_content)
        
        # Project 2
        compose2_content = """
version: '3.8'
services:
  api:
    image: fastapi
    ports:
      - "8002:8000"
  web:
    image: react
    ports:
      - "8003:3000"
"""
        with open(os.path.join(self.project2_dir, "docker-compose.yml"), 'w') as f:
            f.write(compose2_content)
        
        results = self.verifier.verify_multiple_projects(self.test_dir, self.port_assignment, "testuser")
        
        self.assertEqual(len(results), 2)
        self.assertIn("project1", results)
        self.assertIn("project2", results)
        
        # Both projects should be valid
        self.assertTrue(results["project1"].is_valid)
        self.assertTrue(results["project2"].is_valid)
    
    def test_detect_cross_project_conflicts(self):
        """Test detection of conflicts across projects"""
        # Project 1
        compose1_content = """
version: '3.8'
services:
  backend:
    image: node
    ports:
      - "8000:3000"
"""
        with open(os.path.join(self.project1_dir, "docker-compose.yml"), 'w') as f:
            f.write(compose1_content)
        
        # Project 2 - uses same port
        compose2_content = """
version: '3.8'
services:
  api:
    image: fastapi
    ports:
      - "8000:8000"  # Conflict with project1
"""
        with open(os.path.join(self.project2_dir, "docker-compose.yml"), 'w') as f:
            f.write(compose2_content)
        
        results = self.verifier.verify_multiple_projects(self.test_dir, self.port_assignment, "testuser")
        conflicts = self.verifier.detect_cross_project_conflicts(results)
        
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].port, 8000)
        self.assertEqual(conflicts[0].issue_type, "cross_project_conflict")
        self.assertIn("project1", conflicts[0].service_name)
        self.assertIn("project2", conflicts[0].service_name)
    
    def test_generate_verification_report(self):
        """Test verification report generation"""
        # Create projects with various issues
        compose1_content = """
version: '3.8'
services:
  backend:
    image: node
    ports:
      - "8000:3000"
"""
        with open(os.path.join(self.project1_dir, "docker-compose.yml"), 'w') as f:
            f.write(compose1_content)
        
        compose2_content = """
version: '3.8'
services:
  api:
    image: fastapi
    ports:
      - "9999:8000"  # Out of range
"""
        with open(os.path.join(self.project2_dir, "docker-compose.yml"), 'w') as f:
            f.write(compose2_content)
        
        results = self.verifier.verify_multiple_projects(self.test_dir, self.port_assignment, "testuser")
        conflicts = self.verifier.detect_cross_project_conflicts(results)
        report = self.verifier.generate_verification_report(results, conflicts)
        
        # Check report content
        self.assertIn("Port Verification Report", report)
        self.assertIn("Summary:", report)
        self.assertIn("project1", report)
        self.assertIn("project2", report)
        self.assertIn("8000-8019", report)  # Port range
        self.assertIn("out of range", report.lower())  # Should mention the issue


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
    
    def test_verify_project_ports_function(self):
        """Test convenience function for single project verification"""
        compose_content = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "8000:80"
"""
        compose_file = os.path.join(self.test_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        result = verify_project_ports(self.test_dir, self.port_assignment, "testuser")
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.total_ports_used, 1)
    
    def test_verify_all_projects_function(self):
        """Test convenience function for all projects verification"""
        # Create a project
        project_dir = os.path.join(self.test_dir, "test-project")
        os.makedirs(project_dir)
        
        compose_content = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "8000:80"
"""
        compose_file = os.path.join(project_dir, "docker-compose.yml")
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        results, conflicts = verify_all_projects(self.test_dir, self.port_assignment, "testuser")
        
        self.assertEqual(len(results), 1)
        self.assertIn("test-project", results)
        self.assertEqual(len(conflicts), 0)  # No cross-project conflicts


if __name__ == '__main__':
    unittest.main()