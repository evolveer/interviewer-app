"""
validators.py - Validation system for the Interview Practice App

This module provides comprehensive validation for user inputs, API responses,
configuration settings, and session state. It ensures data integrity and
provides helpful feedback for invalid inputs.

Author: Kyra Cole
Date: 2025-06-05
"""

import re
import string
import unicodedata
import json
import os
from typing import Dict, List, Any, Optional
import streamlit as st

class InputValidator:
    """
    InputValidator class provides validation for user text inputs.
    
    Features:
    - Length validation for different input types
    - Content quality assessment
    - Profanity filtering
    - Spam detection
    - Language appropriateness checking
    """
    
    def __init__(self):
        """Initialize the InputValidator with validation rules."""
        # Define validation rules
        self.min_answer_length = 10
        self.max_answer_length = 2000
        self.min_job_role_length = 2
        self.max_job_role_length = 100
        

        
        # Spam detection patterns
        self.spam_patterns = [
            r'(.)\1{10,}',  # Repeated characters
            r'[A-Z]{20,}',  # Excessive caps
            r'[!@#$%^&*]{5,}',  # Excessive special characters
            r'https?://\S+',  # URLs (might be spam)
            r'\b\d{10,}\b',  # Long numbers (phone numbers, etc.)
        ]
        
        # Minimum word count for meaningful responses
        self.min_word_count = 3
    
    def validate_text_input(self, text: str, input_type: str = "answer") -> Dict:
        """
        Validate text input with comprehensive checks.
        
        Args:
            text (str): The text to validate
            input_type (str): Type of input ("answer", "job_role", etc.)
            
        Returns:
            dict: Validation result with is_valid flag, errors, warnings, and cleaned text
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "cleaned_text": text,
            "score": 100  # Quality score out of 100
        }
        
        if not text or not text.strip():
            validation_result["is_valid"] = False
            validation_result["errors"].append("Input cannot be empty")
            validation_result["score"] = 0
            return validation_result
        
       
        validation_result["cleaned_text"] = text
        


        return validation_result
    

    

    

    
 
    

    

    
 
    def _check_repetition(self, text: str) -> float:
        """
        Check for excessive repetition in text.
        
        Args:
            text (str): Text to check
            
        Returns:
            float: Repetition score (0-1, higher means more repetition)
        """
        words = text.lower().split()
        if len(words) <= 1:
            return 0.0
        
        # Count word frequencies
        word_counts = {}
        for word in words:
            word = word.strip(string.punctuation)
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Calculate repetition score
        total_repetitions = sum(count - 1 for count in word_counts.values() if count > 1)
        repetition_score = total_repetitions / len(words)
        
        return repetition_score
    



class APIResponseValidator:
    """
    APIResponseValidator class validates responses from the OpenAI API.
    
    Features:
    - Type-specific validation for different response types
    - Structure validation for evaluation responses
    - Content appropriateness checking
    - JSON schema validation
    """
    
    def __init__(self):
        """Initialize the APIResponseValidator with validation rules."""
        self.expected_evaluation_fields = ["Relevance", "Clarity", "Technical Accuracy", "Depth", "Communication"]
        self.max_response_length = 5000
        self.min_response_length = 5
        
    def validate_openai_response(self, response: Any, expected_type: str) -> Dict:
        """
        Validate OpenAI API response.
        
        Args:
            response (any): Response object from OpenAI API
            expected_type (str): Expected response type ("question", "evaluation", etc.)
            
        Returns:
            dict: Validation result with is_valid flag, errors, warnings, and cleaned response
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "cleaned_response": None
        }
        
        try:
            # Check if response object exists and has expected structure
            if not hasattr(response, 'choices') or not response.choices:
                validation_result["is_valid"] = False
                validation_result["errors"].append("Invalid API response: No choices found")
                return validation_result
            
            # Extract content
            content = response.choices[0].message.content
            
            if not content:
                validation_result["is_valid"] = False
                validation_result["errors"].append("API response is empty")
                return validation_result
            
            # Validate based on expected type
            if expected_type == "question":
                return self._validate_question_response(content, validation_result)
            elif expected_type == "evaluation":
                return self._validate_evaluation_response(content, validation_result)
            elif expected_type == "mood_analysis":
                return self._validate_mood_response(content, validation_result)
            elif expected_type == "ideal_answer":
                return self._validate_ideal_answer_response(content, validation_result)
            else:
                # Generic validation
                return self._validate_generic_response(content, validation_result)
                
        except Exception as e:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"Error validating API response: {str(e)}")
            return validation_result
    
 
    
    def _validate_evaluation_response(self, content: str, validation_result: Dict) -> Dict:
        """
        Validate evaluation response format.
        
        Args:
            content (str): Response content
            validation_result (dict): Current validation result
            
        Returns:
            dict: Updated validation result
        """
        # Check if response contains expected evaluation fields
        missing_fields = []
        scores = {}
        
        for field in self.expected_evaluation_fields:
            pattern = rf"{field}:\s*(\d)"
            match = re.search(pattern, content)
            if match:
                score = int(match.group(1))
                if 1 <= score <= 5:
                    scores[field] = score
                else:
                    validation_result["warnings"].append(f"Score for {field} is out of range (1-5): {score}")
            else:
                missing_fields.append(field)
        
        if missing_fields:
            validation_result["warnings"].append(f"Missing evaluation fields: {', '.join(missing_fields)}")
        
        # Check for feedback section
        if "Feedback:" not in content:
            validation_result["warnings"].append("No feedback section found in evaluation")
        
        # Extract and validate feedback
        feedback_match = re.search(r"Feedback:\s*(.+)", content, re.DOTALL)
        if feedback_match:
            feedback = feedback_match.group(1).strip()
            if len(feedback) < 10:
                validation_result["warnings"].append("Feedback is very brief")
            elif len(feedback) > 500:
                validation_result["warnings"].append("Feedback is very long")
        
        validation_result["cleaned_response"] = {
            "scores": scores,
            "feedback": feedback if 'feedback' in locals() else "",
            "raw_content": content
        }
        
        return validation_result
    
    def _validate_mood_response(self, content: str, validation_result: Dict) -> Dict:
        """
        Validate mood analysis response.
        
        Args:
            content (str): Response content
            validation_result (dict): Current validation result
            
        Returns:
            dict: Updated validation result
        """
        lines = content.strip().split('\n')
        
        if len(lines) < 2:
            validation_result["warnings"].append("Mood response should have mood label and explanation")
        
        # Check if first line contains an emoji
        first_line = lines[0].strip()
        emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]'
        if not re.search(emoji_pattern, first_line):
            validation_result["warnings"].append("Mood response should include an emoji")
        
        # Check for expected mood labels
        expected_moods = ["Encouraging", "Challenging", "Supportive", "Disengaged", "Neutral", "Critical"]
        mood_found = any(mood in first_line for mood in expected_moods)
        if not mood_found:
            validation_result["warnings"].append("Mood response doesn't contain expected mood labels")
        
        validation_result["cleaned_response"] = {
            "mood_label": first_line,
            "explanation": '\n'.join(lines[1:]) if len(lines) > 1 else "",
            "raw_content": content
        }
        
        return validation_result
    

    
    def _validate_generic_response(self, content: str, validation_result: Dict) -> Dict:
        """
        Generic response validation.
        
        Args:
            content (str): Response content
            validation_result (dict): Current validation result
            
        Returns:
            dict: Updated validation result
        """
        # Basic length check
        if len(content) < self.min_response_length:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Response is too short")
        elif len(content) > self.max_response_length:
            validation_result["warnings"].append("Response is very long")
        
        # Check for inappropriate content
        inappropriate_check = self._check_inappropriate_content(content)
        if inappropriate_check["has_issues"]:
            validation_result["warnings"].extend(inappropriate_check["warnings"])
        
        validation_result["cleaned_response"] = content.strip()
        return validation_result
    




