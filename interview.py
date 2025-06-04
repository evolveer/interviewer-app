
## Interview Practice App
# A Streamlit app that simulates an AI interview coach for practice interviews.
# This app allows users to practice answering interview questions with an AI-generated interviewer.
# Requirements:
# - OpenAI API key stored in a .env file
# - Streamlit for the web interface
# - Matplotlib for visualizing evaluation scores
# - Pandas for data manipulation
# Install required packages if not already installed
# pip install streamlit openai matplotlib pandas python-dotenv  
# Import necessary libraries
# Author: Kyra Cole
# Date: 2025-06-03
# Version: 1.1
#   
## This code is licensed under the MIT License.

import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import pandas as pd
import re

# Load API key important security measure
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Streamlit UI ---
st.set_page_config(page_title="Interview Practice App", layout="centered")

st.title("AI Interview Practice")
st.write("Practice answering interview questions with an AI-generated interviewer.")

# Sidebar for parameters
st.sidebar.header("Settings")
temperature = st.sidebar.slider("Creativity (temperature)", 0.0, 1.0, 0.7)
frequency_penalty = st.sidebar.slider("Frequency Penalty", 0.0, 2.0, 1.0)
presence_penalty = st.sidebar.slider("Presence Penalty", 0.0, 2.0, 1.0)

top_p = st.sidebar.slider("Top P", 0.0, 1.0, 0.1)

difficulty = st.sidebar.selectbox("Difficulty Level", ["Easy", "Medium", "Hard"])
wordcount = st.sidebar.slider("Max Ideal Answer Word Count(words)", 50, 200, 100)

# User input
job_role = st.text_input("Job Role (e.g., Software Engineer, HR Manager)", "Technical Project Manager")
custom_question = st.text_area("Ask a specific interview question (optional)")

# --- Session state for conversation ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# System prompt
def get_system_prompt(role, difficulty_level):
    return f"""
You are a professional interview coach simulating a {difficulty_level.lower()} interview for the role of {role}         
Ask concise, focused questions that are easy to understand and answer.
Limit each question to a maximum of 2 sentences or 30 words.    
Ask one question at a time. Use formal but simple language.
Focus on both technical and behavioral aspects appropriate to the role.
"""



# --- OpenAI API call ---
def get_ai_response(messages):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=temperature,

            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            top_p=top_p,
            max_tokens=100,

            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"


def evaluate_answer(question, answer):
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
please don't  judge grammar or spelling mistakes.
Feedback: <text>
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=temperature,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            top_p=top_p,
            max_tokens=100,
            messages=[{"role": "user", "content": eval_prompt}]
        ).choices[0].message.content

        # Extract scores
        scores = {}
        for key in ["Relevance", "Clarity", "Technical Accuracy", "Depth", "Communication"]:
            match = re.search(rf"{key}: (\d)", response)
            scores[key] = int(match.group(1)) if match else 0

        feedback_match = re.search(r"Feedback:\s*(.+)", response, re.DOTALL)
        feedback = feedback_match.group(1).strip() if feedback_match else "No feedback available."

        return scores, feedback
    except Exception as e:
        return {}, f"Evaluation error: {str(e)}"
    
def display_score_chart(scores: dict):
    df = pd.DataFrame(list(scores.items()), columns=["Metric", "Score"])
    fig, ax = plt.subplots()
    ax.barh(df["Metric"], df["Score"], align='center')
    ax.set_xlim(0, 5)
    ax.set_xlabel("Score (1–5)")
    ax.set_title("Answer Evaluation")
    st.pyplot(fig)

def generate_ideal_answer(question, role):
    prompt = f"""
You are an expert interview coach preparing candidates for a {role} role.

Provide a concise  model answer to the following interview question using max word count{wordcount}. Use a professional tone, include real-world logic, and format clearly (e.g., STAR method if applicable).also try  to  implement mood engaging language

Interview Question:
\"\"\"{question}\"\"\"
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=temperature,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            top_p=top_p,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Ideal answer generation error: {str(e)}"


def generate_ideal_answer_based_on_user_input(user_input, question):
    prompt = f"""
