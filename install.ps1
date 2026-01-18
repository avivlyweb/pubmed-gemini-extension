#
# PubMed Gemini Extension - One-Click Installer for Windows
# 
# Usage (copy & paste this ONE line in PowerShell):
#   irm https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/install.ps1 | iex
#

$ErrorActionPreference = "Stop"

# Configuration
$RepoUrl = "https://github.com/avivlyweb/pubmed-gemini-extension"
$InstallDir = "$env:USERPROFILE\.pubmed-gemini-extension"

# Colors
function Write-Color {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Write-Banner {
    Clear-Host
    Write-Host ""
    Write-Color "================================================================" Magenta
    Write-Color "                                                              " Magenta
    Write-Color "   PubMed Gemini Extension                                    " Cyan
    Write-Color "   Medical Research AI for Gemini CLI                         " Cyan
    Write-Color "                                                              " Magenta
    Write-Color "================================================================" Magenta
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Color "[*] $Message" Blue
    Write-Color "----------------------------------------" Blue
}

function Write-Info    { param([string]$Msg) Write-Host "  > $Msg" -ForegroundColor Gray }
function Write-Success { param([string]$Msg) Write-Host "  [OK] $Msg" -ForegroundColor Green }
function Write-Warn    { param([string]$Msg) Write-Host "  [!] $Msg" -ForegroundColor Yellow }
function Write-Err     { param([string]$Msg) Write-Host "  [X] $Msg" -ForegroundColor Red }

function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

# Install Chocolatey (Windows package manager)
function Install-Chocolatey {
    if (Test-Command choco) {
        Write-Success "Chocolatey already installed"
        return
    }
    
    Write-Info "Installing Chocolatey package manager..."
    
    # Check if running as admin
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    
    if (-not $isAdmin) {
        Write-Warn "Chocolatey installation requires administrator privileges."
        Write-Host ""
        Write-Host "  Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
        Write-Host "  Or install dependencies manually:" -ForegroundColor Yellow
        Write-Host "    - Node.js: https://nodejs.org" -ForegroundColor Cyan
        Write-Host "    - Python:  https://python.org" -ForegroundColor Cyan
        Write-Host "    - Git:     https://git-scm.com" -ForegroundColor Cyan
        Write-Host ""
        
        $response = Read-Host "Continue without auto-installing dependencies? (y/n)"
        if ($response -ne 'y') { exit 1 }
        return
    }
    
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    
    # Refresh environment
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    
    Write-Success "Chocolatey installed"
}

# Install Git
function Install-Git {
    if (Test-Command git) {
        Write-Success "Git already installed"
        return
    }
    
    Write-Info "Installing Git..."
    
    if (Test-Command choco) {
        choco install git -y --no-progress | Out-Null
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    } else {
        Write-Err "Please install Git manually: https://git-scm.com"
        exit 1
    }
    
    Write-Success "Git installed"
}

# Install Node.js
function Install-NodeJS {
    $needInstall = $true
    
    if (Test-Command node) {
        $version = (node --version) -replace 'v', '' -split '\.' | Select-Object -First 1
        if ([int]$version -ge 18) {
            Write-Success "Node.js v$(node --version) already installed"
            $needInstall = $false
        } else {
            Write-Warn "Node.js $version found, but 18+ required. Upgrading..."
        }
    }
    
    if ($needInstall) {
        Write-Info "Installing Node.js 20 LTS..."
        
        if (Test-Command choco) {
            choco install nodejs-lts -y --no-progress | Out-Null
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        } else {
            Write-Err "Please install Node.js manually: https://nodejs.org"
            exit 1
        }
        
        Write-Success "Node.js $(node --version) installed"
    }
}

# Install Python
function Install-Python {
    $pythonCmd = $null
    
    # Check for Python 3.10+
    foreach ($cmd in @("python", "python3", "py")) {
        if (Test-Command $cmd) {
            try {
                $version = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                $parts = $version -split '\.'
                if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 10) {
                    $pythonCmd = $cmd
                    break
                }
            } catch {}
        }
    }
    
    if ($pythonCmd) {
        $ver = & $pythonCmd --version
        Write-Success "$ver already installed"
        return $pythonCmd
    }
    
    Write-Info "Installing Python 3.12..."
    
    if (Test-Command choco) {
        choco install python312 -y --no-progress | Out-Null
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        $pythonCmd = "python"
    } else {
        Write-Err "Please install Python manually: https://python.org"
        exit 1
    }
    
    Write-Success "Python $(& $pythonCmd --version) installed"
    return $pythonCmd
}

