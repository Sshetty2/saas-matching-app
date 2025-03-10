from textwrap import dedent
from graph.workflow_state import WorkflowState, AnalysisResultPydantic
from graph.get_ai_client import get_ai_client
from logging_config import log_execution_time, configure_logging
from graph.format_utils import format_software_info, format_cpe_results

logger = configure_logging()

system_prompt = dedent(
    """
    We are matching software alias names to CPE (Common Platform Enumeration) records. Your task is to identify the best possible CPE match and highlight any alternative matches that could be relevant. Return only the CPE ID for the best match and possible matches, not the full CPE record.

    Understanding CPE Matching:
    - A CPE record uniquely describes a software product.
    - CPE records follow this format: cpe:<cpe_version>:<part>:<vendor>:<product>:<version>:<update>:<edition>:<language>:<sw_edition>:<target_sw>:<target_hw>:<other>.
    - CPE records sometimes contain wildcards (*) to indicate that the CPE can match multiple versions.
    
    How to Evaluate Matches:
    1. Prioritize the exact version from the software alias if available.
    2. If the exact version from the software alias appears in the CPE records, select it as the best match.
    3. PREFER WILDCARD (*) VERSIONS FOR UPDATES AND EDITIONS OVER PATCH RELEASES.
    4. If the software alias specifies a version such as "7.0", select 7.0.* rather than a specific patch release like 7.0.104.
    5. Prefer "cpe:2.3:a:apache:tomcat:7.0:*:*:*:*:*:*:*" over "cpe:2.3:a:apache:tomcat:7.0.104:*:*:*:*:*:*:*".
    6. Ensure vendor and product match first before considering version.
    
    Example:
    Prefer "cpe:2.3:a:apache:tomcat:7.0:*:*:*:*:*:*:*"
    Do not select "cpe:2.3:a:apache:tomcat:7.0.104:*:*:*:*:*:*:*" unless no wildcard version exists.
    If multiple wildcard-based matches exist, select the most general one.

    Example:
    Prefer "cpe:2.3:a:apache:tomcat:7.*:*:*:*:*:*:*:*"
    Avoid selecting "cpe:2.3:a:apache:tomcat:7.0.2:*:*:*:*:*:*:*" unless no wildcard exists.
    Select a patch release only if no wildcard version is available.
    If no 7.0.* wildcard version exists but 7.0.104 is available, select it as a fallback.

    Important Rules:
    - Wildcards (*) should always be preferred over patch versions.
    - If an exact version from the software alias exists in CPE, select it.
    - A match is not valid unless both the vendor and product match.
    - If no valid match exists, return an empty best match.
    - Return JSON only with no extra text or explanations.
    
    Return only the ID of the CPE and a reasoning statement for the best match and possible matches.
    If no valid matches exist, return an empty best match.

    Output Instructions:
    1. Return the ID of the CPE and your reasoning for the best match and possible matches as per the format below. 

    Example Output:
    ```json
    {
        "best_match": {
            "id": "523560",
            "reasoning": "Exact match for product name and version."
        },
        "possible_matches": []
    }
    ```

    - If you don't believe that none of the CPE's match the software alias, {"best_match": {}, "possible_matches": []}.
    - If you are confident that there is only one possible match then {"best_match": {id: "...", reasoning: "..."}, "possible_matches": []}.

    **Please return only valid JSON.**
    """
)

user_prompt = dedent(
    """
    Software Alias Name:
    
    "{software_alias}"

    Software Info:
    {formatted_software_info}

    CPE Results (Top Matches from Vector Search):
    {cpe_results}

    Task:
    - Identify the **best** matching CPE record.
    - List **other possible matches** with explanations.
    - RETURN THE ID OF THE CPE AND NOT THE CPE RECORD ITSELF.

    """
)


def find_cpe_by_id(cpe_results, db_id):
    """
    Find a CPE result in the cpe_results array by its ConfigurationsName (CPE ID).

    Args:
        cpe_results (list): List of CPE result objects
        db_id (str): The CPE ID to search for (CPEConfigurationID)
    """
    for cpe in cpe_results:
        db_id_from_cpe_results = cpe.get("CPEConfigurationID")
        cpe_id_from_cpe_results = cpe.get("ConfigurationsName")
        if db_id_from_cpe_results == db_id:
            return cpe_id_from_cpe_results
    return "ERROR: CPE ID not found"


async def analyze_matches(state: WorkflowState) -> WorkflowState:
    cpe_results = state.get("cpe_results", [])
    exact_match = state.get("exact_match", {})

    if not cpe_results or exact_match:
        return state

    software_alias = state.get("software_alias", "")
    software_info = state.get("software_info", {})

    formatted_software_info = format_software_info(software_info)
    formatted_cpe_results = format_cpe_results(cpe_results)

    formatted_user_prompt = user_prompt.format(
        software_alias=software_alias,
        formatted_software_info=formatted_software_info,
        cpe_results=formatted_cpe_results,
    )

    with log_execution_time(logger, f"Analyzing Matches for alias: {software_alias}"):
        try:
            completion_function, model_args, parse_response_function = get_ai_client(
                AnalysisResultPydantic,
                system_prompt,
                formatted_user_prompt,
            )

            response = await completion_function(**model_args)

            result = parse_response_function(response, AnalysisResultPydantic)

            best_match = result.get("best_match", {})
            possible_matches = result.get("possible_matches", [])

            if best_match and "id" in best_match:
                best_match_id = best_match["id"]
                if best_match_id and best_match_id != "N/A":
                    best_match_id = int(best_match_id)
                    cpe_id = find_cpe_by_id(cpe_results, best_match_id)
                    new_best_match = {
                        **best_match,
                        "cpe_id": cpe_id,
                    }
                    result["best_match"] = new_best_match

            processed_possible_matches = []
            if possible_matches:
                for match in possible_matches:
                    if "id" in match:
                        match_id = match["id"]
                        if match_id and match_id != "N/A":
                            match_id = int(match_id)
                            cpe_id = find_cpe_by_id(cpe_results, match_id)
                            new_possible_match = {
                                **match,
                                "cpe_id": cpe_id,
                            }
                            processed_possible_matches.append(new_possible_match)
                result["possible_matches"] = processed_possible_matches

        except Exception as e:
            logger.error(f"Error analyzing matches for alias: {software_alias}; {e}")
            return {
                **state,
                "match_type": "No Match",
                "error": str(e),
                "info": "Error analyzing matches",
            }

    logger.info(f"Analyzed matches for {software_alias}: {result}")
    return {**state, "cpe_matches": result}
