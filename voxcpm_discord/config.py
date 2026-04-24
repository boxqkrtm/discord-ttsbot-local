from __future__ import annotations

import logging
import os
from pathlib import Path


LOGGER = logging.getLogger("voxcpm_discord_bot")
ALLOWED_PROMPT_EXTENSIONS = {".wav", ".mp3", ".ogg"}
DEFAULT_CFG_VALUE = 2.0
DEFAULT_INFERENCE_TIMESTEPS = 10
PENDING_REACTION = "⏳"
MAX_MESSAGE_LENGTH = 400
PCM_FRAME_SIZE = 3840
PCM_PREBUFFER_FRAMES = 20


def data_dir() -> Path:
    return Path(os.getenv("VOXCPM_DATA_DIR", "data-user"))


def model_data_dir() -> Path:
    return Path(os.getenv("VOXCPM_MODEL_DATA_DIR", "data"))


def model_name() -> str:
    return os.getenv("VOXCPM_MODEL", "openbmb/VoxCPM2")


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
