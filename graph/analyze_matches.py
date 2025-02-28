import os
import json
from textwrap import dedent
from ollama import AsyncClient
from graph.workflow_state import WorkflowState, AnalysisResultPydantic
from graph.get_ai_client import get_ai_client
from logging_config import log_execution_time
import logging

logger = logging.getLogger(__name__)

use_local_model = os.getenv("USE_LOCAL_MODEL", "False").lower() == "true"

system_prompt = dedent(
    """
    We are trying to match a software alias name to a CPE record.
    Please try to determine whether the given CPE records match the query software name accurately.
    The CPE records contain the product name and sometimes the version number along with wildcards that indicate a match to other software.
    It should be pretty obvious if the CPE matches the software name but at times it may not be very clear so you should adjust your confidence score accordingly.

    ### Evaluation Criteria:
    - An **exact match** requires the product name and version to be identical.
    - A **close match** has slight differences in the version but is still relevant.
    - Provide a **confidence rating** (0-100%) based on the closeness of the match.

    ###Example:
    Top 3 CPE results:
    [
        "cpe:2.3:a:microsoft:visual_c\\+\\+:2008:sp1:*:*:redistributable_package:*:*:*",
        "cpe:2.3:a:microsoft:visual_c\\+\\+:2010:sp1:*:*:redistributable_package:*:*:*",
        "cpe:2.3:a:microsoft:visual_c\\+\\+:2005:sp1:*:*:redistributable_package:*:*:*"
    ]

    Software alias:
    "Microsoft Visual C++ 2008 Redistributable - x86 9.0.30729.4974"

    #### Output:
        {
        "software_alias": "Microsoft Visual C++ 2008 Redistributable - x86 9.0.30729.4974",
        "match_type": "Exact Match",
        "confidence_score": 100,
        "matched_cpe": "cpe:2.3:a:microsoft:visual_c\\+\\+:2008:sp1:*:*:redistributable_package:*:*:*",
        "reasoning": "The version number and product name are identical."
        }

    ### JSON Response Format:
    {
        "software_alias": "Original software name",
        "match_type": "Exact Match / Close Match / No Match",
        "confidence_score": 0-100,
        "matched_cpe": "CPE Name",
        "reasoning": "Brief explanation of why this match was chosen"
    }

    Do not return anything except valid JSON.
    """
)


async def analyze_matches(state: WorkflowState) -> WorkflowState:
    top_matches = state.get("top_matches", [])
    software_alias = state.get("software_alias", "")

    user_prompt = dedent(
        f"""
        The original software alias name was: "{software_alias}"

        The top 3 CPE results from cosine similarity search:
        {top_matches}

        Analyze these results and determine the best match type and confidence score.
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
            model, completion_function = get_ai_client()

            if use_local_model:
                args = {
                    "format": AnalysisResultPydantic.model_json_schema(),
                    "stream": False,
                }
            else:
                args = {
                    "temperature": 0.5,
                    "response_format": {"type": "json_object"},
                }

            response = await completion_function(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **args,
            )

            if use_local_model:
                analysis_result = AnalysisResultPydantic.model_validate_json(
                    response.message.content
                )

                result = analysis_result.model_dump()
            else:
                result_text = response.choices[0].message.content.strip()

                try:
                    result = json.loads(result_text)
                except json.JSONDecodeError:
                    import re

                    json_match = re.search(
                        r"({.*})", result_text.replace("\n", ""), re.DOTALL
                    )
                    if json_match:
                        result = json.loads(json_match.group(1))
                    else:
                        raise ValueError(
                            f"Could not parse JSON from model response for alias: {software_alias}"
                        )

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
    ## Clear cpe results and db connection to trim output body
    return {**state, "cpe_results": [], "db_connection": None, "cpe_match": result}
