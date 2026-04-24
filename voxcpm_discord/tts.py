from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

import soundfile as sf
import torch
from huggingface_hub import snapshot_download
from voxcpm import VoxCPM
from voxcpm.modules.minicpm4.model import MiniCPMAttention, apply_rotary_pos_emb

from voxcpm_discord.config import (
    DEFAULT_CFG_VALUE,
    DEFAULT_INFERENCE_TIMESTEPS,
    LOGGER,
)
from voxcpm_discord.profiles import UserVoiceProfile


_CPU_ATTENTION_PATCHED = False


def _patch_voxcpm_cpu_attention() -> None:
    global _CPU_ATTENTION_PATCHED
    if _CPU_ATTENTION_PATCHED:
        return

    original_forward_step = MiniCPMAttention.forward_step

    def cpu_safe_forward_step(
        self: MiniCPMAttention,
        hidden_states: torch.Tensor,
        position_emb: tuple[torch.Tensor, torch.Tensor],
        position_id: int,
        kv_cache: tuple[torch.Tensor, torch.Tensor],
    ) -> torch.Tensor:
        if hidden_states.device.type != "cpu":
            return original_forward_step(self, hidden_states, position_emb, position_id, kv_cache)

        bsz, _ = hidden_states.size()
        query_states = self.q_proj(hidden_states)
        key_states = self.k_proj(hidden_states)
        value_states = self.v_proj(hidden_states)

        query_states = query_states.view(bsz, 1, self.num_heads, self.head_dim).transpose(1, 2)
        key_states = key_states.view(bsz, 1, self.num_key_value_heads, self.head_dim).transpose(1, 2)
        value_states = value_states.view(bsz, 1, self.num_key_value_heads, self.head_dim).transpose(1, 2)

        if position_emb is not None:
            cos, sin = position_emb
            query_states, key_states = apply_rotary_pos_emb(query_states, key_states, cos, sin)

        key_cache, value_cache = kv_cache
        key_cache[:, :, position_id, :] = key_states
        value_cache[:, :, position_id, :] = value_states

        visible = position_id + 1
        key_states = key_cache[:, :, :visible, :]
        value_states = value_cache[:, :, :visible, :]

        if self.num_key_value_heads != self.num_heads:
            repeat_factor = self.num_heads // self.num_key_value_heads
            key_states = key_states.repeat_interleave(repeat_factor, dim=1)
            value_states = value_states.repeat_interleave(repeat_factor, dim=1)

        attn_scores = torch.matmul(
            query_states.to(torch.float32),
            key_states.transpose(-1, -2).to(torch.float32),
        ) / (self.head_dim ** 0.5)
        attn_weights = torch.softmax(attn_scores, dim=-1).to(query_states.dtype)
        attn_output = torch.matmul(attn_weights, value_states)
        attn_output = attn_output.transpose(1, 2).contiguous()
        attn_output = attn_output.reshape(bsz, self.num_heads * self.head_dim)
        return self.o_proj(attn_output)

    MiniCPMAttention.forward_step = cpu_safe_forward_step
    _CPU_ATTENTION_PATCHED = True


