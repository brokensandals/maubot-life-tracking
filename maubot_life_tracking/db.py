from mautrix.util.async_db import UpgradeTable, Connection, Database
from typing import Optional, List
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone


DB_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


upgrade_table = UpgradeTable()


@upgrade_table.register(description="v1")
async def upgrade_v1(conn: Connection) -> None:
    await conn.execute(
        """CREATE TABLE rooms (
            id TEXT NOT NULL PRIMARY KEY,
            tz TEXT
        )"""
    )
    await conn.execute(
        """CREATE TABLE prompts (
          room_id TEXT NOT NULL,
          name TEXT NOT NULL,
          message_template TEXT NOT NULL,
          next_run_utc TEXT,
          run_interval_sec INTEGER,
          max_random_delay_sec INTEGER,
          PRIMARY KEY (room_id, name),
          FOREIGN KEY (room_id) REFERENCES rooms(id)
        )"""
    )


class Room:
    def __init__(self, room_id: str, tz: ZoneInfo = None) -> None:
        self.room_id = room_id
        self.tz = tz


class Prompt:
    def __init__(self, room_id: str, name: str, message_template: str, next_run: datetime = None, run_interval: timedelta = None, max_random_delay: timedelta = None) -> None:
        self.room_id = room_id
        self.name = name
        self.message_template = message_template
        self.next_run = next_run
        self.run_interval = run_interval
        self.max_random_delay = max_random_delay


async def fetch_room(db: Database, room_id: str) -> Optional[Room]:
    q = "SELECT tz FROM rooms WHERE id=$1"
    row = await db.fetchrow(q, room_id)
    if not row:
        return None

    tz = None
    try:
        tz = ZoneInfo(row["tz"])
    except:
        # TODO log
        pass
    
    return Room(room_id, tz)


async def upsert_room(db: Database, room: Room) -> None:
    q = """
        INSERT INTO rooms(id, tz) VALUES ($1, $2)
        ON CONFLICT (id) DO UPDATE SET tz=excluded.tz
    """
    tzkey = None
    if room.tz:
        tzkey = room.tz.key
    await db.execute(q, room.room_id, tzkey)


async def fetch_prompt(db: Database, room_id: str, name: str) -> Optional[Prompt]:
    q = "SELECT message_template, next_run_utc, run_interval_sec, max_random_delay_sec FROM prompts WHERE room_id=$1 AND name=$2"
    row = await db.fetchrow(q, room_id, name)
    if not row:
        return None

    prompt = Prompt(room_id, name, row["message_template"])
    if row["next_run_utc"]:
        prompt.next_run = datetime.strptime(row["next_run_utc"], DB_DATETIME_FMT).replace(tzinfo=timezone.utc)
    if row["run_interval_sec"]:
        prompt.run_interval = timedelta(seconds=row["run_interval_sec"])
    if row["max_random_delay_sec"]:
        prompt.max_random_delay = timedelta(seconds=row["max_random_delay_sec"])
    return prompt


async def upsert_prompt(db: Database, prompt: Prompt) -> None:
    q = """
        INSERT INTO prompts(room_id, name, message_template, next_run_utc, run_interval_sec, max_random_delay_sec) VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (room_id, name) DO UPDATE SET message_template=excluded.message_template, next_run_utc=excluded.next_run_utc, run_interval_sec=excluded.run_interval_sec, max_random_delay_sec=excluded.max_random_delay_sec
    """
    next_run_utc = None
    if prompt.next_run:
        next_run_utc = prompt.next_run.strftime(DB_DATETIME_FMT)
    run_interval_sec = None
    if prompt.run_interval:
        run_interval_sec = prompt.run_interval.total_seconds()
    max_random_delay_sec = None
    if prompt.max_random_delay:
        max_random_delay_sec = prompt.max_random_delay.total_seconds()
    await db.execute(q, prompt.room_id, prompt.name, prompt.message_template, next_run_utc, run_interval_sec, max_random_delay_sec)


async def delete_prompt(db: Database, room_id: str, name: str) -> None:
    q = "DELETE FROM prompts WHERE room_id=$1 AND name=$2"
    await db.execute(q, room_id, name)
