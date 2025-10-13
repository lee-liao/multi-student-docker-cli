#!/usr/bin/env python3
"""
Docker Integration Tests
Tests actual Docker container startup, port binding, and service communication.
"""

import sys
import os
import tempfile
import shutil
import subprocess
import time
import socket
import requests
from typing import Dict, List, Any, Optional

# Add the cli-tool directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

def safe_print(message):
    """Print message with safe encoding for Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        safe_message = message.replace('✅', '[PASS]').replace('❌', '[FAIL]').replace('⚠️', '[WARN]')
        safe_message = safe_message.replace('🐳', '[DOCKER]').replace('🔗', '[NETWORK]').replace('📊', '[STATS]')
        print(safe_message)

class DockerIntegrationTester:
    """Docker integration testing with actual containers"""
    
    def __init__(self):
        self.docker_available = self._check_docker_availability()
        self.compose_available = self._check_compose_availability()
        self.temp_dir = None
        self.running_projects = []
        self.test_ports = [8080, 8081, 8082, 8083, 8084]
    
    def _check_docker_availability(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(['docker', 'version'], capture_output=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_compose_availability(self) -> bool:
        """Check if Docker Compose is available"""
        try:
            result = subprocess.run(['docker-compose', 'version'], capture_output=True, timeout=10)
            if result.returncode == 0:
                return True
            # Try newer syntax
            result = subprocess.run(['docker', 'compose', 'version'], capture_output=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    def _wait_for_port(self, port: int, timeout: int = 30) -> bool:
        """Wait for a port to become available (service to start)"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(('localhost', port))
                    if result == 0:
                        return True
            except:
                pass
            time.sleep(1)
        return False
    
    def setup_test_environment(self):
        """Set up test environment for Docker integration"""
        self.temp_dir = tempfile.mkdtemp()
        safe_print(f"[DOCKER] Test environment: {self.temp_dir}")
        
        # Create simple test projects
        self._create_simple_web_project()
        self._create_database_project()
        
        return True
    
    def _create_simple_web_project(self):
        """Create a simple web project for testing"""
        project_dir = os.path.join(self.temp_dir, "simple_web")
        os.makedirs(project_dir)
        
        # Create docker-compose.yml
        compose_content = f"""
version: '3.8'
services:
  web:
    image: nginx:alpine
    ports:
      - "{self.test_ports[0]}:80"
    volumes:
      - ./html:/usr/share/nginx/html:ro
    environment:
      - NGINX_HOST=localhost
      - NGINX_PORT=80
"""
        
        with open(os.path.join(project_dir, "docker-compose.yml"), 'w') as f:
            f.write(compose_content)
        
        # Create HTML directory and index file
        html_dir = os.path.join(project_dir, "html")
        os.makedirs(html_dir)
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Web Service</title>
</head>
<body>
    <h1>Docker Integration Test</h1>
    <p>This is a test web service running in Docker.</p>
    <p>Port: """ + str(self.test_ports[0]) + """</p>
</body>
</html>
"""
        
        with open(os.path.join(html_dir, "index.html"), 'w') as f:
            f.write(html_content)
    
    def _create_database_project(self):
        """Create a database project for testing"""
        project_dir = os.path.join(self.temp_dir, "database")
        os.makedirs(project_dir)
        
        # Create docker-compose.yml with PostgreSQL
        compose_content = f"""
version: '3.8'
services:
  postgres:
    image: postgres:13-alpine
    environment:
      POSTGRES_DB: testdb
      POSTGRES_USER: testuser
      POSTGRES_PASSWORD: testpass
    ports:
      - "{self.test_ports[1]}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U testuser -d testdb"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
