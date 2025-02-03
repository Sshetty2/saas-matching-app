import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

def generate_nvd_query_text(software_alias):
    """Please generate a clean, base query for the NVD API using a system prompt for formatting."""

    # System prompt to enforce strict response formatting
    system_prompt = """
    Please extract software names for querying the National Vulnerability Database (NVD).
    Your task is to simplify software alias names for efficient database searches.

    **Formatting Rules:**
    - Remove version numbers unless they represent a release year.
    - Refrain from removing important data from product names unless it is explicitly a version number.
    - Retain vendor and product names.
    - Remove platform specifiers such as "x86" or "x64" or "resdistributable".
    - Remove dashes and other non-alphanumeric characters while retaining the product name.
    - Always return only the cleaned query text, with no additional commentary.

    **Examples:**
    - Input: Microsoft SQL Server 2008 Setup Support Files 10.1.2731.0  
      Output: Microsoft SQL Server 2008 Setup Support Files

    - Input: Microsoft ASP.NET Core 3.1.2 Shared Framework (x86) 3.1.2.0  
      Output: Microsoft ASP.NET Core 3.1 Shared Framework

    - Input: SQL Server 2012 Database Engine Shared 11.3.6020.0  
      Output: SQL Server 2012 Database Engine Shared

    - Input: MySQL Installer - Community 1.4.32.0  
      Output: MySQL Installer Community

    **Return only the cleaned query text. No explanations, no extra output.**
    """

    user_prompt = f"Extract query text from: {software_alias}"

    response = client.chat.completions.create(
        model=os.getenv("AI_MODEL"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=.3  # Ensures deterministic output
    )

    return response.choices[0].message.content.strip()
