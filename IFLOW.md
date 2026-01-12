# CineLight-Pi - Professional Media Center for Raspberry Pi 4

## Project Overview

CineLight-Pi is a professional media center for Raspberry Pi 4 based on VLC player with CLI. The project includes CEC control, universal playback tracking, TUI file manager, and backup system. The roadmap includes Arduino-based Ambilight integration.

## Architecture

The project consists of a collection of Python and Bash scripts that implement the media center functionality:

- **`vlc_db.py`** - Python library for secure SQLite DB operations
- **`vlc-cec.sh`** - Main VLC script with CEC control
- **`video-menu.sh`** - TUI video file selection menu using dialog
- **`playback-tracker.sh`** - Playback progress tracking library
- **`db-manager.sh`** - Database operations library via Python
- **`serials.sh`** - Series settings management library
- **`edit-time-tput.sh`** - Time editor using tput interface

## Key Components

### 1. Playback Control (VLC)
- Interaction with VLC via RC interface (localhost:4212)
- IR remote control support via CEC
- Support for various video formats (avi, mp4, mkv, mov, wmv, flv)

### 2. Progress Tracking
- Save playback position in SQLite DB
- Support for automatic resume from saved position
- Playback status indication in menu ([X] - watched, [T] - partial, [ ] - not started)

### 3. Series Management
- Automatic series recognition using S##E## pattern
- Series settings support: auto-continue, skip intro/outro
- Time editor for skip markers with tput interface

### 4. Database
- SQLite for storing progress data
- SQL injection protection through parameterized queries
- Support for tables: playback (for progress) and series_settings (for series preferences)

## Key Features

### Remote Control
- OK → Play/Pause
- UP/DOWN/LEFT/RIGHT → seek
- RED → set skip time markers
- GREEN → subtitle toggle
- YELLOW/BLUE → volume control
- 0-9 → jump to percentages

### Time Editor
- Interactive editing via tput
- Support for setting intro/end times and credits duration
- Data validation

### Progress Tracking
- Automatic progress save every 60 seconds
- Final save on playback completion
- Status caching for performance optimization

## Setup and Usage

### Requirements
- bash 4.0+
- Python 3.7+
- VLC media player
- dialog for TUI
- cec-utils for CEC control

### Main Scripts
1. `video-menu.sh` - Launch TUI video selection menu
2. `vlc-cec.sh` - Launch VLC with CEC control
3. `vlc_db.py` - CLI interface for database operations

### CLI Commands for Database
```
# Initialize DB
python3 vlc_db.py init

# Save progress
python3 vlc_db.py save_playback "video.mkv" 120 3600 3

# Get progress
python3 vlc_db.py get_percent "video.mkv"

# Series settings
python3 vlc_db.py save_settings "Show.S01" "1080p.mkv" 1 1 1
```

## Directory Structure

- `DOCS/` - Documentation
- `Log/` - Log files
- `BAK/` - Backups
- `Test/` - Test scripts
- `Py/` - Python utilities
- `RELIS/` - Release scripts
- `archive/` - Archive files

## Development Conventions

- Use snake_case for variable and function names
- Comments in Russian language
- SQL injection protection through parameterized queries
- Use basename for file operation consistency
- Automatic DB initialization on library load

## Session Management

### Starting a New Session
When beginning a new iFlow CLI session:

1. Read the instructions starting from `DOCS/INSTRUCTIONS/INDEX.md`
2. Continue with other instruction files as needed based on your specific tasks:
   - `HANDOFF.md` - Critical project instructions (always read first)
   - `QUICK_START.md` - Priority tasks for the current session
   - `SESSION-START.md` - Daily workflow instructions
   - `SESSION-END.md` - End-of-day procedures
   - Other files as referenced in INDEX.md

### Session Restart Recommendation
It's recommended to restart your iFlow CLI session when the context usage reaches approximately 70-80% of the maximum token limit to maintain optimal performance and prevent potential issues. Monitor your token usage during extended sessions.

## Development Workflow

### Optimization Plan Implementation
1. Read the first few lines of the optimization plan in `DOCS/INSTRUCTIONS/optimisation.md` to understand the current status
2. As you implement each item from the plan, remove or mark it as completed in the plan file
3. Follow the plan systematically, checking off items as they are implemented
4. Ensure all changes comply with existing project conventions and maintain backward compatibility