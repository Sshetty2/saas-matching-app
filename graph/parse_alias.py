import os
import json
from textwrap import dedent
from graph.workflow_state import WorkflowState
import logging
from logging_config import log_execution_time
from openai import AsyncOpenAI
from dotenv import load_dotenv
from graph.get_ai_client import get_ai_client

load_dotenv()

logger = logging.getLogger(__name__)


async def parse_alias(state: WorkflowState) -> WorkflowState:
    """Please generate a clean, base query for the NVD API using a system prompt for formatting."""

    system_prompt = dedent(
        f"""
        We are working on matching software alias names to known product records in a database. 
        To do this, we need to extract the **vendor**, **product**, and **version** from each software alias.

        - **Vendor** is the company or entity that created the software.
        - **Product** is the name of the software itself.
        - **Version** is the specific release number (if available).

        This information will be used to **query a database for similar records** using SQL, so accuracy and generalization are important.  
        If any value is **unclear or missing**, return **"N/A"** instead of making an assumption.

        The output should be a JSON object with the following keys:
        - **software_alias**: The original software alias string.
        - **vendor**: The vendor name.
        - **product**: The product name.
        - **version**: The version number.

        ---

        ### **Examples for Reference**
        #### **Example 1**
        Software Alias: 'jetbrains pycharm 2019.3'
        Extracted Output:
        {{
            "software_alias": "jetbrains pycharm 2019.3",
            "vendor": "JetBrains",
            "product": "PyCharm",
            "version": "2019.3"
        }}
        #### **Example 2**
        Software Alias: 'WinRAR 4.01 (32-bit) (v4.01.0)'
        Extracted Output:
        {{
            "software_alias": "WinRAR 4.01 (32-bit) (v4.01.0)",
            "vendor": "RARLAB",
            "product": "WinRAR",
            "version": "4.01"
        }}
        #### **Example 3**
        Software Alias: 'francisco cifuentes vote for tt news 1.0.1'
        Extracted Output:
        {{
            "software_alias": "francisco cifuentes vote for tt news 1.0.1",
            "vendor": "N/A",
            "product": "N/A",
            "version": "1.0.1"
        }}
        """
    )

    software_alias = state.get("software_alias", "")
    user_prompt = f"Extract query text from: {software_alias}"

    model, completion_function = get_ai_client()

    with log_execution_time(logger, f"Parsing Software Alias {software_alias}"):
        for attempt in range(3):
            try:
                response = await completion_function(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"},
                )

                result = response.choices[0].message.content.strip()
                result = json.loads(result)
                break
            except Exception as e:
                logger.error(f"Error parsing alias (attempt {attempt+1}/3): {e}")
                if attempt == 2:
                    return {
                        "__end__": True,
                        **state,
                        "error": str(e),
                        "info": "Error parsing alias after 3 attempts",
                    }

    logger.info(f"Parsed alias: {result}")
    return {**state, "software_info": result}
