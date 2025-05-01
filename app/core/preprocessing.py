import os
import instaloader
import os
from pathlib import Path
import shutil
from google import genai
import time

__allowed_gemini_extensions__ = [".png", ".jpg", ".txt", ".mp4"]

def __download_insta_post__(shortcode: str):
    base_dir = f"{os.getenv("TEMPORARY_DIRECTORY")}/insta"
    directory = f"{base_dir}/{shortcode}"
    os.makedirs(directory, exist_ok=True)

    insta = instaloader.Instaloader()
    post = instaloader.Post.from_shortcode(insta.context, shortcode)
    insta.download_post(post, target=Path(directory))

def __gemini_wait_until_active__(client, name, timeout=60):
    """Waits until the Gemini file is in 'ACTIVE' state or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        file_info = client.files.get(name=name)
        if file_info.state == "ACTIVE":
            return file_info
        time.sleep(1)
    raise TimeoutError(f"File {name} did not become ACTIVE in time.")

def __summarize_insta_post__(shortcode: str) -> str:
    base_dir = f"{os.getenv("TEMPORARY_DIRECTORY")}/insta"
    directory = f"{base_dir}/{shortcode}"
    client = genai.Client(api_key=os.getenv("API_KEY"))

    files = [ 
        os.path.join(directory, f) for f in os.listdir(directory) 
        if os.path.isfile(os.path.join(directory, f))
    ]

    filtered_files = [
        f for f in files
        if Path(f).suffix in __allowed_gemini_extensions__
    ]
    
    uploaded_files = [client.files.upload(file=f) for f in filtered_files]
    content = uploaded_files + ["Summarize this instagram post"]

    # Wait for files to be uploaded
    for f in uploaded_files:
        __gemini_wait_until_active__(client, f.name)

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=content
    )

    print(response.text)
    return ""


def __delete_insta_post__(shortcode: str):
    base_dir = f"{os.getenv("TEMPORARY_DIRECTORY")}/insta"
    directory = f"{base_dir}/{shortcode}"
    shutil.rmtree(directory)

def insta_post(shortcode: str) -> str:
    try:
        __download_insta_post__(shortcode)
        summary = __summarize_insta_post__(shortcode)
    finally:
        __delete_insta_post__(shortcode)
