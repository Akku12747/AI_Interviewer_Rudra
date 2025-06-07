# AI_Interviewer_Rudra
import speech_recognition as sr
import pyttsx3
import time
import os
from dotenv import load_dotenv
import google.generativeai as genai
import re

# Load environment variables
load_dotenv()
GEMINI_API_KEY = ("GEMINI_API_HERE")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Initialize speech recognition and text-to-speech
recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)  # Speed of speech
tts_engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)

# Track asked questions to ensure uniqueness
asked_questions = []

def speak(text):
    """Convert text to speech."""
    try:
        tts_engine.say(text)
        tts_engine.runAndWait()
    except Exception as e:
        print(f"TTS error: {e}")

def listen(prompt_text):
    """Listen to user's voice input and return text."""
    print(prompt_text)
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=30)
            text = recognizer.recognize_google(audio)
            print(f"You said: {text}")
            return text
        except sr.exceptions.WaitTimeoutError:
            print("No speech detected. Please try again.")
            return None
        except sr.exceptions.UnknownValueError:
            print("Could not understand the audio. Please try again.")
            return None
        except sr.exceptions.RequestError as e:
            print(f"Speech recognition error: {e}")
            return None

def get_input_method():
    """Ask user to choose input method (text or voice)."""
    speak("Would you like to provide your name and job role using text or voice?")
    print("Please say 'text' or 'voice' to choose your input method.")
    choice = listen("Listening for input method...")
    if choice and choice.lower() in ['text', 'voice']:
        return choice.lower()
    speak("I couldn't catch that. I'll assume text input.")
    return 'text'

def get_name_and_role(input_method):
    """Get name and job role via text or voice."""
    name = "User"
    role_type = "Software Engineer"
    
    if input_method == 'text':
        speak("Please type your name.")
        name = input("Enter your name: ").strip() or "User"
        speak(f"Nice to meet you, {name}! Please type your job role, for example, Software Engineer or Marketing Manager.")
        role_type = input("Enter your job role: ").strip() or "Software Engineer"
    else:
        speak("Please say your name.")
        name_input = listen("Please say your name.")
        if name_input:
            name_match = re.search(r'(?:my name is|name is)\s+([^\s,]+)', name_input, re.IGNORECASE)
            name = name_match.group(1) if name_match else name_input.split()[0] if name_input.split() else "User"
        
        time.sleep(1)
        speak(f"Nice to meet you, {name}! Please say your job role, for example, Software Engineer or Marketing Manager.")
        role_input = listen("Please say your job role.")
        if role_input:
            role_match = re.search(r'(?:job role is|role is)\s+(.+)', role_input, re.IGNORECASE)
            role_type = role_match.group(1) if role_match else role_input or "Software Engineer"
    
    speak(f"Got it, {name}, I'll tailor questions for a {role_type} role.")
    return name, role_type

def generate_question(role_type, test_level, interview_type):
    """Generate a unique role-specific interview question using Gemini."""
    question_type = "technical (focusing on role-specific skills and knowledge)" if interview_type.lower() == "technical" else "non-technical (focusing on behavioral, leadership, or soft skills)"
    prompt = f"""
    Generate a single, concise {interview_type} interview question for a {role_type} role at a {test_level} level.
    The question must be appropriate for the role, difficulty level (Beginner, Intermediate, or Advanced), and {question_type}.
    Ensure the question is different from these previously asked questions: {', '.join(asked_questions) if asked_questions else 'None'}.
    """
    try:
        response = model.generate_content(prompt)
        question = response.text.strip()
        if question not in asked_questions:
            asked_questions.append(question)
            return question
        else:
            # Retry if question is a duplicate
            return generate_question(role_type, test_level, interview_type)
    except Exception as e:
        print(f"Error generating question: {e}")
        return f"Tell me about your experience as a {role_type}."

