This is a [maubot](https://github.com/maubot/maubot) plugin that will send you messages on a schedule and record your reactions/replies.

You can and probably should configure it to only respond to messages from specific users.

I wrote this code in a hurry with a "no second takes" mentality, so, I apologize for everything being poorly named and poorly organized.

# Installation

- [Setup maubot](https://docs.mau.fi/maubot/usage/setup/index.html)
- Clone this repo and [use `mbc build -u`](https://docs.mau.fi/maubot/usage/cli/build.html) to build the plugin
- [Create a client and an instance](https://docs.mau.fi/maubot/usage/basic.html)
- Update the configuration; see [base-config.yaml](base-config.yaml) for documentation of the available options

# Usage

Suppose you want to be asked "What's something your grateful for?" every day.

First, messages the bot to tell it to create a prompt.
We'll use the name "gratitude" to refer to the prompt.

```
!lt prompt gratitude What's something your grateful for?
```

Now schedule the next run for 5pm tomorrow, recurring every day:

```
!lt schedule gratitude tomorrow 17:00 1d
```

(You could also say `today` instead of `tomorrow`, or specify a date such as `2024-05-30`.
For the time interval, use "d" for days, "h" for hours, or "m" for minutes.
Or "s" for seconds, but that seems like a bad idea.)

When the time comes, the bot will send you the message "What's something your grateful for?".
You can respond either with an emoji reaction, or a text reply (make sure to actually _reply_, not just message the room), and the bot will save it to the database.

Note that the message may not be sent precisely at the configured time.
The bot only 'wakes up' periodically to check which messages are due; the interval between checks is part of the config yaml.

To dump all your data to a csv, use:

```
!lt csv
```

You can see all the current room's prompts and their schedules using:

```
!lt info
```

You can remove a prompt by name:

```
!lt rmprompt gratitude
```

To unschedule a prompt without deleting it, use `schedule` without arguments:

```
!lt schedule gratitude
```

It's possible to add some randomness to the timing of prompts by specifying a "max random delay".
For example, the following means that the next message for the gratitude prompt should be sent tomorrow at 5pm, and there will be a delay of between 24 and 32 hours for each subsequent message.

```
!lt schedule gratitude tomorrow 17:00 1d 8h
```

The timezone assumed by the `schedule` command can be changed using:

```
!lt timezone America/Chicago
```
