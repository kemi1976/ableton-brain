# Mobile DAW Controller - Design & Implementation

**Use when creating mobile control apps for DAWs (Digital Audio Workstations).**
Design cross-platform controller apps that connect to desktop DAWs via WiFi, USB-OTG, or Bluetooth MIDI.

## 🎯 Procedure

**1. Choose Implementation Platform** (based on device/target)

Select ONE primary platform based on:
- **Native Android**: USB-OTG MIDI, lowest latency, Samsung devices
- **Web PWA**: Universal compatibility, no app store, any phone
- **React Native**: Cross-platform, app store distribution

Never try to build all three simultaneously - pick one and iterate.

**2. Define Connection Protocol**

Establish communication between phone and desktop:
- Use WebSocket for real-time JSON messaging
- Port 5000 is standard (match stream-server.py)
- Protocol: `{"type": "midi"|"action"|"feedback", ...}`
- Auto-reconnect on network changes

**3. Design Touch Control Surface**

UI components for music production:
- **Pad Grid**: 8x8 velocity-sensitive pads
- **Fader Controls**: Vertical sliders with touch hold
- **Knob Controls**: Rotation gestures with haptic feedback
- **Transport Bar**: Play, Stop, Record, Undo, Redo
- **Device Status**: Battery, connection state, latency

**4. Implement MIDI Bridge**

Phone → Desktop MIDI flow:
- **USB-OTG**: Zero-latency, Android USB Host API
- **Bluetooth MIDI**: Standard BLE MIDI profile
- **WiFi MIDI**: Convert WiFi messages to MIDI at backend

**5. Create Integration Points**

Connect to existing system:
- Load presets from JSON files
- Mirror DAW state (project open/closed, track count)
- Send feedback for visual updates

## 📋 Key Files Structure

```
mobile-daw-controller/
├── android/
│   ├── MainActivity.kt         # App lifecycle
│   ├── MidiController.kt       # USB-OTG/Bluetooth MIDI
│   ├── WebSocketClient.kt      # Network connection
│   └── ui/
│       ├── ControlSurface.kt   # Main UI
│       ├── FaderControl.kt     # Vertical sliders
│       └── PadGrid.kt          # Grid of buttons
├── webapp/
│   └── src/                    # React/Vite project
└── react-native/
    └── App.tsx               # Cross-platform entry
```

## ⚠️ Pitfalls

- **Don't support multiple platforms initially** - pick one and complete it fully before adding others.
- **USB-OTG requires Android device tree support** - test with target device (SM-A047F works, but not all Android phones have USB-OTG MIDI drivers).
- **WebSocket port conflicts** - use random port allocation or auto-detect available ports.
- **Touch latency kills music control** - optimize for <16ms response time on all gestures.
- **MIDI message ordering** - use timestamps in JSON to guarantee message order when received over network.

## 🎵 Integration Checklist

- [ ] WebSocket endpoint exposes JSON protocol
- [ ] MIDI messages are 3-byte arrays in JSON format
- [ ] Preset files are loadable from remote server
- [ ] DAW actions (save, export, undo) are exposed as API endpoints
- [ ] MIDI feedback loops are enabled for visual updates

## 🚀 Quick Start Templates

**Native Android** (fastest path):
```bash
# Open Android Studio
File → Import Project → /path/to/android-folder
```

**Web PWA** (universal):
```bash
npm create vite@latest phone-controller --template react-ts
cd phone-controller
npm install
```

**React Native**:
```bash
npx create-expo-app phone-controller
cd phone-controller
npx expo install @react-navigation/native
```

## 🔗 Related Skills

- `eliza-android-assistant` - Android development patterns
- `eliza-web-automation` - WebSocket integration
- `eliza-hacking-lab` - Network protocol design