def evaluate_answer(question, answer, role_type, test_level, interview_type):
    """Evaluate the answer using Gemini and determine if it's correct."""
    if not answer:
        return 0, "No response detected.", "Please provide a clear and detailed answer.", "Incorrect"
    
    question_type = "technical" if interview_type.lower() == "technical" else "non-technical"
    prompt = f"""
    Evaluate the following answer to the {question_type} interview question for a {role_type} role at {test_level} level: '{question}'
    Answer: '{answer}'
    
    Provide a score out of 100 based on:
    - Relevance (50%): Does the answer address the question and {question_type} expectations for the role?
    - Clarity (25%): Is the answer clear and well-structured?
    - Completeness (25%): Does the answer provide sufficient detail for the {test_level} level?
    
    Return a JSON-like response with:
    - total_score (out of 100)
    - feedback (a string summarizing the evaluation)
    - suggestions (a string with improvement suggestions)
    """
    try:
        response = model.generate_content(prompt)
        eval_text = response.text.strip()
        # Simplified parsing (assumes text output; JSON parsing would be ideal)
        lines = eval_text.split('\n')
        total_score = 50  # Default score
        feedback = "Answer evaluated."
        suggestions = f"Ensure your answer is relevant to the {role_type} role and {test_level} level."

        for line in lines:
            if "Score" in line:
                try:
                    total_score = float(line.split(":")[-1].strip())
                except:
                    pass
            elif "Feedback" in line:
                feedback = line.split(":", 1)[-1].strip()
            elif "Suggestions" in line:
                suggestions = line.split(":", 1)[-1].strip()
        
        # Determine if answer is correct (threshold: 70/100)
        status = "Correct" if total_score >= 70 else "Incorrect"
        return total_score, feedback, suggestions, status
    except Exception as e:
        print(f"Error evaluating answer: {e}")
        return 50, "Unable to evaluate answer.", f"Try to be more specific and structured for a {role_type} role.", "Incorrect"

def main():
    # Ask for input method
    speak("Hello! I am Rudra, your AI Interviewer.")
    input_method = get_input_method()
    
    # Get name and job role
    name, role_type = get_name_and_role(input_method)
    
    time.sleep(1)
    
    # Ask for interview test level
    speak(f"What is your interview test level, {name}? Please say Beginner, Intermediate, or Advanced.")
    print("Please say the test level (Beginner, Intermediate, or Advanced).")
    test_level = listen("Listening for test level...")
    if not test_level or test_level.lower() not in ["beginner", "intermediate", "advanced"]:
        test_level = "Intermediate"
        speak(f"I couldn't catch the level, {name}. I'll assume an Intermediate level.")
    else:
        test_level = test_level.capitalize()
        speak(f"Got it, {name}, I'll set the questions to {test_level} level.")
    
    time.sleep(1)
    
    # Ask for interview type (technical or non-technical)
    speak(f"Would you like a technical or non-technical interview, {name}?")
    print("Please say 'Technical' or 'Non-technical'.")
    interview_type = listen("Listening for interview type...")
    if not interview_type or interview_type.lower() not in ["technical", "non-technical", "non technical"]:
        interview_type = "Technical"
        speak(f"I couldn't catch the interview type, {name}. I'll assume a Technical interview.")
    else:
        interview_type = "Non-technical" if interview_type.lower().startswith("non") else "Technical"
        speak(f"Got it, {name}, I'll set the interview to {interview_type}.")
    
    time.sleep(1)
    speak(f"Let's begin the interview for {name}. I will ask you a series of {interview_type.lower()} questions for a {role_type} role at {test_level} level. Please answer clearly.")
    
    # Generate and ask 5 unique questions
    for i in range(5):
        question = generate_question(role_type, test_level, interview_type)
        print(f"\nQuestion {i+1} for {name}: {question}")
        speak(f"Question {i+1}, {name}: {question}")
        time.sleep(1)
        
        answer = listen(f"Listening for your answer, {name}...")
        if answer:
            score, feedback, suggestions, status = evaluate_answer(question, answer, role_type, test_level, interview_type)
            feedback_text = f"Answer Status: {status}\nScore: {score:.1f}/100\nFeedback: {feedback}\nSuggestions: {suggestions}"
            print(feedback_text)
            speak(f"{name}, {feedback_text}")
        else:
            print(f"No valid response from {name}. Moving to next question.")
            speak(f"No valid response, {name}. Moving to next question.")
        
        time.sleep(2)  # Pause before next question
    
    speak(f"Thank you, {name}, for completing the interview for the {role_type} role. Keep practicing to improve your answers!")
    print("Interview completed.")

if __name__ == "__main__":
    main()
