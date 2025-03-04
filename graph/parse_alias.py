from textwrap import dedent
from graph.workflow_state import WorkflowState
import logging
from logging_config import log_execution_time
from graph.get_ai_client import get_ai_client
from graph.workflow_state import SoftwareInfoPydantic

logger = logging.getLogger(__name__)


system_prompt = dedent(
    """
    We are working on matching software alias names to known product records in a database. 
    To do this, we need to extract the **vendor**, **product**, and **version** from each software alias.
    
    ### **Instructions:**
    - **Vendor** is the company or entity that created the software.
    - **Product** is the name of the software itself.
    - **Version** is the specific release number (if available).
    - The vendor, product, and version should be **generalized** to ensure database queries return similar records.

    ### **Vendor Inference Rules:**
    - If the vendor is **explicitly mentioned**, return it as is.
    - If the vendor is **not provided but can be inferred**, return the inferred vendor.
    - If the vendor **cannot be determined**, return N/A.

    **Output Requirements:**
    - Return **only valid JSON** (no extra text, explanations, or markdown).
    - If a value is **missing or unclear**, return N/A.

    ### **JSON Response Format:**
    ```json
    {
        "vendor": "<parsed vendor or N/A>",
        "product": "<parsed product or N/A>",
        "version": "<parsed version or N/A>",
        "inference_reasoning": "<If vendor was inferred, explain briefly. Otherwise, return N/A>"
    }
    ```

    ---

    ### **Examples for Reference**
    
    #### **Example 1 (Standard Parsing)**
    **Software Alias:** `'jetbrains pycharm 2019.3'`
    **Expected Output:**
    ```json
    {
        "vendor": "JetBrains",
        "product": "PyCharm",
        "version": "2019.3",
        "inference_reasoning": "N/A"
    }
    ```

    #### **Example 2 (Vendor Inferred)**
    **Software Alias:** `'WinRAR 4.01 (32-bit) (v4.01.0)'`
    **Expected Output:**
    ```json
    {
        "vendor": "RARLAB",
        "product": "WinRAR",
        "version": "4.01",
        "inference_reasoning": "RARLAB was inferred as the vendor of WinRAR"
    }
    ```
    
    #### **Example 3 (Unclear Vendor)**
    **Software Alias:** `'francisco cifuentes vote for tt news 1.0.1'`
    **Expected Output:**
    ```json
    {
        "vendor": "N/A",
        "product": "N/A",
        "version": "1.0.1",
        "inference_reasoning": "N/A"
    }
    ```

    **Please return only valid JSON. No extra text, explanations, or formatting.**
    """
)

user_prompt = dedent(
    """
    ### Please extract the vendor, product, and version from the following software alias:
    Software Alias: `{software_alias}`

    - Ensure that the vendor is inferred **if possible**.
    - Return **only valid JSON** in the required format.
    """
)


async def parse_alias(state: WorkflowState) -> WorkflowState:
    """Generates a clean, base query for the NVD API using a system prompt for formatting."""

    software_alias = state.get("software_alias", "")

    logger.info(f"Parsing Software Alias for {software_alias}")

    formatted_user_prompt = user_prompt.format(software_alias=software_alias)

    completion_function, model_args, parse_response_function = get_ai_client(
        SoftwareInfoPydantic, system_prompt, formatted_user_prompt, mode="parse"
    )

    with log_execution_time(logger, f"Parsing Software Alias {software_alias}"):
        try:
            response = await completion_function(**model_args)
            result = parse_response_function(response, SoftwareInfoPydantic)

        except Exception as e:
            logger.error(f"Parsing error for alias: {software_alias}; {e}")
            return {
                "__end__": True,
                **state,
                "error": str(e),
                "info": "Error parsing alias",
            }

    logger.info(f"Parsed alias: {result}")
    return {**state, "software_info": result}
