import re
import json
import g4f
from g4f.models import Model, ModelUtils
from typing import Tuple, List  
from termcolor import colored
from dotenv import load_dotenv
import os
import google.generativeai as genai

# Load environment variables
if os.path.exists(".env"):
    load_dotenv(".env")
else:
    load_dotenv("../.env")

# Set environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Configure g4f - enable auto update and logging
g4f.version_checking = False
g4f.debug.logging = True

def generate_response(prompt: str, ai_model: str) -> str:
    """
    Generate a script for a video, depending on the subject of the video.

    Args:
        video_subject (str): The subject of the video.
        ai_model (str): The AI model to use for generation.

    Returns:
        str: The response from the AI model.
    """

    if ai_model == 'g4f':
        from g4f.client import Client
        from g4f import Provider
        client = Client(provider=Provider.Gemini)
        response = client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[{"role": "user", "content": prompt}],
            web_search=False
        )
        return response.choices[0].message.content

    elif ai_model == 'gemmini':
        model = genai.GenerativeModel('gemini-pro')
        response_model = model.generate_content(prompt)
        response = response_model.text

    else:
        raise ValueError("Invalid AI model selected.")

    return response



def get_search_terms(video_subject: str, amount: int, script: str, ai_model: str) -> List[str]:
    """
    Generate a JSON-Array of search terms for stock videos,
    depending on the subject of a video.

    Args:
        video_subject (str): The subject of the video.
        amount (int): The amount of search terms to generate.
        script (str): The script of the video.
        ai_model (str): The AI model to use for generation.

    Returns:
        List[str]: The search terms for the video subject.
    """

    # Build prompt
    prompt = f"""
    # Role: Video Search Terms Generator
    ## Goals:
    Generate {amount} search terms for stock videos, depending on the subject of a video.

    ## Constrains:
    1. the search terms are to be returned as a json-array of strings.
    2. each search term should consist of 1-3 words, always add the main subject of the video.
    3. you must only return the json-array of strings. you must not return anything else. you must not return the script.
    4. the search terms must be related to the subject of the video.
    5. reply with english search terms only.

    ## Output Example:
    ["search term 1", "search term 2", "search term 3","search term 4","search term 5"]
    
    ## Context:
    ### Video Subject
    {video_subject}

    ### Video Script
    {script}

    Please note that you must use English for generating video search terms; Chinese is not accepted.
    """.strip()


    # Let user know
    print(colored(f"Generating {amount} search terms for {video_subject}...", "cyan"))

    # Generate search terms
    response = generate_response(prompt, ai_model)

    # Let user know
    print(colored(f"Response: {response}", "cyan"))
    # Parse response into a list of search terms
    search_terms = []
    
    try:
        search_terms = json.loads(response)
        if not isinstance(search_terms, list) or not all(isinstance(term, str) for term in search_terms):
            raise ValueError("Response is not a list of strings.")

    except (json.JSONDecodeError, ValueError):
        print(colored("[*] GPT returned an unformatted response. Attempting to clean...", "yellow"))

        # Attempt to extract list-like string and convert to list
        match = re.search(r'\["(?:[^"\\]|\\.)*"(?:,\s*"[^"\\]*")*\]', response)
        if match:
            try:
                search_terms = json.loads(match.group())
            except json.JSONDecodeError:
                print(colored("[-] Could not parse response.", "red"))
                return []



    # Let user know
    print(colored(f"\nGenerated {len(search_terms)} search terms: {', '.join(search_terms)}", "cyan"))

    # Return search terms
    return search_terms


def generate_metadata(video_subject: str, script: str, ai_model: str) -> Tuple[str, str, List[str]]:  
    """  
    Generate metadata for a YouTube video, including the title, description, and keywords.  

    Args:  
        video_subject (str): The subject of the video.  
        script (str): The script of the video.  
        ai_model (str): The AI model to use for generation.  

    Returns:  
        Tuple[str, str, List[str]]: The title, description, and keywords for the video.  
    """  

    # Build prompt for title  
    title_prompt = f"""  
    You are an expert YouTube Shorts title writer. Generate a single catchy, SEO-optimized title for a video based on the following script.  
    The title must be attention-grabbing, under 60 characters, and directly reflect the content of the script.  
    Return ONLY the title text — no quotes, no explanations, no extra formatting.  

    Video Subject: {video_subject}  

    Script:  
    {script}  
    """  

    # Generate title  
    title = generate_response(title_prompt, ai_model).strip().strip('"').strip("'")  
    
    # Build prompt for description  
    description_prompt = f"""  
    You are an expert YouTube Shorts description writer. Write a brief, engaging description for a video based on the following script.  
    The description should include relevant hashtags and be optimized for discovery.  
    Return ONLY the description text — no extra formatting or explanations.  

    Video Subject: {video_subject}  

    Script:  
    {script}  
    """  

    # Generate description  
    description = generate_response(description_prompt, ai_model).strip()  

    # Generate keywords  
    keywords = get_search_terms(video_subject, 6, script, ai_model)  

    return title, description, keywords
