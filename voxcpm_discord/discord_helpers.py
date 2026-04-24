from __future__ import annotations

import discord

from voxcpm_discord.config import LOGGER, PENDING_REACTION


async def add_pending_reaction(message: discord.Message) -> None:
    await add_reaction(message, PENDING_REACTION)


async def add_reaction(message: discord.Message, emoji: str) -> None:
    try:
        await message.add_reaction(emoji)
    except discord.HTTPException:
        LOGGER.exception("Failed to add reaction emoji=%s message=%s", emoji, message.id)


async def send_ephemeral(interaction: discord.Interaction, message: str) -> None:
    await interaction.response.send_message(message, ephemeral=True)
