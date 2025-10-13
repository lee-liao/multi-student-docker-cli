#!/usr/bin/env python3
"""
Test script for database initialization template system
"""

import os
import sys
import tempfile
from src.core.database_manager import (
    DatabaseManager, create_database_config,
    generate_postgresql_init, generate_mongodb_init, create_all_database_files
)
from src.core.port_assignment import PortAssignment


def test_database_template_generation():
    """Test database template generation"""
    print("🧪 Testing Database Template Generation")
    print("=" * 42)
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4100,
        segment2_start=8000,
        segment2_end=8100
    )
    
    manager = DatabaseManager("templates")
    
    # Test 1: Generate PostgreSQL init for common project
    print("\n1. Testing PostgreSQL init for common project...")
    
    try:
        config = create_database_config(
            username="Emma",
            project_name="common",
            template_type="common",
            port_assignment=emma_assignment,
            database_type="postgresql",
            output_dir="test_output"
        )
        
        script_content = manager.generate_database_init_script(config)
        
        # Check that content is generated
        if script_content and "CREATE EXTENSION" in script_content:
            print("✅ PostgreSQL common script generated successfully")
            
            # Check for student-specific content
            if "Emma_user" in script_content and "Emma_password_2024" in script_content:
                print("✅ Student-specific credentials applied correctly")
            else:
                print("❌ Student-specific credentials not applied")
                return False
                
        else:
            print("❌ PostgreSQL common script generation failed")
            return False
            
    except Exception as e:
        print(f"❌ PostgreSQL common script generation failed: {e}")
        return False
    
    # Test 2: Generate MongoDB init for common project
    print("\n2. Testing MongoDB init for common project...")
    
    try:
        config = create_database_config(
            username="Emma",
            project_name="common",
            template_type="common",
            port_assignment=emma_assignment,
            database_type="mongodb",
            output_dir="test_output"
        )
        
        script_content = manager.generate_database_init_script(config)
        
        # Check for MongoDB-specific content
        if ("createCollection" in script_content and 
            "Emma_admin" in script_content):
            print("✅ MongoDB common script generated correctly")
        else:
            print("❌ MongoDB common script missing expected content")
            return False
            
    except Exception as e:
        print(f"❌ MongoDB common script generation failed: {e}")
        return False
    
    # Test 3: Generate PostgreSQL init for RAG project
    print("\n3. Testing PostgreSQL init for RAG project...")
    
    try:
        config = create_database_config(
            username="Emma",
            project_name="rag-chatbot",
            template_type="rag",
            port_assignment=emma_assignment,
            database_type="postgresql",
            output_dir="test_output"
        )
        
        script_content = manager.generate_database_init_script(config)
        
        # Check for RAG-specific content
        if ("documents" in script_content and 
            "chat_sessions" in script_content and
            "vector(" in script_content):
            print("✅ PostgreSQL RAG script generated correctly")
        else:
            print("❌ PostgreSQL RAG script missing expected content")
            return False
            
    except Exception as e:
        print(f"❌ PostgreSQL RAG script generation failed: {e}")
        return False
    
    # Test 4: Generate PostgreSQL init for Agent project
    print("\n4. Testing PostgreSQL init for Agent project...")
    
    try:
        config = create_database_config(
            username="Emma",
            project_name="agent-system",
            template_type="agent",
            port_assignment=emma_assignment,
            database_type="postgresql",
            output_dir="test_output"
        )
        
        script_content = manager.generate_database_init_script(config)
        
        # Check for Agent-specific content
        if ("agents" in script_content and 
            "agent_executions" in script_content and
            "agent_memory" in script_content):
            print("✅ PostgreSQL Agent script generated correctly")
        else:
            print("❌ PostgreSQL Agent script missing expected content")
            return False
            
    except Exception as e:
        print(f"❌ PostgreSQL Agent script generation failed: {e}")
        return False
    
    print("\n🎉 All database template generation tests passed!")
    return True


