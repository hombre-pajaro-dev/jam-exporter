"""A Session's working folder and the files in it.

sessions/<date>_<recording>/
  source.m4a       copy of the original recording
  detection.json   loudness waveform + auto-detected Pieces
  pieces/          one file per detected Piece (+ pieces.csv)
  review.json      the band's names, Keep/Drop marks, merges and splits
  export/          Kept Pieces, named, ready for Moises
"""

import csv
import json
import re
import unicodedata
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import audio

PAD = 2.0  # seconds of padding around each cut so nothing gets clipped
KEEP_MIN_LENGTH = 180.0  # Pieces shorter than this start out marked Drop (usually noodling)


@dataclass(frozen=True)
class Session:
    dir: Path

    @property
    def name(self) -> str:
        return self.dir.name

    @property
    def source(self) -> Path:
        return self.dir / "source.m4a"

    @property
    def detection_path(self) -> Path:
        return self.dir / "detection.json"

    @property
    def review_path(self) -> Path:
        return self.dir / "review.json"

    @property
    def pieces_dir(self) -> Path:
        return self.dir / "pieces"

    @property
    def export_dir(self) -> Path:
        return self.dir / "export"

    def load_detection(self) -> dict:
        return json.loads(self.detection_path.read_text())

    def save_detection(self, detection: dict) -> None:
        self.detection_path.write_text(json.dumps(detection))

    def load_review(self) -> list[dict]:
        """The reviewed Pieces, starting from the detected ones if there's no review yet."""
        if self.review_path.exists():
            return json.loads(self.review_path.read_text())["pieces"]
        return [
            {"id": i, "start": p["start"], "end": p["end"], "name": "",
             "keep": p["end"] - p["start"] >= KEEP_MIN_LENGTH}
            for i, p in enumerate(self.load_detection()["pieces"], 1)
        ]

    def save_review(self, pieces: list[dict]) -> None:
        tmp = self.review_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"pieces": pieces}, indent=1, ensure_ascii=False))
        tmp.replace(self.review_path)


def create(recording: Path, root: Path) -> Session:
    recorded = _recorded_date(recording)
    session = Session(root / f"{recorded}_{slug(recording.stem)}")
    session.dir.mkdir(parents=True, exist_ok=True)
    if not session.source.exists():
        shutil.copy2(recording, session.source)
    return session


def resolve(arg: str, root: Path) -> Session:
    for candidate in (Path(arg), root / arg):
        if (candidate / "detection.json").exists():
            return Session(candidate)
    raise SystemExit(f"No detected session at {arg!r} (looked in . and {root}/). Run `scrap detect` first.")


def write_detected_pieces(session: Session, pieces: list[tuple[float, float]], duration: float) -> None:
    shutil.rmtree(session.pieces_dir, ignore_errors=True)
    session.pieces_dir.mkdir()
    with open(session.pieces_dir / "pieces.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "start", "end", "duration", "file"])
        for n, (start, end) in enumerate(pieces, 1):
            file = f"{n:02d}_{hms(start, sep='-')}.m4a"
            audio.cut(session.source, session.pieces_dir / file, max(0, start - PAD), min(duration, end + PAD))
            w.writerow([n, hms(start), hms(end), hms(end - start), file])


def export(session: Session) -> list[Path]:
    duration = session.load_detection()["duration"]
    kept = [p for p in session.load_review() if p["keep"]]
    session.export_dir.mkdir(exist_ok=True)
    for old in session.export_dir.glob("*.m4a"):
        old.unlink()
    out = []
    for n, p in enumerate(kept, 1):
        title = slug(p["name"]) or "untitled"
        dst = session.export_dir / f"{n:02d}_{title}_{hms(p['start'], sep='-')}.m4a"
        audio.cut(session.source, dst, max(0, p["start"] - PAD), min(duration, p["end"] + PAD))
        out.append(dst)
    return out


def slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def hms(seconds: float, sep: str = ":") -> str:
    s = int(seconds)
    return f"{s // 3600}{sep}{s % 3600 // 60:02d}{sep}{s % 60:02d}"


def _recorded_date(recording: Path) -> str:
    created = audio.probe(recording).get("tags", {}).get("creation_time")
    if created:
        return datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d")
    return datetime.fromtimestamp(recording.stat().st_mtime).strftime("%Y-%m-%d")
