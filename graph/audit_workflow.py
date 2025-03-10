from textwrap import dedent
from graph.workflow_state import WorkflowState
from graph.get_ai_client import get_ai_client
from graph.workflow_state import AuditResultPydantic
from logging_config import log_execution_time, configure_logging

logger = configure_logging()

system_prompt = dedent(
    """
    We are running a workflow to match software aliases to CPE records. Your only task is to determine if the provided CPE match reasonably aligns with the software alias.

    Understanding CPE Matching:
    - A CPE record uniquely describes a software product.
    - CPE records follow this format: cpe:<cpe_version>:<part>:<vendor>:<product>:<version>:<update>:<edition>:<language>:<sw_edition>:<target_sw>:<target_hw>:<other>.
    - CPE records sometimes contain wildcards (*) to indicate that the CPE can match multiple versions.
    
    Respond with a simple JSON object:    
    ```json
    {
        "restart": true/false,
        "reasoning": "Brief explanation of your decision"
    }    
    ```

    Set "restart" to true if the match is clearly incorrect and we should look for a better match.
    Set "restart" to false if the match is reasonable and acceptable.

    Examples:

    Example 1:
    Software Alias: "Microsoft Office 2019"
    CPE: "cpe:2.3:a:microsoft:office:2019:*:*:*:*:*:*:*"
    Response: {"restart": false, "reasoning": "The CPE correctly identifies Microsoft as the vendor, Office as the product, and 2019 as the version."}

    Example 2:
    Software Alias: "Adobe Acrobat Reader DC"
    CPE: "cpe:2.3:a:mozilla:firefox:96.0:*:*:*:*:*:*:*"
    Response: {"restart": true, "reasoning": "The CPE is for Mozilla Firefox, which is completely different from Adobe Acrobat Reader DC."}

    Example 3:
    Software Alias: "Oracle Java 8 Update 301"
    CPE: "cpe:2.3:a:oracle:jdk:1.8.0:update301:*:*:*:*:*:*"
    Response: {"restart": false, "reasoning": "The CPE correctly identifies Oracle as the vendor and Java 8 Update 301 (represented as 1.8.0:update301)."}
    """
)

user_prompt = dedent(
    """
    ### Software Alias:
    "{software_alias}"

    ### CPE Match:
    {cpe_id}

    ### Inference Reasoning of the match:
    {inference_reasoning}

    ### Task:
    Does this CPE match reasonably align with the software alias? 
    Return only JSON with your decision to restart or not.
    """
)


async def audit_workflow(state: WorkflowState) -> WorkflowState:
    """
    Quickly audits the current match and determines if the workflow should be restarted.
    """

    software_alias = state.get("software_alias", "")
    cpe_matches = state.get("cpe_matches", {})
    attempts = state.get("attempts", 0)
    exact_match = state.get("exact_match")
    best_match = cpe_matches.get("best_match", {}) if cpe_matches else {}

    # Use exact match if available, otherwise use best match
    cpe_id = exact_match if exact_match else best_match.get("cpe_id")

    inference_reasoning = (
        best_match.get("reasoning", "")
        if best_match
        else "The product and version aligned with the software alias"
    )

    if not cpe_id:
        return {
            **state,
            "audit_result": {
                "restart": True,
                "reasoning": "No exact match or best match",
            },
            "attempts": attempts + 1,
        }

    formatted_user_prompt = user_prompt.format(
        software_alias=software_alias,
        cpe_id=cpe_id,
        inference_reasoning=inference_reasoning,
    )

    with log_execution_time(logger, f"Auditing match for alias: {software_alias}"):
        try:
            completion_function, model_args, parse_response_function = get_ai_client(
                AuditResultPydantic,
                system_prompt,
                formatted_user_prompt,
            )

            response = await completion_function(**model_args)
            audit_result = parse_response_function(response, AuditResultPydantic)

            logger.info(f"Audit result for {software_alias}: {audit_result}")
            restart = audit_result.get("restart", False)
            return {
                **state,
                "audit_result": audit_result,
                "attempts": attempts + 1 if restart else attempts,
            }

        except Exception as e:
            logger.error(f"Error auditing match for alias: {software_alias}; {e}")
            return {
                **state,
                "audit_result": {
                    "restart": True,
                    "reasoning": f"Error during audit: {str(e)}",
                },
                "attempts": attempts + 1,
                "error": str(e),
            }
