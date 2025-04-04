"""
Bot instance initialization.

Creates and configures the Aiogram Bot instance using the token from application settings.
"""
from aiogram import Bot
from app.config import settings

# Aiogram Bot instance initialized with the provided bot token.
bot = Bot(token=settings.bot_token)
