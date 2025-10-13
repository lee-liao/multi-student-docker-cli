#!/usr/bin/env python3
"""
Test Suite for Setup Script Manager
Tests setup script generation with intelligent database detection,
health checking, startup coordination, and error recovery guidance.
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import patch, MagicMock

from src.config.setup_script_manager import (
    SetupScriptManager, 
    SetupScriptConfig, 
    create_setup_script_config,
    generate_setup_script
)
from src.core.port_assignment import PortAssignment


class TestSetupScriptManager(unittest.TestCase):
    """Test setup script generation functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.templates_dir = os.path.join(self.test_dir, "templates")
        self.output_dir = os.path.join(self.test_dir, "output")
        
        # Create directories
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create test port assignment
        self.port_assignment = PortAssignment(
            login_id="testuser",
            segment1_start=8000,
            segment1_end=8009
        )
        
        # Initialize manager
        self.manager = SetupScriptManager(self.templates_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_setup_script_config_creation(self):
        """Test setup script configuration creation"""
        config = create_setup_script_config(
            username="testuser",
            project_name="test-project",
            template_type="rag",
            port_assignment=self.port_assignment,
            output_dir=self.output_dir,
            services=["backend", "frontend"],
            has_common_project=True
        )
        
        self.assertEqual(config.username, "testuser")
        self.assertEqual(config.project_name, "test-project")
        self.assertEqual(config.template_type, "rag")
        self.assertEqual(config.services, ["backend", "frontend"])
        self.assertTrue(config.has_common_project)
    
    def test_intelligent_setup_script_generation_rag_shared(self):
        """Test intelligent setup script generation for RAG with shared infrastructure"""
        config = SetupScriptConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            output_dir=self.output_dir,
            services=["backend", "frontend"]
        )
        
        script_content = self.manager._generate_intelligent_setup_script(config)
        
        # Check script header
        self.assertIn("Setting up test-rag (rag project)", script_content)
        self.assertIn("testuser", script_content)
        
        # Check utility functions
        self.assertIn("print_status()", script_content)
        self.assertIn("print_success()", script_content)
        self.assertIn("wait_for_service()", script_content)
        
        # Check prerequisites
        self.assertIn("Docker is not running", script_content)
        self.assertIn("docker-compose is not installed", script_content)
        
        # Check shared infrastructure validation
        self.assertIn("Common project network found", script_content)
        self.assertIn("Required RAG services are not running", script_content)
        
        # Check health checks
        self.assertIn("Performing RAG health checks", script_content)
        
        # Check error recovery
        self.assertIn("Troubleshooting Information", script_content)
        self.assertIn("docker-compose logs", script_content)
    
    def test_intelligent_setup_script_generation_agent_standalone(self):
        """Test intelligent setup script generation for Agent in standalone mode"""
        config = SetupScriptConfig(
            username="testuser",
            project_name="test-agent",
            template_type="agent",
            port_assignment=self.port_assignment,
            has_common_project=False,
            output_dir=self.output_dir,
            services=["backend", "frontend", "worker", "postgres", "mongodb", "redis"]
        )
        
        script_content = self.manager._generate_intelligent_setup_script(config)
        
        # Check script header
        self.assertIn("Setting up test-agent (agent project)", script_content)
        
        # Check standalone database setup
        self.assertIn("Self-contained project", script_content)
        self.assertIn("PostgreSQL setup", script_content)
        self.assertIn("MongoDB setup", script_content)
        
        # Check service startup coordination
        self.assertIn("Starting database services first", script_content)
        self.assertIn("Starting application services", script_content)
        
        # Check port validation
        self.assertIn("Port availability check", script_content)
    
    def test_intelligent_setup_script_generation_common(self):
        """Test intelligent setup script generation for common infrastructure"""
        config = SetupScriptConfig(
            username="testuser",
            project_name="common",
            template_type="common",
            port_assignment=self.port_assignment,
            has_common_project=False,
            output_dir=self.output_dir,
            services=["postgres", "mongodb", "redis", "chromadb", "jaeger", "prometheus", "grafana"]
        )
        
        script_content = self.manager._generate_intelligent_setup_script(config)
        
        # Check common infrastructure setup
        self.assertIn("Setting up common (common project)", script_content)
        self.assertIn("PostgreSQL setup", script_content)
        self.assertIn("MongoDB setup", script_content)
        self.assertIn("Redis setup", script_content)
        
        # Check observability services
        self.assertIn("Jaeger", script_content)
        self.assertIn("Prometheus", script_content)
        self.assertIn("Grafana", script_content)
    
    def test_setup_template_processing(self):
        """Test processing of existing setup templates"""
        # Create a test template
        template_content = """#!/bin/bash
# Test Template for {{PROJECT_NAME}}
echo "Setting up {{USERNAME}} project"
echo "Backend port: {{BACKEND_PORT}}"
echo "Frontend port: {{FRONTEND_PORT}}"
"""
        
        template_path = os.path.join(self.templates_dir, "rag", "setup.sh.template")
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        
        with open(template_path, 'w') as f:
            f.write(template_content)
        
        config = SetupScriptConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            output_dir=self.output_dir,
            services=["backend", "frontend"]
        )
        
        processed_content = self.manager._process_setup_template(template_path, config)
        
        # Check variable substitution
        self.assertIn("test-rag", processed_content)
        self.assertIn("testuser", processed_content)
        self.assertIn("8007", processed_content)  # Backend port (8th port)
        self.assertIn("8008", processed_content)  # Frontend port (9th port)
    
    def test_setup_variables_generation(self):
        """Test setup script variable generation"""
        config = SetupScriptConfig(
            username="testuser",
            project_name="test-project",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            output_dir=self.output_dir,
            services=["backend", "frontend"]
        )
        
        variables = self.manager._generate_setup_variables(config)
        
        # Check basic variables
        self.assertEqual(variables['USERNAME'], "testuser")
        self.assertEqual(variables['PROJECT_NAME'], "test-project")
        self.assertEqual(variables['TEMPLATE_TYPE'], "rag")
        self.assertTrue(variables['HAS_COMMON_PROJECT'])
        
        # Check port variables
        self.assertEqual(variables['POSTGRES_PORT'], 8000)
        self.assertEqual(variables['MONGODB_PORT'], 8001)
        self.assertEqual(variables['REDIS_PORT'], 8002)
        self.assertEqual(variables['BACKEND_PORT'], 8007)
        self.assertEqual(variables['FRONTEND_PORT'], 8008)
    
    def test_create_setup_script_file(self):
        """Test creating setup script file"""
        config = SetupScriptConfig(
            username="testuser",
            project_name="test-project",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            output_dir=self.output_dir,
            services=["backend", "frontend"]
        )
        
        script_path = self.manager.create_setup_script(config)
        
        # Check file was created
        self.assertTrue(os.path.exists(script_path))
        self.assertEqual(script_path, os.path.join(self.output_dir, "setup.sh"))
        
        # Check file content
        with open(script_path, 'r') as f:
            content = f.read()
        
        self.assertIn("#!/bin/bash", content)
        self.assertIn("testuser", content)
        self.assertIn("test-project", content)
    
    def test_convenience_function(self):
        """Test convenience function for setup script generation"""
        script_path = generate_setup_script(
            username="testuser",
            project_name="test-project",
            template_type="agent",
            port_assignment=self.port_assignment,
            output_dir=self.output_dir,
            services=["backend", "frontend", "worker"],
            has_common_project=False,
            templates_dir=self.templates_dir
        )
        
        # Check file was created
        self.assertTrue(os.path.exists(script_path))
        
        # Check content
        with open(script_path, 'r') as f:
            content = f.read()
        
        self.assertIn("agent project", content)
        self.assertIn("testuser", content)
    
    def test_database_detection_logic(self):
        """Test database detection in setup scripts"""
        # Test RAG with shared infrastructure
        config_shared = SetupScriptConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            output_dir=self.output_dir,
            services=["backend", "frontend"]
        )
        
        script_shared = self.manager._generate_database_setup(config_shared)
        self.assertIn("Common project services are not running", script_shared)
        self.assertIn("cd ../common && ./setup.sh", script_shared)
        
        # Test RAG standalone
        config_standalone = SetupScriptConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=False,
            output_dir=self.output_dir,
            services=["backend", "frontend", "postgres", "redis", "chromadb"]
        )
        
        script_standalone = self.manager._generate_database_setup(config_standalone)
        self.assertIn("PostgreSQL setup", script_standalone)
        self.assertIn("init.sql", script_standalone)
    
    def test_health_checks_generation(self):
        """Test health check generation for different services"""
        config = SetupScriptConfig(
            username="testuser",
            project_name="test-project",
            template_type="agent",
            port_assignment=self.port_assignment,
            has_common_project=False,
            output_dir=self.output_dir,
            services=["backend", "frontend", "worker", "postgres", "mongodb", "redis"]
        )
        
        health_checks = self.manager._generate_health_checks(config)
        
        # Check different service health checks
        self.assertIn("wait_for_service", health_checks)
        self.assertIn("pg_isready", health_checks)
        self.assertIn("mongosh", health_checks)
        self.assertIn("redis-cli ping", health_checks)
        self.assertIn("curl -f http://localhost", health_checks)
    
    def test_error_recovery_guidance(self):
        """Test error recovery guidance generation"""
        config = SetupScriptConfig(
            username="testuser",
            project_name="test-project",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            output_dir=self.output_dir,
            services=["backend", "frontend"]
        )
        
        recovery_guidance = self.manager._generate_error_recovery_guidance(config)
        
        # Check troubleshooting steps
        self.assertIn("Troubleshooting Information", recovery_guidance)
        self.assertIn("docker-compose logs", recovery_guidance)
        self.assertIn("docker-compose restart", recovery_guidance)
        self.assertIn("docker-compose down", recovery_guidance)
        self.assertIn("Full reset", recovery_guidance)
        self.assertIn("Network issues", recovery_guidance)
        self.assertIn("Port conflicts", recovery_guidance)
    
    def test_service_startup_coordination(self):
        """Test service startup coordination"""
        # Test with databases
        config_with_db = SetupScriptConfig(
            username="testuser",
            project_name="test-project",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=False,
            output_dir=self.output_dir,
            services=["backend", "frontend", "postgres", "redis"]
        )
        
        startup_script = self.manager._generate_service_startup(config_with_db)
        self.assertIn("Starting database services first", startup_script)
        self.assertIn("Starting application services", startup_script)
        
        # Test shared infrastructure mode
        config_shared = SetupScriptConfig(
            username="testuser",
            project_name="test-project",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            output_dir=self.output_dir,
            services=["backend", "frontend"]
        )
        
        startup_shared = self.manager._generate_service_startup(config_shared)
        self.assertIn("databases provided by common project", startup_shared)
    
    def test_port_checking_logic(self):
        """Test port availability checking"""
        config = SetupScriptConfig(
            username="testuser",
            project_name="test-project",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            output_dir=self.output_dir,
            services=["backend", "frontend"]
        )
        
        port_check = self.manager._generate_port_check(config)
        
        # Check port checking logic
        self.assertIn("Port availability check", port_check)
        self.assertIn("netstat -tuln", port_check)
        self.assertIn("lsof -ti:", port_check)
        self.assertIn("Port conflicts", port_check)
    
    def test_custom_variables_support(self):
        """Test custom variables in setup scripts"""
        custom_vars = {
            'CUSTOM_API_KEY': 'test-key',
            'CUSTOM_ENDPOINT': 'https://api.example.com'
        }
        
        config = SetupScriptConfig(
            username="testuser",
            project_name="test-project",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            output_dir=self.output_dir,
            services=["backend", "frontend"],
            custom_variables=custom_vars
        )
        
        variables = self.manager._generate_setup_variables(config)
        
        # Check custom variables are included
        self.assertEqual(variables['CUSTOM_API_KEY'], 'test-key')
        self.assertEqual(variables['CUSTOM_ENDPOINT'], 'https://api.example.com')


