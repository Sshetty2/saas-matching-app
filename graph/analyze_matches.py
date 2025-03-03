from textwrap import dedent
from graph.workflow_state import WorkflowState, AnalysisResultPydantic
from graph.get_ai_client import get_ai_client
from logging_config import log_execution_time
from graph.format_utils import format_software_info, format_cpe_matches
import logging
import json

logger = logging.getLogger(__name__)

system_prompt = dedent(
    """
    We are trying to match a software alias name to a CPE record.
    Please try to determine whether the given CPE records match the query software name accurately.
    The CPE records contain the product name and sometimes the version number along with wildcards that indicate a match to other software.
    *It should be quite clear if the CPE matches the software name AND version. 
    A confidence score 70 and above should only be given if the software alias matches with the vendor, product name, AND version exactly with the CPE.*

    ### Evaluation Criteria:
    - An **exact match** requires the product name and version to be identical.
    - A **close match** has SLIGHT differences in the version but is still relevant.
    - Provide a **confidence rating** (0-100%) based on the closeness of the match.

    ### JSON Response Format:
    ```json
    {
        "match_type": "Exact Match / Close Match / Unsure / No Match",
        "confidence_score": 0-100,
        "matched_cpe": "CPE Name",
        "reasoning": "Brief explanation of why this match was chosen and an explanation of the confidence score given"


    ###Example:
    Top 3 CPE results:
    ```json
    [
        "cpe:2.3:a:microsoft:visual_c\\+\\+:2008:sp1:*:*:redistributable_package:*:*:*",
        "cpe:2.3:a:microsoft:visual_c\\+\\+:2010:sp1:*:*:redistributable_package:*:*:*",
        "cpe:2.3:a:microsoft:visual_c\\+\\+:2005:sp1:*:*:redistributable_package:*:*:*"
    ]
    ```

    Software alias:
    "NuGet 6.0.4"

    Output:
    ```json
    {
        "match_type": "Close Match",
        "confidence_score": 60,
        "matched_cpe": "cpe:2.3:a:microsoft:nuget:6.4.0:*:*:*:*:*:*:*",
        "reasoning": "The product name and vendor are the same, but the version number is different between 6.0.4 and 6.4.0"
    }
    ```

    Software alias:
    "Microsoft Visual C++ 2008 Redistributable - x86 9.0.30729.4974"

    Output:
    ```json
    {
        "match_type": "Exact Match",
        "confidence_score": 100,
        "matched_cpe": "cpe:2.3:a:microsoft:visual_c\\+\\+:2008:sp1:*:*:redistributable_package:*:*:*",
        "reasoning": "The version number and product name are identical."
    }
    ```

    Please do not return anything except valid JSON.
    """
)


async def analyze_matches(state: WorkflowState) -> WorkflowState:
    top_matches = state.get("top_matches", [])
    software_alias = state.get("software_alias", "")
    software_info = state.get("software_info", {})

    formatted_software_info = format_software_info(software_info)
    formatted_cpe_matches = format_cpe_matches(top_matches)

    user_prompt = dedent(
        f"""
        ### The original software alias name is: "{software_alias}"

        ### The software info is:
        {formatted_software_info}

        ### The top 3 CPE results from cosine similarity search:
        {formatted_cpe_matches}

        ### Please analyze these results and determine the best match type and confidence score.
        Return only JSON output.
        """
    )

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
                AnalysisResultPydantic, system_prompt, user_prompt, mode="analysis"
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
    return {**state, "cpe_results": [], "cpe_match": result}
