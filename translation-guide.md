# Translation System Guide for Belgrade Game Bot

This guide explains how the translation system works in the Belgrade Game Bot and how to maintain and extend it.

## Overview

The Belgrade Game Bot uses a comprehensive translation system that supports multiple languages (currently English and Russian). The system is designed to be easily extensible and maintainable. The primary components are:

1. **languages.py** - The core translations file that contains the main translation dictionaries and utility functions
2. **languages_update.py** - Additional translations and language-related functions
3. **translation_utils.py** - Utilities for managing, validating, and updating translations

## Key Components

### 1. Translation Dictionaries

Translations are organized in nested dictionaries in `languages.py`:

```python
TRANSLATIONS = {
    "en": {
        "welcome": "Welcome to the Belgrade Game, {user_name}!",
        # More English translations...
    },
    "ru": {
        "welcome": "Добро пожаловать в Новисадскую Игру, {user_name}!",
        # More Russian translations...
    }
}
```

Similarly, specialized dictionaries exist for cycle names and resource names:

```python
CYCLE_NAMES = {
    "en": {"morning": "Morning", "evening": "Evening"},
    "ru": {"morning": "Утренний", "evening": "Вечерний"}
}

RESOURCE_NAMES = {
    "en": {"influence": "Influence", "resources": "Resources", ...},
    "ru": {"influence": "Влияние", "resources": "Gotovina", ...}
}
```

### 2. Translation Functions

The main function for retrieving translations is `get_text`:

```python
get_text(key, lang="en", default=None, **kwargs)
```

- `key` - The translation key to look up
- `lang` - The language code (default: "en")
- `default` - Default text if translation is missing
- `**kwargs` - Format parameters for string formatting

Additional utility functions include:
- `get_cycle_name(cycle, lang="en")` - Get translated cycle name
- `get_resource_name(resource, lang="en")` - Get translated resource name
- `get_action_name(action_type, lang="en")` - Get translated action name
- `format_ideology(ideology_score, lang="en")` - Format ideology description

### 3. Language Management

Functions for getting and setting a player's language preference:

```python
get_player_language(player_id)  # Get language from database
set_player_language(player_id, language)  # Save language to database
```

### 4. Language Initialization

The translation system is initialized during bot startup:

```python
init_language_support()
```

This function:
1. Updates all translations with additions from `languages_update.py`
2. Initializes admin-specific translations
3. Checks for missing translations

## How to Add New Translations

### 1. Adding a Single Translation

To add a new translation key, locate the appropriate section in `languages.py` and add it to both language dictionaries:

```python
TRANSLATIONS = {
    "en": {
        # Existing translations...
        "new_key": "New English text",
    },
    "ru": {
        # Existing translations...
        "new_key": "Новый русский текст",
    }
}
```

### 2. Adding a Group of Related Translations

For larger sets of translations, it's recommended to add them to `languages_update.py`:

```python
ADDITIONAL_TRANSLATIONS = {
    "en": {
        "feature_key1": "Feature description 1",
        "feature_key2": "Feature description 2",
    },
    "ru": {
        "feature_key1": "Описание функции 1",
        "feature_key2": "Описание функции 2",
    }
}
```

### 3. Adding Support for a New Language

To add support for a new language:

1. Add the language to all translation dictionaries in `languages.py`:

```python
TRANSLATIONS = {
    "en": { /* existing translations */ },
    "ru": { /* existing translations */ },
    "de": {
        "welcome": "Willkommen beim Belgrade Game, {user_name}!",
        # ... more German translations
    }
}

CYCLE_NAMES = {
    "en": { /* existing translations */ },
    "ru": { /* existing translations */ },
    "de": {
        "morning": "Morgen",
        "evening": "Abend"
    }
}

RESOURCE_NAMES = {
    "en": { /* existing translations */ },
    "ru": { /* existing translations */ },
    "de": {
        "influence": "Einfluss",
        "resources": "Ressourcen",
        "information": "Information",
        "force": "Kraft"
    }
}

ACTION_NAMES = {
    "en": { /* existing translations */ },
    "ru": { /* existing translations */ },
    "de": {
        "influence": "Einfluss",
        "attack": "Angriff",
        "defense": "Verteidigung",
        "recon": "Aufklärung",
        "info": "Informationsverbreitung",
        "support": "Unterstützung"
    }
}
```

2. Update the language selection UI to include the new language in `bot/commands.py`

## Automatic Translation Checks

The `check_missing_translations()` function in `languages.py` automatically identifies and fixes missing translations during startup:

1. It compares all keys in the English dictionary with other languages
2. For any missing translations, it uses the English text as a fallback
3. It logs warnings for any missing translations

## Translation Utilities

The `translation_utils.py` script provides several tools for managing translations:

### 1. Generating a Translation Report

```bash
python translation_utils.py report
```

This generates a comprehensive report that shows:
- Translation statistics for each language
- Missing translations
- Format string mismatches
- Potentially unused translations

### 2. Exporting and Importing Translations

```bash
# Export translations to JSON
python translation_utils.py export --output translations.json

# Import translations from JSON
python translation_utils.py import --input translations.json
```

This allows you to work with external translation tools or services.

### 3. Generating Translation Stubs

```bash
python translation_utils.py stub
```

This generates a Python file with stubs for missing translations, making it easier to add them.

## Best Practices

1. **Use Keys, Not Direct Strings**: Always use `get_text("key")` instead of hardcoding strings
2. **Add Format Parameters**: For dynamic content, use format parameters: `get_text("welcome", lang, user_name=user.first_name)`
3. **Provide Defaults**: When introducing new keys, provide defaults: `get_text("new_key", lang, default="Default text")`
4. **Group Related Translations**: Organize translations into logical sections in the dictionaries
5. **Comment Translations**: For complex or context-specific translations, add comments
6. **Run Regular Checks**: Periodically use `translation_utils.py report` to check for missing or inconsistent translations

## Working with Format Strings

When creating translations with format placeholders:

1. Ensure all placeholders are present in all languages
2. Be careful with word order - some languages have different grammatical structures
3. Use named placeholders (`{name}`) instead of positional ones (`{0}`)

Example:
```python
# English
"points_earned": "You earned {points} points in {district}",

# Russian
"points_earned": "Вы заработали {points} очков в районе {district}",
```

## Handling Different Grammatical Forms

Some languages have different forms for plurals or gender. Use conditional formatting or multiple keys:

```python
# For plurals
"items_count_one": "1 item",
"items_count_many": "{count} items",

# Then in code
if count == 1:
    message = get_text("items_count_one", lang)
else:
    message = get_text("items_count_many", lang, count=count)
```

## Conclusion

The translation system in Belgrade Game Bot is designed to be comprehensive, maintainable, and easy to extend. By following the practices outlined in this guide, you can ensure a consistent multilingual experience for all users.
