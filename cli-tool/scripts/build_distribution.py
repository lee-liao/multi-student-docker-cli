#!/usr/bin/env python3
"""
Distribution Build Script
Creates distribution packages for the Multi-Student Docker Compose CLI Tool.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import List, Dict, Any
import json

class DistributionBuilder:
    """Builds distribution packages"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.dist_dir = self.root_dir / "dist"
        self.build_dir = self.root_dir / "build"
        self.version = self._get_version()
        
        # Clean previous builds
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        
        self.dist_dir.mkdir()
        self.build_dir.mkdir()
    
    def _get_version(self) -> str:
        """Get version from VERSION file"""
        version_file = self.root_dir / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return "1.0.0"
    
    def build_source_distribution(self) -> Path:
        """Build source distribution"""
        print("Building source distribution...")
        
        # Create source package directory
        package_name = f"multi-student-docker-compose-{self.version}"
        package_dir = self.build_dir / package_name
        package_dir.mkdir()
        
        # Files to include in source distribution
        include_files = [
            "README.md",
            "LICENSE",
            "VERSION",
            "requirements.txt",
            "requirements-dev.txt",
            "setup.py",
            ".gitignore",
        ]
        
        include_dirs = [
            "cli-tool",
            "templates",
            "examples",
            "admin-tools",
        ]
        
        # Copy files
        for file_name in include_files:
            src_file = self.root_dir / file_name
            if src_file.exists():
                shutil.copy2(src_file, package_dir / file_name)
        
        # Copy directories
        for dir_name in include_dirs:
            src_dir = self.root_dir / dir_name
            if src_dir.exists():
                shutil.copytree(src_dir, package_dir / dir_name, 
                              ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', '.pytest_cache'))
        
        # Copy documentation files
        doc_files = [
            "MULTI_STUDENT_DOCKER_COMPOSE_DOCUMENTATION.md",
            "QUICK_START_GUIDE.md",
            "SETUP_SCRIPT_GENERATION_SUMMARY.md",
            "CORS_CONFIGURATION_SUMMARY.md",
            "PORT_VERIFICATION_SUMMARY.md",
            "PROJECT_STATUS_MONITORING_SUMMARY.md",
            "CLEANUP_MAINTENANCE_SUMMARY.md",
            "ERROR_HANDLING_SUMMARY.md",
            "SECURITY_VALIDATION_SUMMARY.md",
            "COMPREHENSIVE_TEST_SUITE_SUMMARY.md",
            "ENHANCED_END_TO_END_VALIDATION_SUMMARY.md",
        ]
        
        for doc_file in doc_files:
            src_file = self.root_dir / doc_file
            if src_file.exists():
                shutil.copy2(src_file, package_dir / doc_file)
        
        # Create tarball
        tarball_path = self.dist_dir / f"{package_name}.tar.gz"
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(package_dir, arcname=package_name)
        
        print(f"Source distribution created: {tarball_path}")
        return tarball_path
    
    def build_binary_distribution(self) -> Path:
        """Build binary distribution (wheel)"""
        print("Building binary distribution...")
        
        try:
            # Build wheel using setup.py
            result = subprocess.run([
                sys.executable, "setup.py", "bdist_wheel"
            ], cwd=self.root_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Find the created wheel
                wheel_files = list(self.dist_dir.glob("*.whl"))
                if wheel_files:
                    wheel_path = wheel_files[0]
                    print(f"Binary distribution created: {wheel_path}")
                    return wheel_path
            
            print(f"Wheel build failed: {result.stderr}")
            
        except Exception as e:
            print(f"Failed to build wheel: {e}")
        
        return None
    
    def build_standalone_package(self) -> Path:
        """Build standalone package with all dependencies"""
        print("Building standalone package...")
        
        package_name = f"multi-student-docker-compose-standalone-{self.version}"
        package_dir = self.build_dir / package_name
        package_dir.mkdir()
        
        # Copy CLI tool
        cli_dir = package_dir / "cli-tool"
        shutil.copytree(self.root_dir / "cli-tool", cli_dir,
                       ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', '.pytest_cache'))
        
        # Copy templates
        templates_dir = package_dir / "templates"
        shutil.copytree(self.root_dir / "templates", templates_dir)
        
        # Copy examples
        examples_dir = package_dir / "examples"
        if (self.root_dir / "examples").exists():
            shutil.copytree(self.root_dir / "examples", examples_dir)
        
        # Copy admin tools (without sensitive data)
        admin_dir = package_dir / "admin-tools"
        if (self.root_dir / "admin-tools").exists():
            shutil.copytree(self.root_dir / "admin-tools", admin_dir,
                           ignore=shutil.ignore_patterns('*.enc', '*.key', 'logs', 'backups'))
        
        # Copy documentation
        docs = [
            "README.md",
            "MULTI_STUDENT_DOCKER_COMPOSE_DOCUMENTATION.md",
            "QUICK_START_GUIDE.md",
        ]
        
        for doc in docs:
            src_file = self.root_dir / doc
            if src_file.exists():
                shutil.copy2(src_file, package_dir / doc)
        
        # Create installation script
        install_script = package_dir / "install.py"
        self._create_install_script(install_script)
        
        # Create run script
        run_script = package_dir / "run.py"
        self._create_run_script(run_script)
        
        # Create ZIP package
        zip_path = self.dist_dir / f"{package_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(package_dir.parent)
                    zipf.write(file_path, arcname)
        
        print(f"Standalone package created: {zip_path}")
        return zip_path
    
    def _create_install_script(self, script_path: Path):
        """Create installation script for standalone package"""
        install_script_content = '''#!/usr/bin/env python3
"""
Installation script for Multi-Student Docker Compose CLI Tool
"""

import os
import sys
import shutil
from pathlib import Path

def main():
    print("Installing Multi-Student Docker Compose CLI Tool...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    
    # Get installation directory
    install_dir = Path.home() / ".local" / "bin"
    install_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy CLI tool
    cli_source = Path(__file__).parent / "cli-tool" / "cli.py"
    cli_target = install_dir / "docker-compose-cli"
    
    if cli_source.exists():
        shutil.copy2(cli_source, cli_target)
        cli_target.chmod(0o755)
        print(f"CLI installed to: {cli_target}")
    else:
        print("Error: CLI tool not found")
        sys.exit(1)
    
    # Copy templates
    templates_source = Path(__file__).parent / "templates"
    templates_target = Path.home() / ".multi-student-docker" / "templates"
    
    if templates_source.exists():
        if templates_target.exists():
            shutil.rmtree(templates_target)
        shutil.copytree(templates_source, templates_target)
        print(f"Templates installed to: {templates_target}")
    
    print("Installation complete!")
    print(f"Add {install_dir} to your PATH to use 'docker-compose-cli' command")
    print("Or run directly: python cli-tool/cli.py")

if __name__ == "__main__":
    main()
'''
        script_path.write_text(install_script_content)
        script_path.chmod(0o755)
    
    def _create_run_script(self, script_path: Path):
        """Create run script for standalone package"""
        run_script_content = '''#!/usr/bin/env python3
"""
Run script for Multi-Student Docker Compose CLI Tool
"""

import sys
import os
from pathlib import Path

# Add cli-tool to path
cli_tool_dir = Path(__file__).parent / "cli-tool"
sys.path.insert(0, str(cli_tool_dir))

# Import and run CLI
try:
    from cli import main
    sys.exit(main())
except ImportError as e:
    print(f"Error importing CLI: {e}")
    print("Make sure you're running from the correct directory")
    sys.exit(1)
'''
        script_path.write_text(run_script_content)
        script_path.chmod(0o755)
    
    def build_docker_image(self) -> bool:
        """Build Docker image"""
        print("Building Docker image...")
        
        # Create Dockerfile
        dockerfile_content = '''
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    docker.io \\
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy application files
COPY cli-tool/ ./cli-tool/
COPY templates/ ./templates/
COPY examples/ ./examples/
COPY README.md ./
COPY VERSION ./

# Create entrypoint
RUN echo '#!/bin/bash\\npython /app/cli-tool/cli.py "$@"' > /usr/local/bin/docker-compose-cli \\
    && chmod +x /usr/local/bin/docker-compose-cli

# Create non-root user
RUN useradd -m -u 1000 student
USER student

ENTRYPOINT ["docker-compose-cli"]
CMD ["--help"]
'''
        
        dockerfile_path = self.root_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        
        try:
            # Build Docker image
            image_tag = f"multi-student-docker-compose:{self.version}"
            result = subprocess.run([
                "docker", "build", "-t", image_tag, "."
            ], cwd=self.root_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Docker image built: {image_tag}")
                return True
            else:
                print(f"Docker build failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Failed to build Docker image: {e}")
            return False
        finally:
            # Clean up Dockerfile
            if dockerfile_path.exists():
                dockerfile_path.unlink()
    
    def create_release_info(self) -> Path:
        """Create release information file"""
        release_info = {
            "version": self.version,
            "release_date": "2023-10-13",
            "python_requires": ">=3.8",
            "docker_requires": ">=20.10",
            "docker_compose_requires": ">=2.0",
            "features": [
                "Isolated port management for multiple students",
                "Template-based project creation (RAG, Agent, Common)",
                "Security validation and audit logging",
                "Project monitoring and status tracking",
                "Cleanup and maintenance tools",
                "Comprehensive error handling",
                "Cross-platform compatibility"
            ],
            "installation_methods": [
                "pip install multi-student-docker-compose",
                "Download standalone package",
                "Clone from GitHub",
                "Docker image"
            ],
            "documentation": [
                "README.md",
                "MULTI_STUDENT_DOCKER_COMPOSE_DOCUMENTATION.md",
                "QUICK_START_GUIDE.md"
            ],
            "support": {
                "issues": "https://github.com/your-org/multi-student-docker-compose/issues",
                "documentation": "https://github.com/your-org/multi-student-docker-compose/blob/main/README.md",
                "email": "support@multi-student-docker.edu"
            }
        }
        
        release_file = self.dist_dir / "release-info.json"
        with open(release_file, 'w') as f:
            json.dump(release_info, f, indent=2)
        
        print(f"Release info created: {release_file}")
        return release_file
    
    def build_all(self) -> Dict[str, Any]:
        """Build all distribution packages"""
        print(f"Building Multi-Student Docker Compose CLI v{self.version}")
        print("="*60)
        
        results = {
            "version": self.version,
            "source_dist": None,
            "binary_dist": None,
            "standalone_package": None,
            "docker_image": False,
            "release_info": None
        }
        
        # Build source distribution
        try:
            results["source_dist"] = str(self.build_source_distribution())
        except Exception as e:
            print(f"Source distribution failed: {e}")
        
        # Build binary distribution
        try:
            binary_dist = self.build_binary_distribution()
            if binary_dist:
                results["binary_dist"] = str(binary_dist)
        except Exception as e:
            print(f"Binary distribution failed: {e}")
        
        # Build standalone package
        try:
            results["standalone_package"] = str(self.build_standalone_package())
        except Exception as e:
            print(f"Standalone package failed: {e}")
        
        # Build Docker image (optional)
        try:
            results["docker_image"] = self.build_docker_image()
        except Exception as e:
            print(f"Docker image build failed: {e}")
        
        # Create release info
        try:
            results["release_info"] = str(self.create_release_info())
        except Exception as e:
            print(f"Release info creation failed: {e}")
        
        # Summary
        print("\n" + "="*60)
        print("BUILD SUMMARY")
        print("="*60)
        print(f"Version: {results['version']}")
        print(f"Source Distribution: {'✓' if results['source_dist'] else '✗'}")
        print(f"Binary Distribution: {'✓' if results['binary_dist'] else '✗'}")
        print(f"Standalone Package: {'✓' if results['standalone_package'] else '✗'}")
        print(f"Docker Image: {'✓' if results['docker_image'] else '✗'}")
        print(f"Release Info: {'✓' if results['release_info'] else '✗'}")
        
        successful_builds = sum(1 for v in results.values() if v and v != self.version)
        print(f"\nSuccessful builds: {successful_builds}/5")
        
        if successful_builds >= 3:
            print("✅ Build completed successfully!")
        else:
            print("⚠️  Some builds failed - check output above")
        
        return results

def main():
    """Main entry point"""
    builder = DistributionBuilder()
    results = builder.build_all()
    
    # Exit with appropriate code
    successful_builds = sum(1 for v in results.values() if v and v != results["version"])
    sys.exit(0 if successful_builds >= 3 else 1)

if __name__ == "__main__":
    main()