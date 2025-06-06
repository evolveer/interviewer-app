"""
Interview Practice App with Enhanced Debugging and Validation

A Streamlit app that simulates an AI interview coach for practice interviews.
This app allows users to practice answering interview questions with an AI-generated interviewer.

Features:
- OpenAI API integration for generating interview questions and evaluations
- Comprehensive logging system for tracking application events and API calls
- Robust validation for user inputs and API responses
- Enhanced error handling with retry logic and user-friendly error messages
- Debug mode for monitoring application state and API interactions
- Performance monitoring for API calls and token usage

Author: Kyra Cole added some improvments from AI
Date: 2025-06-05
Version: 2.0

This code is licensed under the MIT License.
"""

import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import pandas as pd
import re
import time
import json



# Import custom modules for debugging and validation
from app_logger import AppLogger, log_api
from validators import InputValidator, APIResponseValidator, ConfigValidator, SessionStateValidator
from error_handlers import safe_api_call, display_error, update_token_usage
from utility import add_debug_ui, add_admin_panel, store_api_request_response

# Initialize logger
app_logger = AppLogger()
app_logger.logger.info("Application started")


# Initialize validators
input_validator = InputValidator()
api_validator = APIResponseValidator()
config_validator = ConfigValidator()
session_validator = SessionStateValidator()

# Load API key - important security measure
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Streamlit UI ---
st.set_page_config(page_title="Interview Practice App", layout="centered")

st.title("AI Interview Practice")
st.write("Practice answering interview questions with an AI-generated interviewer.")

# Validate configuration at startup
config_validation = config_validator.validate_app_config()
if not config_validation["is_valid"]:
    for error in config_validation["errors"]:
        display_error(error, "error", app_logger)
    st.stop()

# Add debug UI components if enabled
debug_mode = add_debug_ui(app_logger)
if debug_mode:
    add_admin_panel(app_logger)

# Sidebar for parameters
st.sidebar.header("Settings")
temperature = st.sidebar.slider("Creativity (temperature)", 0.0, 1.0, 0.3)
frequency_penalty = st.sidebar.slider("Frequency Penalty", 0.0, 2.0, 1.0)
presence_penalty = st.sidebar.slider("Presence Penalty", 0.0, 2.0, 1.0)
top_p = st.sidebar.slider("Top P", 0.0, 1.0, 0.1)
difficulty = st.sidebar.selectbox("Difficulty Level", ["Easy", "Medium", "Hard"])
wordcount = st.sidebar.slider("Max Ideal Answer Word Count (words)", 50, 200, 100)

# Validate user settings
user_settings = {
    "difficulty": difficulty,
    "temperature": temperature,
    "frequency_penalty": frequency_penalty,
    "presence_penalty": presence_penalty,
    "top_p": top_p,
    "wordcount": wordcount
}

settings_validation = config_validator.validate_user_settings(user_settings)
if settings_validation["warnings"]:
    with st.sidebar.expander("Settings Warnings"):
        for warning in settings_validation["warnings"]:
            st.warning(warning)

# Use corrected settings
corrected_settings = settings_validation["corrected_settings"]
temperature = corrected_settings["temperature"]
frequency_penalty = corrected_settings["frequency_penalty"]
presence_penalty = corrected_settings["presence_penalty"]
top_p = corrected_settings["top_p"]

# --- Session state for conversation ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize token usage tracking
if "token_usage" not in st.session_state:
    st.session_state.token_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "estimated_cost": 0.0
    }

# System prompt
def get_system_prompt(role, difficulty_level):
    """
    Generate the system prompt for the interview coach.
    
    Args:
        role (str): The job role for the interview
        difficulty_level (str): The difficulty level of the interview
        
    Returns:
        str: The system prompt
    """
    return f"""
You are a professional interview coach simulating a {difficulty_level.lower()} interview for the role of {role}         
Ask concise, focused questions that are easy to understand and answer.
Limit each question to a maximum of 2 sentences or 30 words.    
Ask one question at a time. Use formal but simple language.
Focus on both technical and behavioral aspects appropriate to the role.
"""