# Clone or update repository
function Setup-Repository {
    if (Test-Path "$InstallDir\.git") {
        Write-Info "Updating existing installation..."
        Push-Location $InstallDir
        git fetch origin 2>$null
        git reset --hard origin/main 2>$null
        Pop-Location
        Write-Success "Updated to latest version"
    } else {
        if (Test-Path $InstallDir) {
            Remove-Item -Recurse -Force $InstallDir
        }
        Write-Info "Downloading extension..."
        git clone --depth 1 $RepoUrl $InstallDir 2>$null
        Write-Success "Extension downloaded"
    }
}

# Install Node dependencies
function Install-NodeDeps {
    Write-Info "Installing Node.js packages..."
    Push-Location "$InstallDir\pubmed-gemini"
    npm install --silent --no-fund --no-audit 2>$null
    npm run build 2>$null
    Pop-Location
    Write-Success "Node.js packages installed"
}

# Install Python dependencies
function Install-PythonDeps {
    param([string]$PythonCmd)
    
    Write-Info "Setting up Python environment..."
    Push-Location "$InstallDir\pubmed-mcp"
    
    # Create virtual environment
    if (-not (Test-Path "venv")) {
        & $PythonCmd -m venv venv
    }
    
    # Activate and install packages
    & ".\venv\Scripts\pip.exe" install --quiet --upgrade pip 2>$null
    & ".\venv\Scripts\pip.exe" install --quiet httpx mcp 2>$null
    
    Pop-Location
    Write-Success "Python packages installed"
}

# Configure for Gemini CLI
function Configure-GeminiCLI {
    $extDir = "$env:USERPROFILE\.gemini\extensions"
    
    if (-not (Test-Path $extDir)) {
        New-Item -ItemType Directory -Path $extDir -Force | Out-Null
    }
    
    $linkPath = "$extDir\pubmed-gemini"
    if (Test-Path $linkPath) {
        Remove-Item -Recurse -Force $linkPath
    }
    
    # Create junction (symlink alternative for Windows)
    cmd /c mklink /J "$linkPath" "$InstallDir\pubmed-gemini" 2>$null
    
    Write-Success "Extension configured for Gemini CLI"
    
    if (-not (Test-Command gemini)) {
        Write-Host ""
        Write-Warn "Gemini CLI not found!"
        Write-Host ""
        Write-Host "  To install Gemini CLI, visit:" -ForegroundColor Cyan
        Write-Host "  https://gcli.dev" -ForegroundColor Blue
        Write-Host ""
    } else {
        Write-Success "Gemini CLI detected"
    }
}

# Print success message
function Show-Success {
    Write-Host ""
    Write-Color "================================================================" Green
    Write-Color "                                                              " Green
    Write-Color "   Installation Complete!                                     " Green
    Write-Color "                                                              " Green
    Write-Color "================================================================" Green
    Write-Host ""
    Write-Color "How to use:" Cyan
    Write-Host ""
    Write-Host "  1. Open Gemini CLI:"
    Write-Color "     gemini" Yellow
    Write-Host ""
    Write-Host "  2. Try these commands:"
    Write-Host ""
    Write-Color "     /pubmed:search does yoga help anxiety" Blue
    Write-Color "     /pubmed:analyze 34580864" Blue
    Write-Color "     /pubmed:synthesis telemedicine for diabetes" Blue
    Write-Host ""
    Write-Color "----------------------------------------------------------------" Cyan
    Write-Host "  Installation: $InstallDir"
    Write-Host "  Uninstall:    Remove-Item -Recurse $InstallDir"
    Write-Color "----------------------------------------------------------------" Cyan
    Write-Host ""
    Write-Color "Happy researching!" Magenta
    Write-Host ""
}

# Main
function Main {
    Write-Banner
    
    Write-Step "Step 1/5: Package Manager"
    Install-Chocolatey
    
    Write-Step "Step 2/5: Git"
    Install-Git
    
    Write-Step "Step 3/5: Node.js"
    Install-NodeJS
    
    Write-Step "Step 4/5: Python"
    $pythonCmd = Install-Python
    
    Write-Step "Step 5/5: PubMed Extension"
    Setup-Repository
    Install-NodeDeps
    Install-PythonDeps -PythonCmd $pythonCmd
    Configure-GeminiCLI
    
    Show-Success
}

Main
