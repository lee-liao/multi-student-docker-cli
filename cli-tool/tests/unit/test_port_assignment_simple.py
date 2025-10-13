#!/usr/bin/env python3
"""
Simple Port Assignment Tests
Tests core port assignment functionality without complex dependencies.
"""

import sys
import os
import tempfile
import json

# Add the cli-tool directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from src.core.port_assignment import PortAssignment, PortAssignmentManager, get_current_user_assignment

def test_port_assignment_creation():
    """Test creating port assignments"""
    print("Testing Port Assignment Creation...")
    
    # Test basic port assignment
    assignment = PortAssignment("test_user", 8000, 8099)
    assert assignment.login_id == "test_user"
    assert assignment.start_port == 8000
    assert assignment.end_port == 8099
    assert assignment.total_ports == 100
    
    # Test port range validation
    port_range = assignment.get_port_range()
    assert len(port_range) == 100
    assert port_range[0] == 8000
    assert port_range[-1] == 8099
    
    # Test port availability
    assert assignment.is_port_available(8050)
    assert not assignment.is_port_available(7999)  # Below range
    assert not assignment.is_port_available(8100)  # Above range
    
    print("✓ Port Assignment Creation test passed")

def test_port_assignment_manager():
    """Test port assignment manager functionality"""
    print("Testing Port Assignment Manager...")
    
    # Create temporary assignments file
    with tempfile.TemporaryDirectory() as temp_dir:
        assignments_file = os.path.join(temp_dir, "assignments.json")
        
        # Create test assignments
        test_assignments = {
            "user1": {"start_port": 8000, "end_port": 8099, "total_ports": 100},
            "user2": {"start_port": 8100, "end_port": 8199, "total_ports": 100},
            "user3": {"start_port": 8200, "end_port": 8299, "total_ports": 100}
        }
        
        with open(assignments_file, 'w') as f:
            json.dump(test_assignments, f)
        
        # Test manager initialization
        manager = PortAssignmentManager(assignments_file)
        
        # Test loading assignments
        assignments = manager.load_assignments()
        assert len(assignments) == 3
        assert "user1" in assignments
        assert assignments["user1"]["start_port"] == 8000
        
        # Test getting user assignment
        user1_assignment = manager.get_user_assignment("user1")
        assert user1_assignment is not None
        assert user1_assignment.login_id == "user1"
        assert user1_assignment.start_port == 8000
        
        # Test non-existent user
        invalid_assignment = manager.get_user_assignment("invalid_user")
        assert invalid_assignment is None
        
        # Test port conflict detection
        conflicts = manager.detect_port_conflicts()
        assert isinstance(conflicts, list)
        # Should be no conflicts in our test data
        assert len(conflicts) == 0
    
    print("✓ Port Assignment Manager test passed")

def test_port_assignment_validation():
    """Test port assignment validation"""
    print("Testing Port Assignment Validation...")
    
    # Test valid assignment
    valid_assignment = PortAssignment("user1", 8000, 8099)
    assert valid_assignment.validate_assignment()
    
    # Test invalid assignments
    try:
        # Invalid port range (start > end)
        invalid_assignment = PortAssignment("user1", 8099, 8000)
        assert not invalid_assignment.validate_assignment()
    except ValueError:
        pass  # Expected for invalid range
    
    # Test port range calculations
    assignment = PortAssignment("user1", 8000, 8099)
    assert assignment.total_ports == 100
    
    # Test port allocation
    allocated_ports = assignment.allocate_ports(5)
    assert len(allocated_ports) == 5
    assert all(8000 <= port <= 8099 for port in allocated_ports)
    
    print("✓ Port Assignment Validation test passed")

def test_port_assignment_utilities():
    """Test port assignment utility functions"""
    print("Testing Port Assignment Utilities...")
    
    # Test current user assignment (will fail without proper setup, but should handle gracefully)
    try:
        current_assignment = get_current_user_assignment()
        # If it succeeds, validate the result
        if current_assignment:
            assert isinstance(current_assignment, PortAssignment)
            assert current_assignment.login_id is not None
            assert current_assignment.start_port > 0
            assert current_assignment.end_port > current_assignment.start_port
    except Exception as e:
        # Expected to fail in test environment
        assert "Cannot determine current user" in str(e) or "not found" in str(e)
    
    print("✓ Port Assignment Utilities test passed")

def test_port_assignment_edge_cases():
    """Test edge cases for port assignments"""
    print("Testing Port Assignment Edge Cases...")
    
    # Test minimum port range
    min_assignment = PortAssignment("user1", 8000, 8000)
    assert min_assignment.total_ports == 1
    
    # Test large port range
    large_assignment = PortAssignment("user1", 8000, 9999)
    assert large_assignment.total_ports == 2000
    
    # Test port allocation edge cases
    assignment = PortAssignment("user1", 8000, 8004)  # 5 ports
    
    # Allocate all ports
    all_ports = assignment.allocate_ports(5)
    assert len(all_ports) == 5
    
    # Try to allocate more than available
    try:
        too_many_ports = assignment.allocate_ports(10)
        # Should either return available ports or raise exception
        assert len(too_many_ports) <= 5
    except ValueError:
        pass  # Expected behavior
    
    print("✓ Port Assignment Edge Cases test passed")

def run_port_assignment_tests():
    """Run all port assignment tests"""
    print("Running Port Assignment Tests")
    print("=" * 50)
    
    try:
        test_port_assignment_creation()
        test_port_assignment_manager()
        test_port_assignment_validation()
        test_port_assignment_utilities()
        test_port_assignment_edge_cases()
        
        print("\n" + "=" * 50)
        print("✅ All port assignment tests passed!")
        
        print("\n🔌 Port Assignment System Summary:")
        print("=" * 50)
        
        print("\n📋 Core Components Tested:")
        print("  • PortAssignment - Individual user port allocation")
        print("  • PortAssignmentManager - Assignment file management")
        print("  • Port validation and conflict detection")
        print("  • Utility functions and edge cases")
        
        print("\n🔧 Key Features Validated:")
        print("  • Port range allocation and validation")
        print("  • Assignment file loading and parsing")
        print("  • Port conflict detection")
        print("  • Port availability checking")
        print("  • Edge case handling")
        
        print("\n✅ Port assignment system is working correctly!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_port_assignment_tests()
    sys.exit(0 if success else 1)