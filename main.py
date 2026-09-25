"""
main
====
Boots the whole multi-agent system with zero human intervention:

    World (sim) --sensor/raw--> Tracker --track/update--> Predictor
                                                              |
                                                       predict/forecast
                                                              v
                                                          Commander --command/action--> (actuator)

Agents run as independent asyncio tasks and only talk to each other
through the MessageBus -- there is no central "if tracker then predictor"
control flow. The Commander alone decides when the mission is solved
(via the Blackboard) and broadcasts `system/stop`, which this file
listens for to end the run.

Run with:  python main.py
"""

from __future__ import annotations

import asyncio
import logging

from agents import Commander, Predictor, Tracker
from core import Blackboard, MessageBus, Vector2, build_default_registry
from world_sim import run_world

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


async def main() -> None:
    bus = MessageBus()
    blackboard = Blackboard()
    tools = build_default_registry()

    # --- To add a real LLM-backed tool any agent can call, e.g.: ------------
    # async def llm_reason(prompt: str) -> str:
    #     response = await your_llm_client.complete(prompt)
    #     return response
    # tools.register("llm_reason", llm_reason)
    # --------------------------------------------------------------------

    tracker = Tracker("Tracker", bus, blackboard, tools)
    predictor = Predictor("Predictor", bus, blackboard, tools)
    commander = Commander(
        "Commander", bus, blackboard, tools, own_position=Vector2(0.0, 0.0)
    )

    agents = [tracker, predictor, commander]
    agent_tasks = [asyncio.create_task(agent.run()) for agent in agents]

    stop_sub = bus.subscribe("system/stop")

    world_task = asyncio.create_task(run_world(bus, steps=400, dt=0.05))

    async def watch_for_stop() -> None:
        msg = await stop_sub.get()
        logger.info("Stop signal received: %s", msg.payload)
        world_task.cancel()
        for agent in agents:
            agent.stop()

    watcher_task = asyncio.create_task(watch_for_stop())

    done, pending = await asyncio.wait(
        [world_task, watcher_task, *agent_tasks],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # Give agents a moment to finish handling in-flight messages, then
    # cancel whatever is still running (e.g. world_sim if it finished
    # naturally, or agents if the mission was never solved).
    await asyncio.sleep(0.3)
    for task in [world_task, watcher_task, *agent_tasks]:
        if not task.done():
            task.cancel()
    await asyncio.gather(*[world_task, watcher_task, *agent_tasks], return_exceptions=True)

    solved = await blackboard.get("mission_solved", False)
    if solved:
        logger.info("MISSION COMPLETE — agents solved the task autonomously.")
    else:
        logger.info("Run ended without interception (simulation exhausted).")


if __name__ == "__main__":
    asyncio.run(main())
