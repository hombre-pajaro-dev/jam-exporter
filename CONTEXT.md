# Music Scrapper

Tooling for mining long jam-session recordings: finding where each original musical idea was played, so the band can name, revisit and develop them into songs.

## Language

**Session**:
One continuous source recording of a jam (e.g. a 2-hour Voice Memo).
_Avoid_: Recording, file, track

**Segment**:
A contiguous time range of a Session classified as music, talk/tuning, or silence.
_Avoid_: Clip, chunk, part

**Piece**:
One continuous stretch of music in a Session, from when the band starts playing until the music actually stops.
_Avoid_: Song (reserve for a finished composition), take, track, idea

**Review**:
The band's manual pass over detected Pieces: listening, naming, marking each **Keep** or **Drop**, and fixing detection mistakes by merging or splitting Pieces.

**Export**:
The named audio files of all Kept Pieces, ready to upload to Moises.

## Relationships

- A **Session** is divided into many **Segments**
- Each music **Segment** is exactly one **Piece**
- **Pieces** are independent: no grouping of repeated attempts at the same idea
- During **Review** each **Piece** gets a name and a Keep/Drop mark; only Kept **Pieces** go into the **Export**

## Example dialogue

> **Dev:** "The groove at 0:12 stops, you talk for 15 seconds, then play it again — one Piece or two?"
> **Band:** "Two **Pieces**. We'll throw out the bad one by hand; we don't care that it was a retry."

## Flagged ambiguities

- "song" was used both for what was played and for finished compositions — resolved: what was played is a **Piece**; "song" is only what a Piece might become later.
- A change of rhythm or chord progression mid-playing does **not** start a new **Piece**; only the music actually stopping (silence/talk) does. A brief dramatic stop or quiet breakdown inside a song is not a stop — if detection splits there, the band merges it back during **Review**.
- "Take" (repeated attempts at the same idea) was considered and dropped — the band curates duplicates manually.
- "Representative pieces" — automatic "best part" detection was rejected (no algorithm knows which riff matters); manual Highlights were deferred. The band trims in Moises.
- Covers are out of scope for now; the Session is mostly original material (~8 songs expected).
