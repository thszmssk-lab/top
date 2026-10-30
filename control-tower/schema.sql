CREATE TABLE IF NOT EXISTS channels (
  id INTEGER PRIMARY KEY, google_account TEXT NOT NULL, channel_name TEXT NOT NULL,
  UNIQUE(google_account, channel_name));
-- 영상을 만드는 Claude Code 채팅방(제작 세션) 1개 = source 1개
CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY, channel_id INTEGER NOT NULL REFERENCES channels(id),
  name TEXT NOT NULL UNIQUE, kind TEXT NOT NULL CHECK(kind IN ('shorts','long')),
  slot_time TEXT NOT NULL);            -- 매일 업로드 시각 HH:MM
CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES sources(id),
  title TEXT NOT NULL, description TEXT DEFAULT '', tags TEXT DEFAULT '',
  file_path TEXT NOT NULL, thumbnail_path TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'ready' CHECK(status IN ('ready','scheduled','uploaded','failed')),
  scheduled_at TEXT, uploaded_at TEXT, youtube_url TEXT DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  UNIQUE(source_id, file_path));
