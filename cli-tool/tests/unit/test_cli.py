#!/usr/bin/env python3
"""
Test script for CLI tool
"""

import os
import sys
import tempfile
from cli import DockerComposeCLI


def test_cli_basic_functionality():
    """Test basic CLI functionality"""
    print("🧪 Testing CLI Tool Basic Functionality")
    print("=" * 45)
    
    # Save original USER env var
    original_user = os.environ.get('USER')
    
    try:
        # Set test user
        os.environ['USER'] = 'Emma'
        
        cli = DockerComposeCLI()
        
        # Test 1: Help command
        print("\n1. Testing help command...")
        try:
            result = cli.run(['--help'])
            print("✅ Help command works (exit code expected)")
        except SystemExit:
            print("✅ Help command works")
        
        # Test 2: Show ports command
        print("\n2. Testing show-ports command...")
        try:
            result = cli.run(['show-ports'])
            if result == 0:
                print("✅ Show-ports command successful")
            else:
                print(f"❌ Show-ports failed with exit code {result}")
                return False
        except Exception as e:
            print(f"❌ Show-ports failed: {e}")
            return False
        
        # Test 3: Show ports JSON output
        print("\n3. Testing show-ports with JSON output...")
        try:
            result = cli.run(['show-ports', '--json'])
            if result == 0:
                print("✅ Show-ports JSON output successful")
            else:
                print(f"❌ Show-ports JSON failed with exit code {result}")
                return False
        except Exception as e:
            print(f"❌ Show-ports JSON failed: {e}")
            return False
        
        # Test 4: List projects (should be empty initially)
        print("\n4. Testing list-projects command...")
        try:
            result = cli.run(['list-projects'])
            if result == 0:
                print("✅ List-projects command successful")
            else:
                print(f"❌ List-projects failed with exit code {result}")
                return False
        except Exception as e:
            print(f"❌ List-projects failed: {e}")
            return False
        
        # Test 5: Status command
        print("\n5. Testing status command...")
        try:
            result = cli.run(['status'])
            if result == 0:
                print("✅ Status command successful")
            else:
                print(f"❌ Status failed with exit code {result}")
                return False
        except Exception as e:
            print(f"❌ Status failed: {e}")
            return False
        
        # Test 6: Status with JSON
        print("\n6. Testing status with JSON output...")
        try:
            result = cli.run(['status', '--json'])
            if result == 0:
                print("✅ Status JSON output successful")
            else:
                print(f"❌ Status JSON failed with exit code {result}")
                return False
        except Exception as e:
            print(f"❌ Status JSON failed: {e}")
            return False
        
        print("\n🎉 All CLI basic functionality tests passed!")
        return True
        
    finally:
        # Restore original USER env var
        if original_user:
            os.environ['USER'] = original_user
        elif 'USER' in os.environ:
            del os.environ['USER']


def test_cli_error_handling():
    """Test CLI error handling"""
    print("\n🧪 Testing CLI Error Handling")
    print("=" * 35)
    
    # Save original USER env var
    original_user = os.environ.get('USER')
    
    try:
        # Test 1: Unauthorized user
        print("\n1. Testing unauthorized user...")
        os.environ['USER'] = 'UnauthorizedUser'
        
        cli = DockerComposeCLI()
        result = cli.run(['show-ports'])
        
        if result == 3:  # PermissionError exit code
            print("✅ Correctly rejected unauthorized user")
        else:
            print(f"❌ Expected exit code 3, got {result}")
            return False
        
        # Test 2: Invalid command
        print("\n2. Testing invalid command...")
        os.environ['USER'] = 'Emma'
        
        cli = DockerComposeCLI()
        try:
            result = cli.run(['invalid-command'])
            print(f"❌ Expected SystemExit, got result: {result}")
            return False
        except SystemExit as e:
            if e.code == 2:  # argparse exits with 2 for invalid arguments
                print("✅ Invalid command handled gracefully (SystemExit with code 2)")
            else:
                print(f"❌ Unexpected exit code: {e.code}")
                return False
        
        print("\n🎉 All CLI error handling tests passed!")
        return True
        
    finally:
        # Restore original USER env var
        if original_user:
            os.environ['USER'] = original_user
        elif 'USER' in os.environ:
            del os.environ['USER']


def test_secure_logging():
    """Test secure logging functionality"""
    print("\n🧪 Testing Secure Logging")
    print("=" * 30)
    
    from src.security.secure_logger import SecureLogger
    
    # Test sanitization
    logger = SecureLogger()
    
    # Test message sanitization
    test_message = "Database: postgresql://user:secret123@localhost/db API_KEY=sk-abc123"
    sanitized = logger.sanitize_message(test_message)
    
    if '[REDACTED]' in sanitized and 'secret123' not in sanitized:
        print("✅ Message sanitization works")
    else:
        print(f"❌ Message sanitization failed: {sanitized}")
        return False
    
    # Test dictionary sanitization
    test_dict = {
        'password': 'secret123',
        'api_key': 'sk-abc123',
        'port': 5432,
        'debug': True
    }
    
    sanitized_dict = logger.sanitize_dict(test_dict)
    
    if (sanitized_dict['password'] == '[REDACTED]' and 
        sanitized_dict['api_key'] == '[REDACTED]' and
        sanitized_dict['port'] == 5432):
        print("✅ Dictionary sanitization works")
    else:
        print(f"❌ Dictionary sanitization failed: {sanitized_dict}")
        return False
    
    print("🎉 Secure logging tests passed!")
    return True


if __name__ == '__main__':
    # Change to cli-tool directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    success = True
    
    # Run tests
    success &= test_secure_logging()
    success &= test_cli_basic_functionality()
    success &= test_cli_error_handling()
    
    if success:
        print("\n🎉 All CLI tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some CLI tests failed!")
        sys.exit(1)