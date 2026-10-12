"""Thin wrappers around ffmpeg/ffprobe."""

import json
import subprocess
from pathlib import Path

import numpy as np

ANALYSIS_RATE = 8000  # Hz; plenty for loudness


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, check=True, text=True,
    ).stdout
    return json.loads(out)["format"]


def loudness_db(path: Path, fps: int) -> np.ndarray:
    """RMS loudness in dBFS, one value per 1/fps seconds."""
    raw = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path),
         "-ac", "1", "-ar", str(ANALYSIS_RATE), "-f", "s16le", "-"],
        capture_output=True, check=True,
    ).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    hop = ANALYSIS_RATE // fps
    n = len(x) // hop
    frames = x[: n * hop].reshape(n, hop)
    return 20 * np.log10(np.sqrt((frames**2).mean(axis=1)) + 1e-9)


def cut(src: Path, dst: Path, start: float, end: float) -> None:
    """Copy [start, end) of src into dst without re-encoding."""
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{start:.3f}", "-i", str(src),
         "-t", f"{end - start:.3f}", "-map", "0:a", "-c", "copy", "-movflags", "+faststart", str(dst)],
        check=True,
    )
