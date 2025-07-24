from __future__ import annotations

"""Rich-based logging setup used by the command-line entrypoint.

Expose a single ``init_logging`` helper that configures the root logger
and returns a ``rich.console.Console`` instance so callers can still
print richly-formatted panels/messages.
"""

import logging
from typing import Sequence

from rich.console import Console
from rich.logging import RichHandler

__all__: Sequence[str] = ("init_logging",)


def init_logging(level: int = logging.INFO) -> Console:
    """Initialise Rich logging and silence overly-verbose third-party loggers.

    Args:
        level: The minimum log level for *our* code. Defaults to ``logging.INFO``.

    Returns:
        The ``Console`` object created for Rich so that the caller can reuse
        it for coloured terminal output (e.g. ``console.print``).
    """

    console = Console()
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)],
    )

    # Reduce noise from HTTP and Slack libraries – we rarely need their DEBUG logs.
    for noisy in ("slack_sdk", "slack_bolt", "httpcore", "httpx", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return console 