def test_database_validation():
    """Test database script validation"""
    print("\n🧪 Testing Database Script Validation")
    print("=" * 42)
    
    manager = DatabaseManager("templates")
    
    # Test 1: Valid PostgreSQL script
    print("\n1. Testing valid PostgreSQL script validation...")
    
    valid_pg_script = """
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "vector";
    
    CREATE TABLE test_table (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(255) NOT NULL
    );
    
    CREATE INDEX idx_test_name ON test_table(name);
    
    GRANT SELECT ON test_table TO test_user;
    """
    
    try:
        warnings = manager.validate_database_script(valid_pg_script, 'postgresql')
        
        if len(warnings) == 0:
            print("✅ Valid PostgreSQL script passed validation")
        else:
            print(f"⚠️  Valid PostgreSQL script has {len(warnings)} warnings:")
            for warning in warnings[:3]:
                print(f"  - {warning}")
            
    except Exception as e:
        print(f"❌ PostgreSQL validation failed: {e}")
        return False
    
    # Test 2: Invalid PostgreSQL script
    print("\n2. Testing invalid PostgreSQL script validation...")
    
    invalid_pg_script = """
    -- Missing extensions and basic structure
    SELECT 'Hello World';
    """
    
    try:
        warnings = manager.validate_database_script(invalid_pg_script, 'postgresql')
        
        if warnings:
            print(f"✅ Invalid PostgreSQL script correctly detected {len(warnings)} issues")
            print(f"   Sample issues: {warnings[0] if warnings else 'None'}")
        else:
            print("❌ Invalid PostgreSQL script should have validation issues")
            return False
            
    except Exception as e:
        print(f"❌ PostgreSQL validation failed: {e}")
        return False
    
    # Test 3: Valid MongoDB script
    print("\n3. Testing valid MongoDB script validation...")
    
    valid_mongo_script = """
    db.createCollection('test_collection', {
        validator: {
            $jsonSchema: {
                bsonType: 'object',
                required: ['name']
            }
        }
    });
    
    db.test_collection.createIndex({ 'name': 1 });
    
    db.createUser({
        user: 'test_user',
        pwd: 'test_password',
        roles: [{ role: 'readWrite', db: 'test_db' }]
    });
    """
    
    try:
        warnings = manager.validate_database_script(valid_mongo_script, 'mongodb')
        
        if len(warnings) == 0:
            print("✅ Valid MongoDB script passed validation")
        else:
            print(f"⚠️  Valid MongoDB script has {len(warnings)} warnings")
            
    except Exception as e:
        print(f"❌ MongoDB validation failed: {e}")
        return False
    
    print("\n🎉 All database validation tests passed!")
    return True


def test_supported_databases():
    """Test supported database detection"""
    print("\n🧪 Testing Supported Database Detection")
    print("=" * 42)
    
    manager = DatabaseManager("templates")
    
    # Test 1: Common project databases
    print("\n1. Testing common project supported databases...")
    
    try:
        supported = manager.get_supported_databases('common')
        
        if 'postgresql' in supported and 'mongodb' in supported:
            print(f"✅ Common project supports: {', '.join(supported)}")
        else:
            print(f"❌ Common project missing expected databases: {supported}")
            return False
            
    except Exception as e:
        print(f"❌ Common database detection failed: {e}")
        return False
    
    # Test 2: RAG project databases
    print("\n2. Testing RAG project supported databases...")
    
    try:
        supported = manager.get_supported_databases('rag')
        
        if 'postgresql' in supported and 'mongodb' not in supported:
            print(f"✅ RAG project supports: {', '.join(supported)}")
        else:
            print(f"❌ RAG project unexpected databases: {supported}")
            return False
            
    except Exception as e:
        print(f"❌ RAG database detection failed: {e}")
        return False
    
    # Test 3: Agent project databases
    print("\n3. Testing Agent project supported databases...")
    
    try:
        supported = manager.get_supported_databases('agent')
        
        if 'postgresql' in supported and 'mongodb' not in supported:
            print(f"✅ Agent project supports: {', '.join(supported)}")
        else:
            print(f"❌ Agent project unexpected databases: {supported}")
            return False
            
    except Exception as e:
        print(f"❌ Agent database detection failed: {e}")
        return False
    
    print("\n🎉 All supported database detection tests passed!")
    return True


