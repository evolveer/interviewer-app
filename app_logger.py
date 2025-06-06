"""
app_logger.py - Logging system for streamlit openai applications

This module provides a comprehensive logging system for tracking application events,
API calls, user interactions, and errors. It includes functionality for performance
monitoring and rate limit prevention.

Author: Kyra Cole   assisted with AI
Date: 2025-01-05
"""

import logging
import os
import datetime
import json
import time
from functools import wraps

class AppLogger:
    """
    AppLogger class provides structured logging for the Interview Practice App.
    
    Features:
    - Separate log files for general logs and errors
    - Session tracking with unique session IDs
    - Structured JSON log formats
    - API call logging with performance tracking
    - User interaction logging
    - Error logging with context
    - Performance statistics and visualization
    """
    
    def __init__(self, log_dir="logs", log_level=logging.INFO):
        """
        Initialize the logger with specified log directory and level.
        
        Args:
            log_dir (str): Directory to store log files
            log_level (int): Logging level (e.g., logging.INFO, logging.DEBUG)
        """
        self.logger = logging.getLogger("interview_app")
        self.logger.setLevel(log_level)
        
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # File handler for general logs
        log_file = os.path.join(log_dir, f"app_{datetime.datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file)
        
        # File handler for error logs
        error_log_file = os.path.join(log_dir, f"errors_{datetime.datetime.now().strftime('%Y%m%d')}.log")
        error_file_handler = logging.FileHandler(error_log_file)
        error_file_handler.setLevel(logging.ERROR)
        
        # Create formatters and add to handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        error_file_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_file_handler)
        
        # Session ID for tracking user sessions
        self.session_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + str(hash(time.time()))[-4:]
    
    def log_api_call(self, func_name, params=None, response=None, error=None):
        """
        Log API calls with parameters and responses.
        
        Args:
            func_name (str): Name of the API function
            params (dict, optional): Parameters passed to the API (excluding sensitive info)
            response (any, optional): Response from the API
            error (Exception, optional): Error if the API call failed
        """
        log_data = {
            "session_id": self.session_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "function": func_name,
            "parameters": params,
            "success": error is None,
        }
        
        if error:
            log_data["error"] = str(error)
            self.logger.error(f"API Error: {json.dumps(log_data)}")
        else:
            # Don't log full response to avoid excessive logs
            log_data["response_summary"] = str(response)[:100] + "..." if response and len(str(response)) > 100 else response
            self.logger.info(f"API Call: {json.dumps(log_data)}")
    
    def log_user_interaction(self, action, data=None):
        """
        Log user interactions with the app.
        
        Args:
            action (str): Type of user interaction (e.g., "start_practice", "submit_answer")
            data (dict, optional): Additional data about the interaction
        """
        log_data = {
            "session_id": self.session_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "action": action,
            "data": data
        }
        self.logger.info(f"User Interaction: {json.dumps(log_data)}")
    
    def log_error(self, error, context=None):
        """
        Log application errors with context.
        
        Args:
            error (Exception or str): The error that occurred
            context (dict, optional): Additional context about the error
        """
        log_data = {
            "session_id": self.session_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "error": str(error),
            "context": context
        }
        self.logger.error(f"Application Error: {json.dumps(log_data)}")
    
    def get_performance_stats(self):
        """
        Get performance statistics from logs.
        
        Returns:
            dict: Performance statistics including total calls, calls by function, and success rate
        """
        try:
            log_dir = "logs"
            app_logs = [f for f in os.listdir(log_dir) if f.startswith("app_")]
            
            if not app_logs:
                return {"error": "No logs found"}
            
            # Get most recent log
            latest_log = max(app_logs)
            api_calls = []
            
            with open(os.path.join(log_dir, latest_log), "r") as f:
                for line in f:
                    if "API Call:" in line:
                        try:
                            # Extract JSON part
                            json_str = line.split("API Call: ")[1]
                            api_data = json.loads(json_str)
                            api_calls.append(api_data)
                        except:
                            pass
            
            # Calculate statistics
            if not api_calls:
                return {"error": "No API calls found in logs"}
            
            stats = {
                "total_calls": len(api_calls),
                "calls_by_function": {},
                "success_rate": sum(1 for call in api_calls if call.get("success", True)) / len(api_calls) * 100
            }
            
            for call in api_calls:
                func = call.get("function", "unknown")
                if func not in stats["calls_by_function"]:
                    stats["calls_by_function"][func] = 0
                stats["calls_by_function"][func] += 1
            
            return stats
        except Exception as e:
            return {"error": f"Error getting performance stats: {str(e)}"}
    
    def get_api_call_timeline(self, hours=24):
        """
        Get timeline of API calls for the last N hours.
        
        Args:
            hours (int): Number of hours to look back
            
        Returns:
            list: Timeline of API calls with timestamps and function names
        """
        try:
            log_dir = "logs"
            app_logs = [f for f in os.listdir(log_dir) if f.startswith("app_")]
            
            if not app_logs:
                return {"error": "No logs found"}
            
            # Get logs from the last N hours
            now = datetime.datetime.now()
            start_time = now - datetime.timedelta(hours=hours)
            
            api_calls = []
            
            for log_file in app_logs:
                with open(os.path.join(log_dir, log_file), "r") as f:
                    for line in f:
                        if "API Call:" in line:
                            try:
                                # Extract JSON part
                                json_str = line.split("API Call: ")[1]
                                api_data = json.loads(json_str)
                                
                                # Parse timestamp
                                timestamp = datetime.datetime.fromisoformat(api_data.get("timestamp", ""))
                                
                                if timestamp >= start_time:
                                    api_calls.append({
                                        "timestamp": timestamp,
                                        "function": api_data.get("function", "unknown"),
                                        "success": api_data.get("success", True)
                                    })
                            except:
                                pass
            
            # Sort by timestamp
            api_calls.sort(key=lambda x: x["timestamp"])
            
            return api_calls
        except Exception as e:
            return {"error": f"Error getting API call timeline: {str(e)}"}
    
    def check_rate_limits(self, window_minutes=1):
        """
        Check if we're approaching rate limits based on recent API calls.
        
        Args:
            window_minutes (int): Time window in minutes to check
            
        Returns:
            dict: Status information including call count and warnings if approaching limits
        """
        try:
            log_dir = "logs"
            app_logs = [f for f in os.listdir(log_dir) if f.startswith("app_")]
            
            if not app_logs:
                return {"status": "ok", "calls": 0, "window_minutes": window_minutes}
            
            # Get logs from the last N minutes
            now = datetime.datetime.now()
            start_time = now - datetime.timedelta(minutes=window_minutes)
            
            recent_calls = 0
            
            for log_file in sorted(app_logs, reverse=True):  # Start with most recent
                with open(os.path.join(log_dir, log_file), "r") as f:
                    for line in f:
                        if "API Call:" in line:
                            try:
                                # Extract JSON part
                                json_str = line.split("API Call: ")[1]
                                api_data = json.loads(json_str)
                                
                                # Parse timestamp
                                timestamp = datetime.datetime.fromisoformat(api_data.get("timestamp", ""))
                                
                                if timestamp >= start_time:
                                    recent_calls += 1
                            except:
                                pass
            
            # Check against rate limits
            # OpenAI has different rate limits, but let's use a conservative threshold
            # For GPT-4, it might be around 200 RPM (requests per minute) for most users
            warning_threshold = 150  # 75% of assumed limit
            
            if recent_calls > warning_threshold:
                return {
                    "status": "warning",
                    "calls": recent_calls,
                    "window_minutes": window_minutes,
                    "message": f"High API usage detected: {recent_calls} calls in the last {window_minutes} minute(s)"
                }
            
            return {"status": "ok", "calls": recent_calls, "window_minutes": window_minutes}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Decorator for logging API calls
def log_api(logger):
    """
    Decorator for logging API calls.
    
    Args:
        logger (AppLogger): Instance of AppLogger to use for logging
        
    Returns:
        function: Decorated function that logs API calls
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Log parameters (excluding API keys)
                safe_params = {k: v for k, v in kwargs.items() if 'key' not in k.lower()}
                
                # Call the function
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log success
                logger.log_api_call(
                    func.__name__, 
                    params=safe_params,
                    response=result
                )
                
                # Log execution time if it's slow
                if execution_time > 1.0:  # Log if execution takes more than 1 second
                    logger.logger.warning(f"Slow API call: {func.__name__} took {execution_time:.2f} seconds")
                
                return result
            except Exception as e:
                # Log error
                logger.log_api_call(
                    func.__name__,
                    params=safe_params if 'safe_params' in locals() else None,
                    error=e
                )
                raise
        return wrapper
    return decorator

