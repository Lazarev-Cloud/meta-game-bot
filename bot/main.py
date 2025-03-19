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