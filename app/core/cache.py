"""Cache module for storing and retrieving embeddings for similar queries and processed outputs."""

import json
import os
from typing import List

import singlestoredb as s2
from google import genai

from app.core.core import fact_check

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

api_key = os.getenv("API_KEY")

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_database = os.getenv("DB_DATABASE")


# Create a connection to the database
conn = s2.connect(
    host=db_host, port=db_port, user=db_user, password=db_password, database=db_database
)


def get_embedding(text: str) -> List[float]:
    """Get the embedding for the given text using Google GenAI API.
    Args:
        text (str): The text to be embedded.
    Returns:
        List[float]: The embedding vector for the text.
    """
    client = genai.Client(api_key=api_key)
    result = client.models.embed_content(
        model="gemini-embedding-exp-03-07", contents=text
    )
    return result.embeddings[0].values


def find_closest_match(embedding: List[float]) -> List[str]:
    """Find the closest match in the database for the given embedding.
    Args:
        embedding (List[float]): The embedding vector to search for.
    Returns:
        List[str]: A list of matching processed outputs from the database.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            """
SELECT processed_output FROM embeddings WHERE (embedding <*> ((%s):>VECTOR(%s))) > 0.95 LIMIT 1;
            """,
            (json.dumps(embedding), len(embedding)),
        )
        result = cursor.fetchone()
        return result


def cached_fact_check(query: str) -> dict:
    """Check the cache for a similar query and return the result if found.
    If not found, perform a fact check and store the result in the cache.
    Args:
        query (str): The query to be fact-checked.
        request_id (str | None): Optional request ID for tracking.
    Returns:
        dict: A dictionary containing the results of the fact check.
    """
    # Get the embedding for the query
    embedding = get_embedding(query)

    # Find the closest match in the database
    result = find_closest_match(embedding)
    if result:
        print("Found a match in the database.")
        return json.loads(result[0])

    fact_check_result = fact_check(query)
    # If no match is found, store the query and its embedding in the database
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO embeddings (original_text, embedding, processed_output)
            VALUES (%s, (%s:>VECTOR(%s)), %s);
        """,
            (
                query,
                json.dumps(embedding),
                len(embedding),
                json.dumps(fact_check_result),
            ),
        )
    conn.commit()
    return fact_check_result
