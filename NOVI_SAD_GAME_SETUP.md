# Novi Sad Game Setup Guide

This document provides instructions for setting up and running the Novi Sad Game bot, along with information about recent fixes and improvements.

## Overview

The Novi Sad Game is a strategic role-playing game set in 1990s Yugoslavia, focusing on the political dynamics of Novi Sad during this turbulent period. The game includes:

- 8 districts based on real Novi Sad areas
- Local and international politicians with influence mechanics
- Resource management system
- Ideological scale from -5 (reformist) to +5 (conservative)

## Recent Fixes and Improvements

1. **Bot Process Management**
   - Fixed issues with multiple bot instances running simultaneously
   - Improved process killing to prevent conflicts
   - Added proper shutdown procedures for clean restart

2. **Novi Sad Districts**
   - Updated district boundaries to match the game rules
   - Corrected resource distribution for each district
   - Added comprehensive district translations in all supported languages

3. **Resources and Terminology**
   - Updated resource names to use "Gotovina" instead of generic "resources"
   - Aligned resource mechanics with game rules

4. **Politician System**
   - Maintained ideology scale (-5 to +5) for political alignment
   - Verified influence mechanics for local and international politicians

5. **Startup Scripts**
   - Created robust scripts for starting, stopping, and restarting the bot
   - Added proper cleanup of database files when resetting

## Setup Instructions

### Prerequisites

- Python 3.8+
- Telegram Bot API token (set in `.env` file)
- Required Python packages (listed in `requirements.txt`)

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/meta-game-bot.git
   cd meta-game-bot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Copy the example .env file and update with your own Telegram Bot API token:
   ```bash
   cp .env.example .env
   # Edit .env with your preferred editor
   ```

4. **Initialize the database**:
   ```bash
   python init_db.py
   ```

5. **Create districts and politicians**:
   ```bash
   python create_districts.py
   python create_politicians.py
   ```

6. **Verify the setup**:
   ```bash
   python check_novi_sad_setup.py
   ```

### Starting the Bot

You have several options to start the bot:

1. **Complete Reset and Start** (deletes and recreates the database):
   ```bash
   python reset_and_run.py
   ```

2. **Clean Start** (keeps existing data):
   ```bash
   ./restart_bot.sh
   ```

3. **Background Service** (recommended for production):
   ```bash
   ./start_background.sh
   ```

### Stopping the Bot

To stop the bot, you can use:
```bash
pkill -f "python run_bg_service.py"
pkill -f "python run_novi_sad_game.py"
pkill -f "python main.py"
```

### Monitoring

Monitor the bot's log files:
```bash
tail -f service.log  # For the background service
tail -f bot_output.log  # For direct bot output
tail -f bot.log  # For detailed bot logging
```

## Troubleshooting

### Multiple Bot Instances

If you receive errors about multiple bot instances running:
```
Conflict: terminated by other getUpdates request; make sure that only one bot instance is running
```

Use the cleanup script to kill all existing bot processes:
```bash
python cleanup_and_start.py
```

### Database Issues

If you encounter database corruption or errors, reset the database:
```bash
python reset_and_run.py
```

### Translation Warnings

Warnings about missing translations are normal and not critical. The system will fall back to English translations automatically.

## Administration

### Admin Commands

The bot includes several admin commands for game management:
- `/admin_help` - List available admin commands
- `/admin_reset` - Reset a player's actions
- `/admin_give` - Give resources to a player
- `/admin_broadcast` - Send message to all players

Admin user IDs must be configured in the `.env` file.

## Game Structure

The game is structured around the political situation in Novi Sad, Yugoslavia in the 1990s:

- **Districts**: 8 unique areas with different resource production
- **Politicians**: Local and international figures with varying ideologies
- **Resources**: Influence, Gotovina, Information, Force
- **Ideology**: Scale from -5 (reformist) to +5 (conservative)

Players can control districts, interact with politicians, perform actions, and compete for influence in this dynamic political simulation. 