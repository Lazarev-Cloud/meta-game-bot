#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Text formatting utilities for the Belgrade Game bot.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import re
import html

from utils.i18n import _

# Initialize logger
logger = logging.getLogger(__name__)

async def format_player_status(player_data: Dict[str, Any], language: str) -> str:
    """Format player status information for display."""
    try:
        player_name = player_data.get("player_name", "Unknown")
        ideology_score = player_data.get("ideology_score", 0)
        
        # Format ideology label
        ideology_text = _("Strong Reformist", language) if ideology_score <= -5 else \
                        _("Moderate Reformist", language) if ideology_score <= -3 else \
                        _("Slight Reformist", language) if ideology_score < 0 else \
                        _("Neutral", language) if ideology_score == 0 else \
                        _("Slight Conservative", language) if ideology_score <= 2 else \
                        _("Moderate Conservative", language) if ideology_score <= 4 else \
                        _("Strong Conservative", language)
        
        # Format resources
        resources = player_data.get("resources", {})
        influence = resources.get("influence", 0)
        money = resources.get("money", 0)
        information = resources.get("information", 0)
        force = resources.get("force", 0)
        
        # Get actions remaining
        actions_remaining = player_data.get("actions_remaining", 0)
        quick_actions_remaining = player_data.get("quick_actions_remaining", 0)
        
        # Count controlled districts
        controlled_districts = player_data.get("controlled_districts", [])
        district_count = len(controlled_districts)
        
        # Build status message
        status_text = _(
            "*Player Status: {name}*\n\n"
            "🔵 *Ideology:* {ideology_score} ({ideology_text})\n\n"
            "*Resources:*\n"
            "🔹 Influence: {influence}\n"
            "🔹 Money: {money}\n"
            "🔹 Information: {information}\n"
            "🔹 Force: {force}\n\n"
            "*Actions Remaining:*\n"
            "🔹 Main Actions: {actions}\n"
            "🔹 Quick Actions: {quick_actions}\n\n"
            "*Districts Controlled:* {district_count}",
            language
        ).format(
            name=player_name,
            ideology_score=ideology_score,
            ideology_text=ideology_text,
            influence=influence,
            money=money,
            information=information,
            force=force,
            actions=actions_remaining,
            quick_actions=quick_actions_remaining,
            district_count=district_count
        )
        
        return status_text
    except Exception as e:
        logger.error(f"Error formatting player status: {str(e)}")
        return _("Error formatting player status", language)

async def format_district_info(district_data: Dict[str, Any], language: str) -> str:
    """Format district information for display."""
    try:
        name = district_data.get("name", "Unknown")
        description = district_data.get("description", "")
        
        # Format resources
        resources = district_data.get("resources", {})
        influence = resources.get("influence", 0)
        money = resources.get("money", 0)
        information = resources.get("information", 0)
        force = resources.get("force", 0)
        
        # Format control information
        player_control = district_data.get("player_control", 0)
        controlling_player = district_data.get("controlling_player")
        
        control_status = ""
        if controlling_player:
            control_status = _("Controlled by: {player}", language).format(player=controlling_player)
        else:
            control_status = _("No clear control", language)
        
        # Format detailed control info if available
        control_info = ""
        if district_data.get("detailed_info", False):
            control = district_data.get("control", [])
            
            if control:
                control_info = _("\n\n*Control Points:*\n", language)
                for entry in control:
                    player_name = entry.get("player_name", "Unknown")
                    control_points = entry.get("control_points", 0)
                    last_active = entry.get("last_active", False)
                    
                    control_info += f"🔹 {player_name}: {control_points} CP"
                    if not last_active:
                        control_info += f" ({_('inactive', language)})"
                    control_info += "\n"
        
        # Format politicians in district
        politicians_text = ""
        politicians = district_data.get("politicians", [])
        
        if politicians:
            politicians_text = _("\n\n*Politicians in this district:*\n", language)
            for politician in politicians:
                name = politician.get("name", "Unknown")
                ideological_leaning = politician.get("ideological_leaning", 0)
                influence_in_district = politician.get("influence_in_district", 0)
                friendliness = politician.get("friendliness", 50)
                
                # Determine stance icon
                stance_icon = "🟢" if friendliness >= 70 else "🟡" if friendliness >= 30 else "🔴"
                
                politicians_text += f"{stance_icon} *{name}*: "
                politicians_text += _("Influence: {influence}, Ideology: {ideology}", language).format(
                    influence=influence_in_district,
                    ideology=ideological_leaning
                )
                politicians_text += "\n"
        
        # Build district info message
        district_text = _(
            "*District: {name}*\n\n"
            "{description}\n\n"
            "*Control:* {control_status}\n"
            "Your Control Points: {player_control}{control_info}\n\n"
            "*Resources per cycle:*\n"
            "🔹 Influence: {influence}\n"
            "🔹 Money: {money}\n"
            "🔹 Information: {information}\n"
            "🔹 Force: {force}{politicians_text}",
            language
        ).format(
            name=name,
            description=description,
            control_status=control_status,
            player_control=player_control,
            control_info=control_info,
            influence=influence,
            money=money,
            information=information,
            force=force,
            politicians_text=politicians_text
        )
        
        return district_text
    except Exception as e:
        logger.error(f"Error formatting district info: {str(e)}")
        return _("Error formatting district information", language)

