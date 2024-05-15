import unittest
from pathlib import Path
from mautrix.util.async_db import Database
from maubot_life_tracking.db import upgrade_table, fetch_room, upsert_room, Room, Prompt, fetch_prompt, upsert_prompt, delete_prompt
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone

DB_PATH = Path("test.sqlite3")
DB_FILES = [DB_PATH, Path("test.sqlite3-shm"), Path("test.sqlite3-wal")]
DB_URI = f"sqlite:///{DB_PATH.resolve()}"

ZONE = ZoneInfo("America/Los_Angeles")

class TestDb(unittest.IsolatedAsyncioTestCase):
    async def test_basics(self) -> None:
        db = Database.create(DB_URI, upgrade_table=upgrade_table)
        await db.start()
        try:
            self.assertEqual(None, await fetch_room(db, "a"))
            
            room = Room("a")
            await upsert_room(db, room)
            room = await fetch_room(db, "a")
            self.assertEqual("a", room.room_id)
            self.assertEqual(None, room.tz)

            room.tz = ZONE
            await upsert_room(db, room)
            room = await fetch_room(db, "a")
            self.assertEqual("a", room.room_id)
            self.assertEqual(ZONE, room.tz)

            self.assertEqual(None, await fetch_room(db, "b"))

            self.assertEqual(None, await fetch_prompt(db, "a", "foo"))
            prompt = Prompt("a", "foo", "Test Message")
            await upsert_prompt(db, prompt)
            prompt = await fetch_prompt(db, "a", "foo")
            self.assertEqual(prompt.room_id, "a")
            self.assertEqual(prompt.name, "foo")
            self.assertEqual(prompt.message_template, "Test Message")
            self.assertEqual(prompt.next_run, None)
            self.assertEqual(prompt.run_interval, None)
            self.assertEqual(prompt.max_random_delay, None)

            now = datetime.now(timezone.utc).replace(microsecond=0)
            prompt.next_run = now
            prompt.run_interval = timedelta(days=1)
            prompt.max_random_delay = timedelta(hours=16)
            await upsert_prompt(db, prompt)
            prompt = await fetch_prompt(db, "a", "foo")
            self.assertEqual(prompt.room_id, "a")
            self.assertEqual(prompt.name, "foo")
            self.assertEqual(prompt.message_template, "Test Message")
            self.assertEqual(prompt.next_run, now)
            self.assertEqual(prompt.run_interval, timedelta(days=1))
            self.assertEqual(prompt.max_random_delay, timedelta(hours=16))

            await delete_prompt(db, "a", "foo")
            self.assertEqual(None, await fetch_prompt(db, "a", "foo"))
        finally:
            await db.stop()
            for path in DB_FILES:
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()

