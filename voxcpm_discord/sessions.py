from __future__ import annotations

import asyncio
from dataclasses import dataclass

import discord


@dataclass
class SpeechRequest:
    user_id: int
    text: str
    queued_at: float


@dataclass
class GuildSession:
    guild_id: int
    text_channel_id: int
    voice_channel_id: int
    voice_client: discord.VoiceClient
    queue: asyncio.Queue[SpeechRequest]
    worker: asyncio.Task[None] | None
    pending_request: SpeechRequest | None = None