# --- OpenAI API call ---
@log_api(app_logger)
def get_ai_response(messages):
    """
    Get a response from the OpenAI API.
    
    Args:
        messages (list): List of message dictionaries
        
    Returns:
        str: The AI response
    """
    # Check rate limits before making API call
    from error_handlers import check_rate_limits_before_api_call
    rate_limited = check_rate_limits_before_api_call(app_logger)
    if rate_limited:
        time.sleep(1)  # Add a small delay if approaching rate limits
    
    try:
        # Prepare request data
        request_data = {
            "model": "gpt-4o",
            "temperature": temperature,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "top_p": top_p,
            "max_tokens": 100,
            "messages": messages
        }
        
        # Store request for debugging if debug mode is enabled
        if st.session_state.get("debug_mode", False):
            st.session_state.last_api_request = request_data
        
        # Make API call with safe wrapper
        response = safe_api_call(
            lambda: client.chat.completions.create(**request_data),
            app_logger
        )
        
        # Handle error response
        if isinstance(response, dict) and "error" in response:
            display_error(response["error"], "error", app_logger)
            return "I apologize, but I encountered an issue. Please try again."
        
        # Update token usage
        update_token_usage(response.usage)
        
        # Store response for debugging if debug mode is enabled
        store_api_request_response(request_data, response, st.session_state.get("debug_mode", False))
        
        
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        app_logger.log_error(e, {"function": "get_ai_response"})
        return f"Error: {str(e)}"

@log_api(app_logger)
def evaluate_answer(question, answer):
    """
    Evaluate the user's answer to an interview question.
    
    Args:
        question (str): The interview question
        answer (str): The user's answer
        
    Returns:
        tuple: (scores, feedback) - Dictionary of scores and feedback string
    """
    eval_prompt = f"""
You are a professional interview coach. Evaluate the following answer.

Question: {question}
Answer: {answer}
penalize for verbosity, and focus on concise, clear responses.

Give ratings (1–5) for:
- Relevance
- Clarity
- Technical Accuracy
- Depth
- Communication

Then give concise feedback (1–2 sentences).
Respond in this format:
Relevance: X
Clarity: X
Technical Accuracy: X
Depth: X
Communication: X
please don't judge grammar or spelling mistakes.
Feedback: <text>
"""
    try:
        # Prepare request data
        request_data = {
            "model": "gpt-4o",
            "temperature": temperature,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "top_p": top_p,
            "max_tokens": 100,
            "messages": [{"role": "user", "content": eval_prompt}]
        }
        
        # Store request for debugging if debug mode is enabled
        if st.session_state.get("debug_mode", False):
            st.session_state.last_api_request = request_data
        
        # Make API call with safe wrapper
        response = safe_api_call(
            lambda: client.chat.completions.create(**request_data),
            app_logger
        )
        
        # Handle error response
        if isinstance(response, dict) and "error" in response:
            display_error(response["error"], "error", app_logger)
            return {}, "I apologize, but I encountered an issue evaluating your answer."
        
        # Update token usage
        update_token_usage(response.usage)
        
        # Store response for debugging if debug mode is enabled
        store_api_request_response(request_data, response, st.session_state.get("debug_mode", False))
        
        # Validate response
        validation_result = api_validator.validate_openai_response(response, "evaluation")
        
        if not validation_result["is_valid"]:
            for error in validation_result["errors"]:
                app_logger.log_error(error, {"response_validation": "failed"})
            
            # Extract scores manually as fallback
            content = response.choices[0].message.content
            scores = {}
            for key in ["Relevance", "Clarity", "Technical Accuracy", "Depth", "Communication"]:
                match = re.search(rf"{key}: (\d)", content)
                scores[key] = int(match.group(1)) if match else 0
            
            feedback_match = re.search(r"Feedback:\s*(.+)", content, re.DOTALL)
            feedback = feedback_match.group(1).strip() if feedback_match else "No feedback available."
            
            return scores, feedback
        
        # Use validated and structured response
        cleaned_response = validation_result["cleaned_response"]
        return cleaned_response["scores"], cleaned_response["feedback"]
    except Exception as e:
        app_logger.log_error(e, {"function": "evaluate_answer"})
        return {}, f"Evaluation error: {str(e)}"

