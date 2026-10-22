"""
Terminal audio playback module.

Provides interactive audio playback inside the terminal with controls for:
- Play / Pause (Space)
- Fast forward / Rewind (Arrow keys)
- Playback speed adjustment ([ and ])
- Volume adjustment (9 and 0)
- Stop and quit (q or Esc)

Uses mpv with automatic fallback to ffplay or aplay.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def play_audio_in_terminal(audio_path: Path, title: Optional[str] = None) -> bool:
    """
    Play an audio file interactively in the terminal with user controls.
    """
    audio_path = Path(audio_path).resolve()
    if not audio_path.exists():
        print(f"Error: Audio file not found at {audio_path}", file=sys.stderr)
        return False

    mpv_bin = shutil.which("mpv")
    ffplay_bin = shutil.which("ffplay")
    aplay_bin = shutil.which("aplay")

    print("\n" + "=" * 60)
    if title:
        print(f"🔊 Playing: \"{title}\"")
    else:
        print(f"🔊 Playing: {audio_path.name}")
    print("=" * 60)

    if mpv_bin:
        print("⌨️  Playback Controls:")
        print("  [Space]     Pause / Resume")
        print("  [← / →]     Seek backward / forward 5s")
        print("  [↓ / ↑]     Seek backward / forward 1m")
        print("  [[ / ]]     Decrease / Increase speed by 10%")
        print("  [{ / }]     Halve / Double speed")
        print("  [Backspace] Reset speed to 1.0x")
        print("  [9 / 0]     Decrease / Increase volume")
        print("  [q / Esc]   Stop & Quit (Session stays open after audio finishes)")
        print("=" * 60 + "\n")

        cmd = [
            mpv_bin,
            "--no-video",
            "--term-osd-bar",
            "--keep-open=yes",
            str(audio_path),
        ]
        try:
            res = subprocess.run(cmd, check=False)
            if res.returncode in (-2, 130):
                raise KeyboardInterrupt()
            return True
        except KeyboardInterrupt:
            print("\nPlayback stopped.")
            raise

    elif ffplay_bin:
        print("⌨️  Playback Controls (ffplay):")
        print("  [Space]     Pause / Resume")
        print("  [← / →]     Seek 10s")
        print("  [q / Esc]   Stop & Quit (Session stays open after audio finishes)")
        print("=" * 60 + "\n")

        cmd = [
            ffplay_bin,
            "-nodisp",
            str(audio_path),
        ]
        try:
            res = subprocess.run(cmd, check=False)
            if res.returncode in (-2, 130):
                raise KeyboardInterrupt()
            return True
        except KeyboardInterrupt:
            print("\nPlayback stopped.")
            raise

    elif aplay_bin:
        print("Playing audio via aplay (Ctrl+C to stop)...")
        try:
            res = subprocess.run([aplay_bin, str(audio_path)], check=False)
            if res.returncode in (-2, 130):
                raise KeyboardInterrupt()
            return True
        except KeyboardInterrupt:
            print("\nPlayback stopped.")
            raise
    else:
        print(
            "Error: No audio player found on system (mpv, ffplay, or aplay).\n"
            "Please install mpv ('sudo apt install mpv') for terminal playback.",
            file=sys.stderr,
        )
        return False
