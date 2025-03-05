from textwrap import dedent
from graph.workflow_state import WorkflowState, AnalysisResultPydantic
from graph.get_ai_client import get_ai_client
from logging_config import log_execution_time, configure_logging
from graph.format_utils import format_software_info, format_cpe_matches
import json
import inspect

logger = configure_logging()

system_prompt = dedent(
    """
    We are trying to match a software alias name to a CPE record.
    Your goal is to determine whether the given CPE records accurately match the software name.

    ### **Understanding CPE Records:**
    - A **CPE (Common Platform Enumeration)** record describes software uniquely.
    - The **vendor, product, and version fields** help identify a match.
    - Some **CPE records contain wildcards (`*`)**, meaning they match multiple versions.

    ### **How to Evaluate a Match:**
    1. **Exact Match** (100% confidence)  
       - The vendor, product, and version are **identical** between the software alias and the CPE.
    3. **General Match** (85-95% confidence)  
       - If the software alias has a specific version (`7.0.2`), but the CPE record uses a wildcard (`7.0.*`), **prefer the wildcard match**.
    2. **Possible Match** (50-85% confidence)  
       - The vendor and product match, but the version has **minor differences** (e.g., `6.0.4` vs. `6.4.0`).
    4. **No Match or Unclear Match** (0-50% confidence)  
       - If the vendor, product, or version is significantly different.

    ### **JSON Response Format:**
    ```json
    {
        "match_type": "Exact Match / General Match / Possible Match / No Match",
        "confidence_score": 0-100,
        "matched_cpe": "CPE Name",
        "reasoning": "Brief explanation of why this match was chosen and an explanation of the confidence score given."
    }
    ```

    ### **Example Matches**
    **Example 1:**  
    **Software alias:** `"NuGet 6.0.4"`  
    **Top 3 CPE results:**
    ```json
    [
        "cpe:2.3:a:microsoft:nuget:6.1.0:*:*:*:*:*:*:*",
        "cpe:2.3:a:microsoft:nuget:6.4.0:*:*:*:*:*:*:*",
        "cpe:2.3:a:microsoft:nuget:6.6.0:*:*:*:*:*:*:*"
    ]
    ```
    **Expected Output:**
    ```json
    {
        "match_type": "Close Match",
        "confidence_score": 60,
        "matched_cpe": "cpe:2.3:a:microsoft:nuget:6.4.0:*:*:*:*:*:*:*",
        "reasoning": "The product and vendor match, but the version is slightly different between 6.0.4 and 6.4.0."
    }
    ```

    **Example 2 (Wildcard Matching Priority):**  
    **Software alias:** `"Microsoft Office 7.0.2"`  
    **Top 3 CPE results:**
    ```json
    [
        "cpe:2.3:a:microsoft:office:7.0:*:*:*:*:*:*:*",
        "cpe:2.3:a:microsoft:office:7.0.1:*:*:*:*:*:*:*",
        "cpe:2.3:a:microsoft:office:7.0.3:*:*:*:*:*:*:*"
    ]
    ```
    **Expected Output:**
    ```json
    {
        "match_type": "General Match",
        "confidence_score": 85,
        "matched_cpe": "cpe:2.3:a:microsoft:office:7.0:*:*:*:*:*:*:*",
        "reasoning": "The CPE version 7.0.* is a broader match that covers the alias version 7.0.2."
    }
    ```

    **Please return only valid JSON. Do not include any extra text.**
    """
)

user_prompt = dedent(
    """
    ### Software Alias Name:
    "{software_alias}"

    ### Software Info:
    {formatted_software_info}

    ### Top 3 CPE Results (Cosine Similarity Search):
    {formatted_cpe_matches}

    ### Matching Rules Reminder:
    - **Exact Match (100%)**: Vendor, product, and version are identical.
    - **General Match (85-95%)**: Minor differences in version, same product/vendor.
    - **Possible Match (50-85%)**: CPE uses a **wildcard (`*`)**, covering multiple versions.
    - **No Match (0-50%)**: Vendor, product, or version significantly differs.

    ### **Return JSON Only. No extra text.**
    """
)


async def analyze_matches(state: WorkflowState) -> WorkflowState:
    top_matches = state.get("top_matches", [])
    software_alias = state.get("software_alias", "")
    software_info = state.get("software_info", {})

    formatted_software_info = format_software_info(software_info)
    formatted_cpe_matches = format_cpe_matches(top_matches)

    formatted_user_prompt = user_prompt.format(
        software_alias=software_alias,
        formatted_software_info=formatted_software_info,
        formatted_cpe_matches=formatted_cpe_matches,
    )

    attempts = state.get("attempts", 0)

    if not top_matches:
        return {
            "__end__": True,
            **state,
            "match_type": "No Match",
            "info": "No matches found",
        }

    with log_execution_time(logger, f"Analyzing Matches for alias: {software_alias}"):
        try:
            completion_function, model_args, parse_response_function = get_ai_client(
                AnalysisResultPydantic,
                system_prompt,
                formatted_user_prompt,
                mode="analysis",
            )

            response = await completion_function(**model_args)

            result = parse_response_function(response, AnalysisResultPydantic)

        except Exception as e:
            logger.error(f"Error analyzing matches for alias: {software_alias}; {e}")
            return {
                "__end__": True,
                **state,
                "match_type": "No Match",
                "error": str(e),
                "info": "Error analyzing matches",
            }

    logger.info(f"Analyzed matches for {software_alias}: {result}")
    ## Clear cpe results to trim output body
    return {**state, "cpe_results": [], "cpe_match": result, "attempts": attempts + 1}
