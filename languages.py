#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Language support for Belgrade Game Bot
This file contains all translations and language-related utilities
"""

import logging
import sqlite3
import datetime
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

# Dictionary of translations
TRANSLATIONS = {
    "en": {
        # Basic commands and responses
        "welcome": "Welcome to the Belgrade Game, {user_name}! This game simulates the political struggle in 1998 Yugoslavia through control of Belgrade's districts.\n\nPlease enter your character's name:",
        "name_set": "Welcome, {character_name}! You are now a political player in 1998 Belgrade.\n\nUse /help to see available commands and /status to check your current situation.",
        "invalid_name": "Please enter a valid name.",
        "operation_cancelled": "Operation cancelled.",
        "not_registered": "You are not registered. Use /start to begin the game.",

        # Help and documentation
        "help_title": "Belgrade Game Command Guide",
        "help_basic": "*Basic Commands:*\n• /start - Begin the game and register your character\n• /help - Display this command list\n• /status - Check your resources and district control\n• /map - View the current control map\n• /time - Show current game cycle and time until next\n• /news - Display recent news\n• /language - Change interface language",
        "help_action": "*Action Commands:*\n• /action - Submit a main action (influence, attack, defense)\n• /quick_action - Submit a quick action (recon, spread info, support)\n• /cancel_action - Cancel your last pending action\n• /actions_left - Check your remaining actions\n• /view_district [district] - View information about a district",
        "help_resource": "*Resource Commands:*\n• /resources - View your current resources\n• /convert_resource [type] [amount] - Convert resources\n• /check_income - Check your expected resource income",
        "help_political": "*Political Commands:*\n• /politicians - List available politicians\n• /politician_status [name] - Get information about a specific politician\n• /international - Information about international politicians",
        "help_footer": "For detailed game rules, refer to the game document.",
        "admin_commands": "Admin Commands",
        "admin_help_hint": "Use /admin_help to see all admin commands.",

        # Status information
        "status_title": "Status of {character_name}",
        "status_ideology": "Ideology: {ideology} ({score})",
        "status_resources": "*Gotovina:*\n🔵 Influence: {influence}\n💰 Gotovina: {resources}\n🔍 Information: {information}\n👊 Force: {force}",
        "status_actions": "*Actions Remaining:*\nMain Actions: {main}\nQuick Actions: {quick}",
        "status_districts": "*Controlled Districts:*",
        "status_no_districts": "*Controlled Districts:* None",
        "unnamed": "Unnamed",
        "no_username": "No username",
        "id": "ID",
        "name": "Name",
        "username": "Username",
        "ideology": "Ideology",
        "resources": "Gotovina",
        "influence": "Influence",
        "information": "Information",
        "force": "Force",
        "points": "points",

        # Map and districts
        "map_title": "Current Control Map of Belgrade",
        "map_legend": "Legend:",
        "map_strong_control": "🔒 Strong control (80+ points)",
        "map_controlled": "✅ Controlled (60-79 points)",
        "map_contested": "⚠️ Contested (20-59 points)",
        "map_weak": "❌ Weak presence (<20 points)",
        "map_no_control": "No control established",
        "map_too_large": "The map is being generated. Check the web UI for details.",
        "error_generating_map": "Error generating map.",
        "district_not_found": "District '{district_name}' not found. Use /view_district without arguments to see a list of districts.",
        "select_district": "Select a district to view:",
        "current_control": "Current Control",

        # Time information
        "time_info": "*Game Time Information*",
        "time_current": "Current Cycle: *{cycle}*",
        "time_deadlines": "Time until submission deadline: *{deadline}*\nTime until results: *{results}*",
        "time_schedule": "*Daily Schedule:*\nMorning Cycle: 6:00 - 12:00 (submissions), 13:00 (results)\nEvening Cycle: 13:01 - 18:00 (submissions), 19:00 (results)",
        "time_refresh": "Remember: Actions refresh every 3 hours!",
        "deadline_passed": "Deadline passed",
        "hours": "hours",
        "minutes": "minutes",

        # News
        "news_title": "Recent News",
        "no_news": "There is no news to report at this time.",

        # Actions
        "no_main_actions": "You have no main actions left. Actions refresh every 3 hours or at the start of a new cycle.",
        "no_quick_actions": "You have no quick actions left. Actions refresh every 3 hours or at the start of a new cycle.",
        "select_action_type": "Select the type of main action you want to perform:",
        "select_quick_action": "Select the type of quick action you want to perform:",
        "action_cancelled": "Your last pending action has been cancelled and Gotovina refunded.",
        "no_pending_actions": "You have no pending actions to cancel.",
        "actions_refreshed": "Your actions have been refreshed!\n\nMain Actions: {main}\nQuick Actions: {quick}",
        "current_actions": "Current Actions Remaining:\n\nMain Actions: {main}\nQuick Actions: {quick}",

        # Resource management
        "resources_title": "Your Current Gotovina",
        "resources_guide": "*Resource Usage Guide:*\n• *Influence* - Used for political maneuvers, gaining additional actions\n• *Gotovina* - Economy, finances, connections. Can be converted to other Gotovina\n• *Information* - Intelligence, rumors. Used for reconnaissance\n• *Force* - Military, police, criminal structures. Effective for attacks and defense",
        "convert_usage": "Usage: /convert_resource [type] [amount]\nExample: /convert_resource influence 2\n\nThis will convert 2 'Gotovina' into 1 of the specified type.",
        "amount_not_number": "Amount must be a number.",
        "amount_not_positive": "Amount must be positive.",
        "invalid_resource_type": "Invalid resource type. Valid types: {valid_types}",
        "not_enough_resources": "You don't have enough Gotovina. Need {needed}, have {available}.",
        "conversion_success": "Converted {resources_used} Gotovina into {amount} {resource_type}.",
        "no_districts_controlled": "You don't control any districts yet, so you won't receive any Gotovina income.\n\nControl districts (60+ control points) to receive Gotovina each cycle.",
        "income_controlled_districts": "*Controlled Districts:*",
        "income_total": "*Total Per Cycle:*\n🔵 Influence: +{influence}\n💰 Gotovina: +{resources}\n🔍 Information: +{information}\n👊 Force: +{force}",
        "income_note": "*Note:* Gotovina are distributed at the end of each cycle.",
        "income_no_full_control": "You have districts with some presence, but none are fully controlled yet.\n\nYou need 60+ control points in a district to receive Gotovina from it.",

        # Politicians
        "politicians_title": "Key Politicians in Belgrade",
        "no_politicians": "No politicians found in the database.",
        "select_politician": "Select a politician to view:",
        "politician_not_found": "Politician '{name}' not found. Use /politician_status without arguments to see a list.",
        "international_title": "International Politicians",
        "no_international": "No international politicians found in the database.",
        "international_note": "*Note:* International politicians can activate randomly each cycle. Their actions can significantly impact the political landscape in Belgrade. Use /news to stay informed about their latest activities.",
        "relationship": "Relationship",
        "compatibility": "Compatibility",
        "role": "Role",
        "district": "District",
        "key_relationships": "Key Relationships",

        # Ideology descriptions
        "ideology_strongly_conservative": "Strongly Conservative",
        "ideology_conservative": "Conservative",
        "ideology_neutral": "Neutral",
        "ideology_reformist": "Reformist",
        "ideology_strongly_reformist": "Strongly Reformist",

        # Relationship descriptions
        "compatibility_good": "Good ideological compatibility",
        "compatibility_moderate": "Moderate ideological differences",
        "compatibility_poor": "Significant ideological differences",

        # Actions on politicians
        "politician_influence_no_resources": "You need at least 2 Influence resources to influence a politician. Action cancelled.",
        "politician_influence_no_action": "You need a main action to influence a politician. Action cancelled.",
        "politician_influence_success": "You have used your influence on {name}. Your relationship with them may improve. Results will be processed at the end of the cycle.",
        "politician_info_no_resources": "You need at least 1 Information resource to gather info on a politician. Action cancelled.",
        "politician_info_no_action": "You need a quick action to gather info on a politician. Action cancelled.",
        "politician_info_title": "Intelligence Report: {name}",
        "politician_undermine_no_resources": "You need at least 2 Information resources to undermine a politician. Action cancelled.",
        "politician_undermine_no_action": "You need a main action to undermine a politician. Action cancelled.",
        "politician_undermine_success": "You have started undermining {name}'s influence. This may weaken their position in their district. Results will be processed at the end of the cycle.",
        "politician_not_found": "Politician not found.",
        "politician_info_success": "You have gathered valuable information about {name}.",
        "politician_collaborate_success": "You have successfully collaborated with {name} on a political initiative.",
        "politician_request_success": "You have received Gotovina from {name}.",
        "politician_power_success": "You have used {name}'s political influence to pressure your opponents.",
        "politician_rumors_success": "You have spread rumors about {name}, damaging their reputation.",
        "politician_scandal_success": "You have exposed {name} in a political scandal, severely damaging their position.",
        "politician_diplomatic_success": "You have established a diplomatic channel with {name}.",
        "politician_pressure_success": "You have used {name}'s international pressure against your opponents.",

        # Cycle results
        "cycle_results_title": "Results for {cycle} cycle",
        "your_actions": "*Your Actions:*",
        "no_details": "No details available",
        "your_districts": "*Your Districts:*",
        "recent_news": "*Recent News:*",
        "current_resources": "*Current Gotovina:*",

        # Control status
        "control_strong": "🔒 Strong control",
        "control_full": "✅ Controlled",
        "control_contested": "⚠️ Contested",
        "control_weak": "❌ Weak presence",
        "control_points": "points",

        # Language settings
        "language_current": "Your current language is: {language}",
        "language_select": "Please select your preferred language:",
        "language_changed": "Language changed to English",
        "language_button_en": "English",
        "language_button_ru": "Русский",

        # Action types
        "action_influence": "Influence",
        "action_attack": "Attack",
        "action_defense": "Defense",
        "action_recon": "Reconnaissance",
        "action_info": "Spread Information",
        "action_support": "Support",
        "action_cancel": "Cancel",

        # Actions used in interactions
        "select_resources": "Select Gotovina to use for {action_type} action in {district_name}:",
        "insufficient_resources": "You don't have enough {resource_type} Gotovina. Action cancelled.",
        "action_submitted": "Your {action_type} action in {target_name} has been submitted using {resources}. Results will be processed at the end of the cycle.",
        "info_spreading": "Your information has been spread through the news network. It will appear in the next news cycle.",
        "enter_info_content": "What information do you want to spread? Please type your message:",
        "invalid_info_content": "Please provide valid information content.",
        "action_error": "Something went wrong. Please try again.",
        "info_from_user": "Information from {user}",
        "error_district_selection": "Error showing district selection. Please try again.",
        "error_resource_selection": "Error showing resource selection. Please try again.",
        "error_district_info": "Error retrieving district information.",
        "error_politician_info": "Error retrieving politician information.",

        # Status indicators for results
        "status_success": "✅",
        "status_partial": "⚠️",
        "status_failure": "❌",
        "status_info": "ℹ️",

        # Admin commands
        "admin_only": "This command is for administrators only.",
        "admin_news_usage": "Usage: /admin_add_news [title] [content]",
        "admin_news_added": "News added with ID: {news_id}",
        "admin_cycle_processed": "Game cycle processed.",
        "admin_resources_usage": "Usage: /admin_add_resources [player_id] [resource_type] [amount]",
        "admin_invalid_args": "Invalid arguments.",
        "admin_invalid_resource": "Invalid resource type.",
        "admin_player_not_found": "Player {player_id} not found.",
        "admin_resources_added": "Added {amount} {resource_type} to player {player_id}. New total: {new_amount}",
        "admin_control_usage": "Usage: /admin_set_control [player_id] [district_id] [control_points]",
        "admin_district_not_found": "District {district_id} not found.",
        "admin_control_updated": "Updated control for player {player_id} in district {district_id} to {control_points} points.",
        "admin_help_title": "Admin Commands",
        "admin_reset_desc": "Reset a player's available actions",
        "admin_reset_all_desc": "Reset all players' available actions",
        "admin_help_desc": "Show this admin help message",
        "admin_news_desc": "Add a news item",
        "admin_cycle_desc": "Manually process a game cycle",
        "admin_resources_desc": "Add resources to a player",
        "admin_control_desc": "Set district control",
        "admin_ideology_desc": "Set player ideology score (-5 to +5)",
        "admin_list_desc": "List all registered players",
        "admin_error": "Admin error: {error}",
        "admin_player_resources_not_found": "Player {player_id} exists but has no resources record.",
        "admin_reset_actions_usage": "Usage: /admin_reset_actions [player_id]",
        "admin_reset_actions_success": "Actions reset for player {player_id}.",
        "admin_reset_all_actions_success": "Actions reset for {count} players.",
        "admin_set_ideology_usage": "Usage: /admin_set_ideology [player_id] [ideology_score]",
        "admin_set_ideology_success": "Ideology score for player {player_id} set to {score}.",
        "admin_set_ideology_invalid": "Ideology score must be between -5 and +5.",
        "admin_list_players_none": "No players registered.",
        "admin_list_players_title": "Registered Players",
        "admin_control_update_failed": "Failed to update district control.",

        # Notifications
        "actions_refreshed_notification": "Your actions have been refreshed! You now have 1 main action and 2 quick actions available.",

        # District report translations
        "district_report_title": "District Status Report",
        "controlled_by": "Controlled by",
        "contested_by": "Contested by",
        "not_controlled": "Not controlled",
        "players": "players",
        "high_importance": "High importance",
        "medium_importance": "Medium importance",
        "low_importance": "Low importance",
        "error_generating_report": "Error generating report",

        # Politician action translations
        "politician_influence_title": "Politician Influence Report",
        "high_influence": "High influence",
        "medium_influence": "Medium influence",
        "low_influence": "Low influence",

        # Politician action button labels
        "action_pol_info": "Gather Information",
        "action_pol_info_desc": "Learn more about this politician",
        "action_pol_influence": "Influence",
        "action_pol_influence_desc": "Try to improve your relationship",
        "action_pol_collaborate": "Collaborate",
        "action_pol_collaborate_desc": "Work together on a political initiative",
        "action_pol_request": "Request Gotovina",
        "action_pol_request_desc": "Ask for political support and Gotovina",
        "action_pol_power": "Use Political Power",
        "action_pol_power_desc": "Use their political influence to pressure others",
        "action_pol_undermine": "Undermine",
        "action_pol_undermine_desc": "Weaken their influence",
        "action_pol_rumors": "Spread Rumors",
        "action_pol_rumors_desc": "Damage their public reputation",
        "action_pol_scandal": "Create Scandal",
        "action_pol_scandal_desc": "Expose them in a major political scandal",
        "action_pol_diplomatic": "Diplomatic Channel",
        "action_pol_diplomatic_desc": "Establish a diplomatic connection",
        "action_pol_pressure": "International Pressure",
        "action_pol_pressure_desc": "Use international pressure against your opponents",

        # Special event translations
        "event_govt_reshuffle": "Government Reshuffle",
        "event_demonstration": "Mass Demonstration",
        "event_investment": "Foreign Investment",
        "event_sanctions": "Economic Sanctions",
        "event_police_raid": "Police Raid",
        "event_smuggling": "Smuggling Operation",
        "event_diplomatic": "Diplomatic Reception",
        "event_military": "Military Exercise",
        "event_strike": "Worker Strike",
        "event_student": "Student Protest",
        "event_festival": "Cultural Festival",

        # Enhanced error messages
        "db_connection_error": "Database connection error. Please try again later.",
        "invalid_district_error": "Invalid district. Please select a valid district.",
        "invalid_politician_error": "Invalid politician. Please select a valid politician.",
        "insufficient_resources_detailed": "Insufficient resources. You need {required} {resource_type}, but you only have {available}.",
        "invalid_action_error": "Invalid action. Please select a valid action type.",
        "language_detection_error": "Could not detect your language. Defaulting to English.",
        "error_message": "Sorry, something went wrong. The error has been reported.",

        # Joint actions
        "joint_action_title": "Joint Action in {district}",
        "joint_action_description": "Coordinated {action_type} action performed with {count} participants. Power multiplier: {multiplier}x",
        "joint_action_power_increase": "Action power increased by {percent}% due to joint action",

        # Action types for joint actions
        "action_type_influence": "influence",
        "action_type_attack": "attack",
        "action_type_defense": "defense",

        # Cycle summary
        "cycle_summary_title": "Cycle Summary {start}:00-{end}:00",
        "cycle_summary_actions": "🎯 Main Actions:",
        "cycle_summary_action_count": "- {action} in {target}: {count} times",
        "cycle_summary_control": "🏛 Significant Control Changes:",
        "cycle_summary_control_change": "- District {district}: {points:+d} points",

        # Action results
        "action_result_critical": "🌟 Critical success! ({roll}/{chance}) {action} action in {target} completed with excellent results!",
        "action_result_success": "✅ Success! ({roll}/{chance}) {action} action in {target} completed successfully.",
        "action_result_partial": "⚠️ Partial success. ({roll}/{chance}) {action} action in {target} partially completed.",
        "action_result_failure": "❌ Failure. ({roll}/{chance}) {action} action in {target} failed.",

        # Action success details
        "success_control_bonus": "District control bonus: +{bonus}%",
        "success_power_bonus": "Joint action bonus: +{bonus}%",

        # Action power effects
        "effect_primary_boost": "🎯 Enhanced action",
        "effect_precision": "🔍 Precise action",
        "effect_coordinated": "🤝 Coordinated action",
        "effect_tactical": "📋 Tactical action",
        "effect_reveal": "👁 Reveals information",
        "effect_sustain": "⏳ Extended effect",

        # Resource combinations
        "combo_double_primary": "+5 to action power for using two primary resources",
        "combo_influence_info": "+3 to action power for influence and information combination",
        "combo_force_influence": "+3 to action power for force and influence combination",
        "combo_force_info": "+3 to action power for force and information combination",

        # Trade notifications
        "trade_completed_title": "🤝 Trade Completed",
        "trade_completed_sender": "Your trade offer has been accepted by player {receiver_id}",
        "trade_completed_receiver": "You've accepted a trade offer from player {sender_id}",
        "trade_offer_usage": "Usage: /trade <player_id> offer <resource> <amount> request <resource> <amount>",
        "trade_offer_invalid_format": "❌ Invalid command format",
        "trade_offer_received": "📦 New trade offer from player {sender_id}\nOffering: {offered}\nRequesting: {requested}\n\nOffer ID: {offer_id}\nTo accept use: /accept_trade {offer_id}",
        "trade_offer_sent": "✅ Trade offer sent to player {receiver_id}",
        "trade_offer_sent_no_notify": "✅ Trade offer created, but couldn't notify recipient",
        "trade_offer_failed": "❌ Failed to create trade offer",
        "invalid_player_id": "❌ Invalid player ID",
        "error_creating_trade": "❌ Error creating trade offer",
        "accept_trade_usage": "Usage: /accept_trade [offer_id]",
        "trade_accepted": "✅ You've accepted the trade offer. Trade completed!",
        "trade_accepted_notification": "✅ Player {player_id} accepted your trade offer #{offer_id}. Trade completed!",
        "trade_accept_failed": "❌ Failed to accept trade offer. The offer may be invalid or you lack required resources.",
        "invalid_offer_id": "❌ Invalid offer ID. Please provide a correct number.",
        "error_accepting_trade": "❌ Error occurred while accepting trade offer.",
        "get_trade_offer_sender": "Cannot get sender ID for trade offer.",

        # Politician abilities
        "ability_administrative_desc": "Blocks one opponent action in their district",
        "ability_student_protest_desc": "Organizes student protest (+15 to attack in selected district)",
        "ability_shadow_conversion_desc": "Converts 2 of any resource into 3 Force units",
        "ability_diplomatic_immunity_desc": "Protects from one hostile action during the day",
        "ability_media_pressure_desc": "Reduces opponent's action effectiveness in district by 50%",

        "ability_not_available": "Ability not available (requires {required}% relationship level)",
        "ability_on_cooldown": "Ability on cooldown ({hours} hours left)",
        "ability_success": "Ability {name} successfully used",

        # Quick action types
        "action_type_scout": "reconnaissance",
        "action_type_info": "information gathering",
        "action_type_support": "support",

        # Quick action results
        "quick_action_success": "✅ Success! ({roll}/{chance}) Quick action {action} in {target} completed.",
        "quick_action_failure": "❌ Failure. ({roll}/{chance}) Quick action {action} in {target} failed.",

        # Resource distribution
        "resource_distribution_title": "📦 Resource Distribution",
        "resource_from_district": "{district}: {amount}/{base} {resource} ({control_points} control points - {control})",
        "resource_distribution_none": "You didn't receive any district resources this cycle. Control more districts to generate additional income.",
        "resource_distribution_base": "You received base resources: +1 influence, +1 resources, +1 information, +1 force",

        # Control types for resources
        "control_absolute": "🌟 Absolute control (120%)",
        "control_strong": "💪 Full control (100%)",
        "control_firm": "✅ Firm control (80%)",
        "control_contested": "⚠️ Partial control (60%)",
        "control_weak": "⚡ Weak control (40%)",

        # New translations
        "district_desc_stari_grad": "Политическое сердце Нови Сада, где расположены правительственные учреждения",
        "politician_abilities_no_args": {
            "en": "Please specify a politician name to view their abilities.",
            "ru": "Укажите имя политика, чтобы просмотреть его способности."
        },
        "politician_no_abilities": {
            "en": "This politician has no special abilities available to you.",
            "ru": "У этого политика нет доступных для вас специальных способностей."
        },
        "error_using_ability": {
            "en": "Error using ability. Please try again later.",
            "ru": "Ошибка при использовании способности. Пожалуйста, попробуйте позже."
        },
    },

    "ru": {
        # Basic commands and responses
        "welcome": "Добро пожаловать в Новисадскую Игру, {user_name}! Эта игра моделирует политическую борьбу в Югославии 1998 года через контроль над районами Нови Сада.\n\nПожалуйста, введите имя вашего персонажа:",
        "name_set": "Добро пожаловать, {character_name}! Теперь вы политический игрок в Нови Саде 1998 года.\n\nИспользуйте /help для просмотра доступных команд и /status для проверки вашей текущей ситуации.",
        "invalid_name": "Пожалуйста, введите корректное имя.",
        "operation_cancelled": "Операция отменена.",
        "not_registered": "Вы не зарегистрированы. Используйте /start, чтобы начать игру.",

        # Help and documentation
        "help_title": "Руководство по командам Новисадской Игры",
        "help_basic": "*Основные команды:*\n• /start - Начать игру и зарегистрировать персонажа\n• /help - Показать список команд\n• /status - Проверить ресурсы и контроль районов\n• /map - Просмотреть текущую карту контроля\n• /time - Показать текущий игровой цикл и время до следующего\n• /news - Показать последние новости\n• /language - Изменить язык интерфейса",
        "help_action": "*Команды действий:*\n• /action - Подать основную заявку (влияние, атака, защита)\n• /quick_action - Подать быструю заявку (разведка, информация, поддержка)\n• /cancel_action - Отменить последнюю заявку\n• /actions_left - Проверить оставшиеся заявки\n• /view_district [район] - Просмотр информации о районе",
        "help_resource": "*Команды Gotovina:*\n• /resources - Просмотр имеющихся Gotovina\n• /convert_resource [тип] [количество] - Конвертация Gotovina\n• /check_income - Проверка ожидаемого прихода Gotovina",
        "help_political": "*Политические команды:*\n• /politicians - Список доступных политиков\n• /politician_status [имя] - Информация о конкретном политике\n• /international - Информация о международных политиках",
        "help_footer": "Для подробных правил игры обратитесь к игровому документу.",
        "admin_commands": "Команды администратора",
        "admin_help_hint": "Используйте /admin_help для просмотра всех команд администратора.",

        # Status information
        "status_title": "Статус персонажа {character_name}",
        "status_ideology": "Идеология: {ideology} ({score})",
        "status_resources": "*Gotovina:*\n🔵 Влияние: {influence}\n💰 Gotovina: {resources}\n🔍 Информация: {information}\n👊 Сила: {force}",
        "status_actions": "*Оставшиеся действия:*\nОсновные заявки: {main}\nБыстрые заявки: {quick}",
        "status_districts": "*Контролируемые районы:*",
        "status_no_districts": "*Контролируемые районы:* Отсутствуют",
        "unnamed": "Без имени",
        "no_username": "Без имени пользователя",
        "id": "ID",
        "name": "Имя",
        "username": "Имя пользователя",
        "ideology": "Идеология",
        "resources": "Gotovina",
        "influence": "Влияние",
        "information": "Информация",
        "force": "Сила",
        "points": "очков",

        # Map and districts
        "map_title": "Текущая карта контроля Нови Сада",
        "map_legend": "Обозначения:",
        "map_strong_control": "🔒 Сильный контроль (80+ очков)",
        "map_controlled": "✅ Контролируется (60-79 очков)",
        "map_contested": "⚠️ Оспаривается (20-59 очков)",
        "map_weak": "❌ Слабое присутствие (<20 очков)",
        "map_no_control": "Контроль не установлен",
        "map_too_large": "Карта генерируется. Проверьте веб-интерфейс для подробностей.",
        "error_generating_map": "Ошибка при создании карты.",
        "district_not_found": "Район '{district_name}' не найден. Используйте /view_district без аргументов для просмотра списка.",
        "select_district": "Выберите район для просмотра:",
        "current_control": "Текущий контроль",

        # Time information
        "time_info": "*Информация об игровом времени*",
        "time_current": "Текущий цикл: *{cycle}*",
        "time_deadlines": "Время до окончания подачи заявок: *{deadline}*\nВремя до результатов: *{results}*",
        "time_schedule": "*Ежедневное расписание:*\nУтренний цикл: 6:00 - 12:00 (подача заявок), 13:00 (результаты)\nВечерний цикл: 13:01 - 18:00 (подача заявок), 19:00 (результаты)",
        "time_refresh": "Напоминание: Действия обновляются каждые 3 часа!",
        "deadline_passed": "Срок подачи истёк",
        "hours": "ч",
        "minutes": "мин",

        # News
        "news_title": "Последние новости",
        "no_news": "На данный момент новостей нет.",

        # Actions
        "no_main_actions": "У вас не осталось основных заявок. Заявки обновляются каждые 3 часа или в начале нового цикла.",
        "no_quick_actions": "У вас не осталось быстрых заявок. Заявки обновляются каждые 3 часа или в начале нового цикла.",
        "select_action_type": "Выберите тип основной заявки, которую хотите выполнить:",
        "select_quick_action": "Выберите тип быстрой заявки, которую хотите выполнить:",
        "action_cancelled": "Ваша последняя заявка отменена, Gotovina возвращены.",
        "no_pending_actions": "У вас нет ожидающих заявок для отмены.",
        "actions_refreshed": "Ваши заявки обновлены!\n\nОсновные заявки: {main}\nБыстрые заявки: {quick}",
        "current_actions": "Текущие оставшиеся заявки:\n\nОсновные заявки: {main}\nБыстрые заявки: {quick}",

        # Resource management
        "resources_title": "Ваши текущие Gotovina",
        "resources_guide": "*Руководство по использованию Gotovina:*\n• *Влияние* - Используется для политических манёвров, получения дополнительных заявок\n• *Gotovina* - Экономика, финансы, связи. Можно конвертировать в другие Gotovina\n• *Информация* - Разведданные, слухи. Используется для разведки\n• *Сила* - Военные, полиция, криминальные структуры. Эффективны для атак и защиты",
        "convert_usage": "Использование: /convert_resource [тип] [количество]\nПример: /convert_resource influence 2\n\nЭто конвертирует 2 'Gotovina' в 1 указанного типа.",
        "amount_not_number": "Количество должно быть числом.",
        "amount_not_positive": "Количество должно быть положительным.",
        "invalid_resource_type": "Недопустимый тип Gotovina. Допустимые типы: {valid_types}",
        "not_enough_resources": "У вас недостаточно Gotovina. Нужно {needed}, у вас есть {available}.",
        "conversion_success": "Конвертировано {resources_used} Gotovina в {amount} {resource_type}.",
        "no_districts_controlled": "Вы пока не контролируете ни одного района, поэтому не будете получать Gotovina.\n\nКонтролируйте районы (60+ очков контроля) для получения Gotovina каждый цикл.",
        "income_controlled_districts": "*Контролируемые районы:*",
        "income_total": "*Всего за цикл:*\n🔵 Влияние: +{influence}\n💰 Gotovina: +{resources}\n🔍 Информация: +{information}\n👊 Сила: +{force}",
        "income_note": "*Примечание:* Gotovina распределяются в конце каждого цикла.",
        "income_no_full_control": "У вас есть районы с некоторым присутствием, но ни один не контролируется полностью.\n\nДля получения Gotovina из района нужно 60+ очков контроля.",

        # Politicians
        "politicians_title": "Ключевые политики Нови Сада",
        "no_politicians": "В базе данных не найдено политиков.",
        "select_politician": "Выберите политика для просмотра:",
        "politician_not_found": "Политик '{name}' не найден. Используйте /politician_status без аргументов для просмотра списка.",
        "international_title": "Международные политики",
        "no_international": "В базе данных не найдены международные политики.",
        "international_note": "*Примечание:* Международные политики могут активироваться случайным образом в каждом цикле. Их действия могут существенно повлиять на политический ландшафт Нови Сада. Используйте /news для получения актуальной информации об их деятельности.",
        "relationship": "Отношения",
        "compatibility": "Совместимость",
        "role": "Роль",
        "district": "Район",
        "key_relationships": "Ключевые отношения",

        # Ideology descriptions
        "ideology_strongly_conservative": "Крайне консервативный",
        "ideology_conservative": "Консервативный",
        "ideology_neutral": "Нейтральный",
        "ideology_reformist": "Реформистский",
        "ideology_strongly_reformist": "Крайне реформистский",

        # Relationship descriptions
        "compatibility_good": "Хорошая идеологическая совместимость",
        "compatibility_moderate": "Умеренные идеологические различия",
        "compatibility_poor": "Существенные идеологические различия",

        # Actions on politicians
        "politician_influence_no_resources": "Вам нужно минимум 2 единицы Влияния для воздействия на политика. Действие отменено.",
        "politician_influence_no_action": "Вам нужна основная заявка для воздействия на политика. Действие отменено.",
        "politician_influence_success": "Вы использовали своё влияние на {name}. Ваши отношения с ним могут улучшиться. Результаты будут обработаны в конце цикла.",
        "politician_info_no_resources": "Вам нужна минимум 1 единица Информации для сбора данных о политике. Действие отменено.",
        "politician_info_no_action": "Вам нужна быстрая заявка для сбора данных о политике. Действие отменено.",
        "politician_info_title": "Разведывательный отчёт: {name}",
        "politician_undermine_no_resources": "Вам нужно минимум 2 единицы Информации для подрыва влияния политика. Действие отменено.",
        "politician_undermine_no_action": "Вам нужна основная заявка для подрыва влияния политика. Действие отменено.",
        "politician_undermine_success": "Вы начали подрывать влияние {name}. Это может ослабить его позиции в его районе. Результаты будут обработаны в конце цикла.",
        "politician_not_found": "Политик не найден.",
        "politician_info_success": "Вы собрали ценную информацию о {name}.",
        "politician_collaborate_success": "Вы успешно сотрудничали с {name} по политической инициативе.",
        "politician_request_success": "Вы получили Gotovina от {name}.",
        "politician_power_success": "Вы использовали политическое влияние {name} для давления на оппонентов.",
        "politician_rumors_success": "Вы распространили слухи о {name}, нанеся урон их репутации.",
        "politician_scandal_success": "Вы разоблачили {name} в политическом скандале, серьезно подорвав их позицию.",
        "politician_diplomatic_success": "Вы установили дипломатический канал с {name}.",
        "politician_pressure_success": "Вы использовали международное давление {name} против ваших оппонентов.",

        # Cycle results
        "cycle_results_title": "📊 *Результаты {cycle} цикла*",
        "your_actions": "*Ваши действия:*",
        "no_details": "Нет доступных деталей",
        "your_districts": "*Ваши районы:*",
        "recent_news": "*Недавние новости:*",
        "current_resources": "*Текущие Gotovina:*",

        # Control status
        "control_strong": "🔒 Сильный контроль",
        "control_full": "✅ Контролируется",
        "control_contested": "⚠️ Оспаривается",
        "control_weak": "❌ Слабое присутствие",
        "control_points": "очков",

        # Language settings
        "language_current": "Ваш текущий язык: {language}",
        "language_select": "Пожалуйста, выберите предпочитаемый язык:",
        "language_changed": "Язык изменён на русский",
        "language_button_en": "English",
        "language_button_ru": "Русский",

        # Action types
        "action_influence": "Влияние",
        "action_attack": "Атака",
        "action_defense": "Защита",
        "action_recon": "Разведка",
        "action_info": "Распространение информации",
        "action_support": "Поддержка",
        "action_cancel": "Отмена",

        # Resources used in actions
        "select_resources": "Выберите Gotovina для {action_type} действия в районе {district_name}:",
        "insufficient_resources": "У вас недостаточно Gotovina типа {resource_type}. Действие отменено.",
        "action_submitted": "Ваше действие {action_type} в {target_name} было подано с использованием {resources}. Результаты будут обработаны в конце цикла.",
        "info_spreading": "Ваша информация распространена через новостную сеть. Она появится в следующем новостном цикле.",
        "enter_info_content": "Какую информацию вы хотите распространить? Пожалуйста, напишите сообщение:",
        "invalid_info_content": "Пожалуйста, предоставьте корректное содержание информации.",
        "action_error": "Что-то пошло не так. Пожалуйста, попробуйте снова.",
        "info_from_user": "Информация от {user}",
        "error_district_selection": "Ошибка при показе списка районов. Пожалуйста, попробуйте снова.",
        "error_resource_selection": "Ошибка при показе выбора Gotovina. Пожалуйста, попробуйте снова.",
        "error_district_info": "Ошибка при получении информации о районе.",
        "error_politician_info": "Ошибка при получении информации о политике.",

        # Status indicators for results
        "status_success": "✅",
        "status_partial": "⚠️",
        "status_failure": "❌",
        "status_info": "ℹ️",

        # Admin commands
        "admin_only": "Эта команда только для администраторов.",
        "admin_news_usage": "Использование: /admin_add_news [заголовок] [содержание]",
        "admin_news_added": "Новость добавлена с ID: {news_id}",
        "admin_cycle_processed": "Игровой цикл обработан.",
        "admin_resources_usage": "Использование: /admin_add_resources [ID игрока] [тип Gotovina] [количество]",
        "admin_invalid_args": "Недопустимые аргументы.",
        "admin_invalid_resource": "Недопустимый тип Gotovina.",
        "admin_player_not_found": "Игрок {player_id} не найден.",
        "admin_resources_added": "Добавлено {amount} {resource_type} игроку {player_id}. Новый итог: {new_amount}",
        "admin_control_usage": "Использование: /admin_set_control [ID игрока] [ID района] [очки контроля]",
        "admin_district_not_found": "Район {district_id} не найден.",
        "admin_control_updated": "Обновлён контроль для игрока {player_id} в районе {district_id} до {control_points} очков.",
        "admin_help_title": "Команды администратора",
        "admin_reset_desc": "Сбросить доступные действия игрока",
        "admin_reset_all_desc": "Сбросить доступные действия всех игроков",
        "admin_help_desc": "Показать это сообщение помощи администратора",
        "admin_news_desc": "Добавить новость",
        "admin_cycle_desc": "Вручную обработать игровой цикл",
        "admin_resources_desc": "Добавить Gotovina игроку",
        "admin_control_desc": "Установить контроль над районом",
        "admin_ideology_desc": "Установить идеологический показатель игрока (-5 до +5)",
        "admin_list_desc": "Список всех зарегистрированных игроков",
        "admin_error": "Ошибка администратора: {error}",
        "admin_player_resources_not_found": "Игрок {player_id} существует, но не имеет записи Gotovina.",
        "admin_reset_actions_usage": "Использование: /admin_reset_actions [ID игрока]",
        "admin_reset_actions_success": "Действия сброшены для игрока {player_id}.",
        "admin_reset_all_actions_success": "Действия сброшены для {count} игроков.",
        "admin_set_ideology_usage": "Использование: /admin_set_ideology [ID игрока] [оценка идеологии]",
        "admin_set_ideology_success": "Оценка идеологии для игрока {player_id} установлена на {score}.",
        "admin_set_ideology_invalid": "Оценка идеологии должна быть от -5 до +5.",
        "admin_list_players_none": "Нет зарегистрированных игроков.",
        "admin_list_players_title": "Зарегистрированные игроки",
        "admin_control_update_failed": "Не удалось обновить контроль района.",

        # Notifications
        "actions_refreshed_notification": "Ваши заявки обновлены! Теперь у вас есть 1 основная заявка и 2 быстрые заявки.",

        # District report translations
        "district_report_title": "Отчет о состоянии районов",
        "controlled_by": "Контролируется",
        "contested_by": "Оспаривается",
        "not_controlled": "Не контролируется",
        "players": "игроками",
        "high_importance": "Высокая важность",
        "medium_importance": "Средняя важность",
        "low_importance": "Низкая важность",
        "error_generating_report": "Ошибка при создании отчета",

        # Politician action translations
        "politician_influence_title": "Отчет о влиянии политиков",
        "high_influence": "Высокое влияние",
        "medium_influence": "Среднее влияние",
        "low_influence": "Низкое влияние",

        # Politician action button labels
        "action_pol_info": "Собрать информацию",
        "action_pol_info_desc": "Узнать больше об этом политике",
        "action_pol_influence": "Влияние",
        "action_pol_influence_desc": "Попытаться улучшить ваши отношения",
        "action_pol_collaborate": "Сотрудничество",
        "action_pol_collaborate_desc": "Работать вместе над политической инициативой",
        "action_pol_request": "Запросить Gotovina",
        "action_pol_request_desc": "Попросить политическую поддержку и Gotovina",
        "action_pol_power": "Использовать влияние",
        "action_pol_power_desc": "Использовать их политическое влияние для давления на оппонентов",
        "action_pol_undermine": "Подорвать влияние",
        "action_pol_undermine_desc": "Ослабить их влияние",
        "action_pol_rumors": "Распространить слухи",
        "action_pol_rumors_desc": "Нанести урон их репутации",
        "action_pol_scandal": "Создать скандал",
        "action_pol_scandal_desc": "Разоблачить их в крупном политическом скандале",
        "action_pol_diplomatic": "Дипломатический канал",
        "action_pol_diplomatic_desc": "Установить дипломатическую связь",
        "action_pol_pressure": "Международное давление",
        "action_pol_pressure_desc": "Использовать международное давление против ваших оппонентов",

        # Special event translations
        "event_govt_reshuffle": "Перестановки в правительстве",
        "event_demonstration": "Массовая демонстрация",
        "event_investment": "Иностранные инвестиции",
        "event_sanctions": "Экономические санкции",
        "event_police_raid": "Полицейский рейд",
        "event_smuggling": "Контрабандная операция",
        "event_diplomatic": "Дипломатический прием",
        "event_military": "Военные учения",
        "event_strike": "Забастовка рабочих",
        "event_student": "Студенческий протест",
        "event_festival": "Культурный фестиваль",

        # Enhanced error messages
        "db_connection_error": "Ошибка подключения к базе данных. Пожалуйста, попробуйте позже.",
        "invalid_district_error": "Недействительный район. Пожалуйста, выберите правильный район.",
        "invalid_politician_error": "Недействительный политик. Пожалуйста, выберите правильного политика.",
        "insufficient_resources_detailed": "Недостаточно Gotovina. Вам нужно {required} {resource_type}, но у вас есть только {available}.",
        "invalid_action_error": "Недействительное действие. Пожалуйста, выберите правильный тип действия.",
        "language_detection_error": "Не удалось определить ваш язык. Используется английский по умолчанию.",
        "error_message": "Извините, что-то пошло не так. Об ошибке сообщено.",

        # Joint actions
        "joint_action_title": "Совместное действие в {district}",
        "joint_action_description": "Выполнено координированное действие {action_type} с {count} участниками. Множитель силы: {multiplier}x",
        "joint_action_power_increase": "Сила действия увеличена на {percent}% благодаря совместному действию",

        # Action types for joint actions
        "action_type_influence": "влияние",
        "action_type_attack": "атака",
        "action_type_defense": "оборона",

        # Cycle summary
        "cycle_summary_title": "Итоги цикла {start}:00-{end}:00",
        "cycle_summary_actions": "🎯 Основные действия:",
        "cycle_summary_action_count": "- {action} in {target}: {count} раз",
        "cycle_summary_control": "🏛 Значимые изменения контроля:",
        "cycle_summary_control_change": "- Район {district}: {points:+d} очков",

        # Action results
        "action_result_critical": "🌟 Критический успех! ({roll}/{chance}) Действие {action} в {target} выполнено с превосходным результатом!",
        "action_result_success": "✅ Успех! ({roll}/{chance}) Действие {action} в {target} выполнено успешно.",
        "action_result_partial": "⚠️ Частичный успех. ({roll}/{chance}) Действие {action} в {target} выполнено частично.",
        "action_result_failure": "❌ Провал. ({roll}/{chance}) Действие {action} в {target} не удалось выполнить.",

        # Action success details
        "success_control_bonus": "Бонус от контроля района: +{bonus}%",
        "success_power_bonus": "Бонус от совместного действия: +{bonus}%",

        # Action power effects
        "effect_primary_boost": "🎯 Усиленное действие",
        "effect_precision": "🔍 Точное действие",
        "effect_coordinated": "🤝 Координированное действие",
        "effect_tactical": "📋 Тактическое действие",
        "effect_reveal": "👁 Раскрывает информацию",
        "effect_sustain": "⏳ Продлённый эффект",

        # Resource combinations
        "combo_double_primary": "+5 к силе действия за использование двух основных Gotovina",
        "combo_influence_info": "+3 к силе действия за комбинацию влияния и информации",
        "combo_force_influence": "+3 к силе действия за комбинацию силы и влияния",
        "combo_force_info": "+3 к силе действия за комбинацию силы и информации",

        # Trade notifications
        "trade_completed_title": "🤝 Обмен выполнен",
        "trade_completed_sender": "Ваше предложение обмена принято игроком {receiver_id}",
        "trade_completed_receiver": "Вы приняли предложение обмена от игрока {sender_id}",
        "trade_offer_usage": "Использование: /trade <id игрока> offer <Gotovina> <количество> request <Gotovina> <количество>",
        "trade_offer_invalid_format": "❌ Неверный формат команды",
        "trade_offer_received": "📦 Новое предложение обмена от игрока {sender_id}\nПредлагает: {offered}\nЗапрашивает: {requested}\n\nID предложения: {offer_id}\nДля принятия используйте: /accept_trade {offer_id}",
        "trade_offer_sent": "✅ Предложение обмена отправлено игроку {receiver_id}",
        "trade_offer_sent_no_notify": "✅ Предложение обмена создано, но не удалось уведомить получателя",
        "trade_offer_failed": "❌ Не удалось создать предложение обмена",
        "invalid_player_id": "❌ Неверный ID игрока",
        "error_creating_trade": "❌ Ошибка при создании предложения обмена",
        "accept_trade_usage": "Использование: /accept_trade [ID предложения]",
        "trade_accepted": "✅ Вы приняли предложение обмена. Обмен завершен!",
        "trade_accepted_notification": "✅ Игрок {player_id} принял ваше предложение обмена #{offer_id}. Обмен завершен!",
        "trade_accept_failed": "❌ Не удалось принять предложение обмена. Предложение может быть недействительным, или у вас недостаточно Gotovina.",
        "invalid_offer_id": "❌ Неверный ID предложения. Пожалуйста, укажите корректный номер.",
        "error_accepting_trade": "❌ Произошла ошибка при принятии предложения обмена.",
        "get_trade_offer_sender": "Не удалось получить ID отправителя предложения.",

        # Politician abilities
        "ability_administrative_desc": "Блокирует одну заявку противника в своём районе",
        "ability_student_protest_desc": "Организует студенческий протест (+15 к атаке в выбранном районе)",
        "ability_shadow_conversion_desc": "Конвертирует 2 любых Gotovina в 3 единицы Силы",
        "ability_diplomatic_immunity_desc": "Защищает от одной враждебной акции в течение дня",
        "ability_media_pressure_desc": "Снижает эффективность действий противника в районе на 50%",

        "ability_not_available": "Способность недоступна (требуется уровень отношений {required}%)",
        "ability_on_cooldown": "Способность на перезарядке (осталось {hours} ч)",
        "ability_success": "Способность {name} успешно использована",

        # Quick action types
        "action_type_scout": "разведка",
        "action_type_info": "сбор информации",
        "action_type_support": "поддержка",

        # Quick action results
        "quick_action_success": "✅ Успех! ({roll}/{chance}) Быстрое действие {action} в {target} выполнено.",
        "quick_action_failure": "❌ Провал. ({roll}/{chance}) Быстрое действие {action} в {target} не удалось.",

        # Resource distribution
        "resource_distribution_title": "📦 Получение Gotovina",
        "resource_from_district": "{district}: {amount}/{base} {resource} ({control_points} очков контроля - {control})",
        "resource_distribution_none": "You didn't receive any district resources this cycle. Control more districts to generate additional income.",
        "resource_distribution_base": "You received base resources: +1 influence, +1 resources, +1 information, +1 force",

        # Control types for resources
        "control_absolute": "🌟 Абсолютный контроль (120%)",
        "control_strong": "💪 Полный контроль (100%)",
        "control_firm": "✅ Уверенный контроль (80%)",
        "control_contested": "⚠️ Частичный контроль (60%)",
        "control_weak": "⚡ Слабый контроль (40%)",

        # New translations
        "district_desc_stari_grad": "Политическое сердце Нови Сада, где расположены правительственные учреждения",
    }
}

# Cycle names translation
CYCLE_NAMES = {
    "en": {
        "morning": "Morning",
        "evening": "Evening"
    },
    "ru": {
        "morning": "Утренний",
        "evening": "Вечерний"
    }
}

# Resource names translation
RESOURCE_NAMES = {
    "en": {
        "influence": "Influence",
        "resources": "Resources",
        "information": "Information",
        "force": "Force"
    },
    "ru": {
        "influence": "Влияние",
        "resources": "Ресурсы",
        "information": "Информация",
        "force": "Сила"
    }
}

# Action names translation
ACTION_NAMES = {
    "en": {
        "influence": "Influence",
        "attack": "Attack",
        "defense": "Defense",
        "recon": "Reconnaissance",
        "info": "Information Spreading",
        "support": "Support"
    },
    "ru": {
        "influence": "Влияние",
        "attack": "Атака",
        "defense": "Защита",
        "recon": "Разведка",
        "info": "Распространение информации",
        "support": "Поддержка"
    }
}


# Make sure any other missing translations are properly handled
def get_text(key, lang="en", default=None, **kwargs):
    """
    Get text in the specified language with optional formatting

    Parameters:
    key (str): The translation key
    lang (str): Language code (en/ru)
    default (str): Default text if translation is missing
    **kwargs: Variables to format the text with

    Returns:
    str: Translated and formatted text
    """
    # Default to English if the language is not supported
    if lang not in TRANSLATIONS:
        lang = "en"

    # Get the text for the key
    text = TRANSLATIONS[lang].get(key)

    # If not found in the requested language, try English as fallback
    if text is None:
        text = TRANSLATIONS["en"].get(key)
        # Log missing translation
        logging.warning(f"Missing translation for key '{key}' in language '{lang}'")

    # If still not found, use the provided default or return an error message
    if text is None:
        if default is not None:
            text = default
        else:
            return f"[Missing translation: {key}]"

    # Format the text with the provided variables
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError as e:
            # Log formatting error
            logging.error(f"Translation format error: {e} in '{text}' for key '{key}'")
            return f"[Format error in translation: {key}]"

    return text


def get_cycle_name(cycle, lang="en"):
    """Get the translated name of a cycle"""
    if lang not in CYCLE_NAMES:
        lang = "en"

    return CYCLE_NAMES[lang].get(cycle, cycle)


def get_resource_name(resource, lang="en"):
    """Get the translated name of a resource"""
    if lang not in RESOURCE_NAMES:
        lang = "en"

    return RESOURCE_NAMES[lang].get(resource, resource)


def get_action_name(action_type, lang="en"):
    """Get the translated name of an action type"""
    if lang not in ACTION_NAMES:
        lang = "en"

    return ACTION_NAMES[lang].get(action_type, action_type)


# Player language retrieval function for main.py
def get_player_language(player_id):
    """Get player's preferred language"""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        cursor.execute("SELECT language FROM players WHERE player_id = ?", (player_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return result[0]
        else:
            return "en"  # Default to English
    except Exception as e:
        logging.error(f"Error retrieving player language: {e}")
        return "en"  # Default to English on error


