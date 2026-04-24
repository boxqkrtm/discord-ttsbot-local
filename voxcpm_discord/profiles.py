from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UserVoiceProfile:
    sample_voice: str | None = None
    voice_prompt_path: str | None = None
    prompt_text: str | None = None


class VoiceProfileStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.profile_dir = data_dir / "profiles"
        self.generated_dir = data_dir / "generated"
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)

    def get(self, user_id: int) -> UserVoiceProfile:
        profile_path = self._profile_path(user_id)
        if not profile_path.exists():
            return UserVoiceProfile()

        data = json.loads(profile_path.read_text(encoding="utf-8"))
        return UserVoiceProfile(
            sample_voice=data.get("sample_voice"),
            voice_prompt_path=data.get("voice_prompt_path"),
            prompt_text=data.get("prompt_text"),
        )

    def set_sample_voice(self, user_id: int, sample_voice: str) -> UserVoiceProfile:
        profile = self.get(user_id)
        profile.sample_voice = sample_voice.strip()
        self._save(user_id, profile)
        return profile

    def set_voice_prompt(
        self,
        user_id: int,
        suffix: str,
        content: bytes,
        prompt_text: str | None,
    ) -> UserVoiceProfile:
        user_dir = self.profile_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        profile = self.get(user_id)
        existing_prompt = (
            Path(profile.voice_prompt_path) if profile.voice_prompt_path else None
        )
        if (
            existing_prompt
            and existing_prompt.exists()
            and existing_prompt.suffix != suffix
        ):
            existing_prompt.unlink()

        prompt_path = user_dir / f"voice_prompt{suffix}"
        prompt_path.write_bytes(content)

        profile.voice_prompt_path = str(prompt_path)
        profile.prompt_text = prompt_text.strip() if prompt_text else None
        self._save(user_id, profile)
        return profile

    def _profile_path(self, user_id: int) -> Path:
        user_dir = self.profile_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / "profile.json"

    def _save(self, user_id: int, profile: UserVoiceProfile) -> None:
        profile_path = self._profile_path(user_id)
        payload = {
            "sample_voice": profile.sample_voice,
            "voice_prompt_path": profile.voice_prompt_path,
            "prompt_text": profile.prompt_text,
        }
        profile_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
