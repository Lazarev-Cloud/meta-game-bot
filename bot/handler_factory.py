from telegram.ext import CommandHandler

def get_resource_command_handler():
    from bot.commands import resource_conversion_command
    return CommandHandler("convert_resource", resource_conversion_command)