async def format_time(time_interval: str, language: str) -> str:
    """Format time interval for display."""
    try:
        # Parse time string like "01:30:45" to hours, minutes, seconds
        if isinstance(time_interval, str):
            match = re.match(r'^(\d+):(\d+):(\d+)(?:\..*)?$', time_interval)
            if match:
                hours, minutes, seconds = map(int, match.groups())
                
                if hours > 0:
                    return _("{hours}h {minutes}m", language).format(hours=hours, minutes=minutes)
                elif minutes > 0:
                    return _("{minutes}m {seconds}s", language).format(minutes=minutes, seconds=seconds)
                else:
                    return _("{seconds}s", language).format(seconds=seconds)
        
        # If it's not a string or doesn't match the pattern, return as is
        return str(time_interval)
    except Exception as e:
        logger.error(f"Error formatting time: {str(e)}")
        return str(time_interval)

async def format_cycle_info(cycle_info: Dict[str, Any], language: str) -> str:
    """Format game cycle information for display."""
    try:
        cycle_type = cycle_info.get("cycle_type", "Unknown")
        cycle_date = cycle_info.get("cycle_date", "Unknown")
        
        deadline = cycle_info.get("submission_deadline", "Unknown")
        results_time = cycle_info.get("results_time", "Unknown")
        
        time_to_deadline = cycle_info.get("time_to_deadline", "Unknown")
        time_to_results = cycle_info.get("time_to_results", "Unknown")
        
        is_accepting_submissions = cycle_info.get("is_accepting_submissions", False)
        
        # Format status message
        status_text = _(
            "*Current Game Cycle*\n\n"
            "Date: {date}\n"
            "Cycle: {cycle_type}\n\n"
            "Submission Deadline: {deadline}\n"
            "Results Time: {results_time}\n\n"
            "Time until deadline: {time_to_deadline}\n"
            "Time until results: {time_to_results}\n\n"
            "Accepting submissions: {accepting}",
            language
        ).format(
            date=cycle_date,
            cycle_type=cycle_type,
            deadline=deadline,
            results_time=results_time,
            time_to_deadline=await format_time(time_to_deadline, language),
            time_to_results=await format_time(time_to_results, language),
            accepting=_("Yes", language) if is_accepting_submissions else _("No", language)
        )
        
        return status_text
    except Exception as e:
        logger.error(f"Error formatting cycle info: {str(e)}")
        return _("Error formatting cycle information", language)

async def format_news(news_data: Dict[str, Any], language: str) -> str:
    """Format news for display."""
    try:
        public_news = news_data.get("public", [])
        faction_news = news_data.get("faction", [])
        
        news_text = _("*Latest News*\n\n", language)
        
        # Add public news
        if public_news:
            news_text += _("📰 *Public News*\n", language)
            
            for i, news in enumerate(public_news[:3]):  # Show top 3 public news
                title = news.get("title", "")
                content = news.get("content", "")
                cycle_type = news.get("cycle_type", "")
                cycle_date = news.get("cycle_date", "")
                
                news_text += f"*{title}*\n"
                news_text += f"{content}\n"
                news_text += _("({cycle_type} cycle, {date})\n\n", language).format(
                    cycle_type=cycle_type,
                    date=cycle_date
                )
        
        # Add faction news
        if faction_news:
            news_text += _("🔒 *Faction Intel*\n", language)
            
            for i, news in enumerate(faction_news[:3]):  # Show top 3 faction news
                title = news.get("title", "")
                content = news.get("content", "")
                cycle_type = news.get("cycle_type", "")
                cycle_date = news.get("cycle_date", "")
                
                news_text += f"*{title}*\n"
                news_text += f"{content}\n"
                news_text += _("({cycle_type} cycle, {date})\n\n", language).format(
                    cycle_type=cycle_type,
                    date=cycle_date
                )
        
        if not public_news and not faction_news:
            news_text += _("No recent news available.", language)
        
        return news_text
    except Exception as e:
        logger.error(f"Error formatting news: {str(e)}")
        return _("Error formatting news", language)