You are an expert interview coach. Your task is to improve the following user answer to make it ideal for a job interview.

Interview Question: "{question}"

User's Original Answer: "{user_input}"


Please rewrite the answer to:
- Be clear, concise, and professional
- Highlight relevant skills and achievements
- Use a confident tone
- Stay factually consistent with the user's original input
- Use a maximum of {wordcount}
- Use also mood engaging language

Respond with the improved (ideal) answer only.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            temperature=temperature,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            top_p=top_p,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        # remember message is not a dictionary, but a list of choices
        return response.choices[0].message.content
    except Exception as e:
        return "🤖 Error", f"improved answer error: {str(e)}"


def analyze_mood(ai_message):
    mood_prompt = f"""
Analyze the tone of the following interviewer message. Choose one mood label from:
- Encouraging 😊
- Challenging 😐
- Supportive 👍
- Disengaged 😒
- Neutral 😶
- Critical 😠

Return only the label and emoji on the first line.
Then provide a brief explanation on the next line.

Message:
\"\"\"{ai_message}\"\"\"
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=temperature,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            top_p=top_p,
            max_tokens=100,
            messages=[{"role": "user", "content": mood_prompt}]
        ).choices[0].message.content

        lines = response.strip().split("\n", 1)
        emoji_label = lines[0].strip()
        explanation = lines[1].strip() if len(lines) > 1 else "No explanation provided."

        return emoji_label, explanation
    except Exception as e:
        return "🤖 Error", f"Mood analysis error: {str(e)}"

def expensive_api(prompt):
    # Simulate a time-consuming or costly call
    import time
    time.sleep(2)
    return f"Processed response for: '{prompt}'"


def rate_answer(interview_question, user_answer):
    eval_prompt = f"""
You are an expert interview coach. Rate the following answer using 1-5 for each of the following criteria:
Relevance, Clarity, Technical Accuracy, Depth, and Communication.
Then provide brief feedback and suggestions.

Question: {interview_question}
Answer: {user_answer}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=temperature,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        top_p=top_p,
        max_tokens=100,
        messages=[{"role": "user", "content": eval_prompt}]
    )
    return response.choices[0].message.content


# Start interview
if st.button("Start Practice"):
    if not job_role:
        st.warning("Please enter a job role.")
    else:
        system_prompt = get_system_prompt(job_role, difficulty)
        st.session_state.query_count = 0  # Reset query count for new session
        st.session_state.messages = [{"role": "system", "content": system_prompt}]
        initial_prompt = custom_question if custom_question else "Ask me an interview question."
        st.session_state.messages.append({"role": "user", "content": initial_prompt})
        response = get_ai_response(st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.markdown("Interview Coach:")
        st.write(response)

# User response input (after Start is pressed)
if st.session_state.get("messages"):
    user_reply = st.text_area("Your Answer:", key="user_reply")
    if st.button("Submit Answer"):
        # 2nd API security check
        if 'query_count' not in st.session_state:
            st.session_state.query_count = 0
        st.session_state.query_count += 1

        if st.session_state.query_count > 5:
            st.warning("Usage limit reached for this session.")
        else:
            expensive_api(user_reply)  # Simulate an expensive API call

        if user_reply.strip():
            # Append user response
            st.session_state.messages.append({"role": "user", "content": user_reply})

            # Get AI reply
            response = get_ai_response(st.session_state.messages)
            st.session_state.messages.append({"role": "assistant", "content": response})

            # Get previous AI question
            last_question = st.session_state.messages[-3]["content"]

            # Display interaction
            st.markdown("Previous Turn")
            st.markdown(f"**Interview Question:** {last_question}")
            st.markdown(f"**Your Answer:** {user_reply}")

            # Evaluate
            scores, feedback = evaluate_answer(last_question, user_reply)
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
            ideal_answer = generate_ideal_answer_based_on_user_input(last_question, job_role)
            st.markdown("Improved  Answer based on your input")
            with st.expander("Show Model Answer"):
                st.write(ideal_answer)



            # Next question
            st.markdown("👉 Next Question")
            st.write(response)
        else:
            st.warning("Please enter your answer before submitting.")



