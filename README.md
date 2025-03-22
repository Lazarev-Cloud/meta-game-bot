# Novi-Sad Political Strategy Game

A Telegram bot for a political strategy game set in Novi-Sad, Yugoslavia in 1999. Players compete for control over districts, manage resources, interact with politicians, and respond to international events.

## Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL database (via Supabase)
- Telegram Bot API token

### Setup Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/meta-game-bot.git
   cd meta-game-bot
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**

   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`

4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**

   Copy the `.env.example` file to `.env` and fill in your credentials:

   ```bash
   cp .env.example .env
   ```

   Edit the `.env` file with your Telegram Bot token, Supabase credentials, and admin user IDs.

6. **Create necessary directories**

   ```bash
   mkdir -p logs translations
   ```

7. **Initialize the database**

   ```bash
   python db_init.py
   ```

8. **Run the bot**

   ```bash
   python main.py
   ```

## Game Mechanics

### Districts and Control

- Players compete for control over 8 districts in Novi-Sad
- Control points (CP) determine control level:
  - 0-59 CP: No control
  - 60+ CP: District controlled
  - 80+ CP: Strong control (bonus resources)
- Each district provides different resources based on your control level

### Resources

- **Influence**: Used for political actions and gaining politicians' support
- **Money**: Used for economic actions, can be converted to other resources (2:1 ratio)
- **Information**: Used for intelligence and reconnaissance
- **Force**: Used for military/security actions

### Action System

- **Main Actions (ОЗ)**: 1 per cycle, higher impact
  - Influence: Increase control in a district (+10 CP)
  - Attack: Reduce enemy control and gain control
  - Defense: Protect against attacks
  - Politician Influence: Improve relations with politicians
  - Politician Reputation Attack: Reduce a politician's influence
  - Politician Displacement: Significantly reduce a politician's influence
- **Quick Actions (БЗ)**: 2 per cycle, smaller impact
  - Reconnaissance: Gather information
  - Information Spread: Publish news/propaganda
  - Support: Smaller control increase (+5 CP)
  - Kompromat Search: Find compromising information

### Politicians

- Local and international politicians with ideological positions (-5 to +5)
- Relationship levels affect game outcomes:
  - 0-30: Hostile - May work against you
  - 30-70: Neutral - Limited interaction
  - 70-100: Friendly - Provides resources and support
- International politicians can impose effects on the game

### Collective Actions

- Players can join forces for coordinated attacks or defense
- Resources contributed by all participants are combined for stronger effect
- Each participant receives control points based on their contribution

### Game Cycles

- Each day has two cycles: Morning and Evening
- Morning deadlines: 12:00, results at 13:00
- Evening deadlines: 18:00, results at 19:00

## Bot Commands

- `/start` - Begin the game, register as a player
- `/help` - Show available commands
- `/status` - Show your current game status
- `/map` - View the current control map
- `/time` - Check current game cycle information
- `/action` - Submit a main action
- `/quick_action` - Submit a quick action
- `/cancel_action` - Cancel your last action
- `/actions_left` - Check remaining actions
- `/view_district [name]` - Get information about a district
- `/resources` - View your current resources
- `/convert_resource [type] [amount]` - Exchange resources
- `/check_income` - See expected resource income
- `/politicians` - List available politicians
- `/politician_status [name]` - Get information about a politician
- `/international` - View international politicians
- `/collective` - Initiate a collective action
- `/join [action_id]` - Join a collective action
- `/active_actions` - View all active collective actions

### Admin Commands

- `/admin_process` - Process all pending actions and advance the cycle
- `/admin_generate [count]` - Generate international effects

## Technical Details

### Database Structure

The game uses a PostgreSQL database (hosted on Supabase) with the following main tables:

- `players`: Stores player information and game state
- `districts`: Contains district information and resource production
- `politicians`: Stores both local and international politicians
- `actions`: Records all player actions
- `collective_actions`: Tracks coordinated group actions
- `resources`: Manages player resources
- `district_control`: Tracks control points in districts
- `cycles`: Manages game cycles and deadlines

### Internationalization

The bot supports multiple languages:

- English (en_US)
- Russian (ru_RU)

Language selection is done during registration and can be changed later.

### Security Features

- Rate limiting to prevent spam
- Authentication for commands
- Connection pooling and retry mechanisms
- Admin access controls

## Development

### Running Tests

```bash
pytest tests/
```

### Adding New Features

1. Define the feature functionality in the appropriate module
2. Update command handlers or callbacks as needed
3. Add necessary database functions and tables
4. Update internationalization files with new strings
5. Test the feature comprehensively

### Project Structure

- `bot/`: Bot components (commands, callbacks, states, keyboards)
- `db/`: Database interface and SQL files
- `utils/`: Utility functions (i18n, formatting, logging)
- `translations/`: Language files
- `logs/`: Log files
- `tests/`: Test cases

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Supabase](https://supabase.com/)