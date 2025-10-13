#!/usr/bin/env python3
"""
Test Suite for CORS Configuration Manager
Tests CORS origin generation, container hostname generation,
and different rendering scenarios (CSR/SSR).
"""

import unittest
from src.config.cors_config_manager import (
    CorsConfigManager, 
    CorsConfig, 
    create_cors_config,
    generate_cors_variables
)
from src.core.port_assignment import PortAssignment


class TestCorsConfigManager(unittest.TestCase):
    """Test CORS configuration generation functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create test port assignment
        self.port_assignment = PortAssignment(
            login_id="testuser",
            segment1_start=8000,
            segment1_end=8009
        )
        
        # Initialize manager
        self.manager = CorsConfigManager()
    
    def test_cors_config_creation(self):
        """Test CORS configuration creation"""
        config = create_cors_config(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True
        )
        
        self.assertEqual(config.username, "testuser")
        self.assertEqual(config.project_name, "test-rag")
        self.assertEqual(config.template_type, "rag")
        self.assertTrue(config.has_common_project)
        self.assertEqual(config.frontend_port, 8008)  # 9th port (index 8)
        self.assertEqual(config.backend_port, 8007)   # 8th port (index 7)
    
    def test_csr_origins_generation(self):
        """Test Client-Side Rendering origins generation"""
        config = CorsConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            frontend_port=8008,
            backend_port=8007
        )
        
        csr_origins = self.manager._generate_csr_origins(config)
        
        # Check primary origins
        self.assertIn("http://localhost:8008", csr_origins)  # Frontend
        self.assertIn("http://localhost:8007", csr_origins)  # Backend
        
        # Check common dev ports that are in assigned range
        self.assertIn("http://localhost:3000", csr_origins)
        self.assertIn("http://localhost:5000", csr_origins)
        
        # Should be sorted
        self.assertEqual(csr_origins, sorted(csr_origins))
    
    def test_ssr_origins_generation(self):
        """Test Server-Side Rendering origins generation"""
        config = CorsConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            frontend_port=8008,
            backend_port=8007
        )
        
        ssr_origins = self.manager._generate_ssr_origins(config)
        
        # Should include all CSR origins
        csr_origins = self.manager._generate_csr_origins(config)
        for origin in csr_origins:
            self.assertIn(origin, ssr_origins)
        
        # Should include container hostnames
        self.assertTrue(any("testuser-rag-frontend" in origin for origin in ssr_origins))
        self.assertIn("http://testuser-rag-backend:8000", ssr_origins)
    
    def test_development_origins_generation(self):
        """Test comprehensive development origins generation"""
        config = CorsConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            frontend_port=8008,
            backend_port=8007
        )
        
        dev_origins = self.manager._generate_development_origins(config)
        
        # Should include all assigned ports
        for port in self.port_assignment.all_ports:
            self.assertIn(f"http://localhost:{port}", dev_origins)
        
        # Should include HTTPS variants
        self.assertIn("https://localhost:8008", dev_origins)
        self.assertIn("https://localhost:8007", dev_origins)
        
        # Should include common dev tool ports
        self.assertIn("http://localhost:3000", dev_origins)
        self.assertIn("http://localhost:4200", dev_origins)
        self.assertIn("http://localhost:5173", dev_origins)
    
    def test_container_hostnames_rag(self):
        """Test container hostname generation for RAG projects"""
        config = CorsConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            frontend_port=8008,
            backend_port=8007
        )
        
        hostnames = self.manager._generate_container_hostnames(config)
        
        self.assertEqual(hostnames['frontend'], "http://testuser-rag-frontend:3000")
        self.assertEqual(hostnames['backend'], "http://testuser-rag-backend:8000")
        
        # Should include shared infrastructure hostnames
        self.assertEqual(hostnames['postgres_shared'], "http://testuser-postgres:5432")
        self.assertEqual(hostnames['redis_shared'], "http://testuser-redis:6379")
    
    def test_container_hostnames_agent(self):
        """Test container hostname generation for Agent projects"""
        config = CorsConfig(
            username="testuser",
            project_name="test-agent",
            template_type="agent",
            port_assignment=self.port_assignment,
            has_common_project=False,
            frontend_port=8008,
            backend_port=8007
        )
        
        hostnames = self.manager._generate_container_hostnames(config)
        
        self.assertEqual(hostnames['frontend'], "http://testuser-agent-frontend:3000")
        self.assertEqual(hostnames['backend'], "http://testuser-agent-backend:8000")
        self.assertEqual(hostnames['worker'], "http://testuser-agent-worker:8001")
        
        # Should not include shared infrastructure hostnames for standalone
        self.assertNotIn('postgres_shared', hostnames)
    
    def test_container_hostnames_common(self):
        """Test container hostname generation for Common projects"""
        config = CorsConfig(
            username="testuser",
            project_name="common",
            template_type="common",
            port_assignment=self.port_assignment,
            has_common_project=False,
            frontend_port=8008,
            backend_port=8007
        )
        
        hostnames = self.manager._generate_container_hostnames(config)
        
        # Should include all infrastructure services
        self.assertEqual(hostnames['postgres'], "http://testuser-postgres:5432")
        self.assertEqual(hostnames['mongodb'], "http://testuser-mongodb:27017")
        self.assertEqual(hostnames['redis'], "http://testuser-redis:6379")
        self.assertEqual(hostnames['chromadb'], "http://testuser-chromadb:8000")
        self.assertEqual(hostnames['jaeger'], "http://testuser-jaeger:16686")
        self.assertEqual(hostnames['prometheus'], "http://testuser-prometheus:9090")
        self.assertEqual(hostnames['grafana'], "http://testuser-grafana:3000")
    
    def test_complete_cors_config_generation(self):
        """Test complete CORS configuration generation"""
        config = CorsConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            frontend_port=8008,
            backend_port=8007
        )
        
        cors_config = self.manager.generate_cors_config(config)
        
        # Check required keys
        required_keys = [
            'CORS_ORIGINS_CSR', 'CORS_ORIGINS_CSR_LIST',
            'CORS_ORIGINS_SSR', 'CORS_ORIGINS_SSR_LIST',
            'CORS_ORIGINS_DEV', 'CORS_ORIGINS_DEV_LIST',
            'CONTAINER_HOSTNAMES', 'CONTAINER_HOSTNAMES_LIST',
            'FRONTEND_URL_LOCALHOST', 'BACKEND_URL_LOCALHOST',
            'FRONTEND_URL_CONTAINER', 'BACKEND_URL_CONTAINER',
            'FRONTEND_PORT', 'BACKEND_PORT'
        ]
        
        for key in required_keys:
            self.assertIn(key, cors_config)
        
        # Check URL formats
        self.assertEqual(cors_config['FRONTEND_URL_LOCALHOST'], "http://localhost:8008")
        self.assertEqual(cors_config['BACKEND_URL_LOCALHOST'], "http://localhost:8007")
        self.assertEqual(cors_config['FRONTEND_URL_CONTAINER'], "http://testuser-rag-frontend:3000")
        self.assertEqual(cors_config['BACKEND_URL_CONTAINER'], "http://testuser-rag-backend:8000")
        
        # Check port values
        self.assertEqual(cors_config['FRONTEND_PORT'], 8008)
        self.assertEqual(cors_config['BACKEND_PORT'], 8007)
        
        # Check that CSR origins are comma-separated string
        self.assertIsInstance(cors_config['CORS_ORIGINS_CSR'], str)
        self.assertIn("http://localhost:8008", cors_config['CORS_ORIGINS_CSR'])
        
        # Check that CSR origins list is actually a list
        self.assertIsInstance(cors_config['CORS_ORIGINS_CSR_LIST'], list)
        self.assertIn("http://localhost:8008", cors_config['CORS_ORIGINS_CSR_LIST'])
    
    def test_custom_origins_and_ports(self):
        """Test CORS configuration with custom origins and additional ports"""
        config = CorsConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            frontend_port=8008,
            backend_port=8007,
            additional_ports=[8001, 8002],
            custom_origins=["https://example.com", "https://api.example.com"]
        )
        
        csr_origins = self.manager._generate_csr_origins(config)
        
        # Should include additional ports
        self.assertIn("http://localhost:8001", csr_origins)
        self.assertIn("http://localhost:8002", csr_origins)
        
        # Should include custom origins
        self.assertIn("https://example.com", csr_origins)
        self.assertIn("https://api.example.com", csr_origins)
    
    def test_cors_documentation_generation(self):
        """Test CORS documentation generation"""
        config = CorsConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            frontend_port=8008,
            backend_port=8007
        )
        
        documentation = self.manager.generate_cors_documentation(config)
        
        # Check documentation content
        self.assertIn("CORS Configuration Guide", documentation)
        self.assertIn("RAG Applications", documentation)
        self.assertIn("Client-Side Rendering (CSR)", documentation)
        self.assertIn("Server-Side Rendering (SSR)", documentation)
        self.assertIn("http://localhost:8008", documentation)
        self.assertIn("http://localhost:8007", documentation)
        self.assertIn("testuser-rag-frontend", documentation)
        self.assertIn("Common CORS Issues", documentation)
        self.assertIn("Testing CORS Configuration", documentation)
    
    def test_cors_config_validation(self):
        """Test CORS configuration validation"""
        # Valid configuration
        valid_config = CorsConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            frontend_port=8008,
            backend_port=8007
        )
        
        issues = self.manager.validate_cors_config(valid_config)
        self.assertEqual(len(issues), 0)
        
        # Invalid configuration - ports not in range
        invalid_config = CorsConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            frontend_port=9999,  # Not in assigned range
            backend_port=8007
        )
        
        issues = self.manager.validate_cors_config(invalid_config)
        self.assertGreater(len(issues), 0)
        self.assertTrue(any("Frontend port 9999 not in assigned port range" in issue for issue in issues))
        
        # Invalid configuration - same ports
        same_port_config = CorsConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            frontend_port=8007,
            backend_port=8007
        )
        
        issues = self.manager.validate_cors_config(same_port_config)
        self.assertTrue(any("Frontend and backend ports cannot be the same" in issue for issue in issues))
        
        # Invalid custom origins
        invalid_origins_config = CorsConfig(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True,
            frontend_port=8008,
            backend_port=8007,
            custom_origins=["example.com"]  # Missing protocol
        )
        
        issues = self.manager.validate_cors_config(invalid_origins_config)
        self.assertTrue(any("should include protocol" in issue for issue in issues))
    
    def test_convenience_function(self):
        """Test convenience function for generating CORS variables"""
        cors_vars = generate_cors_variables(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True
        )
        
        # Check that all expected variables are present
        self.assertIn('CORS_ORIGINS_CSR', cors_vars)
        self.assertIn('CORS_ORIGINS_SSR', cors_vars)
        self.assertIn('FRONTEND_URL_LOCALHOST', cors_vars)
        self.assertIn('BACKEND_URL_LOCALHOST', cors_vars)
        
        # Check values
        self.assertIn("http://localhost:8008", cors_vars['CORS_ORIGINS_CSR'])
        self.assertEqual(cors_vars['FRONTEND_URL_LOCALHOST'], "http://localhost:8008")
        self.assertEqual(cors_vars['BACKEND_URL_LOCALHOST'], "http://localhost:8007")
    
    def test_different_template_types(self):
        """Test CORS configuration for different template types"""
        # Test RAG
        rag_config = create_cors_config(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True
        )
        
        rag_hostnames = self.manager._generate_container_hostnames(rag_config)
        self.assertIn('frontend', rag_hostnames)
        self.assertIn('backend', rag_hostnames)
        self.assertNotIn('worker', rag_hostnames)
        
        # Test Agent
        agent_config = create_cors_config(
            username="testuser",
            project_name="test-agent",
            template_type="agent",
            port_assignment=self.port_assignment,
            has_common_project=False
        )
        
        agent_hostnames = self.manager._generate_container_hostnames(agent_config)
        self.assertIn('frontend', agent_hostnames)
        self.assertIn('backend', agent_hostnames)
        self.assertIn('worker', agent_hostnames)
        
        # Test Common
        common_config = create_cors_config(
            username="testuser",
            project_name="common",
            template_type="common",
            port_assignment=self.port_assignment,
            has_common_project=False
        )
        
        common_hostnames = self.manager._generate_container_hostnames(common_config)
        self.assertIn('postgres', common_hostnames)
        self.assertIn('mongodb', common_hostnames)
        self.assertIn('grafana', common_hostnames)
    
    def test_port_assignment_edge_cases(self):
        """Test CORS configuration with edge cases in port assignment"""
        # Test with minimal ports
        minimal_ports = PortAssignment(
            login_id="testuser",
            segment1_start=8000,
            segment1_end=8002  # Only 3 ports
        )
        
        config = create_cors_config(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=minimal_ports,
            has_common_project=True
        )
        
        # Should still work with minimal ports
        self.assertEqual(config.frontend_port, 8002)  # Last port
        self.assertEqual(config.backend_port, 8001)   # Second to last port
        
        cors_config = self.manager.generate_cors_config(config)
        self.assertEqual(cors_config['FRONTEND_PORT'], 8002)
        self.assertEqual(cors_config['BACKEND_PORT'], 8001)
    
    def test_shared_vs_standalone_differences(self):
        """Test differences between shared and standalone CORS configurations"""
        # Shared configuration
        shared_config = create_cors_config(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=True
        )
        
        shared_hostnames = self.manager._generate_container_hostnames(shared_config)
        
        # Standalone configuration
        standalone_config = create_cors_config(
            username="testuser",
            project_name="test-rag",
            template_type="rag",
            port_assignment=self.port_assignment,
            has_common_project=False
        )
        
        standalone_hostnames = self.manager._generate_container_hostnames(standalone_config)
        
        # Shared should have shared infrastructure hostnames
        self.assertIn('postgres_shared', shared_hostnames)
        self.assertIn('redis_shared', shared_hostnames)
        
        # Standalone should not have shared infrastructure hostnames
        self.assertNotIn('postgres_shared', standalone_hostnames)
        self.assertNotIn('redis_shared', standalone_hostnames)


if __name__ == '__main__':
    unittest.main()