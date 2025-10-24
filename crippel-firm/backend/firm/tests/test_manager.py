import asyncio

import pytest

from firm.config import FirmConfig
from firm.manager import ManagerBot


@pytest.mark.asyncio
async def test_manager_hire_and_fire(tmp_path):
    config = FirmConfig()
    config.manager.persistence_path = str(tmp_path / "state.json")
    manager = ManagerBot(config)
    bot_id = await manager.hire_research_bot()
    assert bot_id in [record.bot.bot_id for record in manager.registry.active_bots()]
    await manager.fire(bot_id)
    assert manager.registry.get(bot_id) is None
    await manager.shutdown()
