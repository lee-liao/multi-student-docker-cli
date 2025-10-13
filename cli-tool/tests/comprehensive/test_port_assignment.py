#!/usr/bin/env python3
"""
Test script for port assignment parser
"""

import os
import sys
import tempfile
from src.core.port_assignment import PortAssignmentManager, PortAssignment, get_current_user_ports


def test_port_assignment_parsing():
    """Test port assignment parsing functionality"""
    print("🧪 Testing Port Assignment Parser")
    print("=" * 40)
    
    # Test 1: Load encrypted file
    print("\n1. Testing encrypted file loading...")
    
    # Look for encrypted file in parent directory
    encrypted_file = "../student-port-assignments-v1.0.enc"
    if not os.path.exists(encrypted_file):
        print(f"❌ Encrypted file not found: {encrypted_file}")
        print("   Run the encryption tool first: python admin/encrypt_tool.py create v1.0 --input admin/port-assignments.txt")
        return False
    
    try:
        manager = PortAssignmentManager(encrypted_file)
        manager.load_assignments()
        print(f"✅ Successfully loaded port assignments")
        
        metadata = manager.get_metadata()
        print(f"   Version: {metadata['version']}")
        print(f"   Total assignments: {metadata['total_assignments']}")
        
    except Exception as e:
        print(f"❌ Failed to load assignments: {e}")
        return False
    
    # Test 2: Test port assignment lookup
    print("\n2. Testing port assignment lookup...")
    
    try:
        # Test valid user
        assignment = manager.get_student_assignment("Emma")
        print(f"✅ Emma's assignment: {assignment}")
        
        segment1, segment2 = manager.get_student_ports("Emma")
        print(f"   Segment1: {segment1.start}-{segment1.stop-1}")
        if segment2:
            print(f"   Segment2: {segment2.start}-{segment2.stop-1}")
        print(f"   Total ports: {assignment.total_ports}")
        print(f"   All ports: {assignment.all_ports[:5]}... (showing first 5)")
        
    except Exception as e:
        print(f"❌ Failed to get Emma's assignment: {e}")
        return False
    
    # Test 3: Test case sensitivity
    print("\n3. Testing case sensitivity...")
    
    try:
        manager.get_student_assignment("emma")  # lowercase
        print("❌ Should have rejected lowercase 'emma'")
        return False
    except PermissionError as e:
        if "Did you mean 'Emma'?" in str(e):
            print("✅ Correctly suggested case correction")
        else:
            print(f"✅ Correctly rejected lowercase, but message could be better: {e}")
    
    # Test 4: Test unauthorized user
    print("\n4. Testing unauthorized user...")
    
    try:
        manager.get_student_assignment("UnknownUser")
        print("❌ Should have rejected unknown user")
        return False
    except PermissionError as e:
        print(f"✅ Correctly rejected unauthorized user: {e}")
    
    # Test 5: Test port validation
    print("\n5. Testing port validation...")
    
    # Test valid port
    if manager.validate_port_in_range("Emma", 4050):
        print("✅ Correctly validated port 4050 for Emma")
    else:
        print("❌ Should have validated port 4050 for Emma")
        return False
    
    # Test invalid port
    if not manager.validate_port_in_range("Emma", 9999):
        print("✅ Correctly rejected port 9999 for Emma")
    else:
        print("❌ Should have rejected port 9999 for Emma")
        return False
    
    # Test 6: Test single segment assignment
    print("\n6. Testing single segment assignment...")
    
    try:
        sue_assignment = manager.get_student_assignment("Sue")
        print(f"✅ Sue's assignment: {sue_assignment}")
        
        if sue_assignment.has_two_segments:
            print("❌ Sue should have single segment")
            return False
        else:
            print("✅ Correctly identified single segment")
        
    except Exception as e:
        print(f"❌ Failed to get Sue's assignment: {e}")
        return False
    
    # Test 7: Test auto-detection of latest file
    print("\n7. Testing auto-detection of latest encrypted file...")
    
    try:
        auto_manager = PortAssignmentManager()  # No file specified
        auto_manager.load_assignments()
        auto_metadata = auto_manager.get_metadata()
        print(f"✅ Auto-detected file version: {auto_metadata['version']}")
        
    except Exception as e:
        print(f"❌ Auto-detection failed: {e}")
        return False
    
    print("\n🎉 All port assignment parser tests passed!")
    return True


def test_current_user_functions():
    """Test current user convenience functions"""
    print("\n🧪 Testing Current User Functions")
    print("=" * 40)
    
    # Save original USER env var
    original_user = os.environ.get('USER')
    
    try:
        # Test with valid user
        os.environ['USER'] = 'Emma'
        
        try:
            segment1, segment2 = get_current_user_ports()
            print(f"✅ Current user (Emma) ports: {segment1.start}-{segment1.stop-1}")
            if segment2:
                print(f"   Second segment: {segment2.start}-{segment2.stop-1}")
        except Exception as e:
            print(f"❌ Failed to get current user ports: {e}")
            return False
        
        # Test with invalid user
        os.environ['USER'] = 'InvalidUser'
        
        try:
            get_current_user_ports()
            print("❌ Should have rejected invalid user")
            return False
        except PermissionError:
            print("✅ Correctly rejected invalid user")
        
        print("\n🎉 Current user function tests passed!")
        return True
        
    finally:
        # Restore original USER env var
        if original_user:
            os.environ['USER'] = original_user
        elif 'USER' in os.environ:
            del os.environ['USER']


if __name__ == '__main__':
    # Change to cli-tool directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    success = True
    
    # Run tests
    success &= test_port_assignment_parsing()
    success &= test_current_user_functions()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)