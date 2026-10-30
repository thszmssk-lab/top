#!/usr/bin/env python3
"""YouTube 컨트롤타워: 통합 DB + 스케줄 배정 + 대시보드 서버."""
import argparse, json, os, sqlite3, sys
from datetime import datetime, timedelta
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("TOWER_DB", os.path.join(HERE, "tower.db"))

SEED = [  # (구글계정, 채널명, [(제작방, 종류, 업로드시각)])
    ("taejung", "모든 쇼핑", [("시니어쇼츠-GPT", "shorts", "22:15"), ("정치-fork3", "shorts", "10:15")]),
    ("temxo0678", "시선각도", [("롱폼운세-띠별", "long", "17:15"), ("운세숏폼-수진당시선각도", "shorts", "10:15"),
                              ("시니어쇼츠-초반어그로", "shorts", "22:15")]),
    ("missnoble0070", "작두별상대신 수진당", [("롱폼운세-날짜별", "long", "17:45"), ("운세숏폼-수진당시선각도", "shorts", "11:15")]),
]

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON"); return c

def init():
    c = conn(); c.executescript(open(os.path.join(HERE, "schema.sql"), encoding="utf-8").read())
    for acct, ch, srcs in SEED:
        c.execute("INSERT OR IGNORE INTO channels(google_account,channel_name) VALUES(?,?)", (acct, ch))
        cid = c.execute("SELECT id FROM channels WHERE google_account=? AND channel_name=?", (acct, ch)).fetchone()[0]
        for name, kind, slot in srcs:
            # 같은 방 이름이 두 채널에 쓰이면 채널명을 붙여 구분
            n = name if not c.execute("SELECT 1 FROM sources WHERE name=?", (name,)).fetchone() else f"{name}@{ch}"
            c.execute("INSERT OR IGNORE INTO sources(channel_id,name,kind,slot_time) VALUES(?,?,?,?)", (cid, n, kind, slot))
    c.commit(); print("DB 준비 완료:", DB)

def src_id(c, name):
    r = c.execute("SELECT id FROM sources WHERE name=?", (name,)).fetchone()
    if not r: sys.exit(f"알 수 없는 제작방: {name}\n등록된 제작방: " + ", ".join(x[0] for x in c.execute("SELECT name FROM sources")))
    return r[0]

def add(a):
    c = conn()
    c.execute("INSERT OR REPLACE INTO videos(source_id,title,description,tags,file_path,thumbnail_path) VALUES(?,?,?,?,?,?)",
              (src_id(c, a.source), a.title, a.description, a.tags, a.file, a.thumbnail))
    c.commit(); print("등록 완료:", a.title)

def schedule(a):
    """제작방별로 ready 영상에 매일 slot_time 순서로 일정 배정. 마지막 예약/업로드 다음 날부터."""
    c = conn(); now = datetime.now()
    for s in c.execute("SELECT * FROM sources"):
        h, m = map(int, s["slot_time"].split(":"))
        last = c.execute("SELECT MAX(COALESCE(scheduled_at,uploaded_at)) FROM videos WHERE source_id=? AND status IN ('scheduled','uploaded')",
                         (s["id"],)).fetchone()[0]
        t = datetime.fromisoformat(last) + timedelta(days=1) if last else now
        t = t.replace(hour=h, minute=m, second=0, microsecond=0)
        if t <= now: t += timedelta(days=1)
        for v in c.execute("SELECT id FROM videos WHERE source_id=? AND status='ready' ORDER BY id", (s["id"],)).fetchall():
            c.execute("UPDATE videos SET status='scheduled', scheduled_at=? WHERE id=?", (t.strftime("%Y-%m-%dT%H:%M"), v["id"]))
            t += timedelta(days=1)
    c.commit(); print("스케줄 배정 완료"); ls(a)

def interval(a):
    """채널 내 여러 제작방 영상을 N시간 간격으로 분배 (마지막 업로드 시각 기준)."""
    c = conn(); ch = c.execute("SELECT id FROM channels WHERE channel_name=?", (a.channel,)).fetchone()
    if not ch: sys.exit("채널 없음")
    last = c.execute("""SELECT MAX(COALESCE(scheduled_at,uploaded_at)) FROM videos v JOIN sources s ON s.id=v.source_id
                        WHERE s.channel_id=? AND v.status IN ('scheduled','uploaded')""", (ch[0],)).fetchone()[0]
    t = datetime.fromisoformat(last) if last else datetime.now()
    for v in c.execute("""SELECT v.id FROM videos v JOIN sources s ON s.id=v.source_id
                          WHERE s.channel_id=? AND v.status='ready' ORDER BY v.id""", (ch[0],)).fetchall():
        t += timedelta(hours=a.hours)
        c.execute("UPDATE videos SET status='scheduled', scheduled_at=? WHERE id=?", (t.strftime("%Y-%m-%dT%H:%M"), v["id"]))
    c.commit(); ls(a)