class TestSetupScriptIntegration(unittest.TestCase):
    """Test setup script integration with project manager"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.templates_dir = os.path.join(self.test_dir, "templates")
        os.makedirs(self.templates_dir, exist_ok=True)
        
        self.port_assignment = PortAssignment(
            login_id="testuser",
            segment1_start=8000,
            segment1_end=8009
        )
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_template_fallback_behavior(self):
        """Test fallback to intelligent generation when template doesn't exist"""
        manager = SetupScriptManager(self.templates_dir)
        
        config = SetupScriptConfig(
            username="testuser",
            project_name="test-project",
            template_type="nonexistent",
            port_assignment=self.port_assignment,
            has_common_project=False,
            output_dir=self.test_dir,
            services=["backend"]
        )
        
        # Should generate intelligent script since template doesn't exist
        content = manager._generate_setup_script_content(config)
        
        self.assertIn("#!/bin/bash", content)
        self.assertIn("testuser", content)
        self.assertIn("test-project", content)
    
    def test_template_priority_behavior(self):
        """Test that existing templates take priority over intelligent generation"""
        # Create a simple template
        template_dir = os.path.join(self.templates_dir, "test")
        os.makedirs(template_dir, exist_ok=True)
        
        template_content = "#!/bin/bash\necho 'Template for {{USERNAME}}'"
        template_path = os.path.join(template_dir, "setup.sh.template")
        
        with open(template_path, 'w') as f:
            f.write(template_content)
        
        manager = SetupScriptManager(self.templates_dir)
        
        config = SetupScriptConfig(
            username="testuser",
            project_name="test-project",
            template_type="test",
            port_assignment=self.port_assignment,
            has_common_project=False,
            output_dir=self.test_dir,
            services=["backend"]
        )
        
        content = manager._generate_setup_script_content(config)
        
        # Should use template, not intelligent generation
        self.assertIn("Template for testuser", content)
        self.assertNotIn("Checking prerequisites", content)  # Not from intelligent generation


if __name__ == '__main__':
    unittest.main()