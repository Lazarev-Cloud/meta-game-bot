import logging

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from config import TOKEN
from db.schema import setup_database
from bot.commands import register_commands
from game.actions import schedule_jobs
from languages import get_text, get_player_language, set_player_language
# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Start the bot."""
    # Set up the database
    setup_database()

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Register command handlers
    register_commands(application)

    # Register callback handlers
    register_callbacks(application)

    # Set up scheduled jobs
    application.job_queue.run_once(schedule_jobs, 1)

    # Start the Bot
    logger.info("Bot starting up...")
    application.run_polling()
    logger.info("Bot stopped")

# Callback query handler for inline keyboard buttons
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks from inline keyboards."""
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    user = query.from_user

    # Handle language selection
    if callback_data.startswith("lang:"):
        language = callback_data.split(":")[1]
        set_player_language(user.id, language)

        # Confirm language change in the selected language
        response_text = get_text("language_changed", language)
        await query.edit_message_text(response_text)
        return

    # Get player's language preference for all other callbacks
    lang = get_player_language(user.id)

    # Handle action type selection
    if callback_data.startswith("action_type:"):
        action_type = callback_data.split(":")[1]
        context.user_data['action_type'] = action_type

        # Now show districts to select as target
        await show_district_selection(query, get_text("select_district", lang))

    # Handle quick action type selection
    elif callback_data.startswith("quick_action_type:"):
        action_type = callback_data.split(":")[1]
        context.user_data['quick_action_type'] = action_type

        # Different targets based on quick action type
        if action_type in [QUICK_ACTION_RECON, QUICK_ACTION_SUPPORT]:
            await show_district_selection(query, get_text("select_district", lang))
        elif action_type == QUICK_ACTION_INFO:
            await query.edit_message_text(
                get_text("enter_info_content", lang,
                         default="What information do you want to spread? Please type your message:")
            )
            return "WAITING_INFO_CONTENT"

    # Handle district selection for main actions
    elif callback_data.startswith("district_select:"):
        district_id = callback_data.split(":")[1]

        if 'action_type' in context.user_data:
            # For main action
            action_type = context.user_data['action_type']
            await show_resource_selection(query, action_type, district_id)
        elif 'quick_action_type' in context.user_data:
            # For quick action
            action_type = context.user_data['quick_action_type']
            await process_quick_action(query, action_type, "district", district_id)

    # Direct action buttons from district view
    elif callback_data.startswith(("action_influence:", "action_attack:", "action_defend:")):
        parts = callback_data.split(":")
        action_type = parts[0].replace("action_", "")
        district_id = parts[1]

        context.user_data['action_type'] = action_type
        await show_resource_selection(query, action_type, district_id)

    elif callback_data.startswith(("quick_recon:", "quick_support:")):
        parts = callback_data.split(":")
        action_type = parts[0].replace("quick_", "")
        district_id = parts[1]

        context.user_data['quick_action_type'] = action_type
        await process_quick_action(query, action_type, "district", district_id)

    # Handle resource selection
    elif callback_data.startswith("resources:"):
        parts = callback_data.split(":")
        action_type = parts[1]
        target_type = parts[2]
        target_id = parts[3]
        resources = parts[4].split(",")

        await process_main_action(query, action_type, target_type, target_id, resources)

    # Handle view district
    elif callback_data.startswith("view_district:"):
        district_id = callback_data.split(":")[1]
        await show_district_info(query, district_id)

    # Handle view politician
    elif callback_data.startswith("view_politician:"):
        politician_id = int(callback_data.split(":")[1])
        await show_politician_info(query, politician_id)

    # Handle politician actions
    elif callback_data.startswith("pol_influence:"):
        politician_id = int(callback_data.split(":")[1])
        await process_politician_influence(query, politician_id)

    elif callback_data.startswith("pol_info:"):
        politician_id = int(callback_data.split(":")[1])
        await process_politician_info(query, politician_id)

    elif callback_data.startswith("pol_undermine:"):
        politician_id = int(callback_data.split(":")[1])
        await process_politician_undermine(query, politician_id)

    # Handle cancellation
    elif callback_data == "action_cancel":
        await query.edit_message_text("Action cancelled.")

    else:
        await query.edit_message_text(f"Unrecognized callback: {callback_data}")


def register_callbacks(application):
    """Register callback handlers."""
    # Add callback query handler for inline keyboards
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Callback handlers registered")


if __name__ == "__main__":
    main()