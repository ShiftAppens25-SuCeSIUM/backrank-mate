from .google_fact_check import get_reviews_text
from .reviews_processing import process_reviews

def fact_check(query: str) -> dict:
    """
    Perform a fact check on the given query using Google Fact Check API and process the reviews.
    
    Args:
        query (str): The query to be fact-checked.
        
    Returns:
        dict: A dictionary containing the results of the fact check.
    """
    reviews = get_reviews_text(query)
    result = process_reviews(query, reviews)
    return result

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()