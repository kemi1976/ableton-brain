# Real-Time Data Visualization in Desktop Applications

## Pattern: Terminal Visualization with Threading

For features that require real-time data display (MIDI monitoring, sensor data, logs), use this proven pattern:

### Core Architecture
```python
from collections import deque
from typing import Optional, List
import time
import threading

class RealTimeVisualizer:
    def __init__(self, max_items: int = 50):
        self.data_history: deque = deque(maxlen=max_items)
        self.display_lock = threading.Lock()
        self.stats = {'total': 0}
        self._visualizer: Optional['RealTimeVisualizer'] = None
    
    @classmethod
    def get_instance(cls) -> 'RealTimeVisualizer':
        if cls._visualizer is None:
            cls._visualizer = cls()
        return cls._visualizer
    
    def add_data(self, item) -> None:
        with self.display_lock:
            self.data_history.appendleft(item)
            self.stats['total'] += 1
            self.display()
```

### Global Singleton Pattern
Use module-level singleton for shared visualization state:

```python
# Module level
_visualizer: Optional[ClassType] = None

def get_visualizer() -> ClassType:
    global _visualizer
    if _visualizer is None:
        _visualizer = ClassType()
    return _visualizer

def process_data(item):
    viz = get_visualizer()
    viz.add_data(item)
    viz.display()
```

### Display Methods
- **ASCII Console**: Clear screen, format data in tables/grid
- **Colored Output**: Use ANSI codes or colorama for terminal colors
- **Progress Bars**: Character-based (█, ▓, ▒, ░) for visual feedback

### Safety: Clearing Screen
```python
import sys

def clear_screen():
    sys.stdout.write('\033[2J\033[H')  # ANSI escape sequence
    sys.stdout.flush()
```

## Pattern: Data Recording and Export

### Auto-numbered Session Files
```python
from datetime import datetime
from pathlib import Path

def save_session(self, filepath: Optional[str] = None) -> Path:
    if not filepath:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Use PROJECT_ROOT or appropriate default directory
        filepath = Path.cwd() / f"session_{timestamp}.json"
    
    with open(filepath, 'w') as f:
        json.dump(self.to_dict(), f, indent=2)
    
    return Path(filepath)
```

### JSON Serialization Pattern
Ensure all custom objects are JSON-serializable:

```python
@property
def to_dict(self) -> dict:
    return {
        'name': self.name,
        'items': list(self.data_history),
        'stats': dict(self.stats)
    }

def from_dict(data: dict) -> 'SelfType':
    obj = cls()
    obj.name = data['name']
    obj.data_history = deque(data['items'], maxlen=obj.max_items)
    obj.stats = data['stats']
    return obj
```

## Pattern: Interactive Console Controls

Respond to keyboard input without blocking:

```python
def display_with_controls(self):
    print("Controls: [Q]uit, [R]ecord, [C]lear, [S]ave Session")
    
    # Check for key press (non-blocking)
    # Implementation depends on platform
```

## Common Pitfalls

### 1. Operator Precedence (Python 3.14+)
Missing parentheses in arithmetic expressions causes TypeError:
```python
# WRONG:
bar = '█' * abs(val) // 200  # TypeError: unsupported operand type(s)

# CORRECT:
bar = '█' * (abs(val) // 200)
```

### 2. Deque Slicing in Python 3.14
Direct slicing may not work with all deque versions:
```python
# POTENTIALLY PROBLEMATIC:
for item in self.data_history[:20]:

# SAFER:
for item in list(self.data_history)[:20]:
```

### 3. Duplicate Imports
Imports in demo scripts can shadow main module:
```python
# In demo_quick_wins.py - remove redundant imports
from core.midi_monitor import ...  # Import at top only
```

### 4. Hardcoded Paths
Never use Unix-style paths in Windows demos:
```python
# WRONG:
session_file = save_session("/tmp/session.json")

# CORRECT:
session_file = save_session()  # Uses platform-appropriate default
```

### 5. String Concatenation in Formats
Use f-strings consistently:
```python
# CONSISTENT:
print(f"Events: {stats['total']:5d} | Note On: {stats['note_ons']:4d}")

# INCONSISTENT (harder to maintain):
print("Events: " + str(stats['total']) + " | Note On: " + str(stats['note_ons']))
```

## Example: MIDI Monitor Structure

The `midi_monitor.py` file demonstrates this pattern:

- `MIDIContentType` enum for message types
- `MIDIEvent` dataclass for structured event data
- `MIDIEventParser` for parsing raw MIDI bytes
- `MIDIConsoleVisualizer` for ASCII display
- Global `_visualizer` instance for shared state
- Interactive controls via keyboard polling

## Integration with GUI

For GUI applications, replace console output with:

```python
# Tkinter text widget
text_widget.insert(tk.END, formatted_line + "\n")
text_widget.see(tk.END)  # Auto-scroll

# Or update labels/bars
progress_bar['value'] = current_value
label.config(text=f"Status: {message}")
```

## Testing Patterns

Create test MIDI messages by hand:
```python
demo_messages = [
    [0x90, 60, 100],  # C4 note on, velocity 100
    [0xB0, 7, 100],   # Control Change: Volume = 100
    [0xE0, 0, 8192],  # Pitch wheel centered
]
```

Verify visualization output:
```python
def test_visualizer_displays_events():
    viz = MIDIConsoleVisualizer()
    viz.process_message([0x90, 60, 100])
    assert viz.stats['note_ons'] == 1
```