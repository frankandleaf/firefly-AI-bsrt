import os
from openai import OpenAI

 
def call_openai_chat(messages=[], model="gemini-2.5-flash", temperature=0.7):
    api_key = ""
    base_url = ""
    if "gpt" in model:
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")
    elif "gemini" in model:
        api_key = os.environ.get("GEMINI_API_KEY")
        base_url = os.environ.get("GEMINI_BASE_URL")
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    return response.choices[0].message

 
