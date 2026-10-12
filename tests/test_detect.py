import numpy as np

from scrap.detect import FPS, Params, find_pieces

MUSIC, QUIET = -15.0, -40.0


def track(*parts: tuple[float, float]) -> np.ndarray:
    """Build a loudness track from (seconds, dB) parts."""
    return np.concatenate([np.full(int(sec * FPS), db) for sec, db in parts])


def talk(seconds: float) -> np.ndarray:
    """Talking between songs: loud bursts that keep dropping out."""
    pattern = np.tile([MUSIC] * 5 + [QUIET] * 5, int(seconds))  # 0.5 s on / 0.5 s off
    return pattern[: int(seconds * FPS)]


def starts(pieces):
    return [round(s) for s, _ in pieces]


def test_two_songs_separated_by_silence():
    _, pieces = find_pieces(track((60, MUSIC), (20, QUIET), (90, MUSIC)), Params(threshold_db=-25))
    assert starts(pieces) == [0, 80]


def test_talking_between_songs_ends_a_piece_even_though_it_is_loud():
    db = np.concatenate([track((60, MUSIC)), talk(30), track((60, MUSIC))])
    _, pieces = find_pieces(db, Params(threshold_db=-25))
    assert len(pieces) == 2


def test_short_dramatic_stop_does_not_split_a_piece():
    _, pieces = find_pieces(track((60, MUSIC), (4, QUIET), (60, MUSIC)), Params(threshold_db=-25))
    assert len(pieces) == 1


def test_short_noodle_is_ignored():
    _, pieces = find_pieces(track((60, MUSIC), (30, QUIET), (8, MUSIC), (30, QUIET)), Params(threshold_db=-25))
    assert len(pieces) == 1


def test_adaptive_threshold_sits_between_music_and_quiet():
    thr, pieces = find_pieces(track((300, MUSIC), (60, QUIET), (300, MUSIC)))
    assert QUIET < thr < MUSIC
    assert len(pieces) == 2
