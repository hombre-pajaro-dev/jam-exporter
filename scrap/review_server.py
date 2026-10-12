"""Tiny local server for the review page: serves the page, the Session audio, and saves review.json."""

import json
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources

from .session import Session

PAGE = resources.files("scrap").joinpath("review.html")


def serve(session: Session, port: int) -> None:
    detection = session.load_detection()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                self._send(200, "text/html; charset=utf-8", PAGE.read_bytes())
            elif self.path == "/api/session":
                body = {
                    "name": session.name,
                    "duration": detection["duration"],
                    "waveform": detection["waveform"],
                    "waveformFps": detection["waveform_fps"],
                    "thresholdDb": detection["threshold_db"],
                    "pieces": session.load_review(),
                }
                self._send(200, "application/json", json.dumps(body).encode())
            elif self.path == "/audio":
                self._send_audio()
            else:
                self._send(404, "text/plain", b"not found")

        def do_PUT(self) -> None:
            if self.path != "/api/review":
                return self._send(404, "text/plain", b"not found")
            try:
                pieces = _validate(json.loads(self.rfile.read(int(self.headers["Content-Length"]))), detection["duration"])
            except (ValueError, KeyError, TypeError) as e:
                return self._send(400, "text/plain", str(e).encode())
            session.save_review(pieces)
            self._send(204, "text/plain", b"")

        def _send_audio(self) -> None:
            size = session.source.stat().st_size
            start, end = 0, size - 1
            m = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
            if m and (m[1] or m[2]):
                if m[1]:
                    start, end = int(m[1]), min(int(m[2]), size - 1) if m[2] else size - 1
                else:
                    start = max(0, size - int(m[2]))
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            else:
                self.send_response(200)
            self.send_header("Content-Type", "audio/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            self.end_headers()
            with open(session.source, "rb") as f:
                f.seek(start)
                left = end - start + 1
                try:
                    while left > 0:
                        chunk = f.read(min(left, 1 << 16))
                        self.wfile.write(chunk)
                        left -= len(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # the browser seeked elsewhere and dropped this request

        def _send(self, code: int, ctype: str, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Reviewing {session.name} at {url}  (changes save automatically; Ctrl+C to stop)")
    print(f"When done: scrap export {session.name}")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def _validate(body: dict, duration: float) -> list[dict]:
    pieces = []
    for p in body["pieces"]:
        start, end = float(p["start"]), float(p["end"])
        if not 0 <= start < end <= duration + 1:
            raise ValueError(f"bad piece bounds {start}-{end}")
        pieces.append({"id": int(p["id"]), "start": start, "end": end, "name": str(p["name"]), "keep": bool(p["keep"])})
    return sorted(pieces, key=lambda p: p["start"])
