#!/bin/bash
#
# PubMed Gemini Extension - One-Click Installer
# For macOS and Linux - Installs ALL dependencies automatically!
#
# Usage (copy & paste this ONE line):
#   curl -fsSL https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/install.sh | bash
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
REPO_URL="https://github.com/avivlyweb/pubmed-gemini-extension"
INSTALL_DIR="${HOME}/.pubmed-gemini-extension"

# Detect terminal capabilities
supports_emoji() {
    [[ "$TERM_PROGRAM" == "Apple_Terminal" ]] || [[ -n "$WT_SESSION" ]] || \
    [[ "$TERM" == *"256color"* ]] || [[ "$COLORTERM" == "truecolor" ]]
}

if supports_emoji; then
    CHECK="✅" ; CROSS="❌" ; WARN="⚠️" ; ROCKET="🚀" ; GEAR="⚙️" ; PACKAGE="📦" ; PARTY="🎉" ; SEARCH="🔍" ; DNA="🧬"
else
    CHECK="[OK]" ; CROSS="[X]" ; WARN="[!]" ; ROCKET="==>" ; GEAR="[*]" ; PACKAGE="[P]" ; PARTY="[!]" ; SEARCH="[?]" ; DNA="[+]"
fi

# Print functions
banner() {
    clear 2>/dev/null || true
    echo ""
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}                                                              ${PURPLE}║${NC}"
    echo -e "${PURPLE}║${NC}   ${DNA} ${BOLD}${CYAN}PubMed Gemini Extension${NC}                                ${PURPLE}║${NC}"
    echo -e "${PURPLE}║${NC}   ${SEARCH} Medical Research AI for Gemini CLI                     ${PURPLE}║${NC}"
    echo -e "${PURPLE}║${NC}                                                              ${PURPLE}║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

step()    { echo -e "\n${BLUE}${GEAR} ${BOLD}$1${NC}"; echo -e "${BLUE}────────────────────────────────────────${NC}"; }
info()    { echo -e "  ${BLUE}→${NC} $1"; }
success() { echo -e "  ${GREEN}${CHECK}${NC} $1"; }
warn()    { echo -e "  ${YELLOW}${WARN}${NC} $1"; }
error()   { echo -e "  ${RED}${CROSS}${NC} $1"; }

cmd_exists() { command -v "$1" >/dev/null 2>&1; }

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*)  echo "linux" ;;
        MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
        *) echo "unknown" ;;
    esac
}

# Install Homebrew (macOS only)
ensure_homebrew() {
    if [[ "$(detect_os)" != "macos" ]]; then return 0; fi
    
    if cmd_exists brew; then
        success "Homebrew already installed"
        return 0
    fi
    
    info "Installing Homebrew (this may take a minute)..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/null
    
    # Add to PATH for current session
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -f "/usr/local/bin/brew" ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    
    success "Homebrew installed"
}

# Install Git
ensure_git() {
    if cmd_exists git; then
        success "Git already installed"
        return 0
    fi
    
    info "Installing Git..."
    case "$(detect_os)" in
        macos)  brew install git ;;
        linux)
            if cmd_exists apt-get; then sudo apt-get update && sudo apt-get install -y git
            elif cmd_exists dnf; then sudo dnf install -y git
            elif cmd_exists yum; then sudo yum install -y git
            elif cmd_exists pacman; then sudo pacman -S --noconfirm git
            fi ;;
    esac
    success "Git installed"
}

# Install Node.js
ensure_nodejs() {
    local need_install=true
    
    if cmd_exists node; then
        local ver=$(node --version | sed 's/v//' | cut -d. -f1)
        if [[ "$ver" -ge 18 ]]; then
            success "Node.js v$(node --version | sed 's/v//') already installed"
            need_install=false
        else
            warn "Node.js $ver found, but 18+ required. Upgrading..."
        fi
    fi
    
    if $need_install; then
        info "Installing Node.js 20 LTS..."
        case "$(detect_os)" in
            macos)
                brew install node@20
                brew link --overwrite node@20 2>/dev/null || true
                ;;
            linux)
                if cmd_exists apt-get; then
                    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
                    sudo apt-get install -y nodejs
                elif cmd_exists dnf; then
                    curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
                    sudo dnf install -y nodejs
                elif cmd_exists yum; then
                    curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
                    sudo yum install -y nodejs
                elif cmd_exists pacman; then
                    sudo pacman -S --noconfirm nodejs npm
                fi
                ;;
        esac
        success "Node.js $(node --version) installed"
    fi
}

# Install Python 3.10+
ensure_python() {
    local python_cmd=""
    
    # Check for Python 3.10+
    for cmd in python3.13 python3.12 python3.11 python3.10 python3; do
        if cmd_exists "$cmd"; then
            local ver=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
            local major=${ver%%.*}
            local minor=${ver#*.}
            if [[ "$major" -ge 3 ]] && [[ "$minor" -ge 10 ]]; then
                python_cmd="$cmd"
                break
            fi
        fi
    done
    
    # Also check Homebrew paths
    for cmd in /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 /usr/local/bin/python3.12; do
        if [[ -x "$cmd" ]] && [[ -z "$python_cmd" ]]; then
            python_cmd="$cmd"
            break
        fi
    done
    
    if [[ -n "$python_cmd" ]]; then
        success "Python $($python_cmd --version | cut -d' ' -f2) already installed"
        echo "$python_cmd"
        return 0
    fi
    
    info "Installing Python 3.12..."
    case "$(detect_os)" in
        macos)
            brew install python@3.12
            python_cmd="/opt/homebrew/bin/python3.12"
            [[ ! -x "$python_cmd" ]] && python_cmd="/usr/local/bin/python3.12"
            ;;
        linux)
            if cmd_exists apt-get; then
                sudo apt-get update
                sudo apt-get install -y python3.12 python3.12-venv python3-pip 2>/dev/null || \
                sudo apt-get install -y python3.11 python3.11-venv python3-pip 2>/dev/null || \
                sudo apt-get install -y python3.10 python3.10-venv python3-pip
            elif cmd_exists dnf; then
                sudo dnf install -y python3.12 2>/dev/null || \
                sudo dnf install -y python3.11 2>/dev/null || \
                sudo dnf install -y python3.10
            fi
            python_cmd="python3"
            ;;
    esac
    
    success "Python $($python_cmd --version | cut -d' ' -f2) installed"
    echo "$python_cmd"
}

