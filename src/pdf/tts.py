"""
Kokoro TTS synthesis engine wrapper.

Provides audio generation using hexgrad/Kokoro-82M with support for
voice styling (default: af_heart), speed adjustment, GPU acceleration,
and paragraph pacing.
"""

import logging
import os
import subprocess
import warnings
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Generator, List, Optional, Tuple, Union

# Suppress PyTorch, HuggingFace, and Transformers warnings and logs
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("kokoro").setLevel(logging.ERROR)

import numpy as np
import soundfile as sf
import torch


@contextmanager
def suppress_fd():
    """
    Context manager to completely suppress low-level C/Rust stdout and stderr.
    """
    null_fd = os.open(os.devnull, os.O_RDWR)
    save_stdout = os.dup(1)
    save_stderr = os.dup(2)
    try:
        os.dup2(null_fd, 1)
        os.dup2(null_fd, 2)
        yield
    finally:
        os.dup2(save_stdout, 1)
        os.dup2(save_stderr, 2)
        os.close(null_fd)
        os.close(save_stdout)
        os.close(save_stderr)


class KokoroTTS:
    """
    Wrapper around the Kokoro TTS engine.
    """

    def __init__(
        self,
        lang_code: str = "a",
        repo_id: str = "hexgrad/Kokoro-82M",
        device: Optional[str] = None,
    ):
        """
        Initialize the Kokoro TTS pipeline quietly without console noise.
        """
        self.lang_code = lang_code
        self.repo_id = repo_id

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        with suppress_fd():
            from kokoro import KPipeline
            self.pipeline = KPipeline(
                lang_code=self.lang_code,
                repo_id=self.repo_id,
                device=self.device,
            )

    def synthesize(
        self,
        text: str,
        voice: str = "af_heart",
        speed: float = 1.0,
        pause_between_paragraphs: float = 0.25,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> np.ndarray:
        """
        Synthesize text into a single combined numpy audio array at 24000 Hz.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return np.zeros(0, dtype=np.float32)

        sample_rate = 24000
        silence_samples = int(sample_rate * pause_between_paragraphs)
        silence = np.zeros(silence_samples, dtype=np.float32) if silence_samples > 0 else None

        all_audio_chunks: List[np.ndarray] = []
        total_paras = len(paragraphs)

        for p_idx, paragraph in enumerate(paragraphs):
            if progress_callback:
                progress_callback(p_idx + 1, total_paras, paragraph[:60])

            with suppress_fd():
                generator = self.pipeline(
                    paragraph,
                    voice=voice,
                    speed=speed,
                    split_pattern=r'\n+',
                )
                para_audio_chunks = []
                for res in generator:
                    if res.audio is not None:
                        if isinstance(res.audio, torch.Tensor):
                            chunk_np = res.audio.detach().cpu().numpy()
                        else:
                            chunk_np = np.array(res.audio, dtype=np.float32)
                        para_audio_chunks.append(chunk_np)

            if para_audio_chunks:
                para_audio = np.concatenate(para_audio_chunks, axis=0)
                all_audio_chunks.append(para_audio)

                if silence is not None and p_idx < total_paras - 1:
                    all_audio_chunks.append(silence)

        if not all_audio_chunks:
            return np.zeros(0, dtype=np.float32)

        return np.concatenate(all_audio_chunks, axis=0)

    def convert_to_audio_file(
        self,
        text: str,
        output_path: Union[str, Path],
        voice: str = "af_heart",
        speed: float = 1.0,
        pause_between_paragraphs: float = 0.25,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Path:
        """
        Synthesize text and save it to an audio file (.wav or .mp3).
        """
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        audio_data = self.synthesize(
            text=text,
            voice=voice,
            speed=speed,
            pause_between_paragraphs=pause_between_paragraphs,
            progress_callback=progress_callback,
        )

        sample_rate = 24000
        suffix = output_path.suffix.lower()

        if suffix in [".wav", ""]:
            final_path = output_path.with_suffix(".wav")
            sf.write(str(final_path), audio_data, sample_rate)
            return final_path
        elif suffix == ".mp3":
            temp_wav = output_path.with_suffix(".temp.wav")
            sf.write(str(temp_wav), audio_data, sample_rate)
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(temp_wav), "-b:a", "192k", str(output_path)],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                temp_wav.unlink(missing_ok=True)
                return output_path
            except (subprocess.SubprocessError, FileNotFoundError):
                temp_wav.rename(output_path.with_suffix(".wav"))
                return output_path.with_suffix(".wav")
        else:
            sf.write(str(output_path), audio_data, sample_rate)
            return output_path
