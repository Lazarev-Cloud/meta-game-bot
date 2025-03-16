# Belgrade Game Telegram Bot

A feature-rich Telegram bot implementation of a political strategy game set in 1998 Belgrade, Yugoslavia. Players compete for control of city districts, manage resources, interact with politicians, and deal with international influences.

![Version](https://img.shields.io/badge/version-0.0.1-yellow)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Game Overview

The Belgrade Game is set in September 1998, where players act as political actors in Belgrade, the capital of the Federal Republic of Yugoslavia. The city serves as a microcosm for the political, social, and economic forces at play in the country.

### Core Game Mechanics

- **District Control:** Control districts to gain resources and influence
- **Resource Management:** Manage four resource types (Influence, Resources, Information, Force)
- **Political Interactions:** Develop relationships with local and international politicians
- **International Events:** Deal with external forces affecting the political landscape
- **Cycle-based Gameplay:** Strategic actions in morning and evening cycles
- **Multilingual Support:** Play in English or Russian

## Screenshots

*Screenshots will be added after deployment*

## Setup and Installation

### Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Installation Steps

1. **Clone the repository**

```bash
git clone https://github.com/Lazarev-Cloud/meta-game-bot.git
cd meta-game-bot
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure the bot**

- Copy `config.py.example` to `config.py`
- Update `config.py` with your Telegram Bot Token and admin IDs

```python
# config.py
TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_IDS = [
    123456789,  # Replace with your Telegram user ID
]
```

4. **Run the bot**

```bash
python main.py
```

## Game Commands

### Basic Commands

- `/start` - Begin the game and register your character
- `/help` - Display command list
- `/status` - Check resources and district control
- `/map` - View the current control map
- `/time` - Show current game cycle and time
- `/news` - Display recent news
- `/language` - Change interface language (English/Russian)

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

## Technical Details

### Project Structure

```
meta-game-bot/
├── bot/                  # Bot functionality
│   ├── __init__.py
│   ├── callbacks.py      # Callback handlers
│   └── commands.py       # Command handlers
├── db/                   # Database operations
│   ├── __init__.py
│   ├── queries.py        # Database queries
│   └── schema.py         # Database schema
├── game/                 # Game logic
│   ├── __init__.py
│   ├── actions.py        # Game actions
│   ├── districts.py      # District functionality
│   ├── district_utils.py # District utilities
│   ├── politicians.py    # Politician functionality
│   └── politician_utils.py # Politician utilities
├── config.py             # Configuration
├── language_utils.py     # Language utilities
├── languages.py          # Language translations
├── languages_update.py   # Additional translations
├── main.py               # Main entry point
├── validators.py         # Input validators
├── requirements.txt      # Dependencies
├── test_bot.py           # Test script
└── README.md             # Documentation
```

### Technologies Used

- **python-telegram-bot**: Telegram Bot API wrapper
- **SQLite**: Lightweight database
- **Multilingual support**: Fully localized in English and Russian

### Database Schema

The bot uses SQLite with the following main tables:

- `players`: Player information
- `resources`: Player resources
- `districts`: Belgrade districts
- `district_control`: Player control over districts
- `politicians`: Local and international politicians
- `actions`: Player actions
- `news`: In-game news
- `politician_relationships`: Relationships between players and politicians

## Game Rules Overview

### Districts and Control

- Each district represents different political and social forces
- 60+ control points are needed to fully control a district
- 80+ control points provide enhanced benefits
- Districts lose 5 control points per cycle if inactive

### Actions and Resources

- **Main Actions**: Influence, Attack, Defense
- **Quick Actions**: Reconnaissance, Spread Information, Support
- **Resources**: Influence, Resources, Information, Force
- Actions refresh every 3 hours
- Controlled districts provide resources each cycle

### Politicians and Ideology

- Politicians have ideology scores from -5 (reformist) to +5 (conservative)
- Players also have ideology scores affecting compatibility
- Higher compatibility increases action success rates
- International politicians randomly affect the game each cycle

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Based on the Belgrade Game ruleset by lazarev.cloud
- Powered by the python-telegram-bot library
- Thanks to all contributors and testers