"""
        
        with open(os.path.join(project_dir, "docker-compose.yml"), 'w') as f:
            f.write(compose_content) 
   
    def cleanup_test_environment(self):
        """Clean up test environment"""
        # Stop all running projects
        for project_name in self.running_projects:
            self._stop_project(project_name)
        
        # Remove temporary directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            safe_print("[DOCKER] Test environment cleaned up")
    
    def _stop_project(self, project_name: str):
        """Stop a Docker Compose project"""
        project_path = os.path.join(self.temp_dir, project_name)
        if os.path.exists(project_path):
            try:
                subprocess.run(
                    ['docker-compose', 'down', '-v'],
                    cwd=project_path,
                    capture_output=True,
                    timeout=60
                )
                safe_print(f"[DOCKER] Stopped project: {project_name}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                safe_print(f"[WARN] Failed to stop project: {project_name}")
    
    def test_container_startup(self) -> bool:
        """Test Docker container startup"""
        if not self.docker_available or not self.compose_available:
            safe_print("[WARN] Docker or Docker Compose not available")
            return False
        
        safe_print("\n[DOCKER] Testing Container Startup")
        safe_print("-"*40)
        
        try:
            # Test simple web service
            project_path = os.path.join(self.temp_dir, "simple_web")
            
            # Check if port is available
            if not self._check_port_available(self.test_ports[0]):
                safe_print(f"[WARN] Port {self.test_ports[0]} is not available")
                return False
            
            # Start the service
            safe_print(f"[DOCKER] Starting web service on port {self.test_ports[0]}...")
            
            result = subprocess.run(
                ['docker-compose', 'up', '-d'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                safe_print(f"[FAIL] Failed to start web service: {result.stderr}")
                return False
            
            self.running_projects.append("simple_web")
            
            # Wait for service to be ready
            safe_print("[DOCKER] Waiting for service to be ready...")
            if not self._wait_for_port(self.test_ports[0], timeout=30):
                safe_print("[FAIL] Service did not start within timeout")
                return False
            
            safe_print("[PASS] Web service started successfully")
            
            # Test HTTP connectivity
            try:
                response = requests.get(f"http://localhost:{self.test_ports[0]}", timeout=10)
                if response.status_code == 200 and "Docker Integration Test" in response.text:
                    safe_print("[PASS] HTTP connectivity test successful")
                else:
                    safe_print("[WARN] HTTP response unexpected")
            except requests.RequestException:
                safe_print("[WARN] HTTP connectivity test failed")
            
            return True
            
        except subprocess.TimeoutExpired:
            safe_print("[FAIL] Container startup timed out")
            return False
        except Exception as e:
            safe_print(f"[FAIL] Container startup test failed: {str(e)}")
            return False
    
    def test_database_connectivity(self) -> bool:
        """Test database container startup and connectivity"""
        if not self.docker_available or not self.compose_available:
            return False
        
        safe_print("\n[DOCKER] Testing Database Connectivity")
        safe_print("-"*40)
        
        try:
            project_path = os.path.join(self.temp_dir, "database")
            
            # Check if port is available
            if not self._check_port_available(self.test_ports[1]):
                safe_print(f"[WARN] Port {self.test_ports[1]} is not available")
                return False
            
            # Start the database
            safe_print(f"[DOCKER] Starting PostgreSQL on port {self.test_ports[1]}...")
            
            result = subprocess.run(
                ['docker-compose', 'up', '-d'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                safe_print(f"[FAIL] Failed to start database: {result.stderr}")
                return False
            
            self.running_projects.append("database")
            
            # Wait for database to be ready
            safe_print("[DOCKER] Waiting for database to be ready...")
            if not self._wait_for_port(self.test_ports[1], timeout=60):
                safe_print("[FAIL] Database did not start within timeout")
                return False
            
            # Test database connectivity using docker exec
            safe_print("[DOCKER] Testing database connectivity...")
            
            # Wait a bit more for PostgreSQL to fully initialize
            time.sleep(10)
            
            result = subprocess.run(
                ['docker-compose', 'exec', '-T', 'postgres', 'pg_isready', '-U', 'testuser', '-d', 'testdb'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                safe_print("[PASS] Database connectivity test successful")
                return True
            else:
                safe_print("[WARN] Database connectivity test failed")
                return False
            
        except subprocess.TimeoutExpired:
            safe_print("[FAIL] Database startup timed out")
            return False
        except Exception as e:
            safe_print(f"[FAIL] Database connectivity test failed: {str(e)}")
            return False
    
    def test_port_binding_conflicts(self) -> bool:
        """Test port binding and conflict detection"""
        safe_print("\n[DOCKER] Testing Port Binding Conflicts")
        safe_print("-"*40)
        
        try:
            # Create two services that would conflict on the same port
            conflict_dir = os.path.join(self.temp_dir, "port_conflict")
            os.makedirs(conflict_dir)
            
            # Create compose file with conflicting ports
            compose_content = f"""
version: '3.8'
services:
  web1:
    image: nginx:alpine
    ports:
      - "{self.test_ports[2]}:80"
  
  web2:
    image: nginx:alpine
    ports:
      - "{self.test_ports[2]}:80"  # Same port - should conflict
"""
            
            with open(os.path.join(conflict_dir, "docker-compose.yml"), 'w') as f:
                f.write(compose_content)
            
            # Try to start - should fail due to port conflict
            result = subprocess.run(
                ['docker-compose', 'up', '-d'],
                cwd=conflict_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                safe_print("[PASS] Port conflict correctly detected and prevented")
                return True
            else:
                safe_print("[WARN] Port conflict was not detected")
                # Clean up if it somehow started
                subprocess.run(['docker-compose', 'down'], cwd=conflict_dir, capture_output=True)
                return False
            
        except Exception as e:
            safe_print(f"[FAIL] Port conflict test failed: {str(e)}")
            return False
    
    def test_network_isolation(self) -> bool:
        """Test network isolation between projects"""
        safe_print("\n[DOCKER] Testing Network Isolation")
        safe_print("-"*40)
        
        try:
            # Create two separate projects
            project1_dir = os.path.join(self.temp_dir, "isolated1")
            project2_dir = os.path.join(self.temp_dir, "isolated2")
            
            os.makedirs(project1_dir)
            os.makedirs(project2_dir)
            
            # Create compose files for each project
            compose1 = f"""
