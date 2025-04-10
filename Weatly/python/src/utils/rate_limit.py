import time

def rate_limit(tokens_used, elapsed_seconds, cap_per_minute=50000):
    """
    Sleeps for the necessary time to ensure tokens used do not exceed the cap per minute.
    """
    tokens_per_second = cap_per_minute / 60.0
    required_time = tokens_used / tokens_per_second
    wait_time = max(required_time - elapsed_seconds, 0)
    wait_time = min(wait_time, 60)
    if wait_time > 0:
        print(f"Rate limit: waiting {wait_time:.1f}s")
        time.sleep(wait_time)
    else:
        print("No rate limiting needed.")
