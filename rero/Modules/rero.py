# coding=utf-8
"""
Copyright 2017 Luxory (@LXYcs)
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import discord
import datetime
from Rero import redis_manager, events
from Rero.Modules import commands_parser, ranking, osu


class Rero(discord.Client):
    """
    Rero, the multi-purpose bot for Discord.

    For more information about Rero, visit out website
        http://rero.xyz
    We are also present in the following social media sites:
        https://twitter.com/lxycs
        https://www.facebook.com/rerobot/


    """
    __author__ = "Luxory#0018"
    __version__ = "0.0.1-beta-1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_shard = kwargs.get("shard_id")
        self.shard_count = kwargs.get("shard_count")
        self.prefix = kwargs.get("prefix")
        self.startup_timestamp = datetime.datetime.utcnow()
        self.redis = redis_manager.redis_manager.redis
        self.osu = osu.Osu(self)
        self.commands = commands_parser.Commands(self, self.current_shard, self.prefix, self.osu)
        self.ranking = ranking.Rankings(self, self.current_shard)
        self.events = events.Events(self)

    async def on_message(self, message):
        """

        :param message:
        :return:
        """
        # We don't want Rero to be replying to his
        # own messages right? Also a global count
        # of all the sent messages is used with ?info
        if message.author.id == self.user.id:
            self.redis.incr("RERO_SENT_MESSAGES")
            return

        # To keep the bad boys from abusing our lovely bot
        blacklist = self.redis.lrange("user_black_list", 0, -1)
        if str(message.author.id).encode() in blacklist:
            return

        # We don't respond to private messages. We are too cool for
        # that
        if message.channel.is_private:
            try:
                await self.loop.create_task(
                    self.send_message(message.author, "Rero can only be used from a server.\n"
                                                      "If you want to know more about Rero, visit "
                                                      "https://github.com/voqz/rerobot/"))
                return
            except discord.DiscordException:
                return

        # Handles the PM mentions. We created this task first as this
        # is the first priority ;)
        await self.loop.create_task(self.commands.pm_mentions_handler(message))

        #  Message Logger hook. This is basically responsible for handling
        # the logging function for Rero.
        await self.loop.create_task(self.commands.log_message(message))

        # Command Parser handles commands directed at Rero. This is
        # responsible for parsing the commands from regular message content
        # and then taking specific actions
        await self.loop.create_task(self.commands.handle_message(message))

        # XP from messages handles giving xp on servers with Ranking enabled
        await self.loop.create_task(self.ranking.ranking_handler(message))

        # Level Up announcer handles the member level up announcements on
        # servers with ranking enabled and announcements enabled
        await self.loop.create_task(self.ranking.level_up_announcer(message))

        # Osu Link Scanner is responsible for parsing osu based links from
        # messages and then taking some specific actions
        await self.loop.create_task(self.osu.parse_message(message))

    # Event handler codes.
    # We handle each event as a task so that it does not
    # end up slowing down the bot and instead do concurrent
    # jobs
    async def on_ready(self):
        """

        :return:
        """
        self.redis.set("RERO_SENT_MESSAGES", 0)
        self.redis.set("RERO_LOG_WRITES", 0)
        self.redis.set("imgur_remain", "0")
        self.redis.set("imgur_limit", "0")
        self.redis.set("imgur_reset", "0")
        self.redis.set("rero_remain", "0")
        self.redis.set("rero_limit", "0")

        x = discord.Game(name="Yeay! I am back : [{} / {}]".format(self.current_shard, self.shard_count))
        await self.change_status(game=x, idle=False)

    async def on_member_update(self, before, after):
        """
        Called when a member updates state

        :param before:
        :param after:
        :return:
        """
        await self.loop.create_task(self.events.on_member_update(before, after))

    async def on_member_join(self, member):
        """
        Called when a member joins a server

        :param member:
        :return:
        """
        await self.loop.create_task(self.events.on_member_join(member))

    async def on_member_remove(self, member):
        """
        Called when a member is removed from a server

        :param member:
        :return:
        """
        await self.loop.create_task(self.events.on_member_remove(member))

    async def on_server_join(self, server):
        """
        Called when Rero joins a server

        :param server:
        :return:
        """
        await self.loop.create_task(self.events.on_server_join(server))

    async def on_server_remove(self, server):
        """
        Called when Rero is removed from a server

        :param server:
        :return:
        """
        await self.loop.create_task(self.events.on_server_remove(server))

    async def on_channel_delete(self, channel):
        """
        Called when a channel is deleted

        :param channel:
        :return:
        """
        await self.loop.create_task(self.events.on_channel_delete(channel))

    async def on_channel_create(self, channel):
        """
        Called when a channel is created

        :param channel:
        :return:
        """
        await self.loop.create_task(self.events.on_channel_create(channel))

    async def on_channel_update(self, before, after):
        """
        Called when a channel is updated

        :param before:
        :param after:
        :return:
        """
        await self.loop.create_task(self.events.on_channel_update(before, after))

    async def on_server_role_create(self, role):
        """
        Called when a new role is created in a server

        :param role:
        :return:
        """
        await self.loop.create_task(self.events.on_server_role_create(role))

    async def on_server_role_delete(self, role):
        """
        Called when a role is deleted in a server

        :param role:
        :return:
        """
        await self.loop.create_task(self.events.on_server_role_delete(role))

    async def on_server_role_update(self, before, after):
        """
        Called when a new role is updated in a server

        :param before:
        :param after:
        :return:
        """
        await self.loop.create_task(self.events.on_server_role_update(before, after))

    async def on_server_update(self, before, after):
        """
        Called when a server updates state

        :param before:
        :param after:
        :return:
        """
        await self.loop.create_task(self.events.on_server_update(before, after))
