#!/usr/bin/env python3
"""
Test port verification with conflicts
"""

from src.monitoring.port_verification_system import PortVerificationSystem
from src.core.port_assignment import PortAssignment
import tempfile
import os

def test_port_conflicts():
    print('🧪 Testing Port Verification with Conflicts...')

    verifier = PortVerificationSystem()
    port_assignment = PortAssignment(login_id='testuser', segment1_start=8000, segment1_end=8009)

    # Test 1: Out of range ports
    print('\n1. Testing out-of-range ports...')
    test_dir = tempfile.mkdtemp()
    compose_content = """version: '3.8'
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

    compose_file = os.path.join(test_dir, 'docker-compose.yml')
    with open(compose_file, 'w') as f:
        f.write(compose_content)

    result = verifier.verify_project_ports(test_dir, port_assignment, 'testuser')
    print(f'   Valid: {result.is_valid}')
    print(f'   Conflicts: {len(result.conflicts)}')
    
    for conflict in result.conflicts:
        print(f'      ❌ {conflict.service_name}: {conflict.description}')
        if conflict.suggestion:
            print(f'         💡 {conflict.suggestion}')

    # Test 2: Duplicate ports
    print('\n2. Testing duplicate ports...')
    test_dir2 = tempfile.mkdtemp()
    compose_content2 = """version: '3.8'
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

    compose_file2 = os.path.join(test_dir2, 'docker-compose.yml')
    with open(compose_file2, 'w') as f:
        f.write(compose_content2)

    result2 = verifier.verify_project_ports(test_dir2, port_assignment, 'testuser')
    print(f'   Valid: {result2.is_valid}')
    print(f'   Conflicts: {len(result2.conflicts)}')
    
    for conflict in result2.conflicts:
        print(f'      ❌ {conflict.service_name}: {conflict.description}')

    print('\n🎉 Port conflict testing completed!')

if __name__ == '__main__':
    test_port_conflicts()