class VoxCPMService:
    def __init__(self, model_name: str, output_dir: Path, model_data_dir: Path) -> None:
        self.model_name = model_name
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model_config_dir = model_data_dir / "model_overrides"
        self.model_config_dir.mkdir(parents=True, exist_ok=True)
        self._model: VoxCPM | None = None
        self._model_lock = asyncio.Lock()

    async def synthesize(self, text: str, profile: UserVoiceProfile) -> Path:
        model = await self._ensure_model()
        output_path = self.output_dir / f"{uuid.uuid4().hex}.wav"
        kwargs = self._build_generation_kwargs(text, profile)
        await asyncio.to_thread(self._synthesize_sync, model, output_path, kwargs)
        return output_path

    async def warmup(self) -> None:
        await self._ensure_model()

    async def _ensure_model(self) -> VoxCPM:
        async with self._model_lock:
            if self._model is None:
                device, dtype = self._resolve_runtime_config()
                model_source = self._prepare_model_source(device, dtype)
                optimize = device == "cuda"
                LOGGER.info(
                    "Loading model %s with device=%s dtype=%s optimize=%s",
                    self.model_name,
                    device,
                    dtype,
                    optimize,
                )
                self._model = await asyncio.to_thread(
                    VoxCPM.from_pretrained,
                    model_source,
                    load_denoiser=False,
                    optimize=optimize,
                )
        return self._model

    def _resolve_runtime_config(self) -> tuple[str, str]:
        requested_device = os.getenv("VOXCPM_DEVICE", "auto").strip().lower()
        requested_dtype = os.getenv("VOXCPM_DTYPE", "bfloat16").strip().lower()

        if requested_device in {"", "auto"}:
            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        elif requested_device in {"cuda", "cpu", "mps"}:
            device = requested_device
        else:
            raise ValueError(f"Unsupported VOXCPM_DEVICE: {requested_device}")

        if requested_dtype in {"", "auto"}:
            dtype = "bfloat16" if device == "cuda" else "float32"
        elif requested_dtype in {"bfloat16", "bf16", "float16", "fp16", "float32", "fp32"}:
            dtype = requested_dtype
        else:
            raise ValueError(f"Unsupported VOXCPM_DTYPE: {requested_dtype}")

        if device == "cpu" and dtype in {"float16", "fp16", "bfloat16", "bf16"}:
            LOGGER.warning(
                "CPU mode requested with dtype=%s; falling back to float32 for compatibility",
                dtype,
            )
            dtype = "float32"

        if device == "cpu":
            _patch_voxcpm_cpu_attention()

        return device, dtype

    def _prepare_model_source(self, device: str, dtype: str) -> str:
        if device == "cuda" and dtype in {"bfloat16", "bf16"}:
            return self.model_name

        source_path = self._resolve_model_path()
        config = json.loads((source_path / "config.json").read_text(encoding="utf-8"))
        config["device"] = device
        config["dtype"] = dtype

        override_key = hashlib.sha256(
            f"{source_path.resolve()}:{device}:{dtype}".encode("utf-8")
        ).hexdigest()[:12]
        override_dir = self.model_config_dir / override_key
        override_dir.mkdir(parents=True, exist_ok=True)

        for entry in source_path.iterdir():
            target = override_dir / entry.name
            if entry.name == "config.json":
                target.write_text(
                    json.dumps(config, ensure_ascii=True, indent=2),
                    encoding="utf-8",
                )
                continue

            if target.exists():
                continue

            try:
                target.symlink_to(entry.resolve(), target_is_directory=entry.is_dir())
            except OSError:
                if entry.is_dir():
                    shutil.copytree(entry, target)
                else:
                    shutil.copy2(entry, target)

        return str(override_dir)

    def _resolve_model_path(self) -> Path:
        model_path = Path(self.model_name)
        if model_path.is_dir():
            return model_path

        return Path(snapshot_download(repo_id=self.model_name))

    def _build_generation_kwargs(
        self, text: str, profile: UserVoiceProfile
    ) -> dict[str, Any]:
        synthesized_text = text
        if profile.sample_voice:
            synthesized_text = f"({profile.sample_voice}){text}"

        kwargs: dict[str, Any] = {
            "text": synthesized_text,
            "cfg_value": DEFAULT_CFG_VALUE,
            "inference_timesteps": DEFAULT_INFERENCE_TIMESTEPS,
        }

        if profile.voice_prompt_path:
            kwargs["reference_wav_path"] = profile.voice_prompt_path

        if profile.voice_prompt_path and profile.prompt_text:
            kwargs["prompt_wav_path"] = profile.voice_prompt_path
            kwargs["prompt_text"] = profile.prompt_text

        return kwargs

    @staticmethod
    def _synthesize_sync(
        model: VoxCPM, output_path: Path, kwargs: dict[str, Any]
    ) -> None:
        wav = model.generate(**kwargs)
        sf.write(output_path, wav, model.tts_model.sample_rate)
