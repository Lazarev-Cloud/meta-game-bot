# Belgrade Game Telegram Bot

This Telegram bot implements a political strategy game set in 1998 Belgrade, Yugoslavia. Players compete for control of city districts, manage resources, interact with politicians, and deal with international influences.

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- `python-telegram-bot` v20.0 or higher
- SQLite3

### Installation

1. Clone or download this repository.

2. Install required dependencies:
   ```
   pip install python-telegram-bot
   ```

3. Configure the bot:
   - Open `config.py`
   - Replace `YOUR_BOT_TOKEN_HERE` with your actual Telegram bot token (get one from [@BotFather](https://t.me/BotFather))
   - Add your Telegram user ID to `ADMIN_IDS` to gain admin privileges

4. Run the bot:
   ```
   python belgrade_game_bot.py
   ```

## Game Mechanics

### Core Concepts

- **Districts**: Each district of Belgrade represents different political, social, and economic forces in Yugoslavia
- **Control Points (OP)**: Measure influence in a district (60+ points for control)
- **Resources**: Influence, Resources, Information, and Force
- **Politicians**: Local and international figures with ideological alignments
- **Game Cycles**: Morning (6:00-12:00) and Evening (13:01-18:00) cycles

### Player Actions

- **Main Actions**: Influence, Attack, Defense
- **Quick Actions**: Reconnaissance, Spread Information, Support
- **Resource Management**: Converting resources, controlling districts for income
- **Political Interactions**: Influencing politicians, dealing with international events

## Commands

### Basic Commands
- `/start` - Begin the game and register your character
- `/help` - Display command list
- `/status` - Check resources and district control
- `/map` - View the current control map
- `/time` - Show current game cycle and time
- `/news` - Display recent news

### Action Commands
- `/action` - Submit a main action (influence, attack, defense)
- `/quick_action` - Submit a quick action (recon, spread info, support)
- `/cancel_action` - Cancel your last pending action
- `/actions_left` - Check your remaining actions
- `/view_district [district]` - View information about a district

### Resource Commands
- `/resources` - View your current resources
- `/convert_resource [type] [amount]` - Convert resources
- `/check_income` - Check your expected resource income

### Political Commands
- `/politicians` - List available politicians
- `/politician_status [name]` - Get information about a politician
- `/international` - Information about international politicians

### Admin Commands
- `/admin_add_news [title] [content]` - Add a news item
- `/admin_process_cycle` - Manually process a game cycle
- `/admin_add_resources [player_id] [resource_type] [amount]` - Add resources
- `/admin_set_control [player_id] [district_id] [control_points]` - Set district control

## Game Rules

The bot implements the rules described in the game documents. Key points:

- Districts require 60+ control points to be considered controlled
- Control provides resources each cycle
- Actions refresh every 3 hours
- Districts lose 5 control points per cycle if inactive
- International politicians can randomly affect the game

## Maintenance

The bot uses SQLite for data storage. The database file (`belgrade_game.db`) is created automatically when the bot starts. You can back up this file to preserve game state.

## Customization

To modify game mechanics:
- Edit game constants at the top of the file
- Modify the database setup function to change resource distribution
- Adjust process_action function to change success probabilities