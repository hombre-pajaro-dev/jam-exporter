"""scrap detect | review | export"""

import argparse
from pathlib import Path

import numpy as np

from . import audio, detect, session as sess
from .review_server import serve

WAVEFORM_FPS = 2  # resolution of the waveform drawn in the review page


def main() -> None:
    ap = argparse.ArgumentParser(prog="scrap", description=__doc__)
    ap.add_argument("--sessions-dir", type=Path, default=Path("sessions"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("detect", help="find the Pieces in a recording (or re-detect an existing session)")
    d.add_argument("target", help="recording file, or an existing session folder/name")
    d.add_argument("--min-gap", type=float, default=detect.Params.min_gap,
                   help="seconds the music must stop to end a Piece (default %(default)s)")
    d.add_argument("--min-length", type=float, default=detect.Params.min_length,
                   help="ignore music shorter than this many seconds (default %(default)s)")
    d.add_argument("--threshold-db", type=float, default=None,
                   help="fixed loudness-floor threshold in dBFS instead of the adaptive one")
    d.add_argument("--force", action="store_true", help="discard an existing review.json")

    r = sub.add_parser("review", help="open the review page in the browser")
    r.add_argument("session")
    r.add_argument("--port", type=int, default=8765)

    e = sub.add_parser("export", help="cut the Kept Pieces into export/, named")
    e.add_argument("session")

    args = ap.parse_args()
    if args.cmd == "detect":
        _detect(args)
    elif args.cmd == "review":
        serve(sess.resolve(args.session, args.sessions_dir), args.port)
    else:
        s = sess.resolve(args.session, args.sessions_dir)
        files = sess.export(s)
        print(f"Exported {len(files)} Pieces to {s.export_dir}/")
        for f in files:
            print(f"  {f.name}")


def _detect(args: argparse.Namespace) -> None:
    target = Path(args.target)
    if target.is_file():
        s = sess.create(target, args.sessions_dir)
    else:
        s = sess.Session(target if target.is_dir() else args.sessions_dir / args.target)
        if not s.source.exists():
            raise SystemExit(f"{args.target!r} is neither a recording nor a session folder")
    if s.review_path.exists() and not args.force:
        raise SystemExit(f"{s.review_path} already has your review; pass --force to re-detect and discard it")
    s.review_path.unlink(missing_ok=True)

    print(f"Analysing {s.source} ...")
    duration = float(audio.probe(s.source)["duration"])
    db = audio.loudness_db(s.source, detect.FPS)
    params = detect.Params(min_gap=args.min_gap, min_length=args.min_length, threshold_db=args.threshold_db)
    thr, pieces = detect.find_pieces(db, params)

    step = detect.FPS // WAVEFORM_FPS
    waveform = db[: len(db) // step * step].reshape(-1, step).max(axis=1)
    s.save_detection({
        "duration": duration,
        "threshold_db": round(thr, 1),
        "params": {"min_gap": params.min_gap, "min_length": params.min_length},
        "waveform_fps": WAVEFORM_FPS,
        "waveform": np.round(waveform, 1).tolist(),
        "pieces": [{"start": round(a, 1), "end": round(b, 1)} for a, b in pieces],
    })
    sess.write_detected_pieces(s, pieces, duration)

    print(f"Threshold {thr:.1f} dBFS; {len(pieces)} Pieces:")
    for n, (a, b) in enumerate(pieces, 1):
        print(f"  {n:2d}  {sess.hms(a)}  {(b - a) / 60:5.1f} min")
    print(f"\nNext: scrap review {s.name}")
