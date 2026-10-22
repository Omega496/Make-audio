import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add src to path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from pdf.md_to_audio import main


def test_text_temporary_cleanup():
    """Verify that -t generates a temporary file, plays it, and deletes it upon completion."""
    played_file = None
    file_existed_during_playback = False

    def mock_play(audio_path, title=None):
        nonlocal played_file, file_existed_during_playback
        played_file = Path(audio_path)
        file_existed_during_playback = played_file.exists()
        return True

    def mock_synthesize(args, cleaned_text, output_audio_path):
        output_audio_path = Path(output_audio_path)
        output_audio_path.write_bytes(b"RIFFdummywavdata")
        return output_audio_path

    with patch("sys.argv", ["make-audio", "-t", "Quick testing sentence for playback."]), \
         patch("pdf.md_to_audio._run_local_synthesis", side_effect=mock_synthesize), \
         patch("pdf.md_to_audio.play_audio_in_terminal", side_effect=mock_play):
        main()

    assert played_file is not None, "play_audio_in_terminal was not called!"
    assert file_existed_during_playback, "Temporary file did not exist during playback!"
    assert not played_file.exists(), f"Temporary file {played_file} was not deleted after execution!"
    print("✓ test_text_temporary_cleanup passed")


def test_text_temporary_cleanup_on_interrupt():
    """Verify that -t deletes the temporary file even if KeyboardInterrupt occurs during playback."""
    played_file = None

    def mock_play_interrupt(audio_path, title=None):
        nonlocal played_file
        played_file = Path(audio_path)
        raise KeyboardInterrupt()

    def mock_synthesize(args, cleaned_text, output_audio_path):
        output_audio_path = Path(output_audio_path)
        output_audio_path.write_bytes(b"RIFFdummywavdata")
        return output_audio_path

    try:
        with patch("sys.argv", ["make-audio", "-t", "Interrupt test."]), \
             patch("pdf.md_to_audio._run_local_synthesis", side_effect=mock_synthesize), \
             patch("pdf.md_to_audio.play_audio_in_terminal", side_effect=mock_play_interrupt):
            main()
    except (KeyboardInterrupt, SystemExit):
        pass

    assert played_file is not None
    assert not played_file.exists(), f"Temporary file {played_file} was not deleted on KeyboardInterrupt!"
    print("✓ test_text_temporary_cleanup_on_interrupt passed")


def test_text_explicit_output_preserved():
    """Verify that when -o is explicitly provided, the output file is preserved."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target_path = Path(tmpdir) / "saved_audio.wav"

        def mock_synthesize(args, cleaned_text, output_audio_path):
            Path(output_audio_path).write_bytes(b"RIFFdummywavdata")
            return Path(output_audio_path)

        with patch("sys.argv", ["make-audio", "-t", "Save this text.", "-o", str(target_path), "--no-play"]), \
             patch("pdf.md_to_audio._run_local_synthesis", side_effect=mock_synthesize):
            main()

        assert target_path.exists(), "Target file should exist when -o is provided!"
        assert target_path.stat().st_size > 0
    print("✓ test_text_explicit_output_preserved passed")


def test_file_with_play_temporary_cleanup():
    """Verify that 'make-audio notes.md --play' uses a temporary file and deletes it after playback."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "notes.md"
        test_file.write_text("# Chapter 1\nThis is notes content.", encoding="utf-8")
        played_file = None
        file_existed_during_playback = False

        def mock_play(audio_path, title=None):
            nonlocal played_file, file_existed_during_playback
            played_file = Path(audio_path)
            file_existed_during_playback = played_file.exists()
            assert title == "notes.md"
            return True

        def mock_synthesize(args, cleaned_text, output_audio_path):
            Path(output_audio_path).write_bytes(b"RIFFdummywavdata")
            return Path(output_audio_path)

        with patch("sys.argv", ["make-audio", str(test_file), "--play"]), \
             patch("pdf.md_to_audio._run_local_synthesis", side_effect=mock_synthesize), \
             patch("pdf.md_to_audio.play_audio_in_terminal", side_effect=mock_play):
            main()

        assert played_file is not None, "play_audio_in_terminal was not called!"
        assert file_existed_during_playback, "Temporary file did not exist during playback!"
        assert not played_file.exists(), f"Temporary file {played_file} was not deleted after playback!"
        # Verify no notes.wav was created in working directory
        assert not (Path.cwd() / "notes.wav").exists(), "notes.wav should not be created in current directory when --play is used without -o!"
    print("✓ test_file_with_play_temporary_cleanup passed")


def test_file_with_play_cleanup_on_interrupt():
    """Verify that 'make-audio notes.md --play' deletes the temporary file even on KeyboardInterrupt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "notes.md"
        test_file.write_text("# Chapter 1\nThis is notes content.", encoding="utf-8")
        played_file = None

        def mock_play_interrupt(audio_path, title=None):
            nonlocal played_file
            played_file = Path(audio_path)
            raise KeyboardInterrupt()

        def mock_synthesize(args, cleaned_text, output_audio_path):
            Path(output_audio_path).write_bytes(b"RIFFdummywavdata")
            return Path(output_audio_path)

        try:
            with patch("sys.argv", ["make-audio", str(test_file), "--play"]), \
                 patch("pdf.md_to_audio._run_local_synthesis", side_effect=mock_synthesize), \
                 patch("pdf.md_to_audio.play_audio_in_terminal", side_effect=mock_play_interrupt):
                main()
        except (KeyboardInterrupt, SystemExit):
            pass

        assert played_file is not None
        assert not played_file.exists(), f"Temporary file {played_file} was not deleted on KeyboardInterrupt!"
    print("✓ test_file_with_play_cleanup_on_interrupt passed")


def test_file_with_play_explicit_output_preserved():
    """Verify that 'make-audio notes.md -o output.wav --play' preserves the output file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "notes.md"
        test_file.write_text("# Notes\nHello world.", encoding="utf-8")
        out_wav = Path(tmpdir) / "saved_notes.wav"
        played = False

        def mock_play(audio_path, title=None):
            nonlocal played
            played = True
            assert Path(audio_path) == out_wav
            return True

        def mock_synthesize(args, cleaned_text, output_audio_path):
            Path(output_audio_path).write_bytes(b"RIFFdummywavdata")
            return Path(output_audio_path)

        with patch("sys.argv", ["make-audio", str(test_file), "-o", str(out_wav), "--play"]), \
             patch("pdf.md_to_audio._run_local_synthesis", side_effect=mock_synthesize), \
             patch("pdf.md_to_audio.play_audio_in_terminal", side_effect=mock_play):
            main()

        assert played
        assert out_wav.exists(), "Explicit output file should not be deleted!"
        assert out_wav.stat().st_size > 0
    print("✓ test_file_with_play_explicit_output_preserved passed")


def test_mutually_exclusive_args():
    """Verify that specifying both file input and -t errors out."""
    with patch("sys.argv", ["make-audio", "file.md", "-t", "hello"]):
        try:
            main()
            assert False, "Should have exited with error"
        except SystemExit as e:
            assert e.code != 0
    print("✓ test_mutually_exclusive_args passed")


if __name__ == "__main__":
    test_text_temporary_cleanup()
    test_text_temporary_cleanup_on_interrupt()
    test_text_explicit_output_preserved()
    test_file_with_play_temporary_cleanup()
    test_file_with_play_cleanup_on_interrupt()
    test_file_with_play_explicit_output_preserved()
    test_mutually_exclusive_args()
    print("\nAll playback & cleanup tests passed successfully!")
