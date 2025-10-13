# PowerShell Script to Reorganize Multi-Student Docker Compose CLI Tool
# This script moves files from the flat cli-tool structure to organized subdirectories

Write-Host "Starting code reorganization..." -ForegroundColor Green
Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow

# Change to the project root directory
Set-Location "."

# Function to safely move files
function Move-FileIfExists {
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

Write-Host "`n=== Moving Core Modules ===" -ForegroundColor Cyan

# Core modules (some already moved)
Move-FileIfExists "cli-tool/template_processor.py" "cli-tool/src/core/"
Move-FileIfExists "cli-tool/version_manager.py" "cli-tool/src/core/"
Move-FileIfExists "cli-tool/database_manager.py" "cli-tool/src/core/"
Move-FileIfExists "cli-tool/docker_compose_manager.py" "cli-tool/src/core/"
Move-FileIfExists "cli-tool/dockerfile_manager.py" "cli-tool/src/core/"

Write-Host "`n=== Moving Security Modules ===" -ForegroundColor Cyan

# Security modules
Move-FileIfExists "cli-tool/security_validation.py" "cli-tool/src/security/"
Move-FileIfExists "cli-tool/secure_logger.py" "cli-tool/src/security/"

Write-Host "`n=== Moving Monitoring Modules ===" -ForegroundColor Cyan

# Monitoring modules
Move-FileIfExists "cli-tool/project_status_monitor.py" "cli-tool/src/monitoring/"
Move-FileIfExists "cli-tool/port_verification_system.py" "cli-tool/src/monitoring/"

Write-Host "`n=== Moving Maintenance Modules ===" -ForegroundColor Cyan

# Maintenance modules
Move-FileIfExists "cli-tool/cleanup_maintenance_tools.py" "cli-tool/src/maintenance/"

Write-Host "`n=== Moving Configuration Modules ===" -ForegroundColor Cyan

# Configuration modules
Move-FileIfExists "cli-tool/cors_config_manager.py" "cli-tool/src/config/"
Move-FileIfExists "cli-tool/setup_script_manager.py" "cli-tool/src/config/"
Move-FileIfExists "cli-tool/readme_manager.py" "cli-tool/src/config/"

Write-Host "`n=== Moving Utility Modules ===" -ForegroundColor Cyan

# Utility modules
Move-FileIfExists "cli-tool/error_handling.py" "cli-tool/src/utils/"

Write-Host "`n=== Moving Unit Tests ===" -ForegroundColor Cyan

# Unit tests
Move-FileIfExists "cli-tool/test_port_assignment_simple.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_project_manager_simple.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_template_processing_simple.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_error_handling_simple.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_security_validation.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_cleanup_simple.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_project_monitoring_simple.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_cors_config_manager.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_setup_script_manager.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_port_verification_system.py" "cli-tool/tests/unit/"

Write-Host "`n=== Moving Integration Tests ===" -ForegroundColor Cyan

# Integration tests
Move-FileIfExists "cli-tool/test_system_integration.py" "cli-tool/tests/integration/"
Move-FileIfExists "cli-tool/test_end_to_end_workflows.py" "cli-tool/tests/integration/"
Move-FileIfExists "cli-tool/test_docker_integration.py" "cli-tool/tests/integration/"
Move-FileIfExists "cli-tool/test_enhanced_end_to_end_validation.py" "cli-tool/tests/integration/"
Move-FileIfExists "cli-tool/test_project_creation_workflow.py" "cli-tool/tests/integration/"
Move-FileIfExists "cli-tool/test_project_copying.py" "cli-tool/tests/integration/"

Write-Host "`n=== Moving Comprehensive Tests ===" -ForegroundColor Cyan

# Comprehensive tests
Move-FileIfExists "cli-tool/test_error_handling_comprehensive.py" "cli-tool/tests/comprehensive/"
Move-FileIfExists "cli-tool/test_comprehensive_simple.py" "cli-tool/tests/comprehensive/"
Move-FileIfExists "cli-tool/run_comprehensive_tests.py" "cli-tool/tests/comprehensive/"
Move-FileIfExists "cli-tool/test_port_assignment.py" "cli-tool/tests/comprehensive/"
Move-FileIfExists "cli-tool/test_project_manager.py" "cli-tool/tests/comprehensive/"
Move-FileIfExists "cli-tool/test_template_processor.py" "cli-tool/tests/comprehensive/"
Move-FileIfExists "cli-tool/test_cleanup_maintenance_tools.py" "cli-tool/tests/comprehensive/"
Move-FileIfExists "cli-tool/test_project_status_monitor.py" "cli-tool/tests/comprehensive/"
Move-FileIfExists "cli-tool/test_error_handling.py" "cli-tool/tests/comprehensive/"

Write-Host "`n=== Moving Final Tests ===" -ForegroundColor Cyan

# Final tests
Move-FileIfExists "cli-tool/test_final_integration.py" "cli-tool/tests/final/"
Move-FileIfExists "cli-tool/final_cleanup_maintenance_test.py" "cli-tool/tests/final/"
Move-FileIfExists "cli-tool/final_port_verification_test.py" "cli-tool/tests/final/"
Move-FileIfExists "cli-tool/final_project_monitoring_test.py" "cli-tool/tests/final/"

Write-Host "`n=== Moving Additional Test Files ===" -ForegroundColor Cyan

# Additional test files that might exist
Move-FileIfExists "cli-tool/test_cli.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_common_project.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_database_manager.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_docker_compose.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_dockerfile_manager.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_interactive.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_port_conflicts.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_port_verification_simple.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_readme_manager.py" "cli-tool/tests/unit/"
Move-FileIfExists "cli-tool/test_template_engine_enhanced.py" "cli-tool/tests/unit/"

Write-Host "`n=== Moving Scripts ===" -ForegroundColor Cyan

# Move build script from root to scripts
Move-FileIfExists "build_distribution.py" "cli-tool/scripts/"

Write-Host "`n=== Moving Demo and Interactive Files ===" -ForegroundColor Cyan

# Move demo and interactive files to scripts
Move-FileIfExists "cli-tool/demo_interactive.py" "cli-tool/scripts/"

Write-Host "`n=== Reorganization Summary ===" -ForegroundColor Magenta

# Display final directory structure
Write-Host "`nFinal directory structure:" -ForegroundColor Yellow

if (Test-Path "cli-tool/src") {
    Write-Host "`nSource modules (cli-tool/src/):" -ForegroundColor Cyan
    Get-ChildItem "cli-tool/src" -Recurse -File | ForEach-Object {
        $relativePath = $_.FullName.Replace((Get-Location).Path + "\", "")
        Write-Host "  $relativePath" -ForegroundColor White
    }
}

if (Test-Path "cli-tool/tests") {
    Write-Host "`nTest files (cli-tool/tests/):" -ForegroundColor Cyan
    Get-ChildItem "cli-tool/tests" -Recurse -File | ForEach-Object {
        $relativePath = $_.FullName.Replace((Get-Location).Path + "\", "")
        Write-Host "  $relativePath" -ForegroundColor White
    }
}

if (Test-Path "cli-tool/scripts") {
    Write-Host "`nScript files (cli-tool/scripts/):" -ForegroundColor Cyan
    Get-ChildItem "cli-tool/scripts" -Recurse -File | ForEach-Object {
        $relativePath = $_.FullName.Replace((Get-Location).Path + "\", "")
        Write-Host "  $relativePath" -ForegroundColor White
    }
}

Write-Host "`nFiles remaining in cli-tool root:" -ForegroundColor Cyan
Get-ChildItem "cli-tool" -File | ForEach-Object {
    Write-Host "  cli-tool/$($_.Name)" -ForegroundColor White
}

Write-Host "`n✅ Code reorganization completed!" -ForegroundColor Green
Write-Host "`n📝 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Update import statements in files to use new paths" -ForegroundColor White
Write-Host "   2. Update CLI entry point (cli.py) to import from src/" -ForegroundColor White
Write-Host "   3. Update test runner paths" -ForegroundColor White
Write-Host "   4. Test the reorganized code structure" -ForegroundColor White

Write-Host "`n🎯 The code is now properly organized into:" -ForegroundColor Yellow
Write-Host "   • src/core/      - Core functionality (port assignment, project management)" -ForegroundColor White
Write-Host "   • src/security/  - Security validation and logging" -ForegroundColor White
Write-Host "   • src/monitoring/- Status monitoring and verification" -ForegroundColor White
Write-Host "   • src/maintenance/- Cleanup and maintenance tools" -ForegroundColor White
Write-Host "   • src/config/    - Configuration management" -ForegroundColor White
Write-Host "   • src/utils/     - Utilities and error handling" -ForegroundColor White
Write-Host "   • tests/unit/    - Unit tests" -ForegroundColor White
Write-Host "   • tests/integration/ - Integration tests" -ForegroundColor White
Write-Host "   • tests/comprehensive/ - Comprehensive test suites" -ForegroundColor White
Write-Host "   • tests/final/   - Final validation tests" -ForegroundColor White
Write-Host "   • scripts/       - Build and utility scripts" -ForegroundColor White