def mark(vid, status, url=""):
    c = conn()
    up = datetime.now().strftime("%Y-%m-%dT%H:%M") if status == "uploaded" else None
    # 완료가 아닌 상태로 되돌리면 업로드 시각을 지운다
    c.execute("UPDATE videos SET status=?, uploaded_at=?, youtube_url=COALESCE(NULLIF(?,''),youtube_url) WHERE id=?",
              (status, up, url, vid)); c.commit()

def rows():
    return [dict(r) for r in conn().execute("""SELECT v.*, s.name source, s.kind, s.slot_time, c.channel_name, c.google_account
        FROM videos v JOIN sources s ON s.id=v.source_id JOIN channels c ON c.id=s.channel_id
        ORDER BY c.id, s.id, COALESCE(v.scheduled_at, v.uploaded_at, v.created_at)""")]

def ls(a=None):
    for r in rows(): print(f"[{r['id']}] {r['channel_name']} / {r['source']} / {r['status']:9} {r['scheduled_at'] or r['uploaded_at'] or '-'} {r['title']}")

class H(BaseHTTPRequestHandler):
    def _send(self, body, ct="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(200); self.send_header("Content-Type", ct + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _file(self, vid, col):
        r = conn().execute(f"SELECT {col} FROM videos WHERE id=?", (vid,)).fetchone()
        p = r[0] if r else ""
        if not p or not os.path.isfile(p): self.send_error(404); return
        size = os.path.getsize(p); start, end = 0, size - 1
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-"); start = int(a or 0); end = int(b) if b else end
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", mimetypes.guess_type(p)[0] or "application/octet-stream")
        self.send_header("Accept-Ranges", "bytes"); self.send_header("Content-Length", str(end - start + 1))
        if rng: self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        try:
            with open(p, "rb") as f:
                f.seek(start); left = end - start + 1
                while left > 0:
                    d = f.read(min(1 << 20, left))
                    if not d: break
                    self.wfile.write(d); left -= len(d)
        except (BrokenPipeError, ConnectionError): pass
    def do_GET(self):
        if self.path == "/api/videos": self._send(json.dumps(rows(), ensure_ascii=False))
        elif self.path == "/api/sources": self._send(json.dumps([dict(r) for r in conn().execute("""SELECT s.name source, s.kind, s.slot_time, c.channel_name, c.google_account
            FROM sources s JOIN channels c ON c.id=s.channel_id ORDER BY c.id, s.id""")], ensure_ascii=False))
        elif self.path.startswith("/thumb/"): self._file(int(self.path[7:]), "thumbnail_path")
        elif self.path.startswith("/video/"): self._file(int(self.path[7:]), "file_path")
        else: self._send(open(os.path.join(HERE, "dashboard.html"), "rb").read(), "text/html")
    def do_POST(self):
        d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        mark(d["id"], d["status"], d.get("url", "")); self._send('{"ok":true}')
    def log_message(self, *x): pass

def serve(a):
    print(f"대시보드: http://localhost:{a.port}"); ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()

p = argparse.ArgumentParser(); sp = p.add_subparsers(dest="cmd", required=True)
sp.add_parser("init"); sp.add_parser("list"); sp.add_parser("schedule")
x = sp.add_parser("add"); x.add_argument("--source", required=True); x.add_argument("--title", required=True)
x.add_argument("--file", required=True); x.add_argument("--thumbnail", default=""); x.add_argument("--description", default=""); x.add_argument("--tags", default="")
x = sp.add_parser("interval"); x.add_argument("--channel", required=True); x.add_argument("--hours", type=float, default=6)
x = sp.add_parser("done"); x.add_argument("id", type=int); x.add_argument("--url", default="")
x = sp.add_parser("serve"); x.add_argument("--port", type=int, default=8765)
a = p.parse_args()
{"init": lambda: init(), "list": lambda: ls(), "schedule": lambda: schedule(a), "add": lambda: add(a),
 "interval": lambda: interval(a), "done": lambda: mark(a.id, "uploaded", a.url), "serve": lambda: serve(a)}[a.cmd]()
