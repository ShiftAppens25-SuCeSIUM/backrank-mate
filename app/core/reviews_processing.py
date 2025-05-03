"""Process reviews using Google GenAI API.
This module provides functionality to process reviews and generate a fact-checking report.
levaraging  the Google GenAI API.
"""

import json
import os
import time
from pathlib import Path
from google import genai
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool

api_key = os.getenv("API_KEY")

allowed_gemini_extensions = [
    ".png",
    ".jpg",
    ".txt",
    ".mp4",
    ".pdf",
    ".mp3",
    ".mkv",
    ".wav",
]


class GeminiBogusError(Exception):
    """Custom exception for handling errors related to Gemini API."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message



def gemini_wait_until_active(client: genai.Client, name: str, timeout: int = 60):
    """Waits until the Gemini file is in 'ACTIVE' state or timeout.
    Args:
        client (genai.Client): The GenAI client instance.
        name (str): The name of the file to check.
        timeout (int): The maximum time to wait in seconds.
    Raises:
        TimeoutError: If the file does not become 'ACTIVE' within the timeout period.
    """
    start = time.time()
    while time.time() - start < timeout:
        file_info = client.files.get(name=name)
        if file_info.state == "ACTIVE":
            return file_info
        time.sleep(1)
    raise TimeoutError(f"File {name} did not become ACTIVE in time.")


def process_query(query: str, directory: str | None = None) -> dict:
    """
    Process the query using Google GenAI API and generate a fact-checking report.
    Args:
        query (str): The query to be fact-checked.
        directory (str | None): The directory containing files to be uploaded.
    Returns:
        dict: A dictionary containing the results of the fact check.
    """
    google_search_tool = Tool(google_search=GoogleSearch())
    files = (
        [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, f))
        ]
        if directory
        else []
    )
    filtered_files = [f for f in files if Path(f).suffix in allowed_gemini_extensions]
    client = genai.Client(api_key=api_key)
    uploaded_files = [client.files.upload(file=f) for f in filtered_files]

    prompt = f"""
Given the query: {query} and if present the files uploaded

request the fact check api to search for similar claims as in the provided data
in case one is found use its reviews otherwise search the web for your own reviews

determine the following:
1. The overall truth of the query (e.g., "true", "false", "misleading", "innacuracy").
2. The sources that agree with the query and their information, sorted by most recent.
3. The sources that disagree with the query and their information, sorted by most recent.
4. The certainty of the overall truth (0-1 scale).
5. The query itself.


Your answer must only be a valid JSON string
Publisher = {{'name': str, 'site': str}}
Source = {{'publisher': Publisher, 'information_url': str, 'review': str}}
Return: {{"status": str, "agree_sources":\
    List[Source], "disagree_sources": List[Source], "certainty": float, "query": str}}
"""
    for f in uploaded_files:
        gemini_wait_until_active(client, f.name)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=uploaded_files + [prompt],
        config=GenerateContentConfig(
            tools=[google_search_tool],
            response_modalities=["TEXT"],
        ),
    )
    t = response.text
    try:
        t = t.split("```json")[1]
        t = t.split("```")[0]
        data = json.loads(t)
        return data
    except Exception as e:
        raise GeminiBogusError(
            f"Gemini API cannot process the request, please try again later."
        )
