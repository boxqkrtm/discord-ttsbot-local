from __future__ import annotations

from typing import Any

__all__ = ["TTSDiscordBot", "VoxCPMDiscordBot", "hi_main", "main"]


def main() -> None:
    from .app import main as app_main

    app_main()


def hi_main() -> None:
    from .app import hi_main as app_hi_main

    app_hi_main()


def __getattr__(name: str) -> Any:
    if name in {"TTSDiscordBot", "VoxCPMDiscordBot"}:
        from .bot import TTSDiscordBot

        return TTSDiscordBot
    raise AttributeError(name)
