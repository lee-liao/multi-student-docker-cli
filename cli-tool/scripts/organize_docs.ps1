# PowerShell Script to Organize Documentation Files
# Moves all .md files (except README.md) to organized docs/ subdirectories

Write-Host "Starting documentation organization..." -ForegroundColor Green

# Function to safely move files
function Move-DocFile {
    param(
        [string]$Source,
        [string]$Destination
    )
    
    if (Test-Path $Source) {
        try {
            Move-Item $Source $Destination -Force
            Write-Host "✓ Moved: $Source → $Destination" -ForegroundColor Green
        }
        catch {
            Write-Host "✗ Failed to move: $Source → $Destination" -ForegroundColor Red
            Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    else {
        Write-Host "⚠ File not found: $Source" -ForegroundColor Yellow
    }
}

Write-Host "`n=== Moving Component Documentation ===" -ForegroundColor Cyan

# Component-specific documentation
Move-DocFile "SETUP_SCRIPT_GENERATION_SUMMARY.md" "docs/components/"
Move-DocFile "CORS_CONFIGURATION_SUMMARY.md" "docs/components/"
Move-DocFile "PORT_VERIFICATION_SUMMARY.md" "docs/components/"
Move-DocFile "PROJECT_STATUS_MONITORING_SUMMARY.md" "docs/components/"
Move-DocFile "CLEANUP_MAINTENANCE_SUMMARY.md" "docs/components/"
Move-DocFile "ERROR_HANDLING_SUMMARY.md" "docs/components/"
Move-DocFile "SECURITY_VALIDATION_SUMMARY.md" "docs/components/"
Move-DocFile "TEMPLATE_ENGINE_SUMMARY.md" "docs/components/"
Move-DocFile "README_GENERATION_SUMMARY.md" "docs/components/"
Move-DocFile "DATABASE_INITIALIZATION_SUMMARY.md" "docs/components/"
Move-DocFile "DOCKER_COMPOSE_SYSTEM_SUMMARY.md" "docs/components/"
Move-DocFile "DOCKERFILE_SYSTEM_SUMMARY.md" "docs/components/"

Write-Host "`n=== Moving Deployment Documentation ===" -ForegroundColor Cyan

# Deployment and integration documentation
Move-DocFile "DEPLOYMENT_GUIDE.md" "docs/deployment/"
Move-DocFile "FINAL_INTEGRATION_DEPLOYMENT_SUMMARY.md" "docs/deployment/"
Move-DocFile "ENHANCED_END_TO_END_VALIDATION_SUMMARY.md" "docs/deployment/"
Move-DocFile "COMPREHENSIVE_TEST_SUITE_SUMMARY.md" "docs/deployment/"

Write-Host "`n=== Moving Development Documentation ===" -ForegroundColor Cyan

# Development and implementation documentation
Move-DocFile "CODE_REORGANIZATION_SUMMARY.md" "docs/development/"
Move-DocFile "REORGANIZATION_PLAN.md" "docs/development/"
Move-DocFile "IMPLEMENTATION_SUMMARY.md" "docs/development/"
Move-DocFile "PROJECT_CREATION_SUMMARY.md" "docs/development/"
Move-DocFile "PROJECT_COPYING_SUMMARY.md" "docs/development/"
Move-DocFile "COMMON_PROJECT_SUMMARY.md" "docs/development/"

Write-Host "`n=== Moving Summary Documentation ===" -ForegroundColor Cyan

# General summaries and status
Move-DocFile "CURRENT_PROGRESS_STATUS.md" "docs/summaries/"

Write-Host "`n=== Creating Documentation Index ===" -ForegroundColor Cyan

# Create main documentation index
$docsIndex = @"
# Multi-Student Docker Compose CLI Tool - Documentation

## 📚 Documentation Structure

This directory contains comprehensive documentation for the Multi-Student Docker Compose CLI Tool, organized by category for easy navigation.

## 📁 Directory Structure

### 🔧 [Components Documentation](components/)
Component-specific implementation details and technical summaries:
- [Setup Script Generation](components/SETUP_SCRIPT_GENERATION_SUMMARY.md)
- [CORS Configuration](components/CORS_CONFIGURATION_SUMMARY.md)
- [Port Verification System](components/PORT_VERIFICATION_SUMMARY.md)
- [Project Status Monitoring](components/PROJECT_STATUS_MONITORING_SUMMARY.md)
- [Cleanup and Maintenance Tools](components/CLEANUP_MAINTENANCE_SUMMARY.md)
- [Error Handling System](components/ERROR_HANDLING_SUMMARY.md)
- [Security Validation and Logging](components/SECURITY_VALIDATION_SUMMARY.md)
- [Template Engine](components/TEMPLATE_ENGINE_SUMMARY.md)
- [README Generation](components/README_GENERATION_SUMMARY.md)
- [Database Initialization](components/DATABASE_INITIALIZATION_SUMMARY.md)
- [Docker Compose System](components/DOCKER_COMPOSE_SYSTEM_SUMMARY.md)
- [Dockerfile System](components/DOCKERFILE_SYSTEM_SUMMARY.md)

### 🚀 [Deployment Documentation](deployment/)
Deployment, testing, and production readiness documentation:
- [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- [Final Integration Summary](deployment/FINAL_INTEGRATION_DEPLOYMENT_SUMMARY.md)
- [End-to-End Validation](deployment/ENHANCED_END_TO_END_VALIDATION_SUMMARY.md)
- [Comprehensive Test Suite](deployment/COMPREHENSIVE_TEST_SUITE_SUMMARY.md)

### 💻 [Development Documentation](development/)
Development process, implementation details, and code organization:
- [Code Reorganization](development/CODE_REORGANIZATION_SUMMARY.md)
- [Reorganization Plan](development/REORGANIZATION_PLAN.md)
- [Implementation Summary](development/IMPLEMENTATION_SUMMARY.md)
- [Project Creation](development/PROJECT_CREATION_SUMMARY.md)
- [Project Copying](development/PROJECT_COPYING_SUMMARY.md)
- [Common Project Management](development/COMMON_PROJECT_SUMMARY.md)

### 📊 [Summaries](summaries/)
High-level summaries and status reports:
- [Current Progress Status](summaries/CURRENT_PROGRESS_STATUS.md)

## 🎯 Quick Navigation

### For Users
- **Getting Started**: See [README.md](../README.md) in the project root
- **Installation**: See [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md)
- **Usage Examples**: See main [README.md](../README.md)

### For Administrators
- **Deployment**: [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md)
- **Security**: [Security Validation](components/SECURITY_VALIDATION_SUMMARY.md)
- **Monitoring**: [Project Status Monitoring](components/PROJECT_STATUS_MONITORING_SUMMARY.md)

### For Developers
- **Code Structure**: [Code Reorganization](development/CODE_REORGANIZATION_SUMMARY.md)
- **Implementation Details**: [Implementation Summary](development/IMPLEMENTATION_SUMMARY.md)
- **Component Details**: Browse [Components Documentation](components/)

### For Testing
- **Test Suites**: [Comprehensive Test Suite](deployment/COMPREHENSIVE_TEST_SUITE_SUMMARY.md)
- **End-to-End Testing**: [End-to-End Validation](deployment/ENHANCED_END_TO_END_VALIDATION_SUMMARY.md)

## 📋 Documentation Standards

All documentation follows these standards:
- **Comprehensive**: Covers all aspects of each component
- **User-Friendly**: Clear instructions and examples
- **Up-to-Date**: Reflects current implementation
- **Well-Organized**: Logical structure and navigation
- **Professional**: Industry-standard documentation practices

## 🔄 Maintenance

Documentation is maintained alongside code changes and updated with each major release. For the most current information, always refer to the latest version in this directory.

---

**Project**: Multi-Student Docker Compose CLI Tool  
**Version**: 1.0.0  
**Last Updated**: 2023-10-13  
**Documentation Structure**: Organized and Professional
"@

Set-Content "docs/README.md" $docsIndex

Write-Host "✓ Created documentation index: docs/README.md" -ForegroundColor Green

Write-Host "`n=== Documentation Organization Summary ===" -ForegroundColor Magenta

# Display final structure
Write-Host "`nOrganized documentation structure:" -ForegroundColor Yellow

if (Test-Path "docs") {
    Write-Host "`nDocumentation files (docs/):" -ForegroundColor Cyan
    Get-ChildItem "docs" -Recurse -File | ForEach-Object {
        $relativePath = $_.FullName.Replace((Get-Location).Path + "\", "")
        Write-Host "  $relativePath" -ForegroundColor White
    }
}

Write-Host "`nFiles remaining in project root:" -ForegroundColor Cyan
Get-ChildItem "." -File -Filter "*.md" | ForEach-Object {
    Write-Host "  $($_.Name)" -ForegroundColor White
}

Write-Host "`n✅ Documentation organization completed!" -ForegroundColor Green
Write-Host "`n📝 Benefits achieved:" -ForegroundColor Yellow
Write-Host "   • Clean project root with only README.md" -ForegroundColor White
Write-Host "   • Organized documentation by category" -ForegroundColor White
Write-Host "   • Easy navigation with docs/README.md index" -ForegroundColor White
Write-Host "   • Professional documentation structure" -ForegroundColor White
Write-Host "   • Better maintainability and discoverability" -ForegroundColor White

Write-Host "`n🎯 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Update main README.md to reference docs/ directory" -ForegroundColor White
Write-Host "   2. Update any links in other files to point to new locations" -ForegroundColor White
Write-Host "   3. Consider adding docs/ to .gitignore if needed" -ForegroundColor White