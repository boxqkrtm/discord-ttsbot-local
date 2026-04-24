from __future__ import annotations

import re


_DISCORD_EMOJI_RE = re.compile(r"<a?:\w+:\d+>")
_UNICODE_EMOJI_RE = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002702-\U000027B0"
    "]+",
)
_KEYCAP_EMOJI_RE = re.compile(r"[0-9#*]\ufe0f?\u20e3")
_HANGUL_COMPAT_JAMO_NAMES = {
    "ㄱ": "기역",
    "ㄲ": "쌍기역",
    "ㄳ": "기역시옷",
    "ㄴ": "니은",
    "ㄵ": "니은지읒",
    "ㄶ": "니은히읗",
    "ㄷ": "디귿",
    "ㄸ": "쌍디귿",
    "ㄹ": "리을",
    "ㄺ": "리을기역",
    "ㄻ": "리을미음",
    "ㄼ": "리을비읍",
    "ㄽ": "리을시옷",
    "ㄾ": "리을티읕",
    "ㄿ": "리을피읖",
    "ㅀ": "리을히읗",
    "ㅁ": "미음",
    "ㅂ": "비읍",
    "ㅃ": "쌍비읍",
    "ㅄ": "비읍시옷",
    "ㅅ": "시옷",
    "ㅆ": "쌍시옷",
    "ㅇ": "이응",
    "ㅈ": "지읒",
    "ㅉ": "쌍지읒",
    "ㅊ": "치읓",
    "ㅋ": "키읔",
    "ㅌ": "티읕",
    "ㅍ": "피읖",
    "ㅎ": "히읗",
    "ㅏ": "아",
    "ㅐ": "애",
    "ㅑ": "야",
    "ㅒ": "얘",
    "ㅓ": "어",
    "ㅔ": "에",
    "ㅕ": "여",
    "ㅖ": "예",
    "ㅗ": "오",
    "ㅘ": "와",
    "ㅙ": "왜",
    "ㅚ": "외",
    "ㅛ": "요",
    "ㅜ": "우",
    "ㅝ": "워",
    "ㅞ": "웨",
    "ㅟ": "위",
    "ㅠ": "유",
    "ㅡ": "으",
    "ㅢ": "의",
    "ㅣ": "이",
}
_HANGUL_COMPAT_JAMO_RE = re.compile(
    "|".join(
        re.escape(jamo)
        for jamo in sorted(_HANGUL_COMPAT_JAMO_NAMES, key=len, reverse=True)
    )
)


def strip_emojis(text: str) -> str:
    text = _DISCORD_EMOJI_RE.sub("", text)
    text = _KEYCAP_EMOJI_RE.sub("", text)
    text = _UNICODE_EMOJI_RE.sub("", text)
    return text.replace("\u200d", "").replace("\ufe0f", "").strip()


def process_tts_text(text: str) -> str:
    text = strip_emojis(text)
    text = _HANGUL_COMPAT_JAMO_RE.sub(
        lambda match: f" {_HANGUL_COMPAT_JAMO_NAMES[match.group(0)]} ", text
    )
    return " ".join(text.split())