def test_database_connection_info():
    """Test database connection information generation"""
    print("\n🧪 Testing Database Connection Info")
    print("=" * 40)
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4010,
        segment2_start=None,
        segment2_end=None
    )
    
    manager = DatabaseManager("templates")
    
    # Test 1: Common project connection info
    print("\n1. Testing common project connection info...")
    
    try:
        config = create_database_config(
            username="Emma",
            project_name="common",
            template_type="common",
            port_assignment=emma_assignment,
            database_type="all",
            output_dir="test_output"
        )
        
        conn_info = manager.get_database_connection_info(config)
        
        if ('postgresql' in conn_info['databases'] and 
            'mongodb' in conn_info['databases']):
            print("✅ Common project connection info generated")
            print(f"   PostgreSQL: {conn_info['databases']['postgresql']['connection_url']}")
            print(f"   MongoDB: {conn_info['databases']['mongodb']['connection_url']}")
        else:
            print("❌ Common project connection info incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Common connection info generation failed: {e}")
        return False
    
    # Test 2: RAG project connection info
    print("\n2. Testing RAG project connection info...")
    
    try:
        config = create_database_config(
            username="Emma",
            project_name="rag",
            template_type="rag",
            port_assignment=emma_assignment,
            database_type="postgresql",
            output_dir="test_output"
        )
        
        conn_info = manager.get_database_connection_info(config)
        
        if ('postgresql' in conn_info['databases'] and 
            'rag_chatbot' in conn_info['databases']['postgresql']['connection_url']):
            print("✅ RAG project connection info generated")
            print(f"   PostgreSQL: {conn_info['databases']['postgresql']['connection_url']}")
        else:
            print("❌ RAG project connection info incomplete")
            return False
            
    except Exception as e:
        print(f"❌ RAG connection info generation failed: {e}")
        return False
    
    print("\n🎉 All database connection info tests passed!")
    return True


def test_convenience_functions():
    """Test convenience functions"""
    print("\n🧪 Testing Convenience Functions")
    print("=" * 35)
    
    # Create test port assignment
    emma_assignment = PortAssignment(
        login_id="Emma",
        segment1_start=4000,
        segment1_end=4100,
        segment2_start=8000,
        segment2_end=8100
    )
    
    # Test 1: Generate PostgreSQL init
    print("\n1. Testing generate_postgresql_init...")
    
    try:
        script_content = generate_postgresql_init(
            username="Emma",
            project_name="test",
            template_type="rag",
            port_assignment=emma_assignment,
            output_dir="test_output"
        )
        
        if script_content and "CREATE TABLE" in script_content:
            print("✅ PostgreSQL init generation successful")
        else:
            print("❌ PostgreSQL init generation failed")
            return False
            
    except Exception as e:
        print(f"❌ generate_postgresql_init failed: {e}")
        return False
    
    # Test 2: Generate MongoDB init
    print("\n2. Testing generate_mongodb_init...")
    
    try:
        script_content = generate_mongodb_init(
            username="Emma",
            project_name="test",
            template_type="common",
            port_assignment=emma_assignment,
            output_dir="test_output"
        )
        
        if script_content and "createCollection" in script_content:
            print("✅ MongoDB init generation successful")
        else:
            print("❌ MongoDB init generation failed")
            return False
            
    except Exception as e:
        print(f"❌ generate_mongodb_init failed: {e}")
        return False
    
    # Test 3: Create all database files
    print("\n3. Testing create_all_database_files...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            created_files = create_all_database_files(
                username="Emma",
                project_name="test",
                template_type="common",
                port_assignment=emma_assignment,
                output_dir=temp_dir
            )
            
            if created_files:
                print(f"✅ Created {len(created_files)} database files")
                for file_path in created_files.keys():
                    if os.path.exists(file_path):
                        print(f"   ✅ {os.path.basename(file_path)}")
                    else:
                        print(f"   ❌ {os.path.basename(file_path)} not found")
                        return False
            else:
                print("❌ No database files created")
                return False
                
        except Exception as e:
            print(f"❌ create_all_database_files failed: {e}")
            return False
    
    print("\n🎉 All convenience function tests passed!")
    return True


if __name__ == '__main__':
    # Change to project root directory (parent of cli-tool)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    success = True
    
    # Run tests
    success &= test_database_template_generation()
    success &= test_database_validation()
    success &= test_supported_databases()
    success &= test_database_connection_info()
    success &= test_convenience_functions()
    
    if success:
        print("\n🎉 All database initialization template system tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some database tests failed!")
        sys.exit(1)