#!/usr/bin/env python3
"""
Demo of interactive project creation functionality
"""

import os
import sys
from cli import DockerComposeCLI


def demo_interactive_functionality():
    """Demonstrate the interactive project creation"""
    print("🎯 Interactive Project Creation Demo")
    print("=" * 40)
    
    # Set up test environment
    os.environ['USER'] = 'Emma'
    
    cli = DockerComposeCLI()
    cli.setup_logging(quiet=True)  # Reduce log noise
    cli.ensure_user_authorized()
    cli.ensure_dockered_services_dir()
    
    print(f"\n👤 User: {cli.user_assignment.login_id}")
    print(f"📊 Available ports: {cli.user_assignment.total_ports}")
    print(f"📁 Projects directory: {cli.dockered_services_dir}")
    
    # Demo 1: No common project exists
    print(f"\n" + "="*50)
    print(f"📋 DEMO 1: Create RAG project (no common exists)")
    print(f"="*50)
    print(f"Command: cli create-project rag --template rag")
    print(f"")
    
    # Simulate the logic without user input
    common_project_path = os.path.join(cli.dockered_services_dir, "common")
    has_common_project = os.path.exists(common_project_path)
    
    if not has_common_project:
        print(f"💡 No 'common' infrastructure project found")
        print(f"")
        print(f"📊 Recommended approach for resource efficiency:")
        print(f"   1. Create shared infrastructure: cli create-project common --template common")
        print(f"   2. Create your rag project: cli create-project rag --template rag")
        print(f"")
        print(f"🔄 Alternative: Create self-contained project now")
        print(f"   ⚠️  Will include all services (database, cache, monitoring)")
        print(f"   ⚠️  Uses more ports and resources")
        print(f"")
        print(f"💭 User chooses: 1 (create common first)")
        print(f"")
        print(f"🏗️  Creating 'common' infrastructure project first...")
        print(f"   📦 PostgreSQL, MongoDB, Redis")
        print(f"   📊 Jaeger, Prometheus, Grafana")
        print(f"   🌐 Shared network: Emma-network")
        print(f"✅ Common project created successfully")
        print(f"🔗 Now creating rag project in shared mode")
        print(f"   📱 RAG backend and frontend only")
        print(f"   🔌 Connects to existing common infrastructure")
        print(f"   🌐 Uses shared network: Emma-network")
        
        # Create the common directory for next demo
        os.makedirs(common_project_path, exist_ok=True)
    
    # Demo 2: Common project exists
    print(f"\n" + "="*50)
    print(f"📋 DEMO 2: Create Agent project (common exists)")
    print(f"="*50)
    print(f"Command: cli create-project agent --template agent")
    print(f"")
    
    print(f"🔍 Found existing 'common' infrastructure project")
    print(f"📊 Resource Usage Comparison:")
    print(f"")
    print(f"   Option 1: Connect to shared infrastructure (RECOMMENDED)")
    print(f"   ✅ Uses existing databases and services from 'common' project")
    print(f"   ✅ Resource efficient - only creates agent backend/frontend")
    print(f"   ✅ Saves ~6-8 ports, reduces memory usage")
    print(f"   ✅ Shared monitoring and observability")
    print(f"")
    print(f"   Option 2: Create self-contained project")
    print(f"   ⚠️  Creates separate database, Redis, and monitoring services")
    print(f"   ⚠️  Uses ~10-15 ports (you have {cli.user_assignment.total_ports} total)")
    print(f"   ⚠️  Higher memory and CPU usage")
    print(f"   ⚠️  Duplicate infrastructure services")
    print(f"")
    print(f"💭 User chooses: 1 (shared mode - recommended)")
    print(f"")
    print(f"✅ Creating agent project in shared mode")
    print(f"   📱 AGENT backend and frontend only")
    print(f"   🔌 Connects to existing common infrastructure")
    print(f"   🌐 Uses shared network: Emma-network")
    
    # Demo 3: User chooses self-contained
    print(f"\n" + "="*50)
    print(f"📋 DEMO 3: Create ML project (user chooses self-contained)")
    print(f"="*50)
    print(f"Command: cli create-project ml-pipeline --template rag")
    print(f"")
    
    print(f"🔍 Found existing 'common' infrastructure project")
    print(f"📊 Resource Usage Comparison:")
    print(f"   [Same options as above...]")
    print(f"")
    print(f"💭 User chooses: 2 (self-contained)")
    print(f"")
    print(f"⚠️  Creating ml-pipeline project in self-contained mode")
    print(f"   📦 Includes database, cache, and monitoring services")
    print(f"   📱 RAG backend and frontend")
    print(f"   🌐 Own network: Emma-ml-pipeline-network")
    
    # Summary
    print(f"\n" + "="*50)
    print(f"📊 FINAL RESOURCE USAGE SUMMARY")
    print(f"="*50)
    print(f"")
    print(f"📁 ~/dockeredServices/")
    print(f"├── common/              # Shared: PostgreSQL, MongoDB, Redis, Observability")
    print(f"│                        # Ports used: 4000-4005, 8000-8005 (10 ports)")
    print(f"├── rag/                # Shared mode: Backend + Frontend only")
    print(f"│                        # Ports used: 8006-8007 (2 ports)")
    print(f"├── agent/              # Shared mode: Backend + Frontend only")
    print(f"│                        # Ports used: 8008-8009 (2 ports)")
    print(f"└── ml-pipeline/        # Self-contained: All services")
    print(f"                         # Ports used: 4006-4015, 8010-8020 (20 ports)")
    print(f"")
    print(f"📊 Total ports used: 34 out of {cli.user_assignment.total_ports} available")
    print(f"💡 Shared mode saves significant resources!")
    
    print(f"\n🎯 Key Benefits of Interactive Approach:")
    print(f"✅ Users understand resource implications")
    print(f"✅ Recommends efficient shared mode")
    print(f"✅ Still allows self-contained if needed")
    print(f"✅ Automatic common project creation")
    print(f"✅ Clear resource usage feedback")


if __name__ == '__main__':
    demo_interactive_functionality()