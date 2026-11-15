# Quick Wins Implementation Pattern

## Description
Use when implementing and validating 5 quick wins or rapid feature prototypes. This skill captures the proven pattern for delivering working software in 5 focused milestones, with comprehensive testing at each stage.

## Core Principle
Deliver functional value incrementally - 5 features that each work independently, provide immediate feedback, and build a cohesive whole.

## Procedure

### Phase 1: Planning (15-30 minutes)
1. **Identify the 5 Quick Wins** - Choose features that:
   - Can be completed in 2-4 days total
   - Provide tangible value when used independently
   - Build on each other progressively
   - Have clear validation criteria

2. **Prioritize by Dependency** - Order wins so later ones can leverage earlier implementations:
   - Win 1: Foundation (e.g., MIDI Monitor)
   - Win 2: Data Management (e.g., Preset Browser)
   - Win 3: Integration (e.g., DAW Actions)
   - Win 4: User Experience (e.g., Theme System)
   - Win 5: System Integration (e.g., System Tray)

3. **Define Success Criteria** - For each win, specify:
   - Single test case that proves it works
   - Clear output or behavior that confirms completion
   - Minimum viable functionality

### Phase 2: Implementation (2-5 days)
4. **Create Comprehensive Demo** - Before implementing any win:
   - Draft demo_quick_wins.py with all 5 sections
   - Use TODO placeholders or basic print statements
   - Ensure the demo shows progression and integration

5. **Implement Wins 1-2 First** (Day 1-2 focus):
   - Core functionality only
   - Basic visualization/output
   - Immediate verification via demo script

6. **Implement Wins 3-5** (Day 3-5 focus):
   - Integration points between wins
   - Configuration systems
   - Advanced features

### Phase 3: Testing & Validation (Ongoing)
7. **Write Tests Early** - Create test cases for each win:
   - At least 2-3 tests per win
   - Include edge cases in your domain
   - Test integration between wins

8. **Run Tests After Each Implementation**:
   ```bash
   pytest tests/ -v
   ```
   All tests must pass before moving to next win.

9. **Verify Compliance Early** - Check domain-specific constraints:
   - For music: No Islamic content in artist database
   - For medical: HIPAA compliance
   - For finance: No illegal activities in data
   - Document compliance checks in test suite

### Phase 4: Documentation & Release
10. **Update README.md** - Include:
    - Quick Wins status with checkmarks
    - How to run the demo
    - Usage examples for each win
    - Test results summary

11. **Create Completion Report** - Document:
    - What was built (files created/modified)
    - Test results (all passing)
    - Known limitations
    - Future upgrade opportunities

## Key Patterns & Pitfalls

### Pattern: Global Visualizer Instance
Many visualization features need a shared state. Use a module-level singleton:
```python
_visualizer: Optional[ClassType] = None

def get_visualizer() -> ClassType:
    global _visualizer
    if _visualizer is None:
        _visualizer = ClassType()
    return _visualizer
```

### Pattern: JSON-Based Save/Load
For configuration and presets, use JSON for cross-compatibility:
```python
def save_session(self, filepath: Optional[str] = None) -> Path:
    if not filepath:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = PROJECT_ROOT / f"session_{timestamp}.json"
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    return filepath
```

### Pattern: CLI Tool for Management
Create a scripts/ directory for CLI tools that manage features:
```python
if __name__ == "__main__":
    # Parse CLI arguments
    if sys.argv[1] == "list":
        show_presets()
    elif sys.argv[1] == "show":
        show_preset(sys.argv[2])
```

### Pitfall: Duplicate Imports
Remove duplicate imports that cause namespace conflicts:
- Check for `from module import X` in both your code and demo
- Consolidate imports at the top of files
- Use `from main import` for shared functions only

### Pitfall: Path Resolution Issues
When demo scripts import from main module:
- Use `sys.path.insert(0, str(Path(__file__).parent / 'src'))`
- Avoid hardcoded Windows paths in demo files
- Use Path objects for cross-platform compatibility

### Pitfall: Missing Parenthesis in Expressions
Python 3.14+ is strict about operator precedence:
```python
# WRONG (type error in Python 3.14):
bar = '█' * abs(val) // 200

# CORRECT:
bar = '█' * (abs(val) // 200)
```

### Pitfall: Platform-Specific Session Paths
Never hardcode `/tmp/` or similar - use platform-appropriate defaults:
```python
# Use default session location
session_file = save_session()  # Uses PROJECT_ROOT
print(f"Session saved: {session_file.name}")
```

### Pitfall: String Concatenation in Print Statements
For multi-line output, use f-strings or format() consistently:
```python
# Use consistent formatting:
print(f"Events: {stats['total']:5d} | Note On: {stats['note_ons']:4d}")
# NOT mixed styles like:
print("Events: " + str(stats['total']) + " | Note On: " + ...)
```

## Verification Checklist

Before declaring Quick Wins complete:

- [ ] All 5 wins implemented with working code
- [ ] All tests passing (20+ tests recommended)
- [ ] Demo script runs without errors
- [ ] README.md updated with usage instructions
- [ ] Completion report documented
- [ ] Compliance requirements verified
- [ ] No duplicate code or imports
- [ ] Cross-platform paths handled correctly
- [ ] JSON serialization working for sessions/presets
- [ ] Error handling for missing dependencies (docs only, not fail)

## Example: MIDI Quick Wins Pattern

For music production projects, the 5 wins often follow this pattern:

1. **MIDI Monitor** - Real-time traffic visualization
2. **Preset Browser** - Save/load controller mappings
3. **DAW Actions** - One-click project operations
4. **Theme System** - Visual customization
5. **System Integration** - Tray/OS level controls

Each builds on the previous and provides immediate value when used alone.

## Resources

- `scripts/preset_browser.py` - CLI pattern example
- `demo_quick_wins.py` - Comprehensive demo structure
- `README.md` - Updated documentation with quick wins section
- `QUICK_WINS_COMPLETED.md` - Completion report template