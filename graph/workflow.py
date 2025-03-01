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
import asyncio
import tracemalloc
from config import settings

logger = configure_logging()
tracemalloc.start()

openai_api_key = settings.llm.openai_api_key
openai_client = AsyncOpenAI(api_key=openai_api_key)
use_vector_store = settings.execution.use_vector_store


def should_use_vector_store(state) -> Literal["find_matches", "query_database"]:
    if use_vector_store:
        return "find_matches"
    else:
        return "query_database"


async def workflow():
    workflow = StateGraph(WorkflowState)

    workflow.add_node("parse_alias", parse_alias)
    workflow.add_node("find_matches", find_matches)
    workflow.add_node("analyze_matches", analyze_matches)
    workflow.add_node("query_database", query_database)

    workflow.add_edge(START, "parse_alias")
    workflow.add_conditional_edges("parse_alias", should_use_vector_store)
    workflow.add_edge("query_database", "find_matches")
    workflow.add_edge("find_matches", "analyze_matches")
    workflow.add_edge("analyze_matches", END)

    return workflow.compile()


async def run_workflow(software_alias: str):
    agent = await workflow()

    initial_state = {
        "software_alias": software_alias,
        "software_info": {"product": "", "vendor": "", "version": ""},
        "cpe_results": [],
        "cpe_match": {},
        "top_matches": [],
        "error": None,
        "info": None,
    }

    try:
        with log_execution_time(
            logger, f"Running Workflow for alias: {software_alias}"
        ):
            return await agent.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"Error running workflow for alias: {software_alias}; {e}")


async def run_workflows_parallel(software_aliases: list[str]):
    return await asyncio.gather(*[run_workflow(alias) for alias in software_aliases])