class ConfigValidator:
    """
    ConfigValidator class validates application configuration and user settings.
    
    Features:
    - API key validation
    - Directory validation
    - User settings validation with auto-correction
    """
    
    def __init__(self):
        """Initialize the ConfigValidator with validation rules."""
        self.valid_difficulty_levels = ["Easy", "Medium", "Hard"]
        self.valid_temperature_range = (0.0, 1.0)
        self.valid_penalty_range = (0.0, 2.0)
        self.valid_top_p_range = (0.0, 1.0)
        self.valid_word_count_range = (50, 500)
    
    def validate_app_config(self) -> Dict:
        """
        Validate application configuration.
        
        Returns:
            dict: Validation result with is_valid flag, errors, and warnings
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            validation_result["is_valid"] = False
            validation_result["errors"].append("OpenAI API key is not configured")
        elif len(api_key) < 20:  # Basic length check
            validation_result["warnings"].append("API key seems unusually short")
        
        # Check if required directories exist
        required_dirs = ["logs"]
        for dir_name in required_dirs:
            if not os.path.exists(dir_name):
                try:
                    os.makedirs(dir_name)
                    validation_result["warnings"].append(f"Created missing directory: {dir_name}")
                except Exception as e:
                    validation_result["errors"].append(f"Cannot create directory {dir_name}: {str(e)}")
        
        return validation_result
    
    def validate_user_settings(self, settings: Dict) -> Dict:
        """
        Validate user-provided settings.
        
        Args:
            settings (dict): User settings to validate
            
        Returns:
            dict: Validation result with is_valid flag, errors, warnings, and corrected settings
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "corrected_settings": settings.copy()
        }
        
        # Validate difficulty level
        difficulty = settings.get("difficulty")
        if difficulty and difficulty not in self.valid_difficulty_levels:
            validation_result["errors"].append(f"Invalid difficulty level: {difficulty}")
        
        # Validate temperature
        temperature = settings.get("temperature")
        if temperature is not None:
            if not isinstance(temperature, (int, float)):
                validation_result["errors"].append("Temperature must be a number")
            elif not (self.valid_temperature_range[0] <= temperature <= self.valid_temperature_range[1]):
                validation_result["warnings"].append(f"Temperature {temperature} is outside recommended range {self.valid_temperature_range}")
                # Auto-correct extreme values
                if temperature < self.valid_temperature_range[0]:
                    validation_result["corrected_settings"]["temperature"] = self.valid_temperature_range[0]
                elif temperature > self.valid_temperature_range[1]:
                    validation_result["corrected_settings"]["temperature"] = self.valid_temperature_range[1]
        
        # Validate penalties
        for penalty_name in ["frequency_penalty", "presence_penalty"]:
            penalty_value = settings.get(penalty_name)
            if penalty_value is not None:
                if not isinstance(penalty_value, (int, float)):
                    validation_result["errors"].append(f"{penalty_name} must be a number")
                elif not (self.valid_penalty_range[0] <= penalty_value <= self.valid_penalty_range[1]):
                    validation_result["warnings"].append(f"{penalty_name} {penalty_value} is outside valid range {self.valid_penalty_range}")
                    # Auto-correct
                    if penalty_value < self.valid_penalty_range[0]:
                        validation_result["corrected_settings"][penalty_name] = self.valid_penalty_range[0]
                    elif penalty_value > self.valid_penalty_range[1]:
                        validation_result["corrected_settings"][penalty_name] = self.valid_penalty_range[1]
        
        # Validate top_p
        top_p = settings.get("top_p")
        if top_p is not None:
            if not isinstance(top_p, (int, float)):
                validation_result["errors"].append("Top P must be a number")
            elif not (self.valid_top_p_range[0] <= top_p <= self.valid_top_p_range[1]):
                validation_result["warnings"].append(f"Top P {top_p} is outside valid range {self.valid_top_p_range}")
                # Auto-correct
                if top_p < self.valid_top_p_range[0]:
                    validation_result["corrected_settings"]["top_p"] = self.valid_top_p_range[0]
                elif top_p > self.valid_top_p_range[1]:
                    validation_result["corrected_settings"]["top_p"] = self.valid_top_p_range[1]
        
        # Validate word count
        word_count = settings.get("wordcount")
        if word_count is not None:
            if not isinstance(word_count, int):
                validation_result["errors"].append("Word count must be an integer")
            elif not (self.valid_word_count_range[0] <= word_count <= self.valid_word_count_range[1]):
                validation_result["warnings"].append(f"Word count {word_count} is outside recommended range {self.valid_word_count_range}")
        
        return validation_result


