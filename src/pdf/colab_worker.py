#!/usr/bin/env python3
"""
Colab Worker Script for Kokoro TTS.

This script executes remotely on the Google Colab VM.
It reads /content/make_audio_job.json, initializes Kokoro TTS
with CUDA GPU acceleration, synthesizes the audio, and writes
/content/make_audio_output.wav.
"""

import json
import os
import sys
import time
from pathlib import Path

# Silence external warnings
import warnings
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

# Setup espeakng-loader if available
try:
    import espeakng_loader
    from phonemizer.backend.espeak.wrapper import EspeakWrapper
    EspeakWrapper.set_library(espeakng_loader.get_library_path())
    EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
except Exception:
    pass

import numpy as np
import soundfile as sf
import torch
from kokoro import KPipeline


def run_worker():
    job_file = Path("/content/make_audio_job.json")
    if not job_file.exists():
        print(f"[colab-worker] ERROR: Job file not found at {job_file}", file=sys.stderr)
        sys.exit(1)

    with open(job_file, "r", encoding="utf-8") as f:
        job = json.load(f)

    text = job.get("text", "").strip()
    voice = job.get("voice", "af_heart")
    speed = float(job.get("speed", 1.0))
    pause_between_paragraphs = float(job.get("pause_between_paragraphs", 0.25))
    output_path = Path(job.get("output_path", "/content/make_audio_output.wav"))

    if not text:
        print("[colab-worker] ERROR: Input text is empty.", file=sys.stderr)
        sys.exit(1)

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    total_paras = len(paragraphs)
    word_count = sum(len(p.split()) for p in paragraphs)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[colab-worker] Compute device: {device.upper()}")
    if device == "cuda":
        print(f"[colab-worker] GPU: {torch.cuda.get_device_name(0)}")

    print(f"[colab-worker] Initializing Kokoro pipeline (voice: {voice}, speed: {speed})...")
    start_init = time.time()
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device=device)
    print(f"[colab-worker] Pipeline ready in {time.time() - start_init:.2f}s")

    sample_rate = 24000
    silence_samples = int(sample_rate * pause_between_paragraphs)
    silence = np.zeros(silence_samples, dtype=np.float32) if silence_samples > 0 else None

    print(f"[colab-worker] Synthesizing {total_paras} paragraphs ({word_count} words)...")
    all_chunks = []
    start_synth = time.time()

    for p_idx, paragraph in enumerate(paragraphs, 1):
        clean_snippet = paragraph.replace("\n", " ").strip()
        if len(clean_snippet) > 60:
            clean_snippet = clean_snippet[:57] + "..."
        pct = (p_idx / total_paras) * 100
        print(f"[colab-worker] [{pct:5.1f}%] [{p_idx:02d}/{total_paras:02d}] Generating: \"{clean_snippet}\"")

        generator = pipeline(
            paragraph,
            voice=voice,
            speed=speed,
            split_pattern=r"\n+",
        )
        para_chunks = []
        for res in generator:
            if res.audio is not None:
                if isinstance(res.audio, torch.Tensor):
                    chunk_np = res.audio.detach().cpu().numpy()
                else:
                    chunk_np = np.array(res.audio, dtype=np.float32)
                para_chunks.append(chunk_np)

        if para_chunks:
            all_chunks.append(np.concatenate(para_chunks, axis=0))
            if silence is not None and p_idx < total_paras:
                all_chunks.append(silence)

    if not all_chunks:
        print("[colab-worker] WARNING: No audio chunks produced.", file=sys.stderr)
        final_audio = np.zeros(0, dtype=np.float32)
    else:
        final_audio = np.concatenate(all_chunks, axis=0)

    duration_sec = len(final_audio) / sample_rate
    elapsed = time.time() - start_synth
    rtf = elapsed / duration_sec if duration_sec > 0 else 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), final_audio, sample_rate)

    print(f"[colab-worker] Synthesis completed in {elapsed:.2f}s (audio duration: {duration_sec:.1f}s, RTF: {rtf:.3f})")
    print(f"[colab-worker] Audio saved to: {output_path}")
    print("[colab-worker] SUCCESS")


if __name__ == "__main__":
    run_worker()
