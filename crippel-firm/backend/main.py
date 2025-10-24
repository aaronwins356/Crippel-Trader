"""Entrypoint for running the Crippel-Firm simulation."""
from __future__ import annotations

import asyncio
import logging

from firm.brain import ManagerBrain
from firm.config import FirmConfig
from firm.utils.logging import configure_logging


async def main() -> None:
    """Run the manager brain until interrupted."""
    configure_logging()
    config = FirmConfig()
    brain = ManagerBrain(config=config)
    await brain.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Crippel-Firm stopped by user")
