from pdf.cleaner import clean_markdown_for_tts, clean_bengali_markdown, is_bengali_text

__all__ = [
    "clean_markdown_for_tts",
    "clean_bengali_markdown",
    "is_bengali_text",
    "KokoroTTS",
    "ColabTTS",
    "play_audio_in_terminal",
    "main",
]


def __getattr__(name):
    if name == "KokoroTTS":
        from pdf.tts import KokoroTTS
        return KokoroTTS
    elif name == "ColabTTS":
        from pdf.colab_tts import ColabTTS
        return ColabTTS
    elif name == "play_audio_in_terminal":
        from pdf.player import play_audio_in_terminal
        return play_audio_in_terminal
    elif name == "main":
        from pdf.md_to_audio import main
        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


