"""
Google Colab TTS Engine Orchestrator.

Manages remote VM lifecycle, dependency setup, payload upload,
GPU-accelerated synthesis via Google Colab CLI, and audio retrieval.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional, Union

logger = logging.getLogger("colab_tts")


class ColabTTSError(Exception):
    """Custom exception raised when remote Colab TTS fails."""
    pass


class ColabTTS:
    """
    Manages audio synthesis on a Google Colab GPU/CPU runtime via colab CLI.
    """

    def __init__(
        self,
        session_name: str = "make-audio",
        gpu: Optional[str] = "T4",
        timeout: float = 600.0,
        verbose: bool = False,
    ):
        self.session_name = session_name
        self.gpu = gpu if (gpu and gpu.lower() != "none") else None
        self.timeout = timeout
        self.verbose = verbose
        self.worker_script = Path(__file__).resolve().parent / "colab_worker.py"

        if not self.worker_script.exists():
            raise ColabTTSError(f"Worker script not found at {self.worker_script}")

        self._check_colab_installed()

    def _check_colab_installed(self) -> None:
        """Verify the colab CLI binary is available."""
        if not shutil.which("colab"):
            raise ColabTTSError(
                "Google Colab CLI ('colab') was not found in PATH.\n"
                "Please ensure google-colab-cli is installed (e.g. 'uv tool install google-colab-cli' or 'pip install google-colab-cli')."
            )

    def is_session_active(self) -> bool:
        """Check if the designated session is currently running."""
        try:
            res = subprocess.run(
                ["colab", "status", "-s", self.session_name],
                capture_output=True,
                text=True,
                timeout=15,
            )
            output = res.stdout + res.stderr
            if "not found" in output.lower() or "no active sessions" in output.lower():
                return False
            # Also verify against server session list
            sessions_res = subprocess.run(
                ["colab", "sessions"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return self.session_name in sessions_res.stdout
        except Exception as e:
            if self.verbose:
                print(f"[colab-client] Error checking session status: {e}")
            return False

    def ensure_session(self) -> None:
        """Ensure the Colab VM session is active and dependencies are installed."""
        if self.is_session_active():
            if self.verbose:
                print(f"[colab-client] Using active Colab session '{self.session_name}'.")
        else:
            if self.verbose:
                print(f"[colab-client] Provisioning Colab session '{self.session_name}'" +
                      (f" with {self.gpu} GPU..." if self.gpu else "..."))
            cmd = ["colab", "new", "-s", self.session_name]
            if self.gpu:
                cmd.extend(["--gpu", self.gpu])

            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                err_msg = (res.stderr or res.stdout).strip()
                if self.gpu:
                    if self.verbose:
                        print(f"[colab-client] Warning: GPU allocation failed ({err_msg}). Falling back to CPU...")
                    cmd_cpu = ["colab", "new", "-s", self.session_name]
                    res_cpu = subprocess.run(cmd_cpu, capture_output=True, text=True)
                    if res_cpu.returncode != 0:
                        raise ColabTTSError(
                            f"Failed to create Colab session: {res_cpu.stderr or res_cpu.stdout}"
                        )
                else:
                    raise ColabTTSError(f"Failed to create Colab session: {err_msg}")

            if self.verbose:
                print(f"[colab-client] Colab session '{self.session_name}' created successfully.")

        self._ensure_remote_dependencies()

    def _ensure_remote_dependencies(self) -> None:
        """Ensure kokoro, soundfile, and espeakng-loader are installed on the Colab VM."""
        check_proc = subprocess.run(
            ["colab", "exec", "-s", self.session_name, "--timeout", "15"],
            input="import kokoro, soundfile\n",
            capture_output=True,
            text=True,
        )
        if check_proc.returncode == 0 and "error" not in check_proc.stderr.lower():
            if self.verbose:
                print("[colab-client] Remote dependencies verified.")
            return

        if self.verbose:
            print("[colab-client] Installing remote dependencies on Colab VM (kokoro, soundfile, espeakng-loader)...")
        install_proc = subprocess.run(
            ["colab", "install", "-s", self.session_name, "kokoro>=0.9.4", "soundfile>=0.14.0", "espeakng-loader"],
            capture_output=not self.verbose,
            text=True,
        )
        if install_proc.returncode != 0:
            err = install_proc.stderr if hasattr(install_proc, "stderr") else "Installation failed"
            raise ColabTTSError(f"Failed to install dependencies on Colab VM: {err}")
        if self.verbose:
            print("[colab-client] Remote dependencies installed successfully.")

    def convert_to_audio_file(
        self,
        text: str,
        output_path: Union[str, Path],
        voice: str = "af_heart",
        speed: float = 1.0,
        pause_between_paragraphs: float = 0.25,
        stop_session_after: bool = False,
    ) -> Path:
        """
        Upload text job to Colab, execute GPU Kokoro synthesis, and download audio.
        """
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        suffix = output_path.suffix.lower()

        # Step 1: Ensure active session
        self.ensure_session()

        # Step 2: Prepare temporary job JSON payload
        remote_output_wav = "/content/make_audio_output.wav"
        job_data = {
            "text": text,
            "voice": voice,
            "speed": speed,
            "pause_between_paragraphs": pause_between_paragraphs,
            "output_path": remote_output_wav,
            "verbose": self.verbose,
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(job_data, f, ensure_ascii=False)
            local_job_path = f.name

        try:
            # Step 3: Upload job file to Colab
            if self.verbose:
                print("[colab-client] Uploading narration payload to Colab...")
            upload_res = subprocess.run(
                ["colab", "upload", "-s", self.session_name, local_job_path, "/content/make_audio_job.json"],
                capture_output=True,
                text=True,
            )
            if upload_res.returncode != 0:
                raise ColabTTSError(f"Failed to upload job to Colab: {upload_res.stderr or upload_res.stdout}")

            # Step 4: Run remote worker via colab exec
            word_count = len(text.split())
            estimated_timeout = max(self.timeout, float(word_count * 2.0))
            if self.verbose:
                print(f"[colab-client] Executing remote synthesis (timeout: {estimated_timeout:.0f}s)...")

            exec_cmd = [
                "colab", "exec",
                "-s", self.session_name,
                "-f", str(self.worker_script),
                "--timeout", str(estimated_timeout),
            ]

            proc = subprocess.Popen(
                exec_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            worker_success = False
            captured_lines = []
            for line in proc.stdout:
                line_str = line.strip()
                if line_str:
                    captured_lines.append(line_str)
                if "[colab-worker] SUCCESS" in line_str:
                    worker_success = True
                elif self.verbose and line_str:
                    print(line_str)

            proc.wait()
            if proc.returncode != 0 or not worker_success:
                err_details = "\n".join(captured_lines)
                raise ColabTTSError(
                    f"Remote Kokoro synthesis failed (exit code {proc.returncode}):\n{err_details}"
                )

            # Step 5: Download generated audio
            local_wav = output_path.with_suffix(".wav")
            if self.verbose:
                print(f"[colab-client] Downloading generated audio from Colab...")
            download_res = subprocess.run(
                ["colab", "download", "-s", self.session_name, remote_output_wav, str(local_wav)],
                capture_output=True,
                text=True,
            )
            if download_res.returncode != 0 or not local_wav.exists() or local_wav.stat().st_size == 0:
                raise ColabTTSError(
                    f"Failed to download audio from Colab: {download_res.stderr or download_res.stdout}"
                )

            # Step 6: Convert to MP3 if requested
            if suffix == ".mp3":
                try:
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", str(local_wav), "-b:a", "192k", str(output_path)],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    local_wav.unlink(missing_ok=True)
                    final_path = output_path
                except (subprocess.SubprocessError, FileNotFoundError):
                    if self.verbose:
                        print("[colab-client] ffmpeg not available for mp3 encoding; keeping .wav format.")
                    final_path = local_wav
            else:
                final_path = local_wav

            return final_path

        finally:
            # Clean up local temporary job file
            if os.path.exists(local_job_path):
                try:
                    os.unlink(local_job_path)
                except OSError:
                    pass

            # Step 7: Teardown session if requested
            if stop_session_after:
                self.stop_session(self.session_name, verbose=self.verbose)

    @classmethod
    def stop_session(cls, session_name: str = "make-audio", verbose: bool = False) -> bool:
        """Terminate a running Colab session quietly unless verbose is set."""
        if verbose:
            print(f"[colab-client] Stopping Colab session '{session_name}'...")
        res = subprocess.run(
            ["colab", "stop", "-s", session_name],
            capture_output=True,
            text=True,
        )
        output = (res.stdout + res.stderr).strip()
        if verbose and output:
            print(f"[colab-client] {output}")
        return res.returncode == 0
