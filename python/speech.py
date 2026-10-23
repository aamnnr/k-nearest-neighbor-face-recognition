"""Notifikasi suara (Text-to-Speech Bahasa Indonesia)."""

from __future__ import annotations

import logging
import os
import tempfile

logger = logging.getLogger(__name__)


def speak(text: str, enabled: bool = True) -> None:
    """Ucapkan `text`. Kegagalan (mis. tanpa internet) tidak menghentikan program."""
    print(f"[SUARA] {text}")
    if not enabled:
        return

    try:
        from gtts import gTTS
        from playsound import playsound
    except ImportError:
        logger.warning("gTTS/playsound tidak terpasang; notifikasi suara dilewati.")
        return

    fd, audio_path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        gTTS(text=text, lang="id").save(audio_path)
        playsound(audio_path)
    except Exception as exc:  # gTTS butuh internet; playsound bergantung pada OS
        logger.warning("Gagal memutar suara: %s", exc)
    finally:
        try:
            os.remove(audio_path)
        except OSError:
            pass
