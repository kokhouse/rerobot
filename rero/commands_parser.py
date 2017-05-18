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
from Rero import redis_manager, mongo_manager
from Rero.Modules import utility, admin, emojis, custom_commands, fun, nsfw, weeb, games, imgur_async
import re
import discord
import json
import datetime
import aiohttp


class Commands:
    """
    Command Parser
    """
    def __init__(self, context, current_shard, prefix, osu):
        super().__init__()
        self.ctx = context
        self.current_shard = current_shard
        self.prefix = prefix
        self.redis = redis_manager.redis_manager.redis
        self.mongo = mongo_manager.mongo_db.db
        self.mongo_message = mongo_manager.mongo_db.db_messages
        self.emojis = emojis.Emojis(context)
        self.custom_commands = custom_commands.CustomCommands(context)
        self.osu = osu
        self.nsfw = nsfw.NSFW(context)
        self.weeb = weeb.Weeb(context)
        self.games = games.Games(context)
        self.imgur = imgur_async.Imgur(context)

    @staticmethod
    def verify_role(user):
        """
        Verify role for the users who want to use Admin commands

        :param user:
        :return:
        """
        try:
            roles = user.roles
        except AttributeError:
            return False

        for role in roles:
            if role.name == "RERO":
                return True

    def verify_enabled(self, server_id, command: str):
        """
        Verify if this command is enabled in the current server
        :return:
        """
        cursor_check = self.mongo.server_backend.find({"serv_id": server_id})
        if cursor_check.count() != 0:
            for c in cursor_check:
                try:
                    check = c['access'][command]
                except KeyError:
                    check = True

                return check

    def do_we_ignore(self, channel_id, server_id):
        """
        Checks if we should ignore commands from a channel.
        Returns True if we should ignore. Else returns False.

        :return:
        """
        try:
            cursor = self.mongo.server_backend.find({"serv_id": server_id})
            if not cursor.count() == 0:
                for docs in cursor:
                    try:
                        # The id's of the ignored channel
                        # are stored in mongoDB
                        channels = docs['ignored_channels']
                        for channel in channels:
                            if channel_id == channel:
                                return True
                    except KeyError:
                        # There are chances that we will not
                        # find this key in the mongoDB document
                        # if no channels have been ignored yet
                        continue
            return False
        except AttributeError:
            return True

    # TODO: should we put this in a separate file?
    async def log_message(self, message):
        """
        The message logger

        :param message:
        :return:
        """
        log_key = message.server.id + "logger"
        if self.redis.exists(log_key):
            self.redis.incr("RERO_LOG_WRITES")
            new_record = {
                "serv_id": message.server.id,
                "serv_name": message.server.name,
                "channel": {
                    "name": message.channel.name,
                    "id": message.channel.id},
                "time_stamp": message.timestamp,
                "message": {"content_clean": message.clean_content,
                            "content": message.content,
                            "id": message.id},
                "author": {
                    "avatar": message.author.avatar_url,
                    "nick_name": message.author.display_name,
                    "name": message.author.name,
                    "id": message.author.id,
                    "discriminator": message.author.discriminator}
            }
            self.mongo_message.message_log.insert_one(new_record)

    @staticmethod
    async def hastebin_handler(content, output_str):
        """
        Creates hastebin pastes and returns keys

        :return:
        """
        endpoint = "http://hastebin.com/documents"
        headers = {"Content-Type": "text/plain",
                   "User-Agent": "Rero by Lapoozza (https://github.com/lapoozza/rero)"}
        c = re.sub("(.{100})", "\\1\n", content + output_str, 0, re.DOTALL)

        with aiohttp.ClientSession() as session:
            async with session.post(url=endpoint, data=c, headers=headers) as resp:
                data = await resp.read()

        r = json.loads(data.decode("utf-8"))
        return r['key']

    # TODO: Add support for delivering PM mentions to people
    # on other shards
    async def pm_mentions_handler(self, message):
        """
        Sends PM Notifications when someone is mentioned

        :param message:
        :return:
        """
        men = message.mentions
        for m in men:
            m_key = m.id + "pm"
            if self.redis.exists(m_key):
                switch = self.redis.get(m_key).decode("utf-8")
                if switch == "PM Mentions: ON":
                    if m.status == discord.Status.idle or m.status == discord.Status.offline:
                        author = message.author.name
                        channel = message.channel.name
                        server = message.server.name
                        cont = str(message.clean_content)
                        cont_s = len(cont)

                        # --- Last Messages Parser ---
                        m_str = ""
                        o_p_str = ""
                        x = datetime.datetime.utcnow()
                        try:
                            async for entry in self.ctx.logs_from(message.channel, limit=5, before=message):
                                delta = x - entry.timestamp
                                if delta.seconds < 60:
                                    m_str += "[`{}`] **{}**: {}\n".format(str(entry.timestamp.strftime("%H:%M:%S")),
                                                                          entry.author.name, entry.content)
                        except discord.DiscordException:
                            m_str = ""
                        except Exception as e:
                            print(e)
                            m_str = ""

                        if m_str != "":
                            o_p_str = "\n__Messages that lead upto this__\n" + m_str
                        cont_op_str = len(o_p_str)
                        # --- Last Messages Parser ---

                        if cont_op_str + cont_s < 1800:
                            template = "{} mentioned you in Server: **{}** | Channel: **{}**" \
                                       "\n{}\n{}".format(author, server, channel, cont, o_p_str)
                            await self.ctx.send_message(m, template)
                        else:
                            template = "{} mentioned you in Server: **{}** | Channel: **{}**" \
                                       "\nThe message is very big. So I made a hastebin paste: " \
                                       "http://hastebin.com/{} \n*Click link to view your message.*" \
                                .format(author, server, channel, self.hastebin_handler(cont, o_p_str))
                            await self.ctx.send_message(m, template)

                elif switch == "PM Mentions: 24/7":
                    author = message.author.name
                    channel = message.channel.name
                    server = message.server.name
                    cont = str(message.clean_content)
                    cont_s = len(cont)

                    # --- Last Messages Parser ---
                    m_str = ""
                    o_p_str = ""
                    x = datetime.datetime.utcnow()
                    try:
                        async for entry in self.ctx.logs_from(message.channel, limit=5, before=message):
                            delta = x - entry.timestamp
                            if delta.seconds < 60:
                                m_str += "[`{}`] **{}**: {}\n".format(str(entry.timestamp.strftime("%H:%M:%S")),
                                                                      entry.author.name, entry.content)
                    except discord.DiscordException:
                        m_str = ""
                    except Exception as e:
                        print(e)
                        m_str = ""

                    if m_str != "":
                        o_p_str = "\n__Messages that lead upto this__\n" + m_str
                    cont_op_str = len(o_p_str)
                    # --- Last Messages Parser ---

                    if cont_op_str + cont_s < 1800:
                        template = "{} mentioned you in Server: **{}** | Channel: **{}**" \
                                   "\n{}\n{}".format(author, server, channel, cont, o_p_str)
                        await self.ctx.send_message(m, template)
                    else:
                        template = "{} mentioned you in Server: **{}** | Channel: **{}**" \
                                   "\nThe message is very big. So I made a hastebin paste: " \
                                   "http://hastebin.com/{} \n*Click link to view your message.*" \
                            .format(author, server, channel, self.hastebin_handler(cont, o_p_str))
                        await self.ctx.send_message(m, template)

    async def handle_message(self, message):
        """
        This handles the messages

        :param message:
        :return:
        """
        # TODO: Add steam commands later
        # TODO: Add ?sr command later
        # TODO: Add quiz command later
        try:
            # We check if we are supposed to ignore commands from
            # this channel. If we are not supposed to then we continue.
            # Else we return
            if self.do_we_ignore(message.channel.id, message.server.id):
                return
            command = message.content
        except AttributeError:
            return

        # -- Utility Commands --
        if command.startswith(self.prefix + "info"):
            # TODO: this command is not ready to be invoked
            # Need to figure out a way to get information from
            # the connected shards
            await utility.info(self.ctx, message)

        if command == self.prefix + "ping":
            await self.ctx.send_message(message.channel, utility.ping(message, self.current_shard))

        if command == self.prefix + "help":
            await self.ctx.send_message(message.author, utility.help_message())

        if command.startswith(self.prefix + "status"):
            if self.verify_enabled(message.server.id, "status"):
                await utility.status(self.ctx, message)

        if command.startswith(self.prefix + "about"):
            if self.verify_enabled(message.server.id, "about"):
                await utility.about(self.ctx, message)

        if command.startswith(self.prefix + "profile"):
            await utility.profile(self.ctx, message)

        if command.startswith(".r"):
            if self.verify_enabled(message.server.id, "sar"):
                await utility.self_assigned_role(self.ctx, message)

        if command.startswith(self.prefix + "pervert"):
            await utility.pervert(self.ctx, message)

        if command.startswith(self.prefix + "pm"):
            await utility.pm(self.ctx, message)

        if command.startswith(self.prefix + "wiki"):
            if self.verify_enabled(message.server.id, "wikipedia"):
                await utility.wikipedia_parser(self.ctx, message)

        if command.startswith(self.prefix + "clean"):
            if self.verify_enabled(message.server.id, "clean"):
                await utility.clean(self.ctx, message)

        if command.startswith(self.prefix + "names"):
            if self.verify_enabled(message.server.id, "names"):
                await utility.name_changes(self.ctx, message)

        if command.startswith(self.prefix + "giphy"):
            if self.verify_enabled(message.server.id, "giphy"):
                querry = str(message.content[7:])
                querry_format = querry.replace(' ', '+')
                await utility.giphy(self.ctx, message, querry_format)

        if command.startswith(self.prefix + "translate"):
            if self.verify_enabled(message.server.id, "translate"):
                await utility.translator(self.ctx, message)

        if command.startswith(self.prefix + "twitch"):
            if self.verify_enabled(message.server.id, "twitch_manual"):
                t_con = await utility.twitch(message.content[8:])
                await self.ctx.send_message(message.channel, t_con)

        if command.startswith(self.prefix + "whoami"):
            if self.verify_enabled(message.server.id, "whoami/whois"):
                await utility.whoami(self.ctx, message)

        if command.startswith(self.prefix + "whois"):
            if self.verify_enabled(message.server.id, "whoami/whois"):
                await utility.whois(self.ctx, message)

        if command.startswith(self.prefix + "serverinfo"):
            if self.verify_enabled(message.server.id, "serverinfo"):
                await utility.server_info(self.ctx, message)

        if command.startswith(self.prefix + "weather"):
            if self.verify_enabled(message.server.id, "weather"):
                await utility.weather(self.ctx, message)

        if command.startswith(self.prefix + "xkcd"):
            if self.verify_enabled(message.server.id, "xkcd"):
                a = await utility.xkcd(message.content[6:])
                await self.ctx.send_message(message.channel, a)

        # -- Custom Commands --
        if command.startswith(self.prefix + "?"):
            await self.custom_commands.cc_handler(message)

        if command.startswith(self.prefix + "add_cc"):
            await self.custom_commands.add_cc(message)

        if command.startswith(self.prefix + "del_cc"):
            await self.custom_commands.del_cc(message)

        if command.startswith(self.prefix + "list_cc"):
            await self.custom_commands.list_cc(message)

        # -- Experimental Emoji Commands --
        if command == self.prefix + "get_all_emojis":
            await self.ctx.send_message(message.channel, self.emojis.get_all_client_emojis())

        # -- Rank related commands --
        if command.startswith(self.prefix + "xp"):
            await utility.xp(self.ctx, message)

        if command.startswith(self.prefix + "leaderboard"):
            await utility.leaderboard(self.ctx, message)

        # -- Admin Commands --
        if command.startswith(self.prefix + "mute"):
            if self.verify_role(message.author):
                await admin.mute(self.ctx, message.mentions[0] if message.mentions else None, message)

        if command.startswith(self.prefix + "unmute"):
            if self.verify_role(message.author):
                await admin.unmute(self.ctx, message.mentions[0] if message.mentions else None, message)

        if command.startswith(self.prefix + "prune"):
            if self.verify_role(message.author):
                params = command.split(" ", maxsplit=2)
                if 2 <= len(params) <= 3:
                    try:
                        amount = params[2]
                    except IndexError:
                        amount = params[1]
                    await admin.prune(self.ctx, message.mentions[0] if message.mentions else None,
                                      int(amount) if amount.isdigit() else 0, message)
                else:
                    # We force a error message
                    await admin.prune(self.ctx, None, 0, message)

        if command.startswith(self.prefix + "purge"):
            if self.verify_role(message.author):
                params = command.split(" ", maxsplit=1)
                if len(params) == 2:
                    amount = params[1]
                    await admin.purge(self.ctx, int(amount) if amount.isdigit() else 0, message)
                else:
                    # We force a error message
                    await admin.purge(self.ctx, 0, message)

        if command.startswith(self.prefix + "logging"):
            if self.verify_role(message.author):
                params = command.split(" ", maxsplit=1)
                if len(params) == 2:
                    action = params[1].lower()
                    await utility.logging(self.ctx, message, action)
                else:
                    # We force a error message
                    await utility.logging(self.ctx, message, "Invalid_Input")

        if command.startswith(self.prefix + "ignore"):
            if self.verify_role(message.author):
                await admin.ignore(self.ctx, message)

        if command.startswith(self.prefix + "unignore"):
            if self.verify_role(message.author):
                await admin.unignore(self.ctx, message)

        if command.startswith(self.prefix + "auto_role"):
            if self.verify_role(message.author):
                await admin.auto_role(self.ctx, message)

        if command.startswith(self.prefix + "auto_reset"):
            if self.verify_role(message.author):
                await admin.auto_reset(self.ctx, message)

        if command.startswith(self.prefix + "set_welcome"):
            if self.verify_role(message.author):
                await admin.set_welcome(self.ctx, message)

        if command.startswith(self.prefix + "set_leave"):
            if self.verify_role(message.author):
                await admin.set_leave(self.ctx, message)

        if command.startswith(self.prefix + "cc"):
            if self.verify_role(message.author):
                await admin.cc(self.ctx, message)

        if command.startswith(self.prefix + "res_cc"):
            if self.verify_role(message.author):
                await admin.restrict_cc(self.ctx, message)

        if command.startswith(self.prefix + "nsfw"):
            if self.verify_role(message.author):
                await admin.nsfw(self.ctx, message)

        if command.startswith(self.prefix + "set_nsfw"):
            if self.verify_role(message.author):
                await admin.set_nsfw(self.ctx, message)

        if command.startswith(self.prefix + "add_sar"):
            if self.verify_enabled(message.server.id, "sar") and self.verify_role(message.author):
                await admin.add_sar(self.ctx, message)

        if command.startswith(self.prefix + "announce"):
            if self.verify_role(message.author):
                await admin.announce(self.ctx, message)

        if command.startswith(self.prefix + "set_announce"):
            if self.verify_role(message.author):
                await admin.set_announce(self.ctx, message)

        if command.startswith(self.prefix + "color"):
            if self.verify_role(message.author):
                await admin.color(self.ctx, message)

        if command.startswith(self.prefix + "role_add"):
            if self.verify_role(message.author):
                await admin.role_add(self.ctx, message)

        if command.startswith(self.prefix + "role_remove"):
            if self.verify_role(message.author):
                await admin.role_remove(self.ctx, message)

        if command.startswith(self.prefix + "kick"):
            if self.verify_role(message.author):
                await admin.kick(self.ctx, message)

        if command.startswith(self.prefix + "ban"):
            if self.verify_role(message.author):
                await admin.ban(self.ctx, message)

        if command.startswith(self.prefix + "unban"):
            if self.verify_role(message.author):
                await admin.unban(self.ctx, message)

        if command.startswith(self.prefix + "levels"):
            if self.verify_role(message.author):
                await admin.levels(self.ctx, message)

        if command.startswith(self.prefix + "set_levels_an"):
            if self.verify_role(message.author):
                await admin.set_levels_an(self.ctx, message)

        if command.startswith(self.prefix + "set_xp_roles"):
            if self.verify_role(message.author):
                await admin.set_xp_roles(self.ctx, message)

        if command.startswith(self.prefix + "add_twitch"):
            if self.verify_role(message.author):
                await admin.add_twitch(self.ctx, message)

        if command.startswith(self.prefix + "add_feed"):
            if self.verify_role(message.author):
                await admin.add_feed(self.ctx, message)

        if command.startswith(self.prefix + "del_feed"):
            if self.verify_role(message.author):
                await admin.del_feed(self.ctx, message)

        if command.startswith(self.prefix + "list_feed"):
            if self.verify_role(message.author):
                await admin.list_feed(self.ctx, message)

        # -- Fun Commands --
        if command.startswith(self.prefix + "sr"):
            if self.verify_enabled(message.server.id, "sr"):
                await self.ctx.loop.create_task(self.imgur.sub_reddit_parser(message))

        if command.startswith(self.prefix + "quotes"):
            if self.verify_enabled(message.server.id, "quotes"):
                await fun.quotes(self.ctx, message)

        if command.startswith(self.prefix + "fuck"):
            if self.verify_enabled(message.server.id, "fuck"):
                await fun.fuck(self.ctx, message)

        if command.startswith(self.prefix + "lenny"):
            if self.verify_enabled(message.server.id, "memes"):
                await fun.memes(self.ctx, message, "lenny")

        if command.startswith(self.prefix + "lewd"):
            if self.verify_enabled(message.server.id, "memes"):
                await fun.memes(self.ctx, message, "lewd")

        if command.startswith(self.prefix + "pogchamp"):
            if self.verify_enabled(message.server.id, "memes"):
                await fun.memes(self.ctx, message, "pogchamp")

        if command.startswith(self.prefix + "opieop"):
            if self.verify_enabled(message.server.id, "memes"):
                await fun.memes(self.ctx, message, "opieop")

        if command.startswith(self.prefix + "wolfiesgame"):
            if self.verify_enabled(message.server.id, "memes"):
                await fun.memes(self.ctx, message, "wolfiesgame")

        if command.startswith(self.prefix + "megunuke"):
            if self.verify_enabled(message.server.id, "memes"):
                await fun.memes(self.ctx, message, "megunuke")

        if command.startswith(self.prefix + "kappa"):
            if self.verify_enabled(message.server.id, "memes"):
                await fun.memes(self.ctx, message, "kappa")

        if command.startswith(self.prefix + "feelsgoodman"):
            if self.verify_enabled(message.server.id, "memes"):
                await fun.memes(self.ctx, message, "feelsgoodman")

        if command.startswith(self.prefix + "feelsbadman"):
            if self.verify_enabled(message.server.id, "memes"):
                await fun.memes(self.ctx, message, "feelsbadman")

        if command.startswith(self.prefix + "lapz"):
            if self.verify_enabled(message.server.id, "memes"):
                await fun.memes(self.ctx, message, "lapz")

        if command.startswith(self.prefix + "ud"):
            if self.verify_enabled(message.server.id, "ud"):
                await fun.urban_dictionary(self.ctx, message)

        if command.startswith(self.prefix + "8ball"):
            if self.verify_enabled(message.server.id, "8ball"):
                await fun.eightball(self.ctx, message)

        # -- osu! commands --
        if command.startswith(self.prefix + "setosu"):
            if self.verify_enabled(message.server.id, "osu"):
                await self.osu.setosu(message)

        if command.startswith(self.prefix + "sig"):
            if self.verify_enabled(message.server.id, "osu"):
                await self.osu.signature_gen(message)

        if command.startswith(self.prefix + "osu"):
            if self.verify_enabled(message.server.id, "osu"):
                await self.osu.osu(message)

        if command.startswith(self.prefix + "taiko"):
            if self.verify_enabled(message.server.id, "osu"):
                await self.osu.taiko(message)

        if command.startswith(self.prefix + "ctb"):
            if self.verify_enabled(message.server.id, "osu"):
                await self.osu.ctb(message)

        if command.startswith(self.prefix + "mania"):
            if self.verify_enabled(message.server.id, "osu"):
                await self.osu.mania(message)

        if command.startswith(self.prefix + "stats"):
            if self.verify_enabled(message.server.id, "osu"):
                await self.osu.stats_parser(message)

        if command.startswith(self.prefix + "top"):
            if self.verify_enabled(message.server.id, "osu"):
                await self.osu.top_parser(message)

        if command.startswith(self.prefix + "pp"):
            if self.verify_enabled(message.server.id, "osu"):
                await self.osu.get_pp(message)

        # -- NSFW Commands
        if command.startswith(self.prefix + "baka"):
            await self.nsfw.baka(message)

        if command.startswith(self.prefix + "danbooru"):
            await self.nsfw.danbooru(message)

        if command.startswith(self.prefix + "gelbooru"):
            await self.nsfw.gelbooru(message)

        if command.startswith(self.prefix + "rule34"):
            await self.nsfw.rule34(message)

        # -- Weeb Commands --
        if command.startswith(self.prefix + "anime"):
            if self.verify_enabled(message.server.id, "anime"):
                await self.weeb.anime_parser(message)

        if command.startswith(self.prefix + "manga"):
            if self.verify_enabled(message.server.id, "manga"):
                await self.weeb.manga_parser(message)

        # -- Games --
        if command.startswith(self.prefix + "roll"):
            if self.verify_enabled(message.server.id, "roll"):
                await self.games.roll(message)

        if command.startswith(self.prefix + "toss"):
            if self.verify_enabled(message.server.id, "toss"):
                await self.games.toss(message)

        if command.startswith(self.prefix + "choose"):
            if self.verify_enabled(message.server.id, "choose"):
                await self.games.choose(message)

        if command.startswith(self.prefix + "rps"):
            if self.verify_enabled(message.server.id, "roll"):
                rps = games.RPS(message.author, message.author.id)
                rps.lapz_instance = self.ctx
                rps.message = message
                await self.ctx.loop.create_task(rps.main())

        if command.startswith(self.prefix + "guess"):
            if self.verify_enabled(message.server.id, "guess"):
                await self.games.guess(message)

        # TeamRero Functions
        if command.startswith(self.prefix + "r_blist"):
            if self.verify_role(message.author):
                await admin.xp_blacklist(self.ctx, message)

        if command.startswith(self.prefix + "check_blist"):
            if self.verify_role(message.author):
                await admin.list_xp_blacklist(self.ctx, message)

