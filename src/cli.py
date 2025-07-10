"""
Command-line interface (CLI) entry-point for the multi-agent Slack bot.

This is a *demonstration* utility that shows how runtime options can enable or
configure optional features (e.g. the Zoom integration).  It is deliberately
kept lightweight and dependency-free (only the Python standard library).

Example usage
-------------
# Show all pluggable features
python -m src.cli list-features

# Run the bot with Zoom enabled in STUB mode (default)
python -m src.cli run --enable-zoom --zoom-mode stub

# Run the bot with Zoom enabled in LIVE mode (requires Zoom creds)
python -m src.cli run --enable-zoom --zoom-mode live

Adding new features
-------------------
New optional features can register a *setup* callback via the `@plugin` decorator
below.  Each callback receives the parsed `argparse.Namespace` and can mutate
environment variables or perform any initialisation required **before**
`src.main.main()` starts.

For example:

    from src.cli import plugin
    @plugin("tts")
    def _tts_plugin(args):
        if args.enable_tts:
            os.environ["ENABLE_TTS"] = "1"
            ...

Future CLI flags that belong to a plugin should be added to the `run` subparser.
"""

from __future__ import annotations

import argparse
import logging
import os
from typing import Callable, Dict

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Plugin registry utilities
# ---------------------------------------------------------------------------

FEATURE_PLUGINS: Dict[str, Callable[[argparse.Namespace], None]] = {}


def plugin(name: str) -> Callable[[Callable[[argparse.Namespace], None]], Callable[[argparse.Namespace], None]]:
    """Decorator to register a setup function for a feature plugin."""

    def _decorator(func: Callable[[argparse.Namespace], None]):
        FEATURE_PLUGINS[name] = func
        return func

    return _decorator


# ---------------------------------------------------------------------------
#  Built-in demo plugins
# ---------------------------------------------------------------------------

@plugin("zoom")
def _zoom_plugin(args: argparse.Namespace) -> None:
    """Enable Zoom feature based on CLI flags.

    Sets some environment variables that *could* be consumed by the rest of the
    application.  The current `ZoomClient` only relies on the presence of the
    actual Zoom OAuth credentials to switch out of stub mode, but these vars
    serve as a useful signalling mechanism and future hook.
    """

    if not getattr(args, "enable_zoom", False):
        return

    mode = getattr(args, "zoom_mode", "stub")

    # Mark the feature as enabled for downstream code.
    os.environ["BOT_ENABLE_ZOOM"] = "1"
    os.environ["BOT_ZOOM_MODE"] = mode

    log.info("Zoom feature enabled (mode=%s)", mode)


# ---------------------------------------------------------------------------
#  Helper actions
# ---------------------------------------------------------------------------

def _list_features() -> None:
    """Print all available plugins to stdout."""

    print("Available optional features:")
    for feat in sorted(FEATURE_PLUGINS):
        print(f"  • {feat}")


def _run_bot(args: argparse.Namespace) -> None:
    """Activate selected plugins and launch the main application."""

    # ------------------------------------------------------------------
    #  Progress bar powered by "alive-progress" (optional)
    # ------------------------------------------------------------------
    try:
        from alive_progress import alive_bar, config_handler

        # Crimson-tinted smooth theme; fall back silently if invalid
        try:
            config_handler.set_global(theme="smooth", bar_color="crimson")  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001
            pass

        total_steps = len(FEATURE_PLUGINS) + 1  # +1 for the final startup step
        with alive_bar(
            total_steps,
            title="Berkman Klein Slack System",
            dual_line=True,
            force_tty=True,
        ) as bar:

            # 1) Enable plugins with visual feedback
            for name, setup_cb in FEATURE_PLUGINS.items():
                bar.text = f"⏳ Enabling feature: {name}"
                try:
                    setup_cb(args)
                except Exception as exc:
                    log.error("Plugin '%s' failed during setup: %s", name, exc, exc_info=True)
                bar()

            # 2) Adjust logging level before booting the bot
            if args.log_level:
                logging.basicConfig(level=getattr(logging, args.log_level.upper(), "INFO"))

            bar.text = "🚀 Launching Slack bot…"
            bar()

        # Progress bar context finished, proceed to launch main app
    except ModuleNotFoundError:
        # alive-progress not installed – fallback to plain startup
        log.warning("'alive-progress' not found – running without fancy CLI bar")

        for name, setup_cb in FEATURE_PLUGINS.items():
            try:
                setup_cb(args)
            except Exception as exc:
                log.error("Plugin '%s' failed during setup: %s", name, exc, exc_info=True)

        if args.log_level:
            logging.basicConfig(level=getattr(logging, args.log_level.upper(), "INFO"))

    # 3) Import *after* plugins have potentially tweaked env vars so the rest of
    #    the application sees the correct configuration.
    from src.main import main as _main_entry

    _main_entry()


# ---------------------------------------------------------------------------
#  CLI argument parsing
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-agent Slack bot CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- list-features ------------------------------------------------------
    sub_list = subparsers.add_parser("list-features", help="Show available optional features")
    sub_list.set_defaults(_func=lambda _args: _list_features())

    # --- run (default) ------------------------------------------------------
    sub_run = subparsers.add_parser("run", help="Start the Slack bot")

    # Generic options
    sub_run.add_argument("--log-level", default="INFO", help="Root logging level (default: INFO)")

    # Zoom feature flags
    sub_run.add_argument("--enable-zoom", action="store_true", help="Enable the Zoom integration feature")
    sub_run.add_argument("--zoom-mode", choices=["stub", "live"], default="stub", help="Choose Zoom mode when enabled (default: stub)")

    # Placeholder for future plugins to attach their own flags
    # (they can retrieve the subparser via `parser = globals()['RUN_SUBPARSER']` if necessary)

    sub_run.set_defaults(_func=_run_bot)

    args = parser.parse_args()
    args._func(args)  # type: ignore[arg-type]


if __name__ == "__main__":
    main() 