"""Find Pieces in a Session from its loudness.

A loud band playing never drops out, while talking and noodling between songs is
loud in bursts but keeps dipping into quiet. So instead of average loudness we track
the *floor*: the quiet end of a rolling few-second window. The band is playing while
the floor stays high; a Piece ends when the floor stays low for `min_gap` seconds.
"""

from dataclasses import dataclass

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

FPS = 10  # loudness frames per second


@dataclass(frozen=True)
class Params:
    min_gap: float = 8.0  # seconds the music must stop to end a Piece
    min_length: float = 15.0  # shorter bursts of music are ignored
    floor_window: float = 3.0  # seconds of audio the rolling floor looks at
    # Adaptive threshold: "playing" is within `threshold_offset` dB of the floor
    # level the band reaches during music (the 80th percentile of the floor, which
    # holds as long as at least ~20% of the Session is music).
    threshold_offset: float = 6.0
    threshold_db: float | None = None  # fixed threshold, overrides the adaptive one


def loudness_floor(db: np.ndarray, fps: int = FPS, window: float = 3.0) -> np.ndarray:
    w = max(1, int(window * fps))
    padded = np.pad(db, (w // 2, w - w // 2 - 1), mode="edge")
    return np.percentile(sliding_window_view(padded, w), 10, axis=1)


def threshold(floor: np.ndarray, params: Params) -> float:
    if params.threshold_db is not None:
        return params.threshold_db
    return float(np.percentile(floor, 80)) - params.threshold_offset


def find_pieces(db: np.ndarray, params: Params = Params(), fps: int = FPS) -> tuple[float, list[tuple[float, float]]]:
    """Return (threshold_db, [(start_s, end_s), ...]) for a loudness track in dB."""
    floor = loudness_floor(db, fps, params.floor_window)
    thr = threshold(floor, params)
    pieces: list[tuple[float, float]] = []
    for s, e in _runs(floor >= thr):
        start, end = s / fps, e / fps
        if pieces and start - pieces[-1][1] < params.min_gap:
            pieces[-1] = (pieces[-1][0], end)
        else:
            pieces.append((start, end))
    # The floor only rises once most of its window is music, so edges come out
    # about half a window late at the start and early at the end; undo that.
    half, total = params.floor_window / 2, len(db) / fps
    return thr, [(max(0.0, s - half), min(total, e + half)) for s, e in pieces if e - s >= params.min_length]


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    edges = np.flatnonzero(np.diff(np.concatenate(([0], mask.astype(np.int8), [0]))))
    return list(zip(edges[::2].tolist(), edges[1::2].tolist()))
