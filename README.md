# Belgrade Game Bot

A Telegram bot for playing a multiplayer strategic game set in Belgrade. Players compete for control of districts, influence politicians, and manage resources in a dynamic game world.

## 🎮 Game Overview

Belgrade Game is a multiplayer strategy game where players:

- Control districts throughout Belgrade
- Influence politicians to gain advantages
- Gather intelligence on opponents
- Coordinate with other players on joint actions
- Manage and distribute resources strategically

The game runs in cycles (morning and evening), with each cycle resetting player actions and distributing resources based on controlled territories.

## 📋 Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Telegram account
- Bot token from [@BotFather](https://t.me/botfather)

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/belgrade-game-bot.git
   cd belgrade-game-bot
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `config.py` file with your bot token:
   ```python
   TOKEN = "your_telegram_bot_token"
   ADMIN_IDS = [123456789]  # Your Telegram user ID for admin access
   ```

4. Initialize the database and language system:
   ```bash
   python main.py
   ```

### Running the Bot

```bash
python main.py
```

The bot will automatically:
- Set up the database if it doesn't exist
- Initialize the language system
- Register all commands and callbacks
- Schedule regular jobs for game cycles and maintenance

## 🎯 Game Mechanics

### Resources

Players manage four main resources:
- **Influence**: Used for political actions
- **Surveillance**: Used for intelligence gathering
- **Force**: Used for direct confrontations
- **Wealth**: Used for economic actions

Resources are distributed at the start of each game cycle based on controlled districts.

### Actions

Players can perform various actions:
- **Attack**: Challenge another player's control over a district
- **Defend**: Bolster defense in a controlled district
- **Influence**: Attempt to gain control over politicians
- **Gather Intelligence**: Learn about other players' activities
- **Support**: Help another player's action

### Coordinated Actions

Players can initiate or join coordinated actions:
1. The initiator creates an action with specific resource requirements
2. Other players can join by contributing their resources
3. The action's strength increases with more participants
4. Actions expire if not completed within a time limit

## 🌐 Multilingual Support

The bot supports multiple languages:
- English
- Serbian
- More can be added via the language system

Players can change their language with the `/language` command.

## 👨‍💻 Developer Guide

### Project Structure

- **main.py**: Application entry point
- **bot/**: Command and callback handlers
- **db/**: Database access and queries
- **game_jobs.py**: Scheduled game tasks
- **languages_base.py**: Base translations
- **languages_update.py**: Language utilities
- **error_handlers.py**: Error management

### Database Schema

The database uses SQLite with tables for:
- Players and their resources
- Districts and their controllers
- Politicians and their allegiances
- Coordinated actions and participants
- Game news and events

The schema is automatically updated with new versions via the migration system.

### Adding Features

1. Define database schema changes in `main.py` migrations
2. Add translations in `languages_base.py`
3. Implement game logic in appropriate modules
4. Register new commands/callbacks in `main.py`

## 🔧 Administration

Admin commands (only available to users listed in ADMIN_IDS):
- `/admin_help`: View admin commands
- Various commands for game management and monitoring

## 📝 License

[MIT License](LICENSE)

## 🙏 Acknowledgements

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) library
- Contributors and testers who helped improve the game