# Clone or update repository
setup_repository() {
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        info "Updating existing installation..."
        cd "$INSTALL_DIR"
        git fetch origin 2>/dev/null
        git reset --hard origin/main 2>/dev/null || true
        success "Updated to latest version"
    else
        [[ -d "$INSTALL_DIR" ]] && rm -rf "$INSTALL_DIR"
        info "Downloading extension..."
        git clone --depth 1 "$REPO_URL" "$INSTALL_DIR" 2>/dev/null
        success "Extension downloaded"
    fi
}

# Install Node dependencies
install_node_deps() {
    info "Installing Node.js packages..."
    cd "$INSTALL_DIR/pubmed-gemini"
    npm install --silent --no-fund --no-audit 2>/dev/null || npm install
    npm run build 2>/dev/null || true
    success "Node.js packages installed"
}

# Install Python dependencies
install_python_deps() {
    local python_cmd="$1"
    
    info "Setting up Python environment..."
    
    # Check if pubmed-mcp exists
    if [[ ! -d "$INSTALL_DIR/pubmed-mcp" ]]; then
        error "pubmed-mcp directory not found!"
        error "Please ensure the repository was cloned correctly."
        exit 1
    fi
    
    cd "$INSTALL_DIR/pubmed-mcp"
    
    # Create virtual environment
    if [[ ! -d "venv" ]]; then
        $python_cmd -m venv venv
    fi
    
    # Install packages
    source venv/bin/activate
    pip install --quiet --upgrade pip 2>/dev/null
    pip install --quiet httpx mcp 2>/dev/null || pip install httpx mcp
    deactivate
    
    success "Python packages installed"
}

# Configure for Gemini CLI
configure_gemini() {
    # Create extensions directory
    mkdir -p "$HOME/.gemini/extensions"
    
    # Create symlink
    local link_path="$HOME/.gemini/extensions/pubmed-gemini"
    [[ -L "$link_path" ]] && rm "$link_path"
    [[ -d "$link_path" ]] && rm -rf "$link_path"
    ln -sf "$INSTALL_DIR/pubmed-gemini" "$link_path"
    
    success "Extension configured for Gemini CLI"
    
    # Check if Gemini CLI exists
    if ! cmd_exists gemini; then
        echo ""
        warn "Gemini CLI not found!"
        echo ""
        echo -e "  ${CYAN}To install Gemini CLI, visit:${NC}"
        echo -e "  ${BLUE}https://gcli.dev${NC}"
        echo ""
    else
        success "Gemini CLI detected"
    fi
}

# Create launcher script
create_launcher() {
    cat > "$INSTALL_DIR/run-server.sh" << 'EOF'
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/pubmed-mcp/venv/bin/activate"
python3 "$DIR/pubmed-mcp/pubmed_mcp.py"
EOF
    chmod +x "$INSTALL_DIR/run-server.sh"
}

# Print completion message
print_success() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}                                                              ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   ${PARTY} ${BOLD}Installation Complete!${NC}                                  ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                              ${GREEN}║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BOLD}${CYAN}How to use:${NC}"
    echo ""
    echo -e "  ${BOLD}1.${NC} Open Gemini CLI:"
    echo -e "     ${YELLOW}gemini${NC}"
    echo ""
    echo -e "  ${BOLD}2.${NC} Try these commands:"
    echo ""
    echo -e "     ${BLUE}/pubmed:search${NC} does yoga help anxiety"
    echo -e "     ${BLUE}/pubmed:analyze${NC} 34580864"
    echo -e "     ${BLUE}/pubmed:synthesis${NC} telemedicine for diabetes"
    echo ""
    echo -e "${CYAN}────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}Installation:${NC} $INSTALL_DIR"
    echo -e "  ${BOLD}Uninstall:${NC}    rm -rf $INSTALL_DIR ~/.gemini/extensions/pubmed-gemini"
    echo -e "${CYAN}────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "${PURPLE}Happy researching! ${ROCKET}${NC}"
    echo ""
}

# Main
main() {
    banner
    
    local os=$(detect_os)
    info "Detected: $os"
    
    if [[ "$os" == "unknown" ]]; then
        error "Unsupported operating system"
        exit 1
    fi
    
    if [[ "$os" == "windows" ]]; then
        error "Please use the PowerShell installer for Windows:"
        echo "  irm https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/install.ps1 | iex"
        exit 1
    fi
    
    step "Step 1/5: Package Manager"
    ensure_homebrew
    
    step "Step 2/5: Git"
    ensure_git
    
    step "Step 3/5: Node.js"
    ensure_nodejs
    
    step "Step 4/5: Python"
    python_cmd=$(ensure_python)
    
    step "Step 5/5: PubMed Extension"
    setup_repository
    install_node_deps
    install_python_deps "$python_cmd"
    configure_gemini
    create_launcher
    
    print_success
}

main "$@"
