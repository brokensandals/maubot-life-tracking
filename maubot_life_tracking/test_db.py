import unittest
from pathlib import Path
from mautrix.util.async_db import Database
from maubot_life_tracking.db import upgrade_table, fetch_room, upsert_room, Room, Prompt, fetch_prompt, upsert_prompt, delete_prompt, Outreach, insert_outreach, Response, insert_response, fetch_outreaches_and_responses, fetch_prompts
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

            prompts = await fetch_prompts(db, "a")
            self.assertEqual(len(prompts), 1)
            self.assertEqual(prompts[0].room_id, "a")
            self.assertEqual(prompts[0].name, "foo")
            self.assertEqual(prompts[0].message_template, "Test Message")
            self.assertEqual(prompts[0].next_run, now)
            self.assertEqual(prompts[0].run_interval, timedelta(days=1))
            self.assertEqual(prompts[0].max_random_delay, timedelta(hours=16))

            prompts = await fetch_prompts(db, due=now - timedelta(seconds=10))
            self.assertEqual(len(prompts), 1)
            prompts = await fetch_prompts(db, due=now + timedelta(seconds=10))
            self.assertEqual(len(prompts), 0)

            outreach = Outreach("a", "o1", "foo", now, "What's up?")
            await insert_outreach(db, outreach)

            outreach2 = Outreach("a", "o2", "bar", now+timedelta(seconds=-1), "???")
            await insert_outreach(db, outreach2)

            response1 = Response("a", "r1", "o1", now+timedelta(seconds=2), "✅")
            await insert_response(db, response1)
            response2 = Response("a", "r2", "o1", now+timedelta(seconds=3), "oops actually no")
            await insert_response(db, response2)

            ors = await fetch_outreaches_and_responses(db, "a")
            self.assertEqual(len(ors), 2)
            outreach2, outreach2_responses = ors[0]
            self.assertEqual(outreach2.event_id, "o2")
            self.assertEqual(outreach2.prompt_name, "bar")
            self.assertEqual(outreach2.message, "???")
            self.assertEqual(outreach2_responses, [])
            outreach, outreach_responses = ors[1]
            self.assertEqual(outreach.event_id, "o1")
            self.assertEqual(outreach.prompt_name, "foo")
            self.assertEqual(outreach.message, "What's up?")
            self.assertEqual(len(outreach_responses), 2)
            response1 = outreach_responses[0]
            self.assertEqual(response1.event_id, "r1")
            self.assertEqual(response1.message, "✅")
            response2 = outreach_responses[1]
            self.assertEqual(response2.event_id, "r2")
            self.assertEqual(response2.message, "oops actually no")

            await delete_prompt(db, "a", "foo")
            self.assertEqual(None, await fetch_prompt(db, "a", "foo"))
        finally:
            await db.stop()
            for path in DB_FILES:
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()

