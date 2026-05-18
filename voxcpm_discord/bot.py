from __future__ import annotations

import asyncio
import time

import discord
from discord.ext import commands

from voxcpm_discord.config import LOGGER, MAX_MESSAGE_LENGTH, data_dir, model_data_dir, tts_engine
from voxcpm_discord.discord_helpers import add_pending_reaction
from voxcpm_discord.profiles import UserVoiceProfile, VoiceProfileStore
from voxcpm_discord.sessions import GuildSession, SpeechRequest
from voxcpm_discord.text import process_tts_text
from voxcpm_discord.tts import create_tts_service


class TTSDiscordBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.voice_states = True
        intents.messages = True
        intents.message_content = True

        super().__init__(command_prefix=commands.when_mentioned, intents=intents)

        self.profile_store = VoiceProfileStore(data_dir())
        self.tts_service = create_tts_service(
            tts_engine(), self.profile_store.generated_dir, model_data_dir()
        )
        self.sessions: dict[int, GuildSession] = {}
        self._startup_voice_cleanup_done = False
        self._model_warmup_task: asyncio.Task[None] | None = None

    async def setup_hook(self) -> None:
        from voxcpm_discord.cog import VoiceBotCog

        await self.add_cog(VoiceBotCog(self))
        self._model_warmup_task = asyncio.create_task(self._warm_model(), name="tts-model-warmup")
        await self.tree.sync()

    async def on_ready(self) -> None:
        if self.user is None:
            return

        if not self._startup_voice_cleanup_done:
            await self._disconnect_startup_voice_clients()
            self._startup_voice_cleanup_done = True

        LOGGER.info("Logged in as %s", self.user)

    async def _warm_model(self) -> None:
        started_at = time.perf_counter()
        LOGGER.info("Starting model warmup")
        try:
            await self.tts_service.warmup()
        except Exception:
            LOGGER.exception("Model warmup failed")
            return

        LOGGER.info("Model warmup completed in %.1f ms", (time.perf_counter() - started_at) * 1000)

    async def _disconnect_startup_voice_clients(self) -> None:
        if self.sessions:
            guild_ids = list(self.sessions)
            for guild_id in guild_ids:
                await self.close_session(guild_id)

        disconnected_guilds: set[int] = set()
        for voice_client in list(self.voice_clients):
            if voice_client.is_connected():
                LOGGER.info(
                    "Disconnecting startup voice client guild=%s channel=%s",
                    getattr(voice_client.guild, "id", None),
                    getattr(getattr(voice_client, "channel", None), "id", None),
                )
                disconnected_guilds.add(voice_client.guild.id)
                await voice_client.disconnect(force=True)

        for guild in self.guilds:
            if guild.id in disconnected_guilds:
                continue

            member = guild.me
            if member is None or member.voice is None or member.voice.channel is None:
                continue

            channel = member.voice.channel
            LOGGER.info(
                "Clearing stale startup voice state guild=%s channel=%s",
                guild.id,
                channel.id,
            )
            try:
                voice_client = await channel.connect(timeout=10.0, reconnect=False)
                await voice_client.disconnect(force=True)
            except discord.ClientException:
                existing_client = guild.voice_client
                if existing_client is not None and existing_client.is_connected():
                    await existing_client.disconnect(force=True)
            except Exception:
                LOGGER.exception(
                    "Failed to clear stale startup voice state guild=%s channel=%s",
                    guild.id,
                    channel.id,
                )

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        LOGGER.info(
            "Received message guild=%s channel=%s author=%s",
            message.guild.id,
            message.channel.id,
            message.author.id,
        )

        content = process_tts_text(message.clean_content)
        if content.lower() == "hi":
            LOGGER.info(
                "Handled hi message guild=%s channel=%s author=%s",
                message.guild.id,
                message.channel.id,
                message.author.id,
            )
            await message.channel.send("hi")
            return

        session = self.sessions.get(message.guild.id)
        if session is None:
            LOGGER.info("Ignoring message: no active session for guild=%s", message.guild.id)
            return

        if not self._matches_bound_text_channel(message.channel, session.text_channel_id):
            LOGGER.info(
                "Ignoring message: channel=%s parent=%s is not bound text channel=%s for guild=%s",
                message.channel.id,
                getattr(getattr(message.channel, "parent", None), "id", None),
                session.text_channel_id,
                message.guild.id,
            )
            return

        if not isinstance(message.author, discord.Member):
            LOGGER.info("Ignoring message: author=%s is not a guild member", message.author.id)
            return

        if message.author.voice is None or message.author.voice.channel is None:
            LOGGER.info(
                "Ignoring message: author=%s is not in a voice channel",
                message.author.id,
            )
            return

        if message.author.voice.channel.id != session.voice_channel_id:
            LOGGER.info(
                "Ignoring message: author=%s voice channel=%s is not bound voice channel=%s",
                message.author.id,
                message.author.voice.channel.id,
                session.voice_channel_id,
            )
            return

        if not content:
            LOGGER.info("Ignoring message: author=%s sent empty content", message.author.id)
            return

        if len(content) > MAX_MESSAGE_LENGTH:
            content = content[:MAX_MESSAGE_LENGTH]

        await session.queue.put(
            SpeechRequest(
                user_id=message.author.id,
                text=content,
                queued_at=time.perf_counter(),
            )
        )
        LOGGER.info(
            "Queued message guild=%s author=%s queue_size=%s text=%r",
            message.guild.id,
            message.author.id,
            session.queue.qsize(),
            content,
        )
        await add_pending_reaction(message)

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if self.user is None or member.id != self.user.id:
            return

        if before.channel is not None and after.channel is None:
            await self.close_session(member.guild.id, disconnect=False)

    @staticmethod
    def _matches_bound_text_channel(
        channel: discord.abc.GuildChannel | discord.Thread | discord.PartialMessageable,
        bound_channel_id: int,
    ) -> bool:
        if channel.id == bound_channel_id:
            return True

        if isinstance(channel, discord.Thread) and channel.parent_id == bound_channel_id:
            return True

        return False

    async def bind_session(
        self,
        guild_id: int,
        text_channel_id: int,
        voice_channel: discord.VoiceChannel | discord.StageChannel,
    ) -> GuildSession:
        session = self.sessions.get(guild_id)
        if session is not None and (
            session.worker is None or session.worker.done() or not session.voice_client.is_connected()
        ):
            await self.close_session(guild_id)
            session = None

        if session is None:
            voice_client = await voice_channel.connect()
            queue: asyncio.Queue[SpeechRequest] = asyncio.Queue()
            session = GuildSession(
                guild_id=guild_id,
                text_channel_id=text_channel_id,
                voice_channel_id=voice_channel.id,
                voice_client=voice_client,
                queue=queue,
                worker=None,
            )
            self.sessions[guild_id] = session
            session.worker = asyncio.create_task(self.player_loop(guild_id))
            return session

        if session.voice_client.channel != voice_channel:
            await session.voice_client.move_to(voice_channel)

        session.text_channel_id = text_channel_id
        session.voice_channel_id = voice_channel.id
        return session

    async def close_session(self, guild_id: int, disconnect: bool = True) -> None:
        session = self.sessions.pop(guild_id, None)
        if session is None:
            return

        if session.worker is not None:
            session.worker.cancel()
            try:
                await session.worker
            except asyncio.CancelledError:
                pass

        if disconnect and session.voice_client.is_connected():
            await session.voice_client.disconnect(force=True)

    @staticmethod
    def clear_session_queue(session: GuildSession) -> int:
        cleared = 0
        while True:
            try:
                session.queue.get_nowait()
            except asyncio.QueueEmpty:
                return cleared

            session.queue.task_done()
            cleared += 1

    async def player_loop(self, guild_id: int) -> None:
        while True:
            session = self.sessions.get(guild_id)
            if session is None:
                return

            request = session.pending_request
            if request is not None:
                session.pending_request = None
                pulled_from_queue = False
            else:
                request = await session.queue.get()
                pulled_from_queue = True

            requests = [request]
            try:
                profile = self.profile_store.get(request.user_id)
                texts = [request.text]

                while True:
                    try:
                        queued = session.queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break

                    queued_profile = self.profile_store.get(queued.user_id)
                    if queued.user_id != request.user_id or queued_profile != profile:
                        session.pending_request = queued
                        break

                    requests.append(queued)
                    texts.append(queued.text)

                batched_request = SpeechRequest(
                    user_id=request.user_id,
                    text=" ".join(texts),
                    queued_at=request.queued_at,
                )

                LOGGER.info(
                    "Batched speech requests guild=%s author=%s batch_size=%s text=%r",
                    guild_id,
                    batched_request.user_id,
                    len(requests),
                    batched_request.text,
                )

                active_session = self.sessions.get(guild_id)
                if active_session is None or active_session is not session:
                    continue

                if not session.voice_client.is_connected():
                    continue

                await self.play_file(session.voice_client, batched_request, profile)
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.exception(
                    "Failed to synthesize or play speech for guild %s", guild_id
                )
            finally:
                completed = len(requests)
                if not pulled_from_queue:
                    completed -= 1

                for _ in range(completed):
                    session.queue.task_done()

    async def play_file(
        self,
        voice_client: discord.VoiceClient,
        request: SpeechRequest,
        profile: UserVoiceProfile,
    ) -> None:
        while voice_client.is_playing() or voice_client.is_paused():
            await asyncio.sleep(0.1)

        queue: asyncio.Queue[object] = asyncio.Queue(maxsize=2)

        async def produce_audio() -> None:
            try:
                async for output_path in self.tts_service.synthesize_stream(request.text, profile):
                    await queue.put(output_path)
            except Exception as exc:
                await queue.put(exc)
            finally:
                await queue.put(None)

        producer = asyncio.create_task(produce_audio(), name="tts-stream-producer")
        first_audio = True
        chunk_index = 0

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item

                if not voice_client.is_connected():
                    LOGGER.info("Stopping streaming playback: voice client disconnected")
                    break

                chunk_index += 1
                if first_audio:
                    first_audio = False
                    LOGGER.info(
                        "First audio delay author=%s delay_ms=%.1f text=%r",
                        request.user_id,
                        (time.perf_counter() - request.queued_at) * 1000,
                        request.text,
                    )
                else:
                    LOGGER.info(
                        "Streaming audio chunk author=%s chunk=%s text=%r",
                        request.user_id,
                        chunk_index,
                        request.text,
                    )

                await self._play_audio_path(voice_client, item)
        finally:
            if not producer.done():
                producer.cancel()
                try:
                    await producer
                except asyncio.CancelledError:
                    pass

    @staticmethod
    async def _play_audio_path(voice_client: discord.VoiceClient, output_path: object) -> None:
        loop = asyncio.get_running_loop()
        finished = asyncio.Event()
        playback_error: list[Exception | None] = [None]

        def after_playback(error: Exception | None) -> None:
            playback_error[0] = error
            loop.call_soon_threadsafe(finished.set)

        if not voice_client.is_connected():
            return

        voice_client.play(discord.FFmpegPCMAudio(str(output_path)), after=after_playback)
        await finished.wait()

        if playback_error[0] is not None:
            raise RuntimeError("ffmpeg playback failed") from playback_error[0]


VoxCPMDiscordBot = TTSDiscordBot