def set_player_language(player_id, language):
    """Set player's preferred language"""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE players SET language = ? WHERE player_id = ?",
            (language, player_id)
        )

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error setting player language: {e}")
        return False


def format_ideology(ideology_score, lang="en"):
    """Get formatted ideology description based on score"""
    if ideology_score > 3:
        return get_text("ideology_strongly_conservative", lang)
    elif ideology_score > 0:
        return get_text("ideology_conservative", lang)
    elif ideology_score == 0:
        return get_text("ideology_neutral", lang)
    elif ideology_score > -3:
        return get_text("ideology_reformist", lang)
    else:
        return get_text("ideology_strongly_reformist", lang)


def check_missing_translations():
    """Check for missing translations and log warnings."""
    logging.info("Checking for missing translations...")
    missing_count = 0

    # Get all keys in English
    english_keys = set(TRANSLATIONS["en"].keys())

    # Check each language
    for lang in TRANSLATIONS:
        if lang == "en":
            continue

        lang_keys = set(TRANSLATIONS[lang].keys())
        missing_keys = english_keys - lang_keys

        if missing_keys:
            missing_count += len(missing_keys)
            logging.warning(f"Found {len(missing_keys)} missing translations in {lang}:")
            for key in missing_keys:
                TRANSLATIONS[lang][key] = TRANSLATIONS["en"][key]  # Use English as fallback
                logging.warning(f"  - '{key}' (using English fallback)")

    logging.info(f"Translation check complete. Fixed {missing_count} missing translations.")


def init_language_support():
    """Initialize language support by updating and checking translations"""
    # Import language updates
    from languages_update import update_translations, init_admin_language_support

    # Apply updates
    update_translations()
    init_admin_language_support()

    # Check for missing translations
    check_missing_translations()

    logger.info("Language support initialized")

    return True