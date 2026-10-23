import json
import sqlite3


class Store:
    def __init__(self, data_dir):
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / "tachyon.sqlite3"
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS workspaces (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO workspaces VALUES (?, ?)", ("local", json.dumps({
                "preferences": {"theme": "snap", "mode": "simple"}, "activeComponentId": None})))

    def connect(self):
        return sqlite3.connect(self.path)

    def workspace(self):
        with self.connect() as db:
            return json.loads(db.execute("SELECT data FROM workspaces WHERE id = ?", ("local",)).fetchone()[0])

    def patch_workspace(self, changes):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            workspace = json.loads(db.execute("SELECT data FROM workspaces WHERE id = ?", ("local",)).fetchone()[0])
            preferences = changes.pop("preferences", None)
            workspace.update(changes)
            if preferences:
                workspace["preferences"].update(preferences)
            db.execute("UPDATE workspaces SET data = ? WHERE id = ?", (json.dumps(workspace), "local"))
        return workspace
