from textwrap import dedent
from graph.workflow_state import WorkflowState
import logging
from logging_config import log_execution_time
from graph.get_ai_client import get_ai_client
from graph.workflow_state import SoftwareInfoPydantic
from textwrap import dedent
import json

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
    - **Multi-word vendor and product names must be formatted with underscores (`_`).** Example: `Adobe Acrobat Reader → adobe_acrobat_reader`.

    ### **Vendor Inference Rules:**
    - Do your best not to meaningfully change the vendor name so that it is not the same vendor mentioned in the alias.
    - If the vendor is **explicitly mentioned**, return it as is.
    - If the vendor is **not provided but can be inferred**, return the inferred vendor.
    - If the vendor **cannot be determined**, return `"N/A"`.

    ### **Product Name Generalization Rules:**
    - Do your best not to meaningfully change the product name so that it is not the same product mentioned in the alias.
    - **If the product has a known abbreviation, return its full name.**
      - Example: `"ePO"` → `"epolicy_orchestrator"`
      - Example: `"VS Code"` → `"visual_studio_code"`
    - If uncertain, return the product name **as written**.

    **Output Requirements:**
    - Return **only valid JSON** (no extra text, explanations, or markdown).
    - If a value is **missing or unclear**, return `"N/A"`.
    - Ensure **multi-word names use underscores** instead of spaces.

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
        "vendor": "jetbrains",
        "product": "pycharm",
        "version": "2019.3",
        "inference_reasoning": "N/A"
    }
    ```

    #### **Example 2 (Vendor Inferred)**
    **Software Alias:** `'WinRAR 4.01 (32-bit) (v4.01.0)'`
    **Expected Output:**
    ```json
    {
        "vendor": "rarlab",
        "product": "winrar",
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

    #### **Example 4 (Product Abbreviation Generalization)**
    **Software Alias:** `'McAfee ePO 5.10'`
    **Expected Output:**
    ```json
    {
        "vendor": "mcafee",
        "product": "epolicy_orchestrator",
        "version": "5.10",
        "inference_reasoning": "McAfee ePO is commonly known as ePolicy Orchestrator"
    }
    ```

    #### **Example 5 (Underscore Formatting for Multi-Word Names)**
    **Software Alias:** `'Adobe Acrobat Reader DC 2023'`
    **Expected Output:**
    ```json
    {
        "vendor": "adobe",
        "product": "acrobat_reader_dc",
        "version": "2023",
        "inference_reasoning": "Formatted multi-word product name with underscores"
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

user_prompt_requery = dedent(
    """
    ### Reattempting Parsing: Previous Query Returned No Results
    
    The initial attempt to extract vendor, product, and version from `{software_alias}` resulted in a **failed database query**.
    
    **Number of Attempts:** `{query_attempts}`
    
    **Previous Parse Attempt Results (PLEASE DO NOT REPEAT THESE RESULTS):**
    ```json
    {parse_results}
    ```

    ### **Instructions:**
    - **Re-evaluate the software alias** to extract a **more general vendor and/or product** that may yield better search results in the database.
    - If the vendor was not inferred, try switching the vendor and product.
    - Try not to change the product or vendor too much but still make it more general to fit more queries.
    - Return **only valid JSON** in the required format.
    """
)


async def parse_alias(state: WorkflowState) -> WorkflowState:
    """Generates a clean, base query for the NVD API using a system prompt for formatting."""

    software_alias = state.get("software_alias", "")
    query_attempts = state.get("query_attempts", 0)
    parse_results = state.get("parse_results", [])
    product_vector_store = state.get("product_vector_store", None)
    vendor_vector_store = state.get("vendor_vector_store", None)

    if query_attempts:
        formatted_user_prompt = user_prompt_requery.format(
            software_alias=software_alias,
            query_attempts=query_attempts,
            parse_results=parse_results,
        )
        logger.info(f"Reattempting Software Alias Parsing for {software_alias}")
    else:
        formatted_user_prompt = user_prompt.format(
            software_alias=software_alias,
        )
        logger.info(f"Parsing Software Alias for {software_alias}")

    completion_function, model_args, parse_response_function = get_ai_client(
        SoftwareInfoPydantic, system_prompt, formatted_user_prompt, mode="parse"
    )

    with log_execution_time(logger, f"Parsing Software Alias {software_alias}"):
        try:
            response = await completion_function(**model_args)
            result = parse_response_function(response, SoftwareInfoPydantic)

            print("RESULT", result, formatted_user_prompt)

            vendor = result.get("vendor", "")
            product = result.get("product", "")

            if vendor != "" and vendor != "N/A":
                vendor_result = await vendor_vector_store.asimilarity_search(
                    vendor, k=1
                )
                if vendor_result:
                    vendor_result = vendor_result[0].page_content
                    result = {
                        **result,
                        "vendor": vendor_result,
                    }

            if product != "" and product != "N/A":
                product_result = await product_vector_store.asimilarity_search(
                    product, k=1
                )
                if product_result:
                    product_result = product_result[0].page_content
                    result = {
                        **result,
                        "product": product_result,
                    }

        except Exception as e:
            logger.error(f"Parsing error for alias: {software_alias}; {e}")
            return {
                "__end__": True,
                **state,
                "error": str(e),
                "info": "Error parsing alias",
            }

    logger.info(f"Parsed alias: {result}")
    parse_results.append(result)
    return {**state, "software_info": result, "parse_results": parse_results}
