from mautrix.util.async_db import UpgradeTable, Connection, Database
from typing import Optional, List
from zoneinfo import ZoneInfo


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
          next_run DATETIME,
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
    
    def tz_str(self) -> str:
        if self.tz:
            return self.tz.key
        return None


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
    await db.execute(q, room.room_id, room.tz_str())
