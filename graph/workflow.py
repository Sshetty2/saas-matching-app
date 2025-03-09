from typing import Literal
from langgraph.graph import StateGraph, START, END
from openai import AsyncOpenAI
from graph.workflow_state import WorkflowState
from graph.parse_alias import parse_alias
from graph.query_database import query_database
from graph.analyze_matches import analyze_matches
from graph.find_product_matches import find_product_matches
from logging_config import log_execution_time, configure_logging
import asyncio
import tracemalloc
from config import settings

logger = configure_logging()
tracemalloc.start()

openai_api_key = settings.llm.openai_api_key
openai_client = AsyncOpenAI(api_key=openai_api_key)
retry_attempts = settings.execution.retry_attempts
max_concurrent_workflows = settings.execution.max_concurrent_workflows

workflow_semaphore = asyncio.Semaphore(max_concurrent_workflows)


def should_restart_workflow(state) -> Literal["parse_alias", END]:
    cpe_matches = state.get("cpe_matches", {})
    best_match = cpe_matches.get("best_match", {})
    attempts = state.get("attempts", 0)

    # TODO: REMOVE THIS
    return END

    if attempts > retry_attempts:
        return END
    if not best_match:
        return "parse_alias"
    else:
        return END


async def workflow():
    workflow = StateGraph(WorkflowState)

    workflow.add_node("parse_alias", parse_alias)
    workflow.add_node("find_product_matches", find_product_matches)
    workflow.add_node("query_database", query_database)
    workflow.add_node("analyze_matches", analyze_matches)

    workflow.add_edge(START, "parse_alias")

    # workflow.add_conditional_edges("parse_alias", should_try_reparse)

    workflow.add_edge("parse_alias", "find_product_matches")
    workflow.add_edge("find_product_matches", "query_database")
    workflow.add_edge("query_database", "analyze_matches")
    workflow.add_conditional_edges("analyze_matches", should_restart_workflow)

    return workflow.compile()


async def run_workflow(software_alias: str):

    async with workflow_semaphore:
        logger.info(f"Starting workflow for alias: {software_alias}")
        agent = await workflow()

        initial_state = {
            "software_alias": software_alias,
            "software_info": {"product": "", "vendor": "", "version": ""},
            "cpe_results": [],
            "cpe_matches": {"best_match": None, "possible_matches": []},
            "matched_products": [],
            "product_search_results": [],
            "error": None,
            "info": None,
            "parse_results": [],
            "retries": 0,
        }

        try:
            with log_execution_time(
                logger, f"Running Workflow for alias: {software_alias}"
            ):
                return await agent.ainvoke(initial_state)
        except Exception as e:
            logger.error(f"Error running workflow for alias: {software_alias}; {e}")
            return {
                "software_alias": software_alias,
                "error": str(e),
                "match_type": "Error",
                "info": f"Error running workflow: {str(e)}",
            }


async def run_workflows_parallel(software_aliases: list[str]):
    """Run multiple workflows in parallel, limited by the semaphore."""
    logger.info(
        f"Running {len(software_aliases)} workflows in parallel for {software_aliases} with {max_concurrent_workflows} max concurrent workflows"
    )
    tasks = [run_workflow(alias) for alias in software_aliases]
    return await asyncio.gather(*tasks)
