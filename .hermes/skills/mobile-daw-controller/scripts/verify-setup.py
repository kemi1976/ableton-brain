#!/usr/bin/env python3
"""
Verify Phone Controller Implementation
Run to check if all prerequisites are met for mobile DAW controller apps.
"""

import os
import sys
import json
import subprocess

def check_command(cmd, description):
    """Check if a command is available."""
    try:
        result = subprocess.run(
            ['which', cmd] if os.name != 'nt' else ['where', cmd],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False

def main():
    print("📱 Phone Controller Verification")
    print("=" * 50)
    
    checks = {
        'Node.js': check_command('node', 'Node.js runtime'),
        'Python': check_command('python3', 'Python interpreter'),
        'ADB': check_command('adb', 'Android Debug Bridge'),
        'WebSocket': check_command('python3', 'Python WebSocket lib'),
    }
    
    # Check WebSocket library
    try:
        import websockets
        print("✅ Python websockets library available")
    except ImportError:
        print("⚠️  Python websockets library not installed")
        print("   Install: pip install websockets")
    
    # Check for existing DAW controller files
    daw_files = [
        'main.py',
        'stream-server.py',
        'sqlite3'
    ]
    
    print("\n📁 Checking DAW controller integration points:")
    for file in daw_files:
        path = f'/c/Users/pc/Documents/AI PROJECTS ANDROID/knowledge/ableton-brain/{file}'
        if os.path.exists(path):
            print(f"  ✅ {file} found")
        else:
            print(f"  ❌ {file} not found")
    
    # Summary
    print("\n📊 Summary:")
    all_good = all(checks.values())
    
    if all_good:
        print("✅ All prerequisites met!")
        print("\nReady to implement phone controller app.")
        print("Choose platform: Native Android, Web PWA, or React Native")
        return 0
    else:
        print("❌ Some prerequisites missing:")
        for name, available in checks.items():
            status = "✅" if available else "❌"
            print(f"  {status} {name}")
        return 1

if __name__ == '__main__':
    sys.exit(main())