from graph.workflow import run_workflows_parallel
from store.load_vector_store import load_vector_store


import asyncio

# Initialize event loop before other imports to prevent
# "There is no current event loop in thread" errors,
# particularly when running in Docker
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


if __name__ == "__main__":
    result = asyncio.run(
        run_workflows_parallel(
            [
                "Microsoft Visual C++ 2008 Redistributable - x86 9.0.30729.4974",
            ]
        )
    )

    print("RESULT", result)
