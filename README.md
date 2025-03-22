# Novi-Sad Political Strategy Game

## Overview

This Telegram bot implements a complex political strategy game set in Novi-Sad, Yugoslavia in 1999. Players compete for control over districts, manage resources, interact with politicians, and respond to international events.

## Core Game Mechanics

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

## User Interface

The bot provides an intuitive interface through Telegram's inline keyboards:

### Main Menu
- Status: View your resources, districts, and ideology
- Map: See district control across the city
- News: Read public news and faction-specific intelligence
- Actions: Submit main and quick actions
- Resources: Manage and exchange resources
- Politicians: Interact with local and international figures
- Collective Actions: Initiate or join coordinated efforts

### Commands
- `/start` - Begin the game, register as a player
- `/help` - Show available commands
- `/status` - Show your current game status
- `/map` - View the current control map
- `/time` - Check current game cycle information
- `/action` - Submit a main action
- `/quick_action` - Submit a quick action
- `/view_district [name]` - Get information about a district
- `/resources` - View your current resources
- `/convert_resource [type] [amount]` - Exchange resources
- `/check_income` - See expected resource income
- `/politicians` - List available politicians
- `/collective` - Initiate a collective action
- `/join [action_id]` - Join a collective action
- `/active_actions` - View all active collective actions

## Getting Started

1. Register with `/start` and choose your character's name and ideology
2. Check your initial resources with `/status`
3. Explore the city using the map and district information commands
4. Submit actions to gain control of districts
5. Establish relationships with politicians
6. Coordinate with other players through collective actions

Remember that your ideology (-5 to +5) will affect your interactions with politicians and districts, so choose wisely!

## Tips

- Physical presence during actions gives +20 control points
- Control 60+ CP to officially control a district
- Control 80+ CP for bonus resources (120%)
- Districts decay by 5 CP per cycle if you don't take actions there
- Combine different resource types for more effective actions
- Pay attention to ideology compatibility with politicians
- Use reconnaissance to gather information before major actions
- Join or initiate collective actions for maximum impact

Good luck controlling Novi-Sad!