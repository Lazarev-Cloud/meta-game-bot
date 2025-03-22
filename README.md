# Meta Game Bot Architecture

This Telegram bot implements a complex political strategy game set in Novi-Sad, Yugoslavia in 1999. The architecture follows a modular design with clear separation of concerns.

## Core Modules

### 1. Database Layer (`db/`)
- **supabase_client.py**: Client for Supabase database connections
- **queries.py**: Helper functions for common database operations
- The database stores game state including:
  - Player information and resources
  - District control
  - Politician relationships
  - Game cycles
  - Actions and their outcomes

### 2. Game Logic (`game/`)
- **actions.py**: Handling of player actions
- **districts.py**: District control mechanics
- **politicians.py**: Politician relationships and influence 
- **resources.py**: Resource management
- **cycles.py**: Game cycle management
- **international.py**: International political effects
- **collective_actions.py**: Coordinated player actions

### 3. Bot Interface (`bot/`)
- **commands.py**: Command handler registration (/start, /help, etc.)
- **callbacks.py**: Callback query handlers for inline buttons
- **keyboards.py**: Keyboard layouts and button creation
- **states.py**: Conversation states for multi-step interactions
- **middleware.py**: Middleware for authentication, logging, and rate limiting

### 4. Utilities (`utils/`)
- **i18n.py**: Internationalization (English and Russian support)
- **formatting.py**: Text formatting for displaying game data
- **config.py**: Configuration management
- **logger.py**: Logging setup

## Game Mechanics

### Districts and Control
- Players compete for control over 8 districts in Novi-Sad
- Control points (CP) determine control level:
  - 0-59 CP: No control
  - 60+ CP: District controlled
  - 80+ CP: Strong control (bonus resources)
- Each district provides different resources

### Resources
- **Influence**: Used for political actions
- **Money**: Used for economic actions, can be converted to other resources
- **Information**: Used for intelligence and reconnaissance
- **Force**: Used for military/security actions

### Action System
- **Main Actions (ОЗ)**: 1 per cycle, higher impact
  - Influence: Increase control in a district (+10 CP)
  - Attack: Reduce enemy control and gain control
  - Defense: Protect against attacks
- **Quick Actions (БЗ)**: 2 per cycle, smaller impact
  - Reconnaissance: Gather information
  - Information Spread: Publish news/propaganda
  - Support: Smaller control increase (+5 CP)

### Politicians
- Local and international politicians with ideological positions
- Relationship levels affect game outcomes
- International politicians can impose effects on the game

### Game Cycles
- Each day has two cycles: Morning and Evening
- Morning deadlines: 12:00, results at 13:00
- Evening deadlines: 18:00, results at 19:00

## User Interface

The bot uses Telegram's inline keyboards for all interactions, creating an intuitive interface that guides players through the game's complex mechanics.

### Conversation Flow
The bot implements several conversation flows:
- Registration process
- Action submission
- Resource conversion
- Collective action organization

### Internationalization
The bot supports multiple languages (currently English and Russian) using a translation system that can be easily extended to more languages.

## Database Schema

The database includes the following key tables:
- **players**: Player information
- **districts**: District information
- **district_control**: Control points by player/district
- **resources**: Player resources
- **actions**: Player actions
- **politicians**: Local and international political figures
- **player_politician_relations**: Relationships between players and politicians
- **cycles**: Game cycle tracking
- **news**: Game events and announcements

## Deployment Requirements

- Python 3.7+
- python-telegram-bot 20.6+
- Supabase account and project
- PostgreSQL functions for game logic