#!/usr/bin/env python3
"""
Test script for interactive project creation
"""

import os
import sys
from cli import DockerComposeCLI


def test_interactive_scenarios():
    """Test different interactive scenarios"""
    print("🧪 Testing Interactive Project Creation")
    print("=" * 45)
    
    # Save original USER env var
    original_user = os.environ.get('USER')
    
    try:
        # Set test user
        os.environ['USER'] = 'Emma'
        
        cli = DockerComposeCLI()
        
        print("\n📋 Scenario 1: Create RAG project with no common project")
        print("=" * 55)
        print("Command: cli create-project rag --template rag")
        print("Expected: Suggest creating common project first")
        print("\nSimulating user input: Press Enter to see the prompt...")
        input("Press Enter to continue...")
        
        # This will show the interactive prompt
        try:
            result = cli.run(['create-project', 'rag', '--template', 'rag'])
            print(f"Result: {result}")
        except (EOFError, KeyboardInterrupt):
            print("Interactive test interrupted (expected in automated testing)")
        
        print("\n📋 Scenario 2: Create common project first")
        print("=" * 40)
        print("Command: cli create-project common --template common")
        
        result = cli.run(['create-project', 'common', '--template', 'common'])
        print(f"Result: {result}")
        
        # Create a dummy common directory to simulate existing common project
        common_dir = os.path.expanduser("~/dockeredServices/common")
        os.makedirs(common_dir, exist_ok=True)
        
        print("\n📋 Scenario 3: Create RAG project with existing common")
        print("=" * 50)
        print("Command: cli create-project rag --template rag")
        print("Expected: Offer choice between shared and self-contained")
        print("\nSimulating user input: Press Enter to see the prompt...")
        input("Press Enter to continue...")
        
        try:
            result = cli.run(['create-project', 'rag', '--template', 'rag'])
            print(f"Result: {result}")
        except (EOFError, KeyboardInterrupt):
            print("Interactive test interrupted (expected in automated testing)")
        
        return True
        
    finally:
        # Restore original USER env var
        if original_user:
            os.environ['USER'] = original_user
        elif 'USER' in os.environ:
            del os.environ['USER']
        
        # Clean up test directory
        try:
            import shutil
            test_dir = os.path.expanduser("~/dockeredServices")
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
        except:
            pass


def show_example_interactions():
    """Show example of what the interactions look like"""
    print("\n🎯 Example Interactive Sessions")
    print("=" * 35)
    
    print("\n📝 Example 1: No common project exists")
    print("-" * 40)
    print("""
$ cli create-project rag --template rag

💡 No 'common' infrastructure project found

📊 Recommended approach for resource efficiency:
   1. Create shared infrastructure: cli create-project common --template common
   2. Create your rag project: cli create-project rag --template rag

🔄 Alternative: Create self-contained project now
   ⚠️  Will include all services (database, cache, monitoring)
   ⚠️  Uses more ports and resources

Choose: (1=create common first/2=self-contained now/3=cancel) [1]: 1

🏗️  Creating 'common' infrastructure project first...
   📦 PostgreSQL, MongoDB, Redis
   📊 Jaeger, Prometheus, Grafana
   🌐 Shared network: Emma-network
✅ Common project created successfully
🔗 Now creating rag project in shared mode
   📱 RAG backend and frontend only
   🔌 Connects to existing common infrastructure
   🌐 Uses shared network: Emma-network
""")
    
    print("\n📝 Example 2: Common project exists")
    print("-" * 35)
    print("""
$ cli create-project agent --template agent

🔍 Found existing 'common' infrastructure project
📊 Resource Usage Comparison:

   Option 1: Connect to shared infrastructure (RECOMMENDED)
   ✅ Uses existing databases and services from 'common' project
   ✅ Resource efficient - only creates agent backend/frontend
   ✅ Saves ~6-8 ports, reduces memory usage
   ✅ Shared monitoring and observability

   Option 2: Create self-contained project
   ⚠️  Creates separate database, Redis, and monitoring services
   ⚠️  Uses ~10-15 ports (you have 202 total)
   ⚠️  Higher memory and CPU usage
   ⚠️  Duplicate infrastructure services

Choose deployment mode (1=shared/2=self-contained) [1]: 1

✅ Creating agent project in shared mode
   📱 AGENT backend and frontend only
   🔌 Connects to existing common infrastructure
   🌐 Uses shared network: Emma-network
""")


if __name__ == '__main__':
    # Change to cli-tool directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    show_example_interactions()
    
    print("\n" + "=" * 60)
    print("To test interactively, run:")
    print("USER=Emma python cli-tool/cli.py create-project rag --template rag")
    print("=" * 60)