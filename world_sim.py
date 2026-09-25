"""
world_sim
=========
Not an agent -- this is the "environment". It simulates a target moving
along a simple path and publishes noisy SensorReadings onto the bus,
exactly like a real sensor feed, camera pipeline, or webhook would.
In a real deployment you'd delete this file and instead publish
SensorReadings from your actual data source (API poll, Kafka consumer,
webhook handler, etc.) -- the agents don't know or care where readings
come from.
"""

from __future__ import annotations

import asyncio
import math
import random

from core.message_bus import Message, MessageBus
from core.types import SensorReading, Vector2


async def run_world(
    bus: MessageBus,
    *,
    steps: int = 200,
    dt: float = 0.1,
    noise_std: float = 0.4,
) -> None:
    t = 0.0
    for step in range(steps):
        # Target flies a slow spiral -- gives Predictor something nontrivial
        # to extrapolate and gives Commander a moving goal to chase.
        radius = 20 + 0.05 * step
        true_x = radius * math.cos(t)
        true_y = radius * math.sin(t) * 0.6

        noisy = Vector2(
            x=true_x + random.gauss(0, noise_std),
            y=true_y + random.gauss(0, noise_std),
        )

        await bus.publish(
            Message(
                topic="sensor/raw",
                sender="world_sim",
                payload=SensorReading(position=noisy, noise_std=noise_std),
            )
        )

        t += dt
        await asyncio.sleep(dt)
