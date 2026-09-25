# Multi-Agent System Boilerplate

A minimal, dependency-free (pure `asyncio`) framework for a team of
specialized agents that communicate over a shared message bus, share a
tool registry, and coordinate to solve a task with no human in the loop.

```
World (sensor feed) --sensor/raw--> Tracker --track/update--> Predictor
                                                                   |
                                                            predict/forecast
                                                                   v
                                                               Commander --command/action--> actuator
```

Included example: a **Tracker** smooths noisy position readings, a
**Predictor** extrapolates the target's future position, and a
**Commander** steers toward the forecast and declares the mission
solved once it intercepts the target. This is a stand-in for
`[your actual task]` — see "Adapting to your task" below.

## Run it

```bash
pip install -r requirements.txt   # currently zero deps — stdlib only
python main.py
```

You'll see each agent come online, then a stream of `INTERCEPTED`
logs once the Commander closes the distance, ending with:

```
MISSION COMPLETE — agents solved the task autonomously.
```

## Project layout

```
mas/
├── core/
│   ├── types.py          # shared dataclasses (the message "contracts")
│   ├── message_bus.py    # async pub/sub — how agents talk
│   ├── blackboard.py     # shared key/value state — mission status etc.
│   └── tools.py          # shared tool registry — how agents share capabilities
├── agents/
│   ├── base_agent.py     # abstract Agent: subscribe/publish/run loop
│   ├── tracker.py        # perception: raw readings -> smoothed state
│   ├── predictor.py      # forecasting: state -> future state
│   └── commander.py      # decision + actuation, declares "solved"
├── world_sim.py           # example environment/data source (delete in prod)
└── main.py                 # wires everything together, runs the loop
```

## Design principles

- **No central orchestrator.** Agents are independent `asyncio` tasks
  that only communicate via `MessageBus.publish` / `subscribe`. Adding
  a fourth agent (a Logger, an Auditor, a second Predictor ensemble
  member) never requires touching the other three.
- **Typed contracts, not tight coupling.** Agents depend on the
  dataclasses in `core/types.py` (`TrackEstimate`, `Forecast`,
  `Command`), not on each other's internals. Swap Tracker's smoothing
  algorithm for a Kalman filter or a vision model and Predictor/
  Commander don't change.
- **Shared tools, not duplicated code.** `core/tools.py` is a registry
  any agent can call into (`await self.tools.call("distance", a, b)`).
  Register an LLM client, a database query, or a physics solver once;
  every agent gets it.
- **Explicit shared state via Blackboard.** Anything that isn't a
  discrete event (e.g. "is the mission solved yet?") lives on the
  `Blackboard`, a small async-safe key/value store, instead of being
  inferred from message history.

## Adapting to your task

1. **Redefine the contracts** in `core/types.py` — replace
   `SensorReading` / `TrackEstimate` / `Forecast` / `Command` with
   whatever your domain's data actually looks like (e.g. `LogEvent`,
   `RiskScore`, `TradeSignal`).
2. **Rewrite each agent's `handle()`** — the loop, subscribe/publish
   mechanics, and shutdown logic in `base_agent.py` stay the same.
3. **Replace `world_sim.py`** with your real data source: an API
   poller, a webhook receiver, a Kafka consumer, a cron job — anything
   that ends in `await bus.publish(Message(topic="sensor/raw", ...))`.
4. **Plug in an LLM** by registering an async tool in `main.py`:

   ```python
   async def llm_reason(prompt: str) -> str:
       response = await your_llm_client.complete(prompt)
       return response
   tools.register("llm_reason", llm_reason)
   ```

   then call `await self.tools.call("llm_reason", prompt=...)` from
   any agent's `handle()` — Commander is the natural place for this if
   you want an LLM making the final call.
5. **Change the "solved" condition** in `commander.py` — right now
   it's a distance threshold; make it whatever your task's success
   criterion is, then `await self.blackboard.set("mission_solved", True)`
   and `await self.publish("system/stop", ...)`.

## Swapping the transport

`MessageBus` is ~40 lines wrapping `asyncio.Queue`. For a distributed
deployment (agents as separate processes/containers), reimplement
`publish` / `subscribe` against Redis Pub/Sub, NATS, or Kafka — the
`Message` dataclass already serializes cleanly to JSON, and no agent
code needs to change since they only depend on the bus interface.

## Notes

- No external dependencies — pure `asyncio` + stdlib. Add whatever
  client libraries your real tools/LLM need to `requirements.txt`.
- `world_sim.py` exists purely so this repo runs out of the box.
  Delete it once you've wired in a real data source.
