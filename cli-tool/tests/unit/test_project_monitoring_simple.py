#!/usr/bin/env python3
"""
Simple test for project status monitoring system
"""

from src.monitoring.project_status_monitor import ProjectScanner, SystemMonitor, PortUsageAnalyzer, ProjectStatusMonitor
from src.core.port_assignment import PortAssignment
import tempfile
import os

def test_project_monitoring():
    print('🧪 Testing Project Status Monitoring System...')

    # Test 1: Project Scanner
    print('\n1. Testing Project Scanner...')
    test_dir = tempfile.mkdtemp()
    scanner = ProjectScanner(test_dir)

    # Create test project
    project_dir = os.path.join(test_dir, 'test-project')
    os.makedirs(project_dir)

    compose_content = """version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "8000:80"
  api:
    image: node
    ports:
      - "8001:3000"
"""

    with open(os.path.join(project_dir, 'docker-compose.yml'), 'w') as f:
        f.write(compose_content)

    try:
        projects = scanner.scan_projects()
        print(f'   ✅ Found {len(projects)} projects')
        
        if projects:
            project = projects[0]
            print(f'      Name: {project.name}')
            print(f'      Ports: {project.ports_used}')
            print(f'      Compose version: {project.compose_version}')
            
    except Exception as e:
        print(f'   ❌ Scanner failed: {e}')
        return False

    # Test 2: System Monitor
    print('\n2. Testing System Monitor...')
    monitor = SystemMonitor()

    try:
        system_status = monitor.get_system_status()
        print(f'   ✅ System status retrieved')
        print(f'      Docker available: {system_status.docker_available}')
        print(f'      Compose available: {system_status.compose_available}')
        print(f'      Total containers: {system_status.total_containers}')
        
    except Exception as e:
        print(f'   ❌ System monitor failed: {e}')
        return False

    # Test 3: Port Usage Analyzer
    print('\n3. Testing Port Usage Analyzer...')
    analyzer = PortUsageAnalyzer()
    port_assignment = PortAssignment(login_id='testuser', segment1_start=8000, segment1_end=8009)

    try:
        port_usage = analyzer.analyze_port_usage(projects, port_assignment)
        print(f'   ✅ Port usage analyzed')
        print(f'      Total assigned: {port_usage.total_assigned_ports}')
        print(f'      Total used: {port_usage.total_used_ports}')
        print(f'      Usage percentage: {port_usage.usage_percentage:.1f}%')
        print(f'      Available: {port_usage.available_ports}')
        
    except Exception as e:
        print(f'   ❌ Port analyzer failed: {e}')
        return False

    # Test 4: Complete Monitoring Report
    print('\n4. Testing Complete Monitoring Report...')
    try:
        project_monitor = ProjectStatusMonitor(test_dir)
        report = project_monitor.generate_monitoring_report(port_assignment, 'testuser')
        
        print(f'   ✅ Monitoring report generated')
        print(f'      Username: {report.username}')
        print(f'      Total projects: {report.total_projects}')
        print(f'      Running projects: {report.running_projects}')
        print(f'      Warnings: {len(report.warnings)}')
        print(f'      Recommendations: {len(report.recommendations)}')
        
        # Test report formatting
        formatted = project_monitor.format_status_report(report)
        print(f'   ✅ Report formatted ({len(formatted)} characters)')
        
    except Exception as e:
        print(f'   ❌ Monitoring report failed: {e}')
        return False

    print('\n🎉 Project status monitoring system test completed!')
    return True

if __name__ == '__main__':
    test_project_monitoring()