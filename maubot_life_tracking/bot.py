from typing import Type
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from maubot import Plugin, MessageEvent
from maubot.handlers import event, command
from mautrix.types import EventType, MessageEvent
from maubot_life_tracking import db
from mautrix.util.async_db import UpgradeTable
from zoneinfo import ZoneInfo


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("allowlist")
        helper.copy("default_tz")


class LifeTrackingBot(Plugin):
    async def start(self) -> None:
        self.config.load_and_update()
    
    def is_allowed(self, sender: str) -> bool:
        if self.config["allowlist"] == False:
            return True
        return sender in self.config["allowlist"]

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config
    
    @command.new(name="lt", require_subcommand=True)
    async def lt_command(self, evt: MessageEvent) -> None:
        pass

    async def get_room(self, room_id: str) -> db.Room:
        room = await db.fetch_room(self.database, room_id)
        if room is None:
            room = db.Room(room_id)
            await db.upsert_room(self.database, room)
        return room

    def get_tz(self, room: db.Room) -> ZoneInfo:
        if room.tz:
            return room.tz
        return ZoneInfo(self.config["default_tz"])

    @lt_command.subcommand(help="Display configuration for current room.")
    async def info(self, evt: MessageEvent) -> None:
        if not self.is_allowed(evt.sender):
            self.log.warn(f"stranger danger: sender={evt.sender}")
            return
        room = await self.get_room(evt.room_id)
        tz = self.get_tz(room)
        items = []
        if tz == room.tz:
            items.append(f"- Time Zone: {tz.key}")
        else:
            items.append(f"- Time Zone (bot default): {tz.key}")
        msg = "\n".join(items)
        await evt.reply(msg)
    
    @lt_command.subcommand(help="Switch the bot to use a different timezone in this room. Use '-' to switch to the default.")
    @command.argument("tzkey")
    async def timezone(self, evt: MessageEvent, tzkey: str) -> None:
        if not self.is_allowed(evt.sender):
            self.log.warn(f"stranger danger: sender={evt.sender}")
            return
        room = await self.get_room(evt.room_id)
        if tzkey == "-":
            room.tz = None
        else:
            try:
                room.tz = ZoneInfo(tzkey)
            except:
                await evt.reply("Invalid timezone")
                return
        await db.upsert_room(self.database, room)
        await evt.react("✅")

    @event.on(EventType.ROOM_MESSAGE)
    async def handle_msg(self, evt: MessageEvent) -> None:
        if not self.is_allowed(evt.sender):
            self.log.warn(f"stranger danger: sender={evt.sender}")
            return
        pass

    @classmethod
    def get_db_upgrade_table(cls) -> UpgradeTable | None:
        return db.upgrade_table

