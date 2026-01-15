# Arch Whisper Implementation Kickoff

## Project Context
This is **arch-whisper**, a push-to-talk voice transcription tool for Linux (X11/Wayland) that:
- Records audio while holding a hotkey (Ctrl+Space)
- Transcribes using local Whisper (faster-whisper)
- Optionally cleans up text via Claude API
- Pastes directly into the focused application

## Beads System
The implementation is broken into 32 beads (B01-B32) tracked via `bd` (beads CLI). Each bead is a self-contained task with dependencies.

### Key Commands
```bash
bd ready          # Show tasks ready to work (no blockers)
bd show <id>      # Show bead details
bd update <id> -s in_progress   # Mark as in-progress
bd close <id>     # Mark complete when done
bd blocked        # Show what's blocked and why
bd sync           # Sync to beads-sync branch
```

### Implementation Reference
Full specifications for each bead are in `docs/plans/initial_plan/BEADS.md` - read the relevant section before implementing each bead.

## Your Task
Work through beads sequentially, respecting dependencies:

1. **Check ready tasks**: `bd ready`
2. **Pick a ready task** and mark it in-progress: `bd update <id> -s in_progress`
3. **Read the bead spec** from BEADS.md for implementation details
4. **Implement the bead** following the spec exactly
5. **Test/verify** the implementation works
6. **Mark complete**: `bd close <id>`
7. **Commit changes** with message: `Implement B##: <title>`
8. **Repeat** until blocked or all beads done

## Hard Stops
Stop and report if you encounter:
- Missing system dependencies that can't be installed
- Ambiguous requirements needing clarification
- Test failures you can't resolve
- External API/service issues

## Current State
- **Ready**: B01 (pyproject.toml + uv.lock)
- **Blocked**: 31 beads waiting on dependencies
- **Priority**: P0 beads first (MVP), then P1 (Wayland/Claude), then P2 (tests)

## Start Command
```
Begin implementing arch-whisper beads. Run `bd ready` to see available tasks, then work through them following the BEADS.md specifications. Commit after each completed bead.
```
