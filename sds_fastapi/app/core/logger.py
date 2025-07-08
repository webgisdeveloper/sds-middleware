# logging.py

import logging
import time
from fastapi import FastAPI, Request

# 1. Configure the logger
logger = logging.getLogger("api_logger")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("api.log")
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - URL: %(url)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(handler)

# 2. Define the middleware function
async def log_requests(request: Request, call_next):
    """
    Middleware to log incoming requests and outgoing responses.
    """
    # Skip logging for favicon requests
    if request.url.path == '/favicon.ico':
        return await call_next(request)
    
    full_url = str(request.url)
    log_extra = {"url": full_url}

    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = f'{process_time:.2f}'
    
    logger.info(
        f"Request: {request.method} {request.url.path} | "
        f"Response: {response.status_code} | "
        f"Duration: {formatted_process_time}ms",
        extra=log_extra
    )
    
    return response


# 3. Create a function to add the middleware
def add_logging_middleware(app: FastAPI):
    """Adds the logging middleware to the FastAPI app."""
    app.middleware("http")(log_requests)