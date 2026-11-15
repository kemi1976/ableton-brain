#!/usr/bin/env python3
"""
System Tray Mini-Controller
===========================
Windows system tray integration for quick DAW control
"""

import sys
import threading
import time
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Try to import pystray
try:
    import pystray
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    print("Warning: pystray not installed. System tray unavailable.")
    print("Install with: pip install pystray pillow")

class SystemTrayController:
    """System tray mini-controller for Windows"""
    
    def __init__(self):
        self.icon = None
        self.running = False
        self.volume = 0.5
        self.mute = False
        self.current_track = 0
        
        if PYSTRAY_AVAILABLE:
            self._create_menu()
    
    def _create_image(self) -> Image.Image:
        """Create tray icon image"""
        # Create a simple colored square
        image = Image.new('RGB', (64, 64), color='#4ecca3')
        draw = ImageDraw.Draw(image)
        
        # Draw a simple music note
        draw.rectangle([16, 16, 48, 48], fill='#ffffff')
        draw.ellipse([20, 20, 30, 25], fill='#000000')  # Note head
        draw.line([25, 25, 25, 15], fill='#000000', width=2)  # Stem
        
        return image
    
    def _create_menu(self):
        """Create system tray menu"""
        if not PYSTRAY_AVAILABLE:
            return
            
        self.icon = pystray.Icon(
            "ablyton_brain",
            self._create_image(),
            "ABLETON BRAIN",
            menu=pystray.Menu(
                pystray.MenuItem('▶ Play', lambda: self._send_daw_command('play')),
                pystray.MenuItem('⏹ Stop', lambda: self._send_daw_command('stop')),
                pystray.MenuItem('⏮ Previous', lambda: self._send_daw_command('prev')),
                pystray.MenuItem('⏭ Next', lambda: self._send_daw_command('next')),
                pystray.MenuItem('─', None, enabled=False),  # Separator
                pystray.MenuItem('🔊 Volume: {:.0%}'.format(self.volume), 
                               lambda: None, enabled=False),
                pystray.MenuItem('📦 Save Project', lambda: self._send_daw_command('save')),
                pystray.MenuItem('📤 Export', lambda: self._send_daw_command('export')),
                pystray.MenuItem('─', None, enabled=False),
                pystray.MenuItem('❌ Quit', lambda: self.quit())
            )
        )
    
    def _send_daw_command(self, command: str) -> None:
        """Send command to active DAW"""
        # This would integrate with the DAW adapters
        print(f"[Tray] Sending DAW command: {command}")
        
        # Map to OSC/MIDI commands
        commands = {
            'play': self._midi_out,
            'stop': self._midi_out,
            'prev': self._midi_out,
            'next': self._midi_out,
            'save': self._midi_out,
            'export': self._midi_out
        }
        
        if command in commands:
            # In production, would send actual MIDI/OSC
            pass
    
    def _midi_out(self, message: list) -> None:
        """Mock MIDI output - in production connects to rtmidi"""
        print(f"[MIDI Out] {message}")
    
    def start(self):
        """Start the system tray icon"""
        if not PYSTRAY_AVAILABLE:
            print("System tray not available on this system")
            return False
        
        self.running = True
        self.icon.run_detached()
        return True
    
    def quit(self):
        """Quit the system tray"""
        self.running = False
        if self.icon:
            self.icon.stop()
    
    def update_volume(self, level: float):
        """Update volume level"""
        self.volume = max(0.0, min(1.0, level))
        if self.icon:
            # Update menu text
            pass

def create_system_tray():
    """Factory function to create system tray controller"""
    return SystemTrayController()

if __name__ == "__main__":
    tray = create_system_tray()
    if tray.start():
        print("🎵 System Tray Controller running...")
        print("Click the icon in your system tray!")
        try:
            while tray.running:
                time.sleep(1)
        except KeyboardInterrupt:
            tray.quit()
            print("\n🛑 System Tray Controller stopped")