from openai import OpenAI
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_cpe_matches(query_text, cpe_results):
    """Please determine if a CPE match is exact or approximate and return structured JSON output."""


    # Format the CPE results as a JSON string
    cpe_results_str = json.dumps(cpe_results, indent=2)

    # System prompt to ensure structured JSON response
    system_prompt = """
    You are an assistant that evaluates software component matches in the National Vulnerability Database (NVD).
    Your task is to determine whether the given CPE records match the query software name accurately.

    **Evaluation Criteria:**
    - An **exact match** requires the product name and version to be identical.
    - A **close match** has slight differences in the version but is still relevant.
    - Provide a **confidence rating** (0-100%) based on the closeness of the match.

    **Response Format (Strictly JSON Only):**
    ```json
    {
        "query": "Original software name",
        "best_match": {
            "match_type": "Exact Match / Close Match / No Match",
            "confidence_score": 0-100,
            "matched_cpe": "CPE Name",
            "title": "CPE Title",
            "reasoning": "Brief explanation of why this match was chosen"
        }
    }
    ```

    **Do not return anything except valid JSON.**
    """

    # User message (software query and CPE results to analyze)
    user_prompt = f"""
    The original software query was: "{query_text}"

    The top 3 CPE results from cosine similarity search:
    {cpe_results_str}

    Analyze these results and determine the best match type and confidence score.
    Return only JSON output.
    """

    response = client.chat.completions.create(
        model=os.getenv("AI_MODEL"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,  # Slight flexibility while keeping structure
        response_format={ "type": "json_object" }  # Forces JSON output
    )

    # Parse JSON response
    try:
        structured_output = json.loads(response.choices[0].message.content.strip())
    except json.JSONDecodeError:
        structured_output = {"error": "Invalid JSON response from GPT"}

    return structured_output