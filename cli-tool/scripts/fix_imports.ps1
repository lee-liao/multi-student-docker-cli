# PowerShell Script to Fix Import Statements After Code Reorganization
# Updates all import statements to use the new organized directory structure

Write-Host "Starting import statement fixes..." -ForegroundColor Green

# Function to update imports in a file
function Update-ImportsInFile {
    param(
        [string]$FilePath
    )
    
    if (-not (Test-Path $FilePath)) {
        return
    }
    
    try {
        $content = Get-Content $FilePath -Raw
        $originalContent = $content
        $updated = $false
        
        # Define import mappings (old import -> new import)
        $importMappings = @{
            # Core modules
            'from port_assignment import' = 'from src.core.port_assignment import'
            'import port_assignment' = 'import src.core.port_assignment as port_assignment'
            'from project_manager import' = 'from src.core.project_manager import'
            'import project_manager' = 'import src.core.project_manager as project_manager'
            'from template_processor import' = 'from src.core.template_processor import'
            'import template_processor' = 'import src.core.template_processor as template_processor'
            'from version_manager import' = 'from src.core.version_manager import'
            'import version_manager' = 'import src.core.version_manager as version_manager'
            'from database_manager import' = 'from src.core.database_manager import'
            'import database_manager' = 'import src.core.database_manager as database_manager'
            'from docker_compose_manager import' = 'from src.core.docker_compose_manager import'
            'import docker_compose_manager' = 'import src.core.docker_compose_manager as docker_compose_manager'
            'from dockerfile_manager import' = 'from src.core.dockerfile_manager import'
            'import dockerfile_manager' = 'import src.core.dockerfile_manager as dockerfile_manager'
            
            # Security modules
            'from security_validation import' = 'from src.security.security_validation import'
            'import security_validation' = 'import src.security.security_validation as security_validation'
            'from secure_logger import' = 'from src.security.secure_logger import'
            'import secure_logger' = 'import src.security.secure_logger as secure_logger'
            
            # Monitoring modules
            'from project_status_monitor import' = 'from src.monitoring.project_status_monitor import'
            'import project_status_monitor' = 'import src.monitoring.project_status_monitor as project_status_monitor'
            'from port_verification_system import' = 'from src.monitoring.port_verification_system import'
            'import port_verification_system' = 'import src.monitoring.port_verification_system as port_verification_system'
            
            # Maintenance modules
            'from cleanup_maintenance_tools import' = 'from src.maintenance.cleanup_maintenance_tools import'
            'import cleanup_maintenance_tools' = 'import src.maintenance.cleanup_maintenance_tools as cleanup_maintenance_tools'
            
            # Configuration modules
            'from cors_config_manager import' = 'from src.config.cors_config_manager import'
            'import cors_config_manager' = 'import src.config.cors_config_manager as cors_config_manager'
            'from setup_script_manager import' = 'from src.config.setup_script_manager import'
            'import setup_script_manager' = 'import src.config.setup_script_manager as setup_script_manager'
            'from readme_manager import' = 'from src.config.readme_manager import'
            'import readme_manager' = 'import src.config.readme_manager as readme_manager'
            
            # Utility modules
            'from error_handling import' = 'from src.utils.error_handling import'
            'import error_handling' = 'import src.utils.error_handling as error_handling'
        }
        
        # Apply import mappings
        foreach ($oldImport in $importMappings.Keys) {
            $newImport = $importMappings[$oldImport]
            if ($content -match [regex]::Escape($oldImport)) {
                $content = $content -replace [regex]::Escape($oldImport), $newImport
                $updated = $true
            }
        }
        
        # Special handling for sys.path.append patterns
        if ($content -match "sys\.path\.append\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\)\)") {
            # For files in tests/, we need to go up to the cli-tool directory
            if ($FilePath -match "cli-tool[/\\]tests[/\\]") {
                $content = $content -replace "sys\.path\.append\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\)\)", "sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))"
                $updated = $true
            }
            # For files in src/, we need to go up to the cli-tool directory
            elseif ($FilePath -match "cli-tool[/\\]src[/\\]") {
                $content = $content -replace "sys\.path\.append\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\)\)", "sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))"
                $updated = $true
            }
        }
        
        # Write back if updated
        if ($updated -and $content -ne $originalContent) {
            Set-Content $FilePath $content -NoNewline
            Write-Host "✓ Updated imports in: $FilePath" -ForegroundColor Green
            return $true
        }
        else {
            Write-Host "  No changes needed: $FilePath" -ForegroundColor Gray
            return $false
        }
    }
    catch {
        Write-Host "✗ Error updating: $FilePath - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Update CLI entry point
Write-Host "`n=== Updating CLI Entry Point ===" -ForegroundColor Cyan
$cliUpdated = Update-ImportsInFile "cli-tool/cli.py"

# Update all source files
Write-Host "`n=== Updating Source Files ===" -ForegroundColor Cyan
$sourceFiles = Get-ChildItem "cli-tool/src" -Recurse -Filter "*.py"
$sourceUpdated = 0
foreach ($file in $sourceFiles) {
    if (Update-ImportsInFile $file.FullName) {
        $sourceUpdated++
    }
}

# Update all test files
Write-Host "`n=== Updating Test Files ===" -ForegroundColor Cyan
$testFiles = Get-ChildItem "cli-tool/tests" -Recurse -Filter "*.py"
$testUpdated = 0
foreach ($file in $testFiles) {
    if (Update-ImportsInFile $file.FullName) {
        $testUpdated++
    }
}

# Update script files
Write-Host "`n=== Updating Script Files ===" -ForegroundColor Cyan
$scriptFiles = Get-ChildItem "cli-tool/scripts" -Recurse -Filter "*.py"
$scriptUpdated = 0
foreach ($file in $scriptFiles) {
    if (Update-ImportsInFile $file.FullName) {
        $scriptUpdated++
    }
}

# Summary
Write-Host "`n=== Import Fix Summary ===" -ForegroundColor Magenta
Write-Host "CLI entry point: $(if($cliUpdated){'✓ Updated'}else{'○ No changes'})" -ForegroundColor $(if($cliUpdated){'Green'}else{'Yellow'})
Write-Host "Source files updated: $sourceUpdated / $($sourceFiles.Count)" -ForegroundColor Green
Write-Host "Test files updated: $testUpdated / $($testFiles.Count)" -ForegroundColor Green
Write-Host "Script files updated: $scriptUpdated / $($scriptFiles.Count)" -ForegroundColor Green

Write-Host "`n✅ Import statement fixes completed!" -ForegroundColor Green
Write-Host "`n📝 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Test the CLI tool: python cli-tool/cli.py --help" -ForegroundColor White
Write-Host "   2. Run unit tests: python -m pytest cli-tool/tests/unit/" -ForegroundColor White
Write-Tool "   3. Run integration tests: python -m pytest cli-tool/tests/integration/" -ForegroundColor White
Write-Host "   4. Update setup.py if needed for the new package structure" -ForegroundColor White