class SessionStateValidator:
    """
    SessionStateValidator class validates and repairs Streamlit session state.
    
    Features:
    - Required field checking
    - Type validation
    - Consistency checking
    - Session state repair
    """
    
    def __init__(self):
        """Initialize the SessionStateValidator with validation rules."""
        self.required_fields = ["messages", "interview_started", "job_role"]
        self.optional_fields = ["query_count", "token_usage", "initial_prompt"]
    
    def validate_session_state(self) -> Dict:
        """
        Validate current session state.
        
        Returns:
            dict: Validation result with is_valid flag, errors, warnings, and problematic fields
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "missing_fields": [],
            "corrupted_fields": []
        }
        
        # Check required fields
        for field in self.required_fields:
            if field not in st.session_state:
                validation_result["missing_fields"].append(field)
                validation_result["warnings"].append(f"Missing required session field: {field}")
        
        # Validate specific fields
        if "messages" in st.session_state:
            messages_validation = self._validate_messages()
            validation_result["errors"].extend(messages_validation["errors"])
            validation_result["warnings"].extend(messages_validation["warnings"])
        
        if "query_count" in st.session_state:
            query_count = st.session_state.query_count
            if not isinstance(query_count, int) or query_count < 0:
                validation_result["corrupted_fields"].append("query_count")
                validation_result["warnings"].append("Query count is invalid")
        
        if "token_usage" in st.session_state:
            token_validation = self._validate_token_usage()
            validation_result["errors"].extend(token_validation["errors"])
            validation_result["warnings"].extend(token_validation["warnings"])
        
        return validation_result
    
    def _validate_messages(self) -> Dict:
        """
        Validate messages structure in session state.
        
        Returns:
            dict: Validation result with errors and warnings
        """
        result = {"errors": [], "warnings": []}
        
        messages = st.session_state.messages
        if not isinstance(messages, list):
            result["errors"].append("Messages should be a list")
            return result
        
        for i, message in enumerate(messages):
            if not isinstance(message, dict):
                result["errors"].append(f"Message {i} is not a dictionary")
                continue
            
            if "role" not in message:
                result["errors"].append(f"Message {i} missing 'role' field")
            elif message["role"] not in ["system", "user", "assistant"]:
                result["warnings"].append(f"Message {i} has unexpected role: {message['role']}")
            
            if "content" not in message:
                result["errors"].append(f"Message {i} missing 'content' field")
            elif not isinstance(message["content"], str):
                result["errors"].append(f"Message {i} content is not a string")
        
        return result
    
    def _validate_token_usage(self) -> Dict:
        """
        Validate token usage structure in session state.
        
        Returns:
            dict: Validation result with errors and warnings
        """
        result = {"errors": [], "warnings": []}
        
        token_usage = st.session_state.token_usage
        if not isinstance(token_usage, dict):
            result["errors"].append("Token usage should be a dictionary")
            return result
        
        required_fields = ["prompt_tokens", "completion_tokens", "total_tokens", "estimated_cost"]
        for field in required_fields:
            if field not in token_usage:
                result["warnings"].append(f"Token usage missing field: {field}")
            else:
                value = token_usage[field]
                if field == "estimated_cost":
                    if not isinstance(value, (int, float)) or value < 0:
                        result["warnings"].append(f"Invalid estimated cost: {value}")
                else:
                    if not isinstance(value, int) or value < 0:
                        result["warnings"].append(f"Invalid {field}: {value}")
        
        return result
    
    def repair_session_state(self) -> Dict:
        """
        Attempt to repair corrupted session state.
        
        Returns:
            dict: Repair result with repaired flag and actions taken
        """
        repair_result = {
            "repaired": False,
            "actions_taken": []
        }
        
        validation = self.validate_session_state()
        
        # Repair missing required fields
        if "messages" not in st.session_state:
            st.session_state.messages = []
            repair_result["actions_taken"].append("Initialized empty messages list")
            repair_result["repaired"] = True
        
        if "interview_started" not in st.session_state:
            st.session_state.interview_started = False
            repair_result["actions_taken"].append("Set interview_started to False")
            repair_result["repaired"] = True
        
        if "job_role" not in st.session_state:
            st.session_state.job_role = ""
            repair_result["actions_taken"].append("Initialized empty job_role")
            repair_result["repaired"] = True
        
        # Repair corrupted fields
        if "query_count" in validation["corrupted_fields"]:
            st.session_state.query_count = 0
            repair_result["actions_taken"].append("Reset query_count to 0")
            repair_result["repaired"] = True
        
        if "token_usage" not in st.session_state or not isinstance(st.session_state.token_usage, dict):
            st.session_state.token_usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0
            }
            repair_result["actions_taken"].append("Reset token_usage to default values")
            repair_result["repaired"] = True
        
        return repair_result

