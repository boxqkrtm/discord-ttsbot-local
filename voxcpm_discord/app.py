from __future__ import annotations

import asyncio
import os
from pathlib import Path

from voxcpm_discord.bot import VoxCPMDiscordBot
from voxcpm_discord.config import configure_logging, data_dir, model_data_dir, model_name, LOGGER
from voxcpm_discord.profiles import UserVoiceProfile
from voxcpm_discord.tts import VoxCPMService


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    _load_env_file()
    configure_logging()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("DISCORD_TOKEN is required")

    bot = VoxCPMDiscordBot()
    bot.run(token, log_handler=None)


async def _hi_tts_async() -> Path:
    prompt = os.getenv("VOXCPM_HI_TEXT", "hi")
    service = VoxCPMService(model_name(), data_dir() / "generated", model_data_dir())
    output_path = await service.synthesize(prompt, UserVoiceProfile())
    LOGGER.info("Standalone hi TTS generated %s", output_path)
    return output_path


def hi_main() -> None:
    configure_logging()
    output_path = asyncio.run(_hi_tts_async())
    print(output_path)


if __name__ == "__main__":
    main()
