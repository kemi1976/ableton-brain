# WebSocket Protocol Specification

Standard JSON protocol for mobile DAW controller apps to communicate with desktop backend.

## 📐 Message Structure

All messages follow this format:

```json
{
  "type": "message_type",
  "timestamp": 1234567890,
  "data": {...}
}
```

## 📨 Message Types

### 1. MIDI Messages

Send MIDI data from phone to DAW:

```json
{
  "type": "midi",
  "timestamp": 1234567890,
  "message": [144, 60, 100]  // Note On: Channel 0, Note 60, Velocity 100
}
```

**Message Format**: 3-byte MIDI array
- Byte 0: Status (0x90 = Note On, 0x80 = Note Off, 0xB0 = CC, 0xE0 = Pitch Wheel)
- Byte 1: Data 1 (Note number, CC number, etc.)
- Byte 2: Data 2 (Velocity, CC value, pitch value)

### 2. DAW Actions

Control DAW operations:

```json
{
  "type": "action",
  "timestamp": 1234567890,
  "action": "save_project",
  "daw": "ableton",
  "args": {}
}
```

**Available Actions**:
- `save_project`: Save current project
- `export_beatmap`: Bounce to audio file
- `undo`: Undo last action
- `redo`: Redo last action
- `create_track`: Add new MIDI/Audio track
- `arm_track`: Arm selected track for recording
- `record`: Toggle record button

### 3. Playback Controls

Transport commands:

```json
{
  "type": "transport",
  "timestamp": 1234567890,
  "command": "play",
  "value": true
}
```

**Commands**:
- `play`: Play/Pause toggle
- `stop`: Stop playback
- `record`: Record mode toggle
- `goto_start`: Jump to beginning
- `tempo`: Set BPM value

### 4. Parameter Control

Continuous controllers:

```json
{
  "type": "parameter",
  "timestamp": 1234567890,
  "parameter": "track_volume",
  "track_id": 0,
  "value": 0.85
}
```

**Parameters**:
- `track_volume`: Track volume (0.0 - 1.0)
- `track_pan`: Track panning (-1.0 to 1.0)
- `track_mute`: Track mute (true/false)
- `track_solo`: Track solo (true/false)
- `master_volume`: Master output volume

### 5. Feedback Messages

From DAW to phone (real-time monitoring):

```json
{
  "type": "feedback",
  "timestamp": 1234567890,
  "event": "note_on",
  "channel": 0,
  "note": 60,
  "velocity": 100
}
```

**Event Types**:
- `note_on`: MIDI note triggered
- `note_off`: MIDI note released
- `control_change`: CC message received
- `sysex`: System exclusive message
- `connected`: Device connected
- `disconnected`: Device disconnected

### 6. Connection Management

Handshake and status:

```json
{
  "type": "connection",
  "event": "connected",
  "client_id": "phone-123",
  "version": "1.0.0"
}
```

**Events**:
- `connected`: Client connected
- `disconnected`: Client disconnected
- `hello`: Initial connection greeting
- `ping`: Keep-alive message

## 🔄 Message Flow Examples

### MIDI Message Round Trip

```
Phone → DAW: {"type": "midi", "message": [144, 60, 100]}
DAW → Phone: {"type": "feedback", "event": "note_on", "note": 60, "velocity": 100}
```

### Transport Control

```
Phone → DAW: {"type": "transport", "command": "play", "value": true}
DAW → Phone: {"type": "feedback", "event": "playhead_moved", "position": 4.5}
```

### Parameter Automation

```
Phone Drag Fader → {"type": "parameter", "parameter": "track_volume", "value": 0.65}
Phone Release Fader → {"type": "parameter", "parameter": "track_volume", "value": 0.75, "action": "commit"}
```

## 🛠️ Implementation Notes

1. **Timestamps**: Always include for message ordering
2. **Versioning**: Include client version in connection message
3. **Keep-alive**: Send ping every 30 seconds
4. **Error Handling**: Include error message type for failures
5. **Binary Data**: Base64 encode sysex messages

## 🔌 Connection Setup

1. Phone opens WebSocket connection to `ws://desktop-ip:5000/controller`
2. Send connection message with client info
3. Receive hello message from server
4. Begin sending control messages
5. Monitor feedback messages for visual updates

## 📊 Error Messages

```json
{
  "type": "error",
  "timestamp": 1234567890,
  "code": "INVALID_MESSAGE",
  "message": "Unknown MIDI status byte"
}
```

**Common Error Codes**:
- `INVALID_MESSAGE`: Malformed JSON
- `INVALID_MIDI`: Invalid MIDI message format
- `DAW_NOT_CONNECTED`: DAW is not running
- `DEVICE_NOT_FOUND`: MIDI device not found
- `PERMISSION_DENIED`: Missing required permission

## 🎯 Quick Reference

**Connection**: `ws://<ip>:5000/controller`
**Port**: 5000 (standard)
**Format**: JSON
**Encoding**: UTF-8
**Heartbeat**: 30 seconds
**Max Message Size**: 1KB