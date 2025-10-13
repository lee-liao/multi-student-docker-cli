#!/usr/bin/env python3
"""
Simple test for port verification system
"""

from src.monitoring.port_verification_system import DockerComposeParser, PortVerificationSystem
from src.core.port_assignment import PortAssignment
import tempfile
import os

def test_port_verification():
    print('🧪 Testing Port Verification System...')

    # Test 1: Docker Compose Parser
    print('\n1. Testing Docker Compose Parser...')
    parser = DockerComposeParser()

    # Create test compose file
    test_dir = tempfile.mkdtemp()
    compose_content = """version: '3.8'
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

    compose_file = os.path.join(test_dir, 'docker-compose.yml')
    with open(compose_file, 'w') as f:
        f.write(compose_content)

    try:
        mappings = parser.parse_compose_file(compose_file)
        print(f'   ✅ Parsed {len(mappings)} port mappings')
        for mapping in mappings:
            print(f'      {mapping.service_name}: {mapping.host_port} → {mapping.container_port}')
    except Exception as e:
        print(f'   ❌ Parser failed: {e}')
        return False

    # Test 2: Port Verification
    print('\n2. Testing Port Verification...')
    verifier = PortVerificationSystem()
    port_assignment = PortAssignment(login_id='testuser', segment1_start=8000, segment1_end=8009)

    try:
        result = verifier.verify_project_ports(test_dir, port_assignment, 'testuser')
        print(f'   ✅ Verification completed')
        print(f'      Valid: {result.is_valid}')
        print(f'      Ports used: {result.total_ports_used}')
        print(f'      Conflicts: {len(result.conflicts)}')
        print(f'      Warnings: {len(result.warnings)}')
        
        if result.suggestions:
            print(f'      Suggestions: {result.suggestions[0]}')
            
    except Exception as e:
        print(f'   ❌ Verification failed: {e}')
        import traceback
        traceback.print_exc()
        return False

    print('\n🎉 Port verification system test completed!')
    return True

if __name__ == '__main__':
    test_port_verification()