def display_score_chart(scores: dict):
    """
    Display a bar chart of evaluation scores.
    
    Args:
        scores (dict): Dictionary of scores
    """
    df = pd.DataFrame(list(scores.items()), columns=["Metric", "Score"])
    fig, ax = plt.subplots()
    ax.barh(df["Metric"], df["Score"], align='center')
    ax.set_xlim(0, 5)
    ax.set_xlabel("Score (1–5)")
    ax.set_title("Answer Evaluation")
    st.pyplot(fig)

@log_api(app_logger)
def generate_ideal_answer(question, role):
    """
    Generate an ideal answer to an interview question.
    
    Args:
        question (str): The interview question
        role (str): The job role
        
    Returns:
        str: The ideal answer
    """
    prompt = f"""
You are an expert interview coach preparing candidates for a {role} role.

Provide a concise model answer to the following interview question using max word count {wordcount}. Use a professional tone, include real-world logic, and format clearly (e.g., STAR method if applicable). Also try to implement mood engaging language.

Interview Question:
\"\"\"{question}\"\"\"
"""
    try:
        # Prepare request data
        request_data = {
            "model": "gpt-4o",
            "temperature": temperature,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "top_p": top_p,
            "max_tokens": 100,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        # Store request for debugging if debug mode is enabled
        if st.session_state.get("debug_mode", False):
            st.session_state.last_api_request = request_data
        
        # Make API call with safe wrapper
        response = safe_api_call(
            lambda: client.chat.completions.create(**request_data),
            app_logger
        )
        
        # Handle error response
        if isinstance(response, dict) and "error" in response:
            display_error(response["error"], "error", app_logger)
            return "I apologize, but I encountered an issue generating an ideal answer."
        
        # Update token usage
        update_token_usage(response.usage)
        
        # Store response for debugging if debug mode is enabled
        store_api_request_response(request_data, response, st.session_state.get("debug_mode", False))
    
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        app_logger.log_error(e, {"function": "generate_ideal_answer"})
        return f"Ideal answer generation error: {str(e)}"

@log_api(app_logger)
def generate_ideal_answer_based_on_user_input(user_input, question):
    """
    Generate an improved answer based on the user's input.
    
    Args:
        user_input (str): The user's answer
        question (str): The interview question
        
    Returns:
        str: The improved answer
    """
    prompt = f"""
You are an expert interview coach. Your task is to improve the following user answer to make it ideal for a job interview.

Interview Question: "{question}"

User's Original Answer: "{user_input}"

Please rewrite the answer to:
- Be clear, concise, and professional
- Highlight relevant skills and achievements
- Use a confident tone
- Stay factually consistent with the user's original input
- Try to limit the answer to the max {wordcount} words
- Use also mood engaging language

Respond with the improved (ideal) answer only.
"""
    try:
        # Prepare request data
        request_data = {
            "model": "gpt-4o",
            "temperature": temperature,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "top_p": top_p,
            "max_tokens": 100,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        # Store request for debugging if debug mode is enabled
        if st.session_state.get("debug_mode", False):
            st.session_state.last_api_request = request_data
        
        # Make API call with safe wrapper
        response = safe_api_call(
            lambda: client.chat.completions.create(**request_data),
            app_logger
        )
        
        # Handle error response
        if isinstance(response, dict) and "error" in response:
            display_error(response["error"], "error", app_logger)
            return "I apologize, but I encountered an issue generating an improved answer."
        
        # Update token usage
        update_token_usage(response.usage)
        
        # Store response for debugging if debug mode is enabled
        store_api_request_response(request_data, response, st.session_state.get("debug_mode", False))

        

        
        return response.choices[0].message.content.strip()
    except Exception as e:
        app_logger.log_error(e, {"function": "generate_ideal_answer_based_on_user_input"})
        return f"Improved answer error: {str(e)}"

@log_api(app_logger)
def analyze_mood(ai_message):
    """
    Analyze the mood of the AI interviewer.
    
    Args:
        ai_message (str): The AI interviewer's message
        
    Returns:
        tuple: (emoji_label, mood_explanation) - Mood label with emoji and explanation
    """
    mood_prompt = f"""
You are an HR of a Company which want to hire. Analyze the tone of the following message from the applicant. Choose one mood label from:
- Encouraging 😊
- Challenging 😐
- Supportive 👍
- Disengaged 😒
- Neutral 😶
- Critical 😠

Return only the label and emoji on the first line.
Then provide a brief explanation on the next line.
Provide tips what the applicant can do to improve the mood of the interviewer.
Message:
\"\"\"{ai_message}\"\"\"
"""
    try:
        # Prepare request data
        request_data = {
            "model": "gpt-4o",
            "temperature": temperature,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "top_p": top_p,
            "max_tokens": 100,
            "messages": [{"role": "user", "content": mood_prompt}]
        }
        
        # Store request for debugging if debug mode is enabled
        if st.session_state.get("debug_mode", False):
            st.session_state.last_api_request = request_data
        
        # Make API call with safe wrapper
        response = safe_api_call(
            lambda: client.chat.completions.create(**request_data),
            app_logger
        )
        
        # Handle error response
        if isinstance(response, dict) and "error" in response:
            display_error(response["error"], "error", app_logger)
            return "🤖 Error", "I apologize, but I encountered an issue analyzing the mood."
        
        # Update token usage
        update_token_usage(response.usage)
        
        # Store response for debugging if debug mode is enabled
        store_api_request_response(request_data, response, st.session_state.get("debug_mode", False))
        
        # Validate response
        validation_result = api_validator.validate_openai_response(response, "mood_analysis")
        
        if not validation_result["is_valid"]:
            for error in validation_result["errors"]:
                app_logger.log_error(error, {"response_validation": "failed"})
            
            # Extract mood manually as fallback
            content = response.choices[0].message.content
            lines = content.strip().split("\n", 1)
            emoji_label = lines[0].strip()
            explanation = lines[1].strip() if len(lines) > 1 else "No explanation provided."
            
            return emoji_label, explanation
        
        # Use validated and structured response
        cleaned_response = validation_result["cleaned_response"]
        return cleaned_response["mood_label"], cleaned_response["explanation"]
    except Exception as e:
        app_logger.log_error(e, {"function": "analyze_mood"})
        return "🤖 Error", f"Mood analysis error: {str(e)}"

def clear_reply():
    """Clear the user reply input field."""
    st.session_state["user_reply"] = ""

# Validate session state
session_validation = session_validator.validate_session_state()
if session_validation["errors"]:
    st.warning("Session state issues detected. Attempting repair...")
    repair_result = session_validator.repair_session_state()
    if repair_result["repaired"]:
        st.success("Session state repaired successfully.")
    else:
        st.error("Could not repair session state. Please restart the application.")

# Initialize interview state
if "interview_started" not in st.session_state:
    st.session_state.interview_started = False

# Job role input form (before interview starts)
if not st.session_state.interview_started:
    job_role = st.text_input(
        "Job Role (e.g., Software Engineer, HR Manager)",
        "Technical Project Manager",
        key="job_role_input"
    )
    
    # Validate job role input
    if job_role:
        job_role_validation = input_validator.validate_text_input(job_role, "job_role")
        if not job_role_validation["is_valid"]:
            for error in job_role_validation["errors"]:
                st.error(f"❌ {error}")
        elif job_role_validation["warnings"]:
            with st.expander("💡 Job Role Suggestions"):
                for warning in job_role_validation["warnings"]:
                    st.warning(warning)
    
    st.session_state.query_count = 0  # Initialize query count
    custom_question = st.text_area("Ask a specific interview question (optional)", key="job_question_custom")
    


# Start interview button
if st.button("Start Practice", key="start_practice_main", disabled=st.session_state.interview_started) and not st.session_state.interview_started:
    # Log user interaction
    app_logger.log_user_interaction("start_practice", {"job_role": job_role, "difficulty": difficulty})
    
    if not job_role:
        st.warning("Please enter a job role.")
    else:
        st.session_state.interview_started = True  # Set flag
        st.session_state.job_role = job_role  # Save job role
        st.session_state.query_count = 0

        # Get AI reply
        system_prompt = get_system_prompt(job_role, difficulty)
        st.session_state.messages = [{"role": "system", "content": system_prompt}]
        
        if custom_question:
            st.session_state.initial_prompt = custom_question
        else:
            first_question = get_ai_response(st.session_state.messages)
            st.session_state.initial_prompt = first_question

        st.session_state.messages.append({"role": "user", "content": st.session_state.initial_prompt})

# User response input (after Start is pressed)
if st.session_state.get("messages"):
    if 'query_count' not in st.session_state or st.session_state.query_count == 0:
        response = st.session_state.initial_prompt
        st.markdown("👉 First Question")
        st.write(response)
    
    user_reply = st.text_area("Your Answer:", key="user_reply")
    

    if st.button("Submit Answer", key="submit_answer") and st.session_state.interview_started:
        # Log user interaction
        app_logger.log_user_interaction("submit_answer", {"answer_length": len(user_reply) if user_reply else 0})
        
        # Check query count
        if 'query_count' not in st.session_state or st.session_state.query_count is None:
            st.session_state.query_count = 0

        st.session_state.query_count += 1

        if st.session_state.query_count > 5:
            st.warning("Usage limit reached for this session.")
        else:
            if user_reply.strip():
                # Final validation before processing
                validation_result = input_validator.validate_text_input(user_reply, "answer")
                if not validation_result["is_valid"]:
                    for error in validation_result["errors"]:
                        st.error(f"❌ {error}")
                else:
                    # Use cleaned text
                    cleaned_reply = validation_result["cleaned_text"]
                    
                    # Append user response
                    st.session_state.messages.append({"role": "user", "content": cleaned_reply})

                    # Get AI question
                    response = get_ai_response(st.session_state.messages)
                    st.session_state.messages.append({"role": "assistant", "content": response})

                    # Get previous AI question
                    last_question = st.session_state.messages[-3]["content"]

                    # Display interaction
                    st.markdown("Previous Turn")
                    st.markdown(f"**Interview Question:** {last_question}")
                    st.markdown(f"**Your Answer:** {cleaned_reply}")

                    # Evaluate
                    scores, feedback = evaluate_answer(last_question, cleaned_reply)
                    if scores:
                        st.markdown("Evaluation")
                        display_score_chart(scores)
                    
                    # Optional feedback
                    with st.expander("Show Feedback"):
                        st.write(feedback)

                    # --- Mood analysis ---
                    emoji_label, mood_explanation = analyze_mood(response)
                    st.markdown("Interviewer Mood")
                    st.markdown(f"**Mood:** {emoji_label}")
                    with st.expander("Explain Mood"):
                        st.write(mood_explanation)

                    # --- Ideal Answer ---
                    ideal_answer = generate_ideal_answer_based_on_user_input(cleaned_reply, last_question)
                    st.markdown("Improved Answer based on your input")
                    with st.expander("Show Model Answer"):
                        st.write(ideal_answer)

                    # Next question
                    st.markdown("👉 Next Question")
                    st.write(response)
                    log = {
                        "job_role": st.session_state.job_role,
                        "difficulty": difficulty,
                        "question": last_question,
                        "user_answer": user_reply,
                        "model_feedback": feedback,
                        "mood_feedback": emoji_label,
                        "mood_explanation": mood_explanation,
                        "scores": scores,
                        "ideal_answer": generate_ideal_answer(last_question, st.session_state.job_role),
                        "improved_user_answer": ideal_answer,
                    }

                    # Append to a persistent JSONL file (one JSON object per line)
                    log_file = "interview_log.json"
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(log, ensure_ascii=False) + "\n")
            else:
                st.warning("Please enter your answer before submitting.")

# Add a reset button
if st.session_state.interview_started:
    if st.sidebar.button("Reset Interview"):
        # Log user interaction
        app_logger.log_user_interaction("reset_interview", {})
        
        # Clear session state
        for key in list(st.session_state.keys()):
            if key != "debug_mode" and key != "token_usage":
                del st.session_state[key]
        
        # Reinitialize required fields
        st.session_state.interview_started = False
        st.session_state.messages = []
        st.session_state.query_count = 0
        
        # Force UI to update
        st.experimental_rerun()

