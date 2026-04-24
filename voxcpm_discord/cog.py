from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from voxcpm_discord.config import ALLOWED_PROMPT_EXTENSIONS, LOGGER, MAX_MESSAGE_LENGTH
from voxcpm_discord.discord_helpers import (
    add_pending_reaction,
    send_ephemeral,
)
from voxcpm_discord.profiles import UserVoiceProfile
from voxcpm_discord.text import process_tts_text

if TYPE_CHECKING:
    from voxcpm_discord.bot import VoxCPMDiscordBot


class VoiceSettingsModal(discord.ui.Modal, title="음성 설정"):
    sample_voice = discord.ui.TextInput(
        label="스타일",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=300,
        placeholder="음성 클로닝의 경우 비워주세요. 예: 차분한 젊은 여성 목소리, 또렷하고 따뜻한 톤",
    )
    prompt_text = discord.ui.TextInput(
        label="클로닝 대본",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
        placeholder="업로드한 음성 파일의 정확한 대본을 입력하세요. (입력하지 않는 경우 큰 품질 저하)",
    )

    def __init__(
        self,
        bot: VoxCPMDiscordBot,
        user_id: int,
        clone_file: tuple[str, bytes] | None,
        profile: UserVoiceProfile,
    ) -> None:
        super().__init__()
        self.bot = bot
        self.user_id = user_id
        self.clone_file = clone_file
        self.sample_voice.default = profile.sample_voice or ""
        self.prompt_text.default = profile.prompt_text or ""

    async def on_submit(self, interaction: discord.Interaction) -> None:
        sample_voice = str(self.sample_voice.value).strip()
        prompt_text = str(self.prompt_text.value).strip()

        profile = self.bot.profile_store.set_sample_voice(self.user_id, sample_voice)

        if self.clone_file is not None:
            suffix, content = self.clone_file
            profile = self.bot.profile_store.set_voice_prompt(
                self.user_id,
                suffix,
                content,
                prompt_text or None,
            )
        elif profile.voice_prompt_path and profile.prompt_text != (prompt_text or None):
            existing_path = Path(profile.voice_prompt_path)
            profile = self.bot.profile_store.set_voice_prompt(
                self.user_id,
                existing_path.suffix,
                existing_path.read_bytes(),
                prompt_text or None,
            )

        status = ["음성 설정을 저장했습니다."]
        status.append(f"스타일: `{profile.sample_voice or '미설정'}`")
        status.append(f"클로닝: `{Path(profile.voice_prompt_path).name if profile.voice_prompt_path else '미설정'}`")
        status.append(f"클로닝 대본: `{profile.prompt_text or '미설정'}`")
        await send_ephemeral(interaction, "\n".join(status))


