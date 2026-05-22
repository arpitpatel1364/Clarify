#!/bin/bash
# Clarify — Ubuntu Setup Script
# Run: bash install.sh

set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║        Clarify Installer            ║"
echo "║     AI Text Explainer for Ubuntu     ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Install it first: sudo apt install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PYTHON_VERSION found"

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    xclip \
    xsel \
    xdotool \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxkbcommon-x11-0 \
    libglib2.0-0 \
    2>/dev/null || true

echo "✓ System dependencies installed"

# Create virtual environment
echo ""
echo "🐍 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip -q

# Install Python packages
echo ""
echo "📥 Installing Python packages (this may take a minute)..."
pip install -r requirements.txt -q

echo "✓ All packages installed"

# Create desktop launcher
echo ""
echo "🖥️  Creating desktop launcher..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p ~/.local/share/applications

cat > ~/.local/share/applications/clarify.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Clarify
Comment=AI Text Explainer
Exec=bash -c "cd $SCRIPT_DIR && source venv/bin/activate && python main.py"
Icon=$SCRIPT_DIR/assets/logo.png
Terminal=false
Categories=Utility;
StartupNotify=false
StartupWMClass=Clarify
EOF

chmod +x ~/.local/share/applications/clarify.desktop
echo "✓ Desktop launcher created"

# Create run script
cat > run.sh << 'RUNEOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
python main.py "$@"
RUNEOF
chmod +x run.sh

echo ""
echo "╔══════════════════════════════════════╗"
echo "║         Installation Complete! ✓     ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "▶  To run Clarify:"
echo "   ./run.sh"
echo ""
echo "   Or find it in your app launcher as 'Clarify'"
echo ""
echo "💡 First run: Right-click the tray icon → Settings"
echo "   Add your API key for Claude, OpenAI, or any provider."
echo ""
