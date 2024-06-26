from typing import Type, Optional
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from maubot import Plugin, MessageEvent
from maubot.handlers import event, command
from mautrix.types import EventType, MessageEvent
from maubot_life_tracking import db
from mautrix.util.async_db import UpgradeTable
from zoneinfo import ZoneInfo
from datetime import datetime, timezone, timedelta
from maubot_life_tracking.parsers import parse_datetime, parse_interval, render_template, render_csv
import asyncio
import random


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("allowlist")
        helper.copy("default_tz")
        helper.copy("exec_frequency")


class LifeTrackingBot(Plugin):
    async def start(self) -> None:
        self.config.load_and_update()
        self.running = True
        self.run_loop_task = self.run_loop()
        asyncio.create_task(self.run_loop_task)
    
    async def stop(self) -> None:
        self.running = False
        self.run_loop_task = None

    async def run_loop(self) -> None:
        while self.running:
            now = datetime.now(timezone.utc)
            prompts = await db.fetch_prompts(self.database, due=now)
            self.log.info(f"Found {len(prompts)} prompts ready for outreach")
            for prompt in prompts:
                now = datetime.now(timezone.utc)
                room = await self.get_room(prompt.room_id)
                tz = self.get_tz(room)
                localnow = now.astimezone(tz)
                message = render_template(prompt.message_template, localnow)
                evt_id = await self.client.send_text(room.room_id, message)
                outreach = db.Outreach(room.room_id, evt_id, prompt.name, now, message)
                await db.insert_outreach(self.database, outreach)
                if prompt.run_interval is None:
                    prompt.next_run = None
                else:
                    delay = 0
                    if prompt.max_random_delay is not None:
                        delay = random.randint(0, int(prompt.max_random_delay.total_seconds()))
                    prompt.next_run += prompt.run_interval + timedelta(seconds=delay)
                await db.upsert_prompt(self.database, prompt)

            await asyncio.sleep(parse_interval(self.config["exec_frequency"]).total_seconds())
    
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
            items.append(f"- Time zone: {tz.key}")
        else:
            items.append(f"- Time zone (bot default): {tz.key}")
        
        prompts = await db.fetch_prompts(self.database, room.room_id)
        if prompts:
            items.append("- Prompts:")
            now = datetime.now(timezone.utc)
            for prompt in prompts:
                items.append(f"  - {prompt.name}:")
                if prompt.next_run:
                    items.append(f"    - Next run: {prompt.next_run.isoformat()} ({prompt.next_run - now} from now)")
                else:
                    items.append(f"    - Not scheduled")
                if prompt.run_interval is not None:
                    items.append(f"    - Run interval: {prompt.run_interval}")
                else:
                    items.append(f"    - No run interval defined")
                if prompt.max_random_delay is not None:
                    items.append(f"    - Max random delay: {prompt.max_random_delay}")
                else:
                    items.append(f"    - No random delay")
                items.append(f"    - Message template: {prompt.message_template}")
        else:
            items.append("- No prompts created")

        msg = "\n".join(items)
        await evt.mark_read()
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
                await evt.mark_read()
                await evt.reply("Invalid timezone")
                return
        await db.upsert_room(self.database, room)
        await evt.mark_read()
        await evt.react("✅")
    
    @lt_command.subcommand(help="Create a new prompt or update its message template.")
    @command.argument("prompt_name")
    @command.argument("message_template", pass_raw=True)
    async def prompt(self, evt: MessageEvent, prompt_name: str, message_template: str) -> None:
        if not self.is_allowed(evt.sender):
            self.log.warn(f"stranger danger: sender={evt.sender}")
            return
        room = await self.get_room(evt.room_id)
        prompt = await db.fetch_prompt(self.database, room.room_id, prompt_name)
        if prompt is None:
            prompt = db.Prompt(room.room_id, prompt_name, message_template)
        else:
            prompt.message_template = message_template
        await db.upsert_prompt(self.database, prompt)
        await evt.mark_read()
        await evt.react("✅")
    
    @lt_command.subcommand(help="Delete the specified prompt (if it exists).")
    @command.argument("prompt_name")
    async def rmprompt(self, evt: MessageEvent, prompt_name: str) -> None:
        if not self.is_allowed(evt.sender):
            self.log.warn(f"stranger danger: sender={evt.sender}")
            return
        await db.delete_prompt(self.database, evt.room_id, prompt_name)
        await evt.mark_read()
        await evt.react("✅")
    
    @lt_command.subcommand(help="Generate a CSV of outreaches and responses.")
    async def csv(self, evt: MessageEvent) -> None:
        if not self.is_allowed(evt.sender):
            self.log.warn(f"stranger danger: sender={evt.sender}")
            return
        ors = await db.fetch_outreaches_and_responses(self.database, evt.room_id)
        csvtext = render_csv(ors)
        await evt.mark_read()
        # TODO ability to send as a file instead
        # TODO escape text
        csvtext = csvtext.removesuffix("\n")
        csvmd = f"```csv\n{csvtext}\n```"
        await evt.reply(csvmd)
    
    @lt_command.subcommand(help="Set the next run date and time, run interval, and random delay for a prompt.")
    @command.argument("prompt_name")
    @command.argument("date", required=False)
    @command.argument("time", required=False)
    @command.argument("run_interval", required=False)
    @command.argument("max_random_delay", required=False)
    async def schedule(self, evt: MessageEvent, prompt_name: str, date: Optional[str], time: Optional[str], run_interval: Optional[str], max_random_delay: Optional[str]) -> None:
        if not self.is_allowed(evt.sender):
            self.log.warn(f"stranger danger: sender={evt.sender}")
            return
        room = await self.get_room(evt.room_id)
        prompt = await db.fetch_prompt(self.database, room.room_id, prompt_name)
        if prompt is None:
            await evt.mark_read()
            await evt.reply("You must create the prompt with the !prompt command first.")
            return

        if date and not time:
            await evt.mark_read()
            await evt.reply("You must supply a time if you supply a date.")
            return

        if not date:
            prompt.next_run = None
        else:
            try:
                prompt.next_run = parse_datetime(f"{date} {time}", self.get_tz(room))
            except Exception as e:
                self.log.warn(e)
                await evt.mark_read()
                await evt.reply("Unable to parse date or time. Date should be 'today', 'tomorrow', or 'YYYY-MM-DD'. Time should be 'HH:MM'.")
                return

        if not run_interval:
            prompt.run_interval = None
        else:
            try:
                prompt.run_interval = parse_interval(run_interval)
            except Exception as e:
                self.log.warn(e)
                await evt.mark_read()
                await evt.reply(f"Unable to parse run interval. Expected format is 15d, 15h, or 15m, for 15 days, hours, or minutes, respectively.")
                return

        if not max_random_delay:
            prompt.max_random_delay = None
        else:
            try:
                prompt.max_random_delay = parse_interval(max_random_delay)
            except Exception as e:
                self.log.warn(e)
                await evt.mark_read()
                await evt.reply("Unable to parse max random delay. Expected format is 15d, 15h, or 15m, for 15 days, hours, or minutes, respectively.")
                return
        
        await db.upsert_prompt(self.database, prompt)
        await evt.mark_read()
        await evt.react("✅")


    @event.on(EventType.ROOM_MESSAGE)
    async def handle_msg(self, evt: MessageEvent) -> None:
        if not self.is_allowed(evt.sender):
            self.log.warn(f"stranger danger: sender={evt.sender}")
            return
        room = await self.get_room(evt.room_id)
        if evt.content.relates_to and evt.content.relates_to.in_reply_to and evt.content.relates_to.in_reply_to.event_id:
            outreach_event_id = evt.content.relates_to.in_reply_to.event_id
            outreach = await db.fetch_outreach(self.database, room.room_id, outreach_event_id)
            if outreach:
                ts = datetime.fromtimestamp(evt.timestamp / 1000, timezone.utc)
                response = db.Response(room.room_id, evt.event_id, outreach.event_id, ts, evt.content.body)
                await db.insert_response(self.database, response)
        await evt.mark_read()
    
    @event.on(EventType.REACTION)
    async def handle_reaction(self, evt: MessageEvent) -> None:
        if not self.is_allowed(evt.sender):
            self.log.warn(f"stranger danger: sender={evt.sender}")
            return
        room = await self.get_room(evt.room_id)
        if evt.content.relates_to and evt.content.relates_to.event_id:
            outreach_event_id = evt.content.relates_to.event_id
            outreach = await db.fetch_outreach(self.database, room.room_id, outreach_event_id)
            if outreach:
                ts = datetime.fromtimestamp(evt.timestamp / 1000, timezone.utc)
                response = db.Response(room.room_id, evt.event_id, outreach.event_id, ts, evt.content.relates_to.key)
                await db.insert_response(self.database, response)

    @classmethod
    def get_db_upgrade_table(cls) -> UpgradeTable | None:
        return db.upgrade_table

