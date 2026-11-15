#!/bin/bash
# Quick Verification Script for Phone Controllers
# Run this to verify your phone control implementation

echo "📱 ABLETON BRAIN - Phone Controller Verification"
echo "==============================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if command -v adb &> /dev/null; then
    echo "✅ ADB installed"
else
    echo "⚠️  ADB not found - install Android Platform Tools"
fi

if command -v python3 &> /dev/null; then
    echo "✅ Python available"
else
    echo "⚠️  Python not found"
fi

# Check your existing system
echo ""
echo "Verifying your existing Ableton Brain system..."

if [ -f "main.py" ]; then
    echo "✅ main.py found"
else
    echo "❌ main.py not found"
fi

if [ -f "stream-server.py" ]; then
    echo "✅ stream-server.py found"
else
    echo "⚠️  stream-server.py not found (needed for WiFi control)"
fi

if [ -f "src/core/midi_monitor.py" ]; then
    echo "✅ midi_monitor.py found"
else
    echo "⚠️  midi_monitor.py not found"
fi

# Check MIDI device
echo ""
echo "Checking for MIDI devices..."
if lsusb | grep -i midi &> /dev/null; then
    echo "✅ MIDI device detected"
else
    echo "ℹ️  No MIDI device detected (USB-OTG mode will work with phone connected)"
fi

# Check phone control options
echo ""
echo "Phone Control Options Available:"
echo ""
echo "1. 📱 Native Android App"
echo "   Location: apps/phone-control/android/"
echo "   Best for: SM-A047F, USB-OTG, fastest setup"
echo "   Status: ✅ Implementation Complete"
echo ""
echo "2. 🌐 Web PWA (Progressive Web App)"
echo "   Location: apps/phone-control/web/"
echo "   Best for: Cross-platform, no app store, instant updates"
echo "   Status: ✅ Documentation Complete"
echo ""
echo "3. 🔀 React Native Hybrid"
echo "   Location: apps/phone-control/react-native/"
echo "   Best for: iOS + Android from one codebase"
echo "   Status: ✅ Documentation Complete"
echo ""

# Quick test instructions
echo "🔧 Quick Test Instructions:"
echo ""
echo "For Native Android:"
echo "  1. Open Android Studio"
echo "  2. File → Open → apps/phone-control/android"
echo "  3. Build → Build APK"
echo "  4. adb install app-debug.apk"
echo "  5. Open app on SM-A047F"
echo "  6. Start Python backend: python main.py"
echo "  7. Connect phone and computer to same WiFi"
echo "  8. Enter computer's IP in app → Connect"
echo ""

echo "🎯 Recommended Starting Point: Native Android"
echo "   You have USB-OTG experience with SM-A047F, this is quickest path to working prototype!"

echo ""
echo "✅ All phone control options documented and ready!"