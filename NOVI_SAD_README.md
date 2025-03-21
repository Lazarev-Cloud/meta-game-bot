# Novi Sad Game Conversion

This document outlines the changes made to convert the Belgrade Game to the Novi Sad Game, which is set in 1990s Yugoslavia.

## Changes Made

### 1. Geography and Districts

- Updated district coordinates and boundaries to Novi Sad locations
- Created 8 districts based on real Novi Sad areas:
  - **Stari Grad**: Historical and administrative center (+2 Influence, +2 Information)
  - **Liman**: University and scientific center (+2 Influence, +2 Information)
  - **Petrovaradin**: Cultural heritage, tourism (+2 Influence, +1 Gotovina)
  - **Podbara**: Industrial district (+3 Gotovina, +1 Force)
  - **Detelinara**: Residential district, working class (+2 Gotovina, +2 Influence)
  - **Satelit**: New district, economic growth (+3 Gotovina, +1 Influence)
  - **Adamovicevo**: Military objects, security (+3 Force, +1 Influence)
  - **Sremska Kamenica**: Suburb, shadow economy (+3 Force, +1 Information)

### 2. Politicians

Created a comprehensive politician system with:

- **Local Politicians**: 9 key Novi Sad politicians with ideological scores, district influence, and special abilities
  - Each connected to specific districts and with unique game effects
  - Ideology scale from -5 (reformist) to +5 (conservative)

- **International Politicians**: 10 international figures who can influence the game
  - Each with specific actions that affect game mechanics
  - Random activation during game cycles
  - Special effects on districts based on ideology control

### 3. Resources and Terminology

- Renamed "Resources" to "Gotovina" (cash) per the game rules
- Updated resource distribution for each district to match game design
- Implemented special resource effects from politicians

### 4. Language Support

- Updated all translations (English, Russian, and Serbian) to reference Novi Sad
- Added District name translations in all three languages
- Fixed Serbian translation completeness

### 5. Game Mechanics

- Implemented international politician influence mechanics
- Added politician ideology bonus calculations
- Created database schema updates to support new game elements
- Fixed district detection by location based on new coordinates

### 6. Testing and Verification

- Updated test cases to match Novi Sad coordinates
- Created verification scripts to check configuration
- Ensured all tests pass with the new setup

## Setup Instructions

To set up the Novi Sad game:

1. Run `python3 create_districts.py` to create the districts
2. Run `python3 create_politicians.py` to populate politicians
3. Run `python3 check_novi_sad_setup.py` to verify the setup

## Game Structure

The game is now structured around the political situation in Novi Sad, Yugoslavia in the 1990s. Players can:

- Control districts by taking actions
- Interact with local politicians
- Experience the effects of international political figures
- Gain resources (Influence, Gotovina, Information, Force)
- Align with ideologies on the reformist vs. conservative spectrum

The game reflects the complex political situation of 1990s Yugoslavia, with tensions between preserving the old order and implementing reforms. 