# validate_app.py

"""
Validation Script for Streamlit Interview Practice App
Author: Kyra Cole (adapted by ChatGPT the first version 0.0.1)
"""

import pytest
import os
from openai import OpenAI

# Dummy functions to simulate your actual app logic if the function are working, but not if the performance is not as expected.
# These should be replaced with the actual functions from your app
# Version 0.0.1
# Note: Ensure these functions are imported from your actual app file
# Replace these with actual imports from your app file

def evaluate_answer(question, answer):
    # Replace with actual logic
    return {"Relevance": 4, "Clarity": 5, "Technical Accuracy": 4, "Depth": 4, "Communication": 5}, "Good answer."

def generate_ideal_answer(question, role):
    return f"Ideal answer for role {role} to question: {question}"

def generate_ideal_answer_based_on_user_input(user_input, question):
    return f"Improved version of: {user_input} for question: {question}"

def test_env_variable():
    assert os.getenv("OPENAI_API_KEY"), "Missing OPENAI_API_KEY in environment"

def test_evaluation_format():
    q = "Tell me about a time you led a team."
    a = "I led a 5-person team on a deadline-critical project."
    scores, feedback = evaluate_answer(q, a)
    assert all(k in scores for k in ["Relevance", "Clarity", "Technical Accuracy", "Depth", "Communication"]), "Missing score keys"
    assert isinstance(feedback, str) and len(feedback) > 0

def test_generate_ideal_answer():
    output = generate_ideal_answer("Describe a conflict at work", "Project Manager")
    assert "conflict" in output.lower()
    assert isinstance(output, str)

def test_generate_ideal_answer_based_on_user_input():
    improved = generate_ideal_answer_based_on_user_input("I resolved it by talking to the client", "How did you handle a client conflict?")
    assert "resolved" in improved.lower() or "improved" in improved.lower()
    assert isinstance(improved, str)

def test_score_types():
    q = "How do you handle pressure?"
    a = "I plan and prioritize, and stay calm under deadlines."
    scores, _ = evaluate_answer(q, a)
    for val in scores.values():
        assert isinstance(val, int) and 0 <= val <= 5, f"Invalid score value: {val}"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