async def format_income_info(income_data: Dict[str, Any], language: str) -> str:
    """Format income information for display."""
    try:
        district_income = income_data.get("district_income", [])
        totals = income_data.get("totals", {})
        next_cycle = income_data.get("next_cycle", {})
        
        income_text = _(
            "*Expected Resource Income*\n\n"
            "Next cycle: {cycle_type} cycle, {date}\n\n",
            language
        ).format(
            cycle_type=next_cycle.get("type", "Unknown"),
            date=next_cycle.get("date", "Unknown")
        )
        
        # Add district breakdown
        if district_income:
            income_text += _("*District Breakdown:*\n", language)
            
            for district in district_income:
                name = district.get("district", "Unknown")
                control_points = district.get("control_points", 0)
                control_percentage = district.get("control_percentage", "0%")
                income = district.get("income", {})
                
                influence = income.get("influence", 0)
                money = income.get("money", 0)
                information = income.get("information", 0)
                force = income.get("force", 0)
                
                income_text += f"*{name}* ({control_points} CP, {control_percentage})\n"
                
                resources = []
                if influence > 0:
                    resources.append(f"{influence} {_('Influence', language)}")
                if money > 0:
                    resources.append(f"{money} {_('Money', language)}")
                if information > 0:
                    resources.append(f"{information} {_('Information', language)}")
                if force > 0:
                    resources.append(f"{force} {_('Force', language)}")
                
                if resources:
                    income_text += _("Income: ", language) + ", ".join(resources) + "\n\n"
                else:
                    income_text += _("No income from this district\n\n", language)
        
        # Add totals
        influence_total = totals.get("influence", 0)
        money_total = totals.get("money", 0)
        information_total = totals.get("information", 0)
        force_total = totals.get("force", 0)
        
        income_text += _(
            "*Total Expected Income:*\n"
            "🔹 Influence: {influence}\n"
            "🔹 Money: {money}\n"
            "🔹 Information: {information}\n"
            "🔹 Force: {force}",
            language
        ).format(
            influence=influence_total,
            money=money_total,
            information=information_total,
            force=force_total
        )
        
        return income_text
    except Exception as e:
        logger.error(f"Error formatting income info: {str(e)}")
        return _("Error formatting income information", language)

async def format_politicians_list(politicians_data: Dict[str, Any], language: str) -> str:
    """Format list of politicians for display."""
    try:
        politicians = politicians_data.get("politicians", [])
        type_filter = politicians_data.get("type", "all")
        player_ideology = politicians_data.get("player_ideology", 0)
        
        # Title based on type
        title = ""
        if type_filter == "local":
            title = _("*Local Politicians*", language)
        elif type_filter == "international":
            title = _("*International Politicians*", language)
        else:
            title = _("*All Politicians*", language)
        
        politicians_text = f"{title}\n\n"
        
        if not politicians:
            politicians_text += _("No politicians found.", language)
            return politicians_text
        
        # Group by type if showing all
        if type_filter == "all":
            local_politicians = [p for p in politicians if p.get("type") == "local"]
            international_politicians = [p for p in politicians if p.get("type") == "international"]
            
            if local_politicians:
                politicians_text += _("*Local Politicians:*\n", language)
                for politician in local_politicians:
                    politicians_text += await format_single_politician(politician, player_ideology, language)
                politicians_text += "\n"
            
            if international_politicians:
                politicians_text += _("*International Politicians:*\n", language)
                for politician in international_politicians:
                    politicians_text += await format_single_politician(politician, player_ideology, language)
        else:
            # Just show the filtered list
            for politician in politicians:
                politicians_text += await format_single_politician(politician, player_ideology, language)
        
        return politicians_text
    except Exception as e:
        logger.error(f"Error formatting politicians list: {str(e)}")
        return _("Error formatting politicians list", language)

