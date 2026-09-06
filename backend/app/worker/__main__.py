"""Background worker entry point: ``python -m app.worker``.

Runs the capture and classification consumers concurrently in one process, plus
the contradiction watcher. The stream consumers are separate Redis groups, so
they can be split into separate deployments later without code changes.
"""

import asyncio
import logging
import signal

from app.ai import close_ai_client
from app.core.database import engine
from app.core.redis import close_redis
from app.worker import (
    capture_worker,
    classification_worker,
    contradiction_worker,
    live_doc_diff_worker,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)

logger = logging.getLogger("app.worker")


async def main() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for signal_name in ("SIGINT", "SIGTERM"):
        signal_number = getattr(signal, signal_name, None)
        if signal_number is None:
            continue
        try:
            loop.add_signal_handler(signal_number, stop_event.set)
        except NotImplementedError:
            # Windows asyncio has no signal handler support; KeyboardInterrupt
            # still unwinds through the run() call below.
            pass

    try:
        # return_exceptions keeps one crashed consumer from silently cancelling
        # the other; both are logged before shutdown.
        results = await asyncio.gather(
            capture_worker.run(stop_event),
            classification_worker.run(stop_event),
            contradiction_worker.run(stop_event),
            live_doc_diff_worker.run(stop_event),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, BaseException) and not isinstance(
                result, asyncio.CancelledError
            ):
                logger.error("Worker exited with an error", exc_info=result)
    finally:
        await close_ai_client()
        await close_redis()
        await engine.dispose()
        logger.info("Worker shut down")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
