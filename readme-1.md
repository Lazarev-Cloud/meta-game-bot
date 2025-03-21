```
+------------------------------------+
|           Telegram API             |
+------------------------------------+
                  |
+------------------------------------+
|       Bot Framework (python-       |
|          telegram-bot)             |
+------------------------------------+
                  |
+---------------------------------------+
|                                       |
| +---------------+    +---------------+|
| |  Command      |    |  Callback     ||
| |  Handlers     |    |  Handlers     ||
| +---------------+    +---------------+|
|                                       |
| +---------------+    +---------------+|
| |  Message      |    |  Error        ||
| |  Formatters   |    |  Handlers     ||
| +---------------+    +---------------+|
|                                       |
+---------------------------------------+
                  |
+---------------------------------------+
|         Game Logic Layer              |
| +---------------+    +---------------+|
| |  Player       |    |  District     ||
| |  Management   |    |  Control      ||
| +---------------+    +---------------+|
|                                       |
| +---------------+    +---------------+|
| |  Resource     |    |  Politician   ||
| |  Management   |    |  System       ||
| +---------------+    +---------------+|
|                                       |
| +---------------+    +---------------+|
| |  Action       |    |  Notification ||
| |  Processing   |    |  System       ||
| +---------------+    +---------------+|
+---------------------------------------+
                  |
+---------------------------------------+
|         Database Layer                |
| +---------------+    +---------------+|
| |  Query        |    |  Transaction  ||
| |  Execution    |    |  Management   ||
| +---------------+    +---------------+|
|                                       |
| +---------------+    +---------------+|
| |  Schema       |    |  Migration    ||
| |  Management   |    |  Support      ||
| +---------------+    +---------------+|
+---------------------------------------+
                  |
+------------------------------------+
|           SQLite Database          |
+------------------------------------+
```

# Belgrade Game Bot Setup Instructions

This document provides instructions for setting up and running the Belgrade Game Telegram Bot after the code fixes.

## Prerequisites

- Python 3.12 or higher
- pip (Python package installer)
- A Telegram Bot token (from BotFather)

## Setup Steps

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/belgrade-game-bot.git
cd belgrade-game-bot
```

2. **Create and activate a virtual environment (recommended)**

```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Create the .env file**

Copy the example .env file and add your Telegram Bot token:

```bash
cp .env.example .env
```

Then edit the `.env` file to add your Telegram Bot token and admin IDs.

5. **Set up the directory structure**

Run the setup script to ensure all required directories and files exist:

```bash
python setup.py
```

6. **Initialize the database**

The database will be automatically initialized when you first run the bot, but you can also set it up separately:

```bash
python -c "from db.schema import setup_database; setup_database()"
```

7. **Run the bot**

```bash
python main.py
```

## Troubleshooting

If you encounter any issues during setup:

1. **Check for syntax errors**

```bash
python -m py_compile main.py
```

2. **Verify file permissions**

Ensure that all Python files have executable permissions:

```bash
# On macOS/Linux
chmod +x main.py
```

3. **Check log files**

Examine the `bot.log` file for error messages:

```bash
tail -n 100 bot.log
```

4. **Database issues**

If there are issues with the database, you can delete it and let the bot recreate it:

```bash
rm belgrade_game.db
```

## Common Issues

1. **F-string with backslash**: Make sure any f-strings containing backslashes are properly formatted.

2. **Missing callback handlers**: Ensure all callback patterns are registered in `bot/callbacks.py`.

3. **Import errors**: Check that all required modules are imported and the directory structure is correct.

## Additional Resources

- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)