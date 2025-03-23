#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Menu navigation helpers for the Meta Game bot.
"""

import logging
from typing import Dict, Any, Callable, Awaitable, Optional, Union

from telegram import Update, Message, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.keyboards import get_start_keyboard
from utils.i18n import _, get_user_language

# Initialize logger
logger = logging.getLogger(__name__)

class MenuManager:
    """Manager for hierarchical menu navigation."""
    
    def __init__(self):
        """Initialize the menu manager."""
        # Menu structure: {menu_name: {menu_data}}
        self.menus = {}
        
        # History for each user: {telegram_id: [menu_history]}
        self.menu_history = {}
    
    def register_menu(
        self, 
        menu_name: str, 
        title_generator: Callable[[str, str], Awaitable[str]],
        keyboard_generator: Callable[[str, str], Awaitable[InlineKeyboardMarkup]],
        parent_menu: Optional[str] = None
    ) -> None:
        """
        Register a menu in the navigation system.
        
        Args:
            menu_name: Unique identifier for the menu
            title_generator: Async function(telegram_id, language) that returns the menu title
            keyboard_generator: Async function(telegram_id, language) that returns the menu keyboard
            parent_menu: Optional parent menu name for back navigation
        """
        self.menus[menu_name] = {
            'title_generator': title_generator,
            'keyboard_generator': keyboard_generator,
            'parent': parent_menu
        }
    
    def get_user_history(self, telegram_id: str) -> list:
        """
        Get menu history for a user.
        
        Args:
            telegram_id: The user's Telegram ID
            
        Returns:
            List of menu names in the user's history
        """
        if telegram_id not in self.menu_history:
            self.menu_history[telegram_id] = []
        
        return self.menu_history[telegram_id]
    
    def clear_history(self, telegram_id: str) -> None:
        """
        Clear menu history for a user.
        
        Args:
            telegram_id: The user's Telegram ID
        """
        self.menu_history[telegram_id] = []
    
    async def navigate_to(
        self, 
        update: Update, 
        menu_name: str, 
        replace_last: bool = False,
        context_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Navigate to a specific menu.
        
        Args:
            update: The update triggering navigation
            menu_name: The name of the menu to navigate to
            replace_last: If True, replace the last menu in history instead of adding new
            context_data: Optional data to pass to the title/keyboard generators
        """
        # Get user info
        user = update.effective_user
        telegram_id = str(user.id)
        language = await get_user_language(telegram_id)
        
        # Check if menu exists
        if menu_name not in self.menus:
            logger.error(f"Attempted to navigate to non-existent menu: {menu_name}")
            if update.callback_query:
                await update.callback_query.answer(_("Menu not found", language))
            return
        
        # Get menu data
        menu = self.menus[menu_name]
        
        # Generate title and keyboard
        try:
            title = await menu['title_generator'](telegram_id, language, context_data)
            keyboard = await menu['keyboard_generator'](telegram_id, language, context_data)
            
            # Update navigation history
            history = self.get_user_history(telegram_id)
            if replace_last and history:
                history[-1] = menu_name
            else:
                history.append(menu_name)
                
            # Update the message
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    title,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                await update.callback_query.answer()
            else:
                await update.message.reply_text(
                    title,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
        except Exception as e:
            logger.error(f"Error navigating to menu {menu_name}: {e}")
            if update.callback_query:
                await update.callback_query.answer(_("Error loading menu", language))
    
    async def go_back(self, update: Update) -> None:
        """
        Navigate back to the previous menu.
        
        Args:
            update: The update triggering back navigation
        """
        # Get user info
        user = update.effective_user
        telegram_id = str(user.id)
        language = await get_user_language(telegram_id)
        
        # Get history
        history = self.get_user_history(telegram_id)
        
        # Check if we have history to go back to
        if len(history) <= 1:
            # Go to main menu
            await self.navigate_to(update, "main_menu", True)
            return
        
        # Remove current menu and get previous
        history.pop()
        previous_menu = history[-1]
        
        # Navigate to previous menu, replacing the current history entry
        await self.navigate_to(update, previous_menu, True)
    
    async def to_main_menu(self, update: Update) -> None:
        """
        Navigate back to the main menu, clearing history.
        
        Args:
            update: The update triggering navigation to main menu
        """
        # Get user info
        user = update.effective_user
        telegram_id = str(user.id)
        
        # Clear history
        self.clear_history(telegram_id)
        
        # Navigate to main menu
        await self.navigate_to(update, "main_menu")

# Create a global menu manager instance
menu_manager = MenuManager()

# Register basic menus
async def main_menu_title(telegram_id: str, language: str, context_data: Optional[Dict[str, Any]] = None) -> str:
    """Generate main menu title."""
    return _("Main Menu - Novi-Sad Political Game", language)

async def main_menu_keyboard(telegram_id: str, language: str, context_data: Optional[Dict[str, Any]] = None) -> InlineKeyboardMarkup:
    """Generate main menu keyboard."""
    return get_start_keyboard(language)

# Initialize menus
def setup_menus():
    """Set up the menu navigation system."""
    # Register main menu
    menu_manager.register_menu(
        "main_menu",
        main_menu_title,
        main_menu_keyboard
    )
    
    # More menus will be registered by other modules
