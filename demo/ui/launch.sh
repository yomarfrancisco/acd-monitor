#!/bin/bash

# ACD Monitor UI Demo - Launch Script
# Iteration 1: Dark Theme + RBB Economics Branding

echo "🚀 Launching ACD Monitor UI Demo - Dark Theme Edition"
echo ""

# Check if we're in the right directory
if [ ! -f "index.html" ]; then
    echo "❌ Error: Please run this script from the demo/ui directory"
    echo "   cd demo/ui"
    echo "   ./launch.sh"
    exit 1
fi

echo "✅ New Design Features:"
echo "   • Dark theme (Cursor-inspired)"
echo "   • RBB Economics branding"
echo "   • Mobile-first centering"
echo "   • Professional typography"
echo "   • Hero chart as central focus"
echo ""

# Detect OS and launch
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "🍎 Opening in default browser (macOS)..."
    open index.html
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "🐧 Opening in default browser (Linux)..."
    xdg-open index.html
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows
    echo "🪟 Opening in default browser (Windows)..."
    start index.html
else
    echo "❓ Unknown OS. Please open index.html manually in your browser."
    exit 1
fi

echo ""
echo "🎯 What to Review:"
echo "   • Dark theme appearance and contrast"
echo "   • RBB Economics logo prominence"
echo "   • Content centering (mobile-first)"
echo "   • Professional typography"
echo "   • Hero chart styling and colors"
echo ""
echo "🔄 To refresh, simply reload the page in your browser"
echo ""
echo "📝 Feedback: Look for professional appearance, RBB branding, and Cursor-like simplicity"