async def format_single_politician(politician: Dict[str, Any], player_ideology: int, language: str) -> str:
    """Format a single politician entry."""
    name = politician.get("name", "Unknown")
    description = politician.get("description", "")
    ideology = politician.get("ideological_leaning", 0)
    friendliness = politician.get("friendliness", 50)
    district = politician.get("district")
    country = politician.get("country")
    
    # Determine stance icon
    stance_icon = "🟢" if friendliness >= 70 else "🟡" if friendliness >= 30 else "🔴"
    
    # Calculate ideology compatibility
    ideology_diff = abs(player_ideology - ideology)
    compatibility = "✓✓" if ideology_diff <= 2 else "✓" if ideology_diff <= 4 else "✗"
    
    result = f"{stance_icon} *{name}* ({compatibility})\n"
    
    if district:
        result += _("District: {district}", language).format(district=district)
    elif country:
        result += _("Country: {country}", language).format(country=country)
    
    result += f", {_('Ideology', language)}: {ideology}\n\n"
    
    return result

async def format_politician_info(politician_data: Dict[str, Any], language: str) -> str:
    """Format detailed politician information for display."""
    try:
        name = politician_data.get("name", "Unknown")
        description = politician_data.get("description", "")
        type_str = politician_data.get("type", "local")
        ideology = politician_data.get("ideological_leaning", 0)
        friendliness = politician_data.get("friendliness", 50)
        friendliness_status = politician_data.get("friendliness_status", "neutral")
        ideology_compatibility = politician_data.get("ideology_compatibility", 0)
        district = politician_data.get("district")
        country = politician_data.get("country")
        influence_in_district = politician_data.get("influence_in_district", 0)
        activity_percentage = politician_data.get("activity_percentage")
        
        # Format active effects for international politicians
        active_effects_text = ""
        if type_str == "international" and "active_effects" in politician_data:
            active_effects = politician_data.get("active_effects", [])
            
            if active_effects:
                active_effects_text = _("\n\n*Active Effects:*\n", language)
                
                for effect in active_effects:
                    effect_type = effect.get("effect_type", "Unknown")
                    description = effect.get("description", "")
                    target_district = effect.get("target_district")
                    
                    active_effects_text += f"- *{effect_type.capitalize()}*"
                    if target_district:
                        active_effects_text += f" ({_('Target', language)}: {target_district})"
                    active_effects_text += f"\n  {description}\n"
        
        # Determine stance description
        stance_description = ""
        if friendliness_status == "loyal":
            stance_description = _("Strong supporter who actively helps you", language)
        elif friendliness_status == "friendly":
            stance_description = _("Favors your position and may provide resources", language)
        elif friendliness_status == "neutral":
            stance_description = _("Neither supports nor opposes you", language)
        elif friendliness_status == "hostile":
            stance_description = _("Actively works against your interests", language)
        
        # Build politician info message
        politician_text = _(
            "*{name}*\n\n"
            "{description}\n\n"
            "*Type:* {type}\n",
            language
        ).format(
            name=name,
            description=description,
            type=_("Local Politician", language) if type_str == "local" else _("International Politician", language)
        )
        
        # Add location info
        if district:
            politician_text += _("*District:* {district}\n", language).format(district=district)
            if influence_in_district is not None:
                politician_text += _("*Influence in District:* {influence}\n", language).format(influence=influence_in_district)
        elif country:
            politician_text += _("*Country:* {country}\n", language).format(country=country)
            if activity_percentage is not None:
                politician_text += _("*Activity Level:* {activity}%\n", language).format(activity=activity_percentage)
        
        # Add ideology and relationship info
        politician_text += _(
            "*Ideological Position:* {ideology}\n"
            "*Compatibility with You:* {compatibility}\n"
            "*Friendliness Level:* {friendliness}/100\n"
            "*Current Stance:* {stance_status} - {stance_description}{active_effects}",
            language
        ).format(
            ideology=ideology,
            compatibility=_("Compatible (+{bonus} CP)", language).format(bonus=ideology_compatibility) if ideology_compatibility > 0 else 
                        _("Incompatible ({penalty} CP)", language).format(penalty=ideology_compatibility) if ideology_compatibility < 0 else
                        _("Neutral", language),
            friendliness=friendliness,
            stance_status=friendliness_status.capitalize(),
            stance_description=stance_description,
            active_effects=active_effects_text
        )
        
        return politician_text
    except Exception as e:
        logger.error(f"Error formatting politician info: {str(e)}")
        return _("Error formatting politician information", language)