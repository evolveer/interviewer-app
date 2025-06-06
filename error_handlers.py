"""
error_handlers.py - functions for handling API errors, displaying user-friendly messages, and managing rate limits.

Author: Kyra Cole
Date: 2025-02-05
"""

import time
import streamlit as st
from typing import Any, Callable, Dict, Optional

def safe_api_call(func: Callable, app_logger, *args, **kwargs) -> Any:
    """
    Wrapper for API calls with enhanced error handling.
    
    Features:
    - Automatic retries with exponential backoff
    - Error type differentiation
    - User-friendly error messages
    
    Args:
        func (callable): The API function to call
        app_logger: Instance of AppLogger for logging errors
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        any: Result of the function call or error dictionary
    """
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Log the error
            app_logger.log_error(e, {
                "function": func.__name__ if hasattr(func, "__name__") else "unknown_function",
                "attempt": attempt + 1,
                "max_retries": max_retries
            })
            
            # Handle specific error types
            if "RateLimitError" in error_type:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                return {"error": "Rate limit exceeded. Please try again later."}
            
            elif "AuthenticationError" in error_type:
                return {"error": "API authentication failed. Please check your API key."}
            
            elif "Timeout" in error_type:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return {"error": "Request timed out. Please try again."}
            
            else:
                return {"error": f"An error occurred: {error_msg}"}
    
    return {"error": "Maximum retry attempts reached."}

def display_error(error_message: str, level: str = "error", app_logger = None) -> None:
    """
    Display error messages to users in a consistent format.
    
    Args:
        error_message (str): The error message to display
        level (str): Error level ("error", "warning", or "info")
        app_logger: Optional AppLogger instance for logging
    """
    if level == "error":
        st.error(f"😕 {error_message}")
    elif level == "warning":
        st.warning(f"⚠️ {error_message}")
    else:
        st.info(f"ℹ️ {error_message}")
    
    # Log displayed errors
    if app_logger:
        app_logger.log_error(error_message, {"displayed_to_user": True, "level": level})
    
    # For serious errors, provide recovery options
    if level == "error":
        if st.button("Restart Session"):
            st.session_state.clear()
            st.experimental_rerun()

def check_rate_limits_before_api_call(app_logger):
    """
    Check rate limits before making an API call.
    
    Args:
        app_logger: AppLogger instance for checking rate limits
        
    Returns:
        bool: True if rate limited, False otherwise
    """
    rate_status = app_logger.check_rate_limits(window_minutes=1)
    
    if rate_status.get("status") == "warning":
        st.warning(f"⚠️ {rate_status.get('message')}. API calls may be throttled.")
        time.sleep(2)  # Add a small delay to help spread out requests
        return True
    
    return False

def update_token_usage(usage):
    """
    Update token usage statistics in session state.
    
    Args:
        usage: Token usage object from OpenAI API response
    """
    if "token_usage" not in st.session_state:
        st.session_state.token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0
        }
    
    # Update counts
    st.session_state.token_usage["prompt_tokens"] += usage.prompt_tokens
    st.session_state.token_usage["completion_tokens"] += usage.completion_tokens
    st.session_state.token_usage["total_tokens"] += usage.total_tokens
    
    # Calculate estimated cost (using approximate pricing)
    # GPT-4o pricing: $0.01 per 1K prompt tokens, $0.03 per 1K completion tokens
    prompt_cost = usage.prompt_tokens * 0.01 / 1000
    completion_cost = usage.completion_tokens * 0.03 / 1000
    st.session_state.token_usage["estimated_cost"] += prompt_cost + completion_cost