class VoiceBotCog(commands.Cog):
    def __init__(self, bot: VoxCPMDiscordBot) -> None:
        self.bot = bot

    @app_commands.command(name="생성", description="프롬프트를 wav 음성 파일로 생성합니다")
    @app_commands.rename(promptstring="프롬프트")
    @app_commands.describe(promptstring="wav로 생성할 텍스트 프롬프트")
    async def generate_wav(
        self, interaction: discord.Interaction, promptstring: str
    ) -> None:
        prompt = process_tts_text(promptstring)
        if not prompt:
            await send_ephemeral(interaction, "생성할 텍스트를 입력해 주세요.")
            return

        if len(prompt) > MAX_MESSAGE_LENGTH:
            await send_ephemeral(
                interaction,
                f"프롬프트는 최대 {MAX_MESSAGE_LENGTH}자까지 입력할 수 있습니다.",
            )
            return

        LOGGER.info(
            "Handled /생성 command guild=%s channel=%s author=%s text=%r",
            interaction.guild_id,
            interaction.channel_id,
            interaction.user.id,
            prompt,
        )
        await interaction.response.defer(thinking=True)

        progress_message = await interaction.followup.send("생성 중...", wait=True)
        await add_pending_reaction(progress_message)
        try:
            profile = self.bot.profile_store.get(interaction.user.id)
            output_path = await self.bot.tts_service.synthesize(prompt, profile)
        except Exception:
            LOGGER.exception(
                "Failed to generate wav for /생성 guild=%s channel=%s author=%s",
                interaction.guild_id,
                interaction.channel_id,
                interaction.user.id,
            )
            await interaction.followup.send(
                "wav 생성 중 오류가 발생했습니다.", ephemeral=True
            )
            return

        filename = f"voxcpm-{output_path.stem}.wav"
        response_message = await interaction.followup.send(
            content="생성 완료",
            file=discord.File(output_path, filename=filename),
            wait=True,
        )
        await add_pending_reaction(response_message)

    @app_commands.command(name="들어와", description="현재 음성 채널에 들어옵니다")
    async def join(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or interaction.channel_id is None:
            await send_ephemeral(interaction, "서버 텍스트 채널에서만 사용할 수 있습니다.")
            return

        member = interaction.user
        if (
            not isinstance(member, discord.Member)
            or member.voice is None
            or member.voice.channel is None
        ):
            await send_ephemeral(interaction, "먼저 음성 채널에 들어가 있어야 합니다.")
            return

        voice_channel = member.voice.channel
        session = await self.bot.bind_session(
            interaction.guild.id, interaction.channel_id, voice_channel
        )
        await send_ephemeral(
            interaction,
            f"텍스트 채널 <#{session.text_channel_id}> 와 음성 채널 `{voice_channel.name}` 에 바인딩했습니다.",
        )

    @app_commands.command(name="나가", description="현재 음성 채널에서 나갑니다")
    async def leave(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await send_ephemeral(interaction, "서버에서만 사용할 수 있습니다.")
            return

        session = self.bot.sessions.get(interaction.guild.id)
        if session is None:
            await send_ephemeral(interaction, "현재 활성 세션이 없습니다.")
            return

        channel_name = (
            str(session.voice_client.channel)
            if session.voice_client.channel is not None
            else str(session.voice_channel_id)
        )
        await self.bot.close_session(interaction.guild.id)
        await send_ephemeral(
            interaction,
            f"음성 채널 `{channel_name}` 에서 나갔습니다.",
        )

    @app_commands.command(
        name="설정",
        description="음성 클로닝 파일과 스타일 설정을 확인하거나 저장합니다",
    )
    @app_commands.rename(file="파일")
    @app_commands.describe(
        file="선택 사항: 클로닝에 사용할 wav, mp3, 또는 ogg 파일",
    )
    async def open_voice_settings(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment | None = None,
    ) -> None:
        clone_file = None
        if file is not None:
            suffix = Path(file.filename.lower()).suffix
            if suffix not in ALLOWED_PROMPT_EXTENSIONS:
                await send_ephemeral(interaction, "wav, mp3, 또는 ogg 파일만 업로드할 수 있습니다.")
                return
            clone_file = (suffix, await file.read())

        profile = self.bot.profile_store.get(interaction.user.id)
        modal = VoiceSettingsModal(self.bot, interaction.user.id, clone_file, profile)
        await interaction.response.send_modal(modal)

    @app_commands.command(
        name="멈춰",
        description="지금까지 쌓인 큐를 모두 삭제하고 현재 출력을 중지합니다",
    )
    async def shut_up(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await send_ephemeral(interaction, "서버에서만 사용할 수 있습니다.")
            return

        session = self.bot.sessions.get(interaction.guild.id)
        if session is None:
            await send_ephemeral(interaction, "현재 활성 세션이 없습니다.")
            return

        cleared = self.bot.clear_session_queue(session)
        if session.voice_client.is_playing() or session.voice_client.is_paused():
            session.voice_client.stop()

        await send_ephemeral(
            interaction,
            f"현재 출력을 중지하고 대기 중인 메시지 {cleared}개를 삭제했습니다.",
        )
