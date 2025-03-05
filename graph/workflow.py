import os
from typing import Literal
from langgraph.graph import StateGraph, START, END
from openai import AsyncOpenAI
from graph.workflow_state import WorkflowState
from graph.parse_alias import parse_alias
from graph.query_database import query_database
from graph.find_matches import find_matches
from graph.analyze_matches import analyze_matches
from logging_config import log_execution_time, configure_logging
from store.load_vector_store import load_vector_store
import asyncio
import tracemalloc
from config import settings

logger = configure_logging()
tracemalloc.start()

openai_api_key = settings.llm.openai_api_key
openai_client = AsyncOpenAI(api_key=openai_api_key)
use_vector_store = settings.execution.use_vector_store
retry_attempts = settings.execution.retry_attempts
max_concurrent_workflows = settings.execution.max_concurrent_workflows

workflow_semaphore = asyncio.Semaphore(max_concurrent_workflows)

product_vector_store = None
vendor_vector_store = None

logger.info("Loading Vector Stores")
with log_execution_time(logger, "Loading Vector Stores"):
    if product_vector_store is None:
        product_vector_store = load_vector_store("product")
    if vendor_vector_store is None:
        vendor_vector_store = load_vector_store("vendor")


def should_try_reparse(state) -> Literal["parse_alias", END]:
    parse_results = state.get("parse_results", [])
    parse_results_count = len(parse_results)
    vectors_found = state.get("vectors_found", False)

    if vectors_found:
        return "query_database"

    if parse_results_count > 3:
        logger.info(f"No results found after {parse_results_count} attempts")
        return END
    else:
        return "parse_alias"


def should_restart_workflow(state) -> Literal["parse_alias", END]:
    cpe_match = state.get("cpe_match", {})
    confidence_score = cpe_match.get("confidence_score", None)
    attempts = state.get("attempts", 0)

    if attempts > retry_attempts or confidence_score is None:
        return END
    if confidence_score < 40:
        return "parse_alias"
    else:
        return END


async def workflow():
    workflow = StateGraph(WorkflowState)

    workflow.add_node("parse_alias", parse_alias)
    workflow.add_node("find_matches", find_matches)
    workflow.add_node("analyze_matches", analyze_matches)
    workflow.add_node("query_database", query_database)

    workflow.add_edge(START, "parse_alias")

    workflow.add_conditional_edges("parse_alias", should_try_reparse)
    workflow.add_edge("find_matches", "analyze_matches")
    workflow.add_conditional_edges("analyze_matches", should_restart_workflow)

    return workflow.compile()


async def run_workflow(software_alias: str):

    async with workflow_semaphore:
        logger.info(f"Starting workflow for alias: {software_alias}")
        agent = await workflow()

        global product_vector_store
        global vendor_vector_store

        logger.info("Loading Vector Stores")
        with log_execution_time(logger, "Loading Vector Stores"):
            if product_vector_store is None:
                product_vector_store = load_vector_store("product")
            if vendor_vector_store is None:
                vendor_vector_store = load_vector_store("vendor")

        initial_state = {
            "software_alias": software_alias,
            "software_info": {"product": "", "vendor": "", "version": ""},
            "cpe_results": [],
            "cpe_match": {},
            "top_matches": [],
            "error": None,
            "info": None,
            "query_type": None,
            "query_results": None,
            "parse_results": [],
            "product_vector_store": product_vector_store,
            "vendor_vector_store": vendor_vector_store,
            "retries": 0,
            "vectors_found": False,
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