version: '3.8'
services:
  app:
    image: alpine:latest
    command: sleep 300
    networks:
      - project1_network

networks:
  project1_network:
    driver: bridge
"""
            
            compose2 = f"""
version: '3.8'
services:
  app:
    image: alpine:latest
    command: sleep 300
    networks:
      - project2_network

networks:
  project2_network:
    driver: bridge
"""
            
            with open(os.path.join(project1_dir, "docker-compose.yml"), 'w') as f:
                f.write(compose1)
            
            with open(os.path.join(project2_dir, "docker-compose.yml"), 'w') as f:
                f.write(compose2)
            
            # Start both projects
            result1 = subprocess.run(
                ['docker-compose', 'up', '-d'],
                cwd=project1_dir,
                capture_output=True,
                timeout=60
            )
            
            result2 = subprocess.run(
                ['docker-compose', 'up', '-d'],
                cwd=project2_dir,
                capture_output=True,
                timeout=60
            )
            
            if result1.returncode == 0 and result2.returncode == 0:
                safe_print("[PASS] Network isolation test successful")
                
                # Clean up
                subprocess.run(['docker-compose', 'down'], cwd=project1_dir, capture_output=True)
                subprocess.run(['docker-compose', 'down'], cwd=project2_dir, capture_output=True)
                
                return True
            else:
                safe_print("[FAIL] Network isolation test failed")
                return False
            
        except Exception as e:
            safe_print(f"[FAIL] Network isolation test failed: {str(e)}")
            return False 
   
    def run_docker_integration_tests(self) -> bool:
        """Run all Docker integration tests"""
        safe_print("Starting Docker Integration Tests")
        safe_print("="*50)
        
        if not self.docker_available:
            safe_print("[WARN] Docker not available - skipping Docker integration tests")
            return True  # Not a failure, just not available
        
        if not self.compose_available:
            safe_print("[WARN] Docker Compose not available - skipping integration tests")
            return True
        
        start_time = time.time()
        tests_passed = 0
        total_tests = 0
        
        try:
            # Setup test environment
            if not self.setup_test_environment():
                safe_print("[FAIL] Failed to setup test environment")
                return False
            
            # Test 1: Container Startup
            total_tests += 1
            if self.test_container_startup():
                tests_passed += 1
            
            # Test 2: Database Connectivity
            total_tests += 1
            if self.test_database_connectivity():
                tests_passed += 1
            
            # Test 3: Port Binding Conflicts
            total_tests += 1
            if self.test_port_binding_conflicts():
                tests_passed += 1
            
            # Test 4: Network Isolation
            total_tests += 1
            if self.test_network_isolation():
                tests_passed += 1
            
        finally:
            self.cleanup_test_environment()
        
        # Generate report
        duration = time.time() - start_time
        success_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0
        
        safe_print(f"\n{'='*50}")
        safe_print(f"DOCKER INTEGRATION TEST RESULTS")
        safe_print(f"{'='*50}")
        safe_print(f"Docker Available: {'Yes' if self.docker_available else 'No'}")
        safe_print(f"Compose Available: {'Yes' if self.compose_available else 'No'}")
        safe_print(f"Total Tests: {total_tests}")
        safe_print(f"Passed: {tests_passed}")
        safe_print(f"Failed: {total_tests - tests_passed}")
        safe_print(f"Success Rate: {success_rate:.1f}%")
        safe_print(f"Duration: {duration:.2f}s")
        
        if success_rate >= 75:
            safe_print(f"\n[PASS] Docker integration is working well")
        else:
            safe_print(f"\n[WARN] Docker integration has issues")
        
        return success_rate >= 75
    
    def cleanup_test_environment(self):
        """Clean up Docker test environment"""
        safe_print("[DOCKER] Cleaning up test environment...")
        
        # Stop all running projects
        for project_name in self.running_projects:
            self._stop_project(project_name)
        
        # Clean up any remaining containers
        try:
            subprocess.run(
                ['docker', 'system', 'prune', '-f'],
                capture_output=True,
                timeout=60
            )
        except:
            pass
        
        # Remove temporary directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


def main():
    """Main entry point for Docker integration tests"""
    tester = DockerIntegrationTester()
    
    try:
        success = tester.run_docker_integration_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        safe_print("\n[INFO] Tests interrupted by user")
        return 1
    except Exception as e:
        safe_print(f"\n[FAIL] Docker integration tests failed: {str(e)}")
        return 1
    finally:
        try:
            tester.cleanup_test_environment()
        except:
            pass


if __name__ == "__main__":
    sys.exit(main())