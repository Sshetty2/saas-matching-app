from textwrap import dedent
from graph.workflow_state import WorkflowState
import logging
from logging_config import log_execution_time
from graph.get_ai_client import get_ai_client
from graph.workflow_state import SoftwareInfoPydantic

logger = logging.getLogger(__name__)


async def parse_alias(state: WorkflowState) -> WorkflowState:
    """Generates a clean, base query for the NVD API using a system prompt for formatting."""

    system_prompt = dedent(
        f"""
        We are working on matching software alias names to known product records in a database. 
        To do this, we need to extract the **vendor**, **product**, and **version** from each software alias.
        The vendor, product, and version should be generalized such that DB queries can be made based on similar records.

        - **Vendor** is the company or entity that created the software.
        - **Product** is the name of the software itself.
        - **Version** is the specific release number (if available).

        This information will be used to **query a database for similar records** using SQL, so accuracy and generalization are important.  
        If any value is **unclear or missing**, return **"N/A"**, though it may be neccessary to infer the vendor name based on the product.
        Please only return the vendor, product, and version and no supporting information even if inferences are made.

        The output should be a JSON object with the following keys:
        - **vendor**: The vendor name.
        - **product**: The product name.
        - **version**: The version number.

        ---

        ### **Examples for Reference**
        #### **Example 1**
        Software Alias: 'jetbrains pycharm 2019.3'
        Extracted Output:
        {{
            "vendor": "JetBrains",
            "product": "PyCharm",
            "version": "2019.3",
            "inference_reasoning": "N/A"
        }}
        #### **Example 2**
        Software Alias: 'WinRAR 4.01 (32-bit) (v4.01.0)'
        Extracted Output:
        {{
            "vendor": "RARLAB",
            "product": "WinRAR",
            "version": "4.01",
            "inference_reasoning": "RARLAB was inferred as the vendor of WinRAR"
        }}
        #### **Example 3**
        Software Alias: 'francisco cifuentes vote for tt news 1.0.1'
        Extracted Output:
        {{
            "vendor": "N/A",
            "product": "N/A",
            "version": "1.0.1",
            "inference_reasoning": "N/A"
        }}
        """
    )

    software_alias = state.get("software_alias", "")
    user_prompt = dedent(
        f"""
        ### Please extract the vendor, product, and version from the following software alias: 
        ##### {software_alias}
        """
    )
    logger.info(f"Parsing Software Alias for {software_alias}")

    completion_function, model_args, parse_response_function = get_ai_client(
        SoftwareInfoPydantic, system_prompt, user_prompt, mode="parse"
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
