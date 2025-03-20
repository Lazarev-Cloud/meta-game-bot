def setup_jobs(application):
    job_queue = application.job_queue
    
    # Schedule game cycle processing every 3 hours
    job_queue.run_repeating(
        process_game_cycle, 
        interval=datetime.timedelta(hours=3),
        first=get_next_cycle_time()
    )
    
def get_next_cycle_time():
    """Calculate the next 3-hour cycle start time"""
    now = datetime.datetime.now()
    current_hour = now.hour
    next_cycle = (current_hour // 3 + 1) * 3
    next_time = now.replace(hour=next_cycle, minute=0, second=0, microsecond=0)
    
    if next_time < now:
        next_time += datetime.timedelta(days=1)
        
    return next_time 

def main():
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("register", register_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("resources", resources_command))
    application.add_handler(CommandHandler("districts", districts_command))
    application.add_handler(CommandHandler("view_district", view_district_command))
    application.add_handler(CommandHandler("action", action_command))
    application.add_handler(CommandHandler("quick_action", quick_action_command))
    application.add_handler(CommandHandler("trade", trade_command))
    application.add_handler(CommandHandler("accept_trade", accept_trade_command))
    application.add_handler(CommandHandler("cancel_trade", cancel_trade_command))
    application.add_handler(CommandHandler("map", map_command))
    application.add_handler(CommandHandler("set_location", set_location_command))
    application.add_handler(CommandHandler("location", get_location_command))

    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(button)) 