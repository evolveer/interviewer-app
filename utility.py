"""
utility.py - Utility functions for the Interview Practice App

This module provides helper functions and utilities that don't fit into other modules.
It includes functions for debugging UI components, admin panel features, and other
miscellaneous utilities.

Author: Kyra Cole
Date: 2025-06-05
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from typing import Dict, List, Any, Optional

def add_debug_ui(app_logger):
    """
    Add debug UI components to the sidebar.
    
    Args:
        app_logger: AppLogger instance for accessing logs and performance stats
    """
    debug_mode = st.sidebar.checkbox("Debug Mode", False, key="debug_mode")
    
    if debug_mode:
        st.sidebar.subheader("Debug Information")
        
        # Show session state
        if st.sidebar.checkbox("Show Session State"):
            # Convert non-serializable items to string for display
            serializable_state = {}
            for k, v in st.session_state.items():
                try:
                    # Check if it can be serialized
                    import json
                    json.dumps({k: v})
                    serializable_state[k] = v
                except (TypeError, OverflowError):
                    serializable_state[k] = str(v)
            st.sidebar.json(serializable_state)
        
        # Show API request/response
        if "last_api_request" in st.session_state and "last_api_response" in st.session_state:
            if st.sidebar.checkbox("Show Last API Call"):
                st.sidebar.subheader("Last API Request")
                st.sidebar.json(st.session_state.last_api_request)
                
                st.sidebar.subheader("Last API Response")
                st.sidebar.json(st.session_state.last_api_response)
        
        # Show token usage
        if "token_usage" in st.session_state:
            st.sidebar.subheader("Token Usage")
            
            # Display token usage metrics
            col1, col2 = st.sidebar.columns(2)
            col1.metric("Prompt Tokens", st.session_state.token_usage["prompt_tokens"])
            col2.metric("Completion Tokens", st.session_state.token_usage["completion_tokens"])
            
            col1, col2 = st.sidebar.columns(2)
            col1.metric("Total Tokens", st.session_state.token_usage["total_tokens"])
            col2.metric("Est. Cost ($)", f"${st.session_state.token_usage['estimated_cost']:.4f}")
        
        return True
    
    return False

def add_admin_panel(app_logger):
    """
    Add admin panel to the sidebar.
    
    Args:
        app_logger: AppLogger instance for accessing logs and performance stats
    """
    if st.sidebar.checkbox("Show Admin Panel", False):
        st.sidebar.header("Admin Panel")
        
        # Error log viewer
        if st.sidebar.button("View Error Logs"):
            try:
                log_dir = "logs"
                error_logs = [f for f in os.listdir(log_dir) if f.startswith("errors_")]
                
                if not error_logs:
                    st.sidebar.info("No error logs found")
                else:
                    selected_log = st.sidebar.selectbox("Select Error Log", error_logs)
                    with open(os.path.join(log_dir, selected_log), "r") as f:
                        log_content = f.readlines()
                    
                    # Display last 50 errors by default
                    num_lines = st.sidebar.slider("Number of errors to display", 10, 100, 50)
                    st.sidebar.text_area("Recent Errors", "".join(log_content[-num_lines:]), height=300)
            except Exception as e:
                st.sidebar.error(f"Error reading logs: {str(e)}")
        
        # Performance stats
        if st.sidebar.checkbox("Show Performance Stats"):
            stats = app_logger.get_performance_stats()
            
            if "error" in stats:
                st.sidebar.error(stats["error"])
            else:
                st.sidebar.subheader("API Performance")
                st.sidebar.metric("Total API Calls", stats["total_calls"])
                st.sidebar.metric("Success Rate", f"{stats['success_rate']:.1f}%")
                
                # Create a bar chart of API calls by function
                if stats["calls_by_function"]:
                    data = pd.DataFrame({
                        "Function": list(stats["calls_by_function"].keys()),
                        "Calls": list(stats["calls_by_function"].values())
                    })
                    
                    fig, ax = plt.subplots()
                    ax.barh(data["Function"], data["Calls"])
                    ax.set_xlabel("Number of Calls")
                    ax.set_title("API Calls by Function")
                    st.sidebar.pyplot(fig)
        
        # API call timeline
        if st.sidebar.checkbox("Show API Call Timeline"):
            timeline_hours = st.sidebar.slider("Hours to Display", 1, 48, 24)
            api_timeline = app_logger.get_api_call_timeline(hours=timeline_hours)
            
            if isinstance(api_timeline, dict) and "error" in api_timeline:
                st.sidebar.error(api_timeline["error"])
            elif not api_timeline:
                st.sidebar.info("No API calls found in the selected time period")
            else:
                # Create a DataFrame for visualization
                df = pd.DataFrame(api_timeline)
                # Convert timestamp objects to strings for display
                df["hour"] = df["timestamp"].apply(lambda x: x.strftime("%Y-%m-%d %H:00"))
                
                # Count calls by hour
                hourly_counts = df.groupby("hour").size().reset_index(name="count")
                
                # Create a line chart
                fig, ax = plt.subplots()
                ax.plot(hourly_counts["hour"], hourly_counts["count"], marker='o')
                ax.set_xlabel("Hour")
                ax.set_ylabel("Number of API Calls")
                ax.set_title("API Calls by Hour")
                plt.xticks(rotation=45)
                plt.tight_layout()
                st.sidebar.pyplot(fig)

def store_api_request_response(request_data, response, debug_mode=False):
    """
    Store API request and response in session state for debugging.
    
    Args:
        request_data (dict): API request data
        response: API response object
        debug_mode (bool): Whether debug mode is enabled
    """
    if debug_mode:
        # Store request
        st.session_state.last_api_request = request_data
        
        # Store response (if it exists and has expected structure)
        if response and hasattr(response, 'choices') and response.choices:
            response_data = {
                "content": response.choices[0].message.content,
                "finish_reason": response.choices[0].finish_reason,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            st.session_state.last_api_response = response_data

