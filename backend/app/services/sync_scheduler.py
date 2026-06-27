import asyncio
import contextlib
import logging

from app.services.update_service import update_service


logger = logging.getLogger(__name__)


class SyncScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None

    def start(self, interval_seconds: int) -> None:
        if self._task and not self._task.done():
            return

        self._task = asyncio.create_task(self._run(interval_seconds))
        logger.info("Automatic source sync scheduled every %s second(s).", interval_seconds)

    async def stop(self) -> None:
        if not self._task:
            return

        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self, interval_seconds: int) -> None:
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                result = await asyncio.to_thread(update_service.run_sync)
                logger.info("Automatic source sync completed: %s", result)
            except Exception:
                logger.exception("Automatic source sync failed.")


sync_scheduler = SyncScheduler()
