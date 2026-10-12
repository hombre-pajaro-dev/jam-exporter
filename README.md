# music scrapper

Finds the **Pieces** in a long jam **Session** recording, lets the band **Review** them (name, keep/drop,
merge, split), and **Exports** the keepers as named files ready to drag into Moises. See `CONTEXT.md`
for the vocabulary.

## Setup

Needs `ffmpeg` (`brew install ffmpeg`) and Python ≥ 3.11.

```sh
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/pip install -e '.[dev]'
source .venv/bin/activate
```

## Use

```sh
scrap detect "New Recording 57.m4a"     # → sessions/2026-10-11_new-recording-57/
scrap review 2026-10-11_new-recording-57 # opens the review page in your browser
scrap export 2026-10-11_new-recording-57 # → .../export/*.m4a, upload these to Moises
```

Detection splits wherever the music stops for 8+ seconds and ignores music shorter than 15 seconds.
If it splits songs too eagerly or glues them together, re-run with different settings
(this discards your review, so tune before reviewing):

```sh
scrap detect 2026-10-11_new-recording-57 --min-gap 12 --force
```

Cuts are stream-copied (no re-encoding, no quality loss) with 2 s of padding on each side.
