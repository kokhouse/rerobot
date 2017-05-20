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
import datetime
from Rero import redis_manager, mongo_manager
from Rero.Modules import ranking
import discord
import psutil
import os
import wikipedia
import json
import random
import aiohttp
import re


db = mongo_manager.mongo_db.db
redis = redis_manager.redis_manager.redis

with open("config/settings.yaml") as file:
    settings_file = file.read()
file.close()
settings = yaml.load(settings_file)

def ping(message, current_shard):
    """
    Ping Command

    :param current_shard:
    :param message:
    :return:
    """
    now = datetime.datetime.utcnow()
    msg_time_stamp = message.timestamp
    difference = now - msg_time_stamp
    return "**PONG**\nReply in {} s from **SHARD {}**".format(str(difference), str(current_shard))


def help_message():
    """

    :return:
    """
    help_text = """
    **RERO**
    *The multipurpose utility bot for Discord.*

    Commands
    ```ruby
    .             ?names : List of detected name changes
     ?pm [on, off, 24/7] : Sends you PM if you get mentioned
         ?8ball question : Answers a question 8 ball style
           ?sr subreddit : Grab random image from the subreddit
             ?anime name : Grab a anime from MAL
             ?manga name : Grab a manga from MAL
               ?ud query : Urban Dictionary definition
             ?wiki query : Wikipedia summary of querry
            ?giphy query : Gif matching querry
          ?xkcd [number] : Random xkcd or specify a number
           ?weather city : Get weather information
    ```
    For a complete list of functions (*too many to send by PM*),

    Want Rero in your server too?
    <https://discordapp.com/oauth2/authorize?client_id=314796406948757504&scope=bot&permissions=8>

    Visit RERO's Server:
    https://discord.gg/nSHt53W
    """
    return help_text

async def info(ctx, message):
    """
    Displays Rero information

    :param ctx:
    :param message:
    :return:
    """
    # TODO: this command needs to be fixed later
    servs = len(ctx.servers)
    ch = list(ctx.get_all_channels())
    channels = len(ch)
    mem = list(ctx.get_all_members())
    members = len(mem)

    current = datetime.datetime.now()
    diff = current - ctx.startup_timestamp
    days = diff.days
    seconds = diff.seconds
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    # total_c = ctx.usage_track_admin['admin'] + ctx.usage_track['user']
    # total_m = ctx.usage_track_admin['total_msg']

    # r_min = (days * 24 * 60) + (h * 60) + m
    # msg_rate = float(total_c / r_min)
    # total_msg_rate = float(total_m / r_min)
    try:
        proc = psutil.Process(pid=os.getpid())
        rss = float(proc.memory_info().rss) / 1000000
        rss_per = float(proc.memory_percent())
        cpu_per = float(proc.cpu_percent(interval=0.2))
        sys_str = "RAM: {0:.2f} MB | CPU Usage: {1:.2f}% (*calculated for `2 ms` interval*)" \
            .format(rss, rss_per, cpu_per)
    except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
        sys_str = ""

    # ret_str = "`Connected to '{0}' Servers with '{1}' Channels and '{2}' Members`" \
    #           "\nCurrent uptime is {3} Days, {4} Hours, {5} Minutes, {6} Seconds" \
    #           "\n**{7}** commands were __used__ till now (**~{8:.2f}** per min)" \
    #           "\n**{9}** messages were __sent__ till now (**~{10:.2f}** per min)" \
    #           "\n**{11}** messages were __seen__ till now (**~{12:.2f}** per min)" \
    #           "\n{13}" \
    #     .format(str(servs), str(channels), str(members), str(days), str(h),
    #             str(m), str(s), str(total_c), msg_rate, ctx.rero_sent_message,
    #             float(ctx.rero_sent_message / r_min), str(total_m), total_msg_rate, sys_str)

    ret_str = "`Connected to '{0}' Servers with '{1}' Channels and '{2}' Members`" \
              "\nCurrent uptime is {3} Days, {4} Hours, {5} Minutes, {6} Seconds" \
              "\n{7}\n**SHARD: {8} / 2**" \
        .format(str(servs), str(channels), str(members), str(days), str(h),
                str(m), str(s), sys_str, ctx.current_shard)

    await ctx.send_message(message.channel, ret_str)

async def logging(ctx, message, action: str):
    """
    Set message logging status

    :param ctx:
    :param action:
    :param message:
    :return:
    """

    key = message.server.id + "logger"
    if action == "on":
        if redis.exists(key):
            await ctx.send_message(message.channel, "**Error**: `Logging is already enabled.`")
            return
        redis.set(key, "LOGGING: GLOBAL")
        await ctx.send_message(message.channel, "**Success**: Logging `Enabled`\n"
                                                "*Remember this is a experimental function. Thank "
                                                "you for participating in the alpha test.*")
        return
    elif action == "off":
        if redis.exists(key):
            redis.delete(key)
            await ctx.send_message(message.channel, "**Success**: Logging `Disabled`")
            return
        await ctx.send_message(message.channel, "**Error**: `Logging is already disabled.`")
        return
    else:
        await ctx.send_message(message.channel, "**Error**: `Invalid input. Valid choices are 'on' and 'off'`")
        return


async def xp(ctx, message):
    """
    Returns current XP

    :param ctx:
    :param message:
    :return:
    """
    server_id = message.server.id
    key_check = server_id + "lvl_track"

    # If Rankings are not enabled, we don't
    # wanna display the xp and leaderboard
    if redis.exists(key_check):

        # First we check if set_xp_roles are active. What this means is
        # we check if only specific roles can access the xp command.
        # This was originally designed keep osu! Discord in mind
        key = message.server.id + "xp_roles"
        if redis.exists(key):
            role_ran = redis.llen(key)
            if not role_ran == 0:
                allowed_roles = redis.lrange(key, 0, -1)
                for a in allowed_roles:
                    role_id = a.decode("utf-8")
                    role_c = discord.utils.get(message.server.roles, id=role_id)

                    # If the current user's roles are white-listed
                    # we process his request
                    if role_c in message.author.roles:

                        # if someone is mentioned then we display
                        # the mentioned users info. Else we display
                        # the senders info
                        mentions = message.mentions
                        if not len(mentions) == 0:
                            mem = mentions[0]
                            user_id = mem.id
                            name = mem.name
                        else:
                            user_id = message.author.id
                            name = message.author.name

                        cursor_mem = db.user_db_new.find({
                            "user_id": user_id,
                            "experience_per_server": {
                                "$elemMatch": {
                                    "server_id": message.server.id
                                }
                            }
                        })
                        if cursor_mem.count() == 0:
                            await ctx.send_message(message.channel, ":scream: **Error** `This member has no XP.`")
                            return
                        for i in cursor_mem:
                            for j in i['experience_per_server']:
                                if j["server_id"] == message.server.id:
                                    try:
                                        xp_s = float(j['xp'])
                                    except KeyError:
                                        await ctx.send_message(message.channel,
                                                               ":scream: **Error** `This member has no XP.`")
                                        return
                                    try:
                                        level = int(j['level'])
                                    except KeyError:
                                        level = ranking.xp_to_level(xp_s)

                                    try:
                                        message_count = j['message_count']
                                    except KeyError:
                                        message_count = "0"

                                    await ctx.send_message(message.channel,
                                                           ranking.get_xp_info(level, user_id, name, server_id, xp_s,
                                                                               message_count))
                                    return

        else:
            # if someone is mentioned then we display
            # the mentioned users info. Else we display
            # the senders info
            mentions = message.mentions
            if not len(mentions) == 0:
                mem = mentions[0]
                user_id = mem.id
                name = mem.name
            else:
                user_id = message.author.id
                name = message.author.name

            cursor_mem = db.user_db_new.find({
                "user_id": user_id,
                "experience_per_server": {
                    "$elemMatch": {
                        "server_id": message.server.id
                    }
                }
            })

            if cursor_mem.count() == 0:
                await ctx.send_message(message.channel, ":scream: **Error** `This member has no XP.`")
                return
            for i in cursor_mem:
                for j in i['experience_per_server']:
                    if j["server_id"] == message.server.id:
                        try:
                            xp_s = float(j['xp'])
                        except KeyError:
                            await ctx.send_message(message.channel, ":scream: **Error** `This member has no XP.`")
                            return
                        try:
                            level = int(j['level'])
                        except KeyError:
                            level = ranking.xp_to_level(xp_s)

                        try:
                            message_count = j['message_count']
                        except KeyError:
                            message_count = "0"

                        await ctx.send_message(message.channel,
                                               ranking.get_xp_info(level, user_id, name, server_id, xp_s,
                                                                   message_count))
                        return


def leaderboard_generator(a, message):
    """
    Returns a nicely formatted leaderboard

    :return:
    """
    leaderboard_sorted = sorted(a, key=lambda a: float(a[1]), reverse=True)
    if len(leaderboard_sorted) < 5:
        op_str = "**Error** `Leaderboards are only available if you have at-least 5 'active' members.`"
        return op_str

    elif len(leaderboard_sorted) >= 5:
        n1 = discord.utils.get(message.server.members, id=str(leaderboard_sorted[0][0]))
        na1 = n1.name if n1 else ""
        n2 = discord.utils.get(message.server.members, id=str(leaderboard_sorted[1][0]))
        na2 = n2.name if n2 else ""
        n3 = discord.utils.get(message.server.members, id=str(leaderboard_sorted[2][0]))
        na3 = n3.name if n3 else ""
        n4 = discord.utils.get(message.server.members, id=str(leaderboard_sorted[3][0]))
        na4 = n4.name if n4 else ""
        n5 = discord.utils.get(message.server.members, id=str(leaderboard_sorted[4][0]))
        na5 = n5.name if n5 else ""

        op_str = "{0} **Leaderboards**\n" \
                 ":crown: **{1} | {2:.1f} XP | {3} Msgs**\n" \
                 ":two: {4} | {5:.1f} XP | {6} Msgs\n" \
                 ":three: {7} | {8:.1f} XP | {9} Msgs\n" \
                 ":four: {10} | {11:.1f} XP | {12} Msgs\n" \
                 ":five: {13} | {14:.1f} XP | {15} Msgs" \
            .format(message.server.name,
                    na1, float(leaderboard_sorted[0][1]), leaderboard_sorted[0][2],
                    na2, float(leaderboard_sorted[1][1]), leaderboard_sorted[1][2],
                    na3, float(leaderboard_sorted[2][1]), leaderboard_sorted[2][2],
                    na4, float(leaderboard_sorted[3][1]), leaderboard_sorted[3][2],
                    na5, float(leaderboard_sorted[4][1]), leaderboard_sorted[4][2])
        return op_str


async def leaderboard(ctx, message):
    """
    Displays the Leaderboard

    :param ctx:
    :param message:
    :return:
    """
    server_id = message.server.id
    key_check = server_id + "lvl_track"

    # If Rankings are not enabled, we don't
    # wanna display the xp and leaderboard
    if redis.exists(key_check):

        # First we check if set_xp_roles are active. What this means is
        # we check if only specific roles can access the xp command.
        # This was originally designed keep osu! Discord in mind
        key = str(message.server.id) + "xp_roles"
        if redis.exists(key):
            role_ran = redis.llen(key)

            if not role_ran == 0:
                allowed_roles = redis.lrange(key, 0, -1)
                for a in allowed_roles:
                    id_r = a.decode("utf-8")
                    role_c = discord.utils.get(message.server.roles, id=id_r)
                    if role_c in message.author.roles:
                        a = []
                        cursor_mem = db.user_db_new.find({"experience_per_server.server_id": message.server.id})
                        if cursor_mem.count() == 0:
                            await ctx.send_message(message.channel, "**Error** `Ranking not enabled on this "
                                                                    "server.`")
                            return
                        else:
                            for i in cursor_mem:
                                for j in i['experience_per_server']:
                                    if j['server_id'] == message.server.id:
                                        try:
                                            msg_count = j['message_count']
                                        except KeyError:
                                            msg_count = "0"
                                        a.append((i['user_id'], j['xp'], msg_count))

                            await ctx.send_message(message.channel, leaderboard_generator(a, message))
                            return
        else:
            a = []
            cursor_mem = db.user_db_new.find({"experience_per_server.server_id": message.server.id})
            if cursor_mem.count() == 0:
                await ctx.send_message(message.channel, "**Error** `Ranking not enabled on this "
                                                        "server.`")
                return
            else:
                for i in cursor_mem:
                    for j in i['experience_per_server']:
                        if j['server_id'] == message.server.id:
                            try:
                                msg_count = j['message_count']
                            except KeyError:
                                msg_count = "0"
                            a.append((i['user_id'], j['xp'], msg_count))

                await ctx.send_message(message.channel, leaderboard_generator(a, message))
                return

async def status(ctx, message):
    """
    Change Rero profile status

    :param ctx:
    :param message:
    :return:
    """
    cursor = db.user_db_new.find({"user_id": message.author.id})
    if not cursor.count() == 0:
        status_txt = message.content[8:]
        if len(status_txt) > 50:
            await ctx.send_message(message.channel, "**Error** `Status text must be less that 50 characters.`")
            return

        field = {"user_id": message.author.id}
        update = {
            "$set": {
                "profile.status_text": status_txt
            },
            "$currentDate": {
                 "last_updated": {
                     "$type": "date"
                 }
            }
        }
        db.user_db_new.update_one(field, update)
        await ctx.send_message(message.channel, "**Success** `Status text updated.`")
        return

async def about(ctx, message):
    """
    Change Rero profile about_me text

    :param ctx:
    :param message:
    :return:
    """
    cursor = db.user_db_new.find({"user_id": message.author.id})
    if not cursor.count() == 0:
        about_me_text = message.content[7:]
        if len(about_me_text) > 1000:
            await ctx.send_message(message.channel, "**Error** `'About Me' must be less than 1000 characters.`")
            return

        field = {"user_id": message.author.id}
        update = {
            "$set": {
                "profile.about_me_box": about_me_text
            },
            "$currentDate": {
                "last_updated": {
                     "$type": "date"
                }
            }
        }
        db.user_db_new.update_one(field, update)
        await ctx.send_message(message.channel, "**Success** `'About Me' section updated.`")
        return

async def profile(ctx, message):
    """
    Returns a link to your current Rero profile

    :param ctx:
    :param message:
    :return:
    """
    cursor = db.user_db_new.find({"user_id": message.author.id})
    if not cursor.count() == 0:
        await ctx.send_message(message.channel, "https://github.com/voqz/rerobot/u/{}".format(message.author.id))
        return

async def self_assigned_role(ctx, message):
    """
    Assign SAR

    :param ctx:
    :param message:
    :return:
    """
    role_alias = message.content[3:]
    role_m = message.author.roles
    cursor = db.server_backend.find({"serv_id": message.server.id})
    if cursor.count() == 0:
        return

    try:
        for j in cursor:
            avail_sar = j['self_assigned_roles']
            memb_ids = []
            k_id = None

            for i in role_m:
                memb_ids.append(i.id)

            for k in avail_sar:
                if k['role_alias'] == role_alias:
                    k_id = k['role_id']
            if k_id:
                if k_id in memb_ids:
                    role = discord.utils.get(message.server.roles, id=k_id)
                    if role:
                        await ctx.remove_roles(message.author, role)
                        await ctx.send_message(message.channel, "`You are not '{}' anymore ;w;`".format(role_alias))
                        return

                role = discord.utils.get(message.server.roles, id=k_id)
                if role:
                    await ctx.add_roles(message.author, role)
                    await ctx.send_message(message.channel, "`You are now '{}'`".format(role_alias))
                    return
    except KeyError:
        return

async def pervert(ctx, message):
    """
    Toggle the Pervert role

    :param ctx:
    :param message:
    :return:
    """
    role_m = message.author.roles
    for i in role_m:
        if i.name == "Pervert":
            role = discord.utils.get(message.server.roles, name="Pervert")
            if role:
                await ctx.remove_roles(message.author, role)
                await ctx.send_message(message.channel, "**Success** `You are not a Pervert anymore.`")
                return
    role = discord.utils.get(message.server.roles, name="Pervert")
    if role:
        await ctx.add_roles(message.author, role)
        await ctx.send_message(message.channel, "**Success** `Now you can enjoy the good stuff ;)`")
        return

async def pm(ctx, message):
    """
    Sends PM notifications when someone is mentioned

    :param ctx:
    :param message:
    :return:
    """
    switch = message.content[4:]
    if switch == "":
        await ctx.send_message(message.channel, "**Error**: No option mentioned"
                                                "\nUsage: `;;pm on`, `?pm off`, `?pm 24/7`"
                                                "\n**ON**: You will only get a PM (when you get mentioned) "
                                                "if you are offline/idle."
                                                "\n**24/7**: You will get a PM whenever you get mentioned.")
        return
    elif str(switch).lower() == "on":
        key = message.author.id + "pm"
        redis.set(key, "PM Mentions: ON")
        await ctx.send_message(message.channel, "**PM ON**: I will send you a PM when you get mentioned "
                                                "and if you happen to be away or offline.")
    elif str(switch) == "24/7":
        key = message.author.id + "pm"
        redis.set(key, "PM Mentions: 24/7")
        await ctx.send_message(message.channel, "**PM 24/7**: I will send you a PM whenever you get "
                                                "mentioned.")
    elif str(switch).lower() == "off":
        key = message.author.id + "pm"
        if redis.exists(key):
            redis.delete(key)
            await ctx.send_message(message.channel, "**PM OFF**: I won't send you PM's. To re-enable, "
                                                    "use `?pm on`")
        else:
            await ctx.send_message(message.channel, "**Error** `PM mentions are already turned OFF for you.`")
    else:
        await ctx.send_message(message.channel, "**Error**: invalid option"
                                                "\nUsage: `;;pm on`, `?pm 24/7` and `?pm off`")

async def wikipedia_parser(ctx, message):
    """
    Returns a wikipedia definition

    :param ctx:
    :param message:
    :return:
    """
    try:
        querry = message.content[6:]
        search = wikipedia.summary(str(querry), sentences=4)
        await ctx.send_message(message.channel, "```{}```".format(search))

    except wikipedia.DisambiguationError as e:
        length = len(e.options)
        if length == 1:
            await ctx.send_message(message.channel, "Did you mean? `{}`".format(e.options[0]))
        elif length == 2:
            await ctx.send_message(message.channel, "Did you mean? `{}` or `{}`"
                                                    .format(e.options[0], e.options[1]))
        else:
            await ctx.send_message(message.channel,
                                   "Disambiguation in you query. It can mean `{}`, `{}` and {} more."
                                   .format(e.options[0], e.options[1], str(length)))
    except wikipedia.PageError:
        await ctx.send_message(message.channel, "No pages matched your querry :cry:")
    except wikipedia.HTTPTimeoutError:
        await ctx.send_message(message.channel, "Hey there, slow down you searches for a bit!")
    except wikipedia.RedirectError:
        await ctx.send_message(message.channel,
                               "Error: page title unexpectedly resolves to a redirect. "
                               "Please re-check your query.")
    except wikipedia.WikipediaException:
        await ctx.send_message(message.channel, "Error: The search parameter must be set.")

async def clean(ctx, message):
    """
    Cleans the previous messages

    :param ctx:
    :param message:
    :return:
    """
    try:
        message_bucket = []
        async for entry in ctx.logs_from(message.channel):
            if entry.author == ctx.user:
                message_bucket.append(entry)
        await ctx.delete_messages(message_bucket)
        await ctx.send_message(message.channel, ':sweat_drops: `Cleaned.`')
    except discord.Forbidden:
        await ctx.send_message(message.channel, '**Error**: `I do not have permissions to get channel logs`')
        return
    except discord.NotFound:
        await ctx.send_message(message.channel, '**Error**: `The channel you are requesting for doesnt exist.`')
        return
    except discord.HTTPException:
        return

async def name_changes(ctx, message):
    """
    Returns a list of detected name changes

    :param ctx:
    :param message:
    :return:
    """
    cont = message.content[7:]
    if str(cont) == '':
        cursor = db.name_changes.find({"user_id": str(message.author.id)})
        if cursor.count() == 0:
            await ctx.send_message(message.channel, "No name changes detected")
        else:
            for docs in cursor:
                names = docs['names']
                name_agg = ''
                for name in names:
                    name_agg += str(name) + ', '
                await ctx.send_message(message.channel, "{}".format(name_agg))
    else:
        m = discord.utils.get(message.server.members, display_name=str(cont))
        if m is None:
            await ctx.send_message(message.channel, "Discord member not found. Make sure you type the "
                                                    "current Discord name only. Also, don't use `@`.")
            return

        cursor = db.name_changes.find({"user_id": str(m.id)})
        if cursor.count() == 0:
            await ctx.send_message(message.channel, "No name changes detected")
        else:
            for docs in cursor:
                names = docs['names']
                name_agg = ''
                for name in names:
                    name_agg += str(name) + ', '
                await ctx.send_message(message.channel, "{}".format(name_agg))

async def whoami(self, message):
    """

    :param self:
    :param message:
    """
    role = ''
    name = message.author.name
    if name == "@here":
        corrected_name = ">>HERE<<"
    elif name == "@everyone":
        corrected_name = ">>EVERYONE<<"
    else:
        corrected_name = name

    idsa = message.author.id
    server = message.author.server
    j_dict = {"year": str(message.author.joined_at.year),
              "month": str(message.author.joined_at.month),
              "day": str(message.author.joined_at.day),
              "hour": str(message.author.joined_at.hour),
              "minute": str(message.author.joined_at.minute)}
    avatar_url = message.author.avatar_url
    disrim = message.author.discriminator
    for r in message.author.roles:
        if not str(r) == '@everyone':
            r = str(r.name) + ', '
            role += r
        elif str(r) == '@everyone':
            continue

    # noinspection PyPep8
    opstr = "```ruby\n" \
            ".           Name : {}\n" \
            "              ID : {}\n" \
            "  Current Server : {}\n" \
            "       Joined on : {}-{}-{} @ {}:{} UTC\n" \
            "           Roles : \n" \
            "             {}\n" \
            "   Discriminator : {}\n```" \
            "{}".format(corrected_name, idsa, server, j_dict["year"], j_dict["month"], j_dict["day"],
                        j_dict["hour"], j_dict["minute"], role, disrim, avatar_url)
    await self.send_message(message.channel, opstr)

async def whois(self, message):
    """

    :param self:
    :param message:
    :return:
    """
    member = message.mentions

    for memb in member:
        j_dict = {"year": str(memb.joined_at.year),
                  "month": str(memb.joined_at.month),
                  "day": str(memb.joined_at.day),
                  "hour": str(memb.joined_at.hour),
                  "minute": str(memb.joined_at.minute)}
        role = ''
        name = memb.name
        if name == "@here":
            corrected_name = ">>HERE<<"
        elif name == "@everyone":
            corrected_name = ">>EVERYONE<<"
        else:
            corrected_name = name

        idsa = memb.id
        server = memb.server
        avatar_url = memb.avatar_url
        disrim = memb.discriminator
        for r in memb.roles:
            if not str(r) == '@everyone':
                r = str(r.name) + ', '
                role += r
            elif str(r) == '@everyone':
                continue

        opstr = "```ruby\n" \
                ".           Name : {}\n" \
                "              ID : {}\n" \
                "  Current Server : {}\n" \
                "       Joined on : {}-{}-{} @ {}:{} UTC\n" \
                "           Roles : \n" \
                "             {}\n" \
                "  Discriminator : {}\n```" \
                "{}".format(corrected_name, idsa, server, j_dict["year"], j_dict["month"], j_dict["day"],
                            j_dict["hour"], j_dict["minute"], role, disrim, avatar_url)
        await self.send_message(message.channel, opstr)

async def giphy(self, message, querry):
    """
    GIPHY gif search

    :param self:
    :param message:
    :param querry: gif search querry (example: awesome+dogs+swag)
    :return: gif image matching search criteria
    """
    try:
        endpoint = "http://api.giphy.com/v1/gifs/search?"
        payload = {"q": querry,
                   "api_key": settings[GIPHY_API_KEY],
                   "limit": "10",
                   '"offset': "0"}
        with aiohttp.ClientSession() as session:
            async with session.get(url=endpoint, params=payload) as resp:
                data = await resp.read()

        r = json.loads(data.decode("utf-8"))
        payload = r['data']
        if len(payload) == 0 or payload is None:
            await self.send_message(message.channel, 'GIPHY ERROR: *No items matched the search querry.*')
            return
        rnd = random.randint(0, len(payload) - 1)
        image = payload[rnd]['images']['original']['url']
        await self.send_message(message.channel, str(image))
    except ValueError:
        await self.send_message(message.channel, 'GIPHY ERROR: *No items matched the search querry.*')
    except IndexError:
        await self.send_message(message.channel, 'GIPHY ERROR: *No items matched the search querry.*')

async def xkcd(querry):
    """

    :param querry:
    :return:
    """
    try:
        q_int = int(querry)
        endpoint = "http://xkcd.com/{}/info.0.json".format(str(q_int))
        with aiohttp.ClientSession() as session:
            async with session.get(url=endpoint) as resp:
                data = await resp.read()

        r = json.loads(data.decode("utf-8"))
        # r = requests.get("http://xkcd.com/{}/info.0.json".format(str(q_int)))
        # data = r.json()
        alt = r['alt']
        img = r['img']
        num = r['num']
        title = r['title']
        trans = r['transcript']
        t_raw = re.sub("{{.*?}}", "", trans)
        t_clean = re.sub("[\[,\]]", "", t_raw)

        ret_str = "Title: `{}`" \
                  "\nAlt: `{}`" \
                  "\nXKCD no.: `{}`" \
                  "\nTranscript: ```{}```" \
                  "\n{}".format(title, alt, num, t_clean, img)
        return ret_str

    except ValueError:
        q_int = random.randint(1, 1500)
        endpoint = "http://xkcd.com/{}/info.0.json".format(str(q_int))
        with aiohttp.ClientSession() as session:
            async with session.get(url=endpoint) as resp:
                data = await resp.read()

        r = json.loads(data.decode("utf-8"))
        alt = r['alt']
        img = r['img']
        num = r['num']
        title = r['title']
        trans = r['transcript']
        t_raw = re.sub("{{.*?}}", "", trans)
        t_clean = re.sub("[\[,\]]", "", t_raw)

        ret_str = "Title: `{}`" \
                  "\nAlt: `{}`" \
                  "\nXKCD no.: `{}`" \
                  "\nTranscript: ```{}```" \
                  "\n{}".format(title, alt, num, t_clean, img)
        return ret_str


async def weather(self, message):
    """
    Weather function

    :param self:
    :param message:
    :return:
    """
    city = message.content[9:]
    endpoint = "http://api.openweathermap.org/data/2.5/weather?"
    payload = {'q': city,
               'units': 'metric',
               'appid': settings["OPENWEATHERMAP_APP_ID"]}
    try:
        with aiohttp.ClientSession() as session:
            async with session.get(url=endpoint, params=payload) as resp:
                data = await resp.read()

        r = json.loads(data.decode("utf-8"))
        if r['cod'] == 404:
            await self.send_message(message.channel, "Error: Not found city")
            return
        if r['cod'] == 200:
            cty = r['name']
            country = r['sys']['country']
            tempc = r['main']['temp']
            tempf = (tempc * (9 / 5)) + 32
            humidity = r['main']['humidity']
            icon = r['weather'][0]['icon']
            weathers = r['weather'][0]['main']
            icon_str = "http://openweathermap.org/img/w/" + icon + ".png"

            op_string = "**{}/ {}**" \
                        "\n*Weather*: {}" \
                        "\n*Temperature*: {} C ({} F)" \
                        "\n*Humidity*: {}%" \
                        "\n{}".format(cty, country, weathers, "%.2f" % float(tempc), "%.2f" % float(tempf),
                                      "%.2f" % float(humidity), icon_str)

            await self.send_message(message.channel, op_string)
    except Exception as e:
        print("Weather Error: ")
        print(str(e))

async def translate(text, lang):
    """
    Yandex language translation interface

    :param text:
    :param lang:
    :return:
    """
    key = settings["YANDEX_API_KEY"]
    endpoint = 'https://translate.yandex.net/api/v1.5/tr.json/translate?'
    ui_code = {
        'Albanian': 'sq',
        'English': 'en',
        'Arabic': 'ar',
        'Armenian': 'hy',
        'Azerbaijan': 'az',
        'Afrikaans': 'af',
        'Basque': 'eu',
        'Belarusian': 'be',
        'Bulgarian': 'bg',
        'Bosnian': 'bs',
        'Welsh': 'cy',
        'Vietnamese': 'vi',
        'Hungarian': 'hu',
        'Haitian (Creole)': 'ht',
        'Galician': 'gl',
        'Dutch': 'nl',
        'Greek': 'el',
        'Georgian': 'ka',
        'Danish': 'da',
        'Yiddish': 'he',
        'Indonesian': 'id',
        'Irish': 'ga',
        'Italian': 'it',
        'Icelandic': 'is',
        'Spanish': 'es',
        'Kazakh': 'kk',
        'Catalan': 'ca',
        'Kyrgyz': 'ky',
        'Chinese': 'zh',
        'Korean': 'ko',
        'Latin': 'la',
        'Latvian': 'lv',
        'Lithuanian': 'lt',
        'Malagasy': 'mg',
        'Malay': 'ms',
        'Maltese': 'mt',
        'Macedonian': 'mk',
        'Mongolian': 'mn',
        'German': 'de',
        'Norwegian': 'no',
        'Persian': 'fa',
        'Polish': 'pl',
        'Portuguese': 'pt',
        'Romanian': 'ro',
        'Russian': 'ru',
        'Serbian': 'sr',
        'Slovakian': 'sk',
        'Slovenian': 'sl',
        'Swahili': 'sw',
        'Tajik': 'tg',
        'Thai': 'th',
        'Tagalog': 'tl',
        'Tatar': 'tt',
        'Turkish': 'tr',
        'Uzbek': 'uz',
        'Ukrainian': 'uk',
        'Finnish': 'fi',
        'French': 'fr',
        'Croatian': 'hr',
        'Czech': 'cs',
        'Swedish': 'sv',
        'Estonian': 'et',
        'Japanese': 'ja',
    }

    for langs in ui_code:
        lwr = str(langs).lower()
        if lwr == str(lang).lower():
            ui = ui_code[langs]
            payload = {
                'key': key,
                'text': text,
                'lang': ui
            }
            with aiohttp.ClientSession() as session:
                async with session.get(url=endpoint, params=payload) as resp:
                    data = await resp.read()

            r = json.loads(data.decode("utf-8"))
            # r = requests.get(url=endpoint, params=payload)
            # data = r.json()
            return r['text']
    return 'Translation not possible'


async def twitch(channel):
    """
    Twitch status checker

    :param channel:
    :return: The channel details
    """
    endpoint = "https://api.twitch.tv/kraken/streams/{}".format(str(channel))
    with aiohttp.ClientSession() as session:
        async with session.get(url=endpoint) as resp:
            data = await resp.read()

    r = json.loads(data.decode("utf-8"))
    try:
        status_text = r['stream']
    except KeyError:
        status_text = r['status']
        if status == 404:
            message = r['status']
            return message

    if status_text is None:
        return "Stream is not live"
    else:
        game = r['stream']['channel']['game']
        viewers = r['stream']['viewers']
        url = r['stream']['channel']['url']

        s_text = "`{}` is currently live. " \
                 "\nViewers: `{}`" \
                 "\nPlaying: `{}`" \
                 "\nTwitch Link: <{}>".format(channel, viewers, game, url)
        return s_text

async def translator(ctx, message):
    """

    :param ctx:
    :param message:
    :return:
    """
    cont = message.content[11:]
    parts = cont.split('>')
    if not len(parts) == 2:
        await ctx.send_message(message.channel,
                               "**Error**: Bad request. Use `>` and specify a language."
                               "\nExample: `?translate what am i doing>japanese`")
        return
    try:
        msg = parts[0]
        lang = parts[1]
    except KeyError:
        await ctx.send_message(message.channel,
                               "**Error**: Bad request. Use `>` and specify a language."
                               "\nExample: `?translate what am i doing>japanese`")
        return
    trans = await translate(msg, lang)
    await ctx.send_message(message.channel, trans)

async def server_info(ctx, message):
    """

    :param ctx:
    :param message:
    :return:
    """
    name = message.server.name
    idss = message.server.id
    roles = message.server.roles
    region = message.server.region
    owner = message.server.owner.name
    channels = message.server.channels
    members = message.server.members
    welcome_message = ""
    nsfw_status = ""
    nsfw_chan_name = ""
    # icon = message.server.icon_url
    if redis.exists(message.server.id):
        an_n = "ON"
        an_s = redis.get(message.server.id).decode("utf-8")
        if an_s == "Announcements: ON":
            chan = ctx.get_channel(message.server.id)
            if chan is not None:
                an_name = chan.name
            else:
                an_name = ""

            # cursor = db.servers.find({"serv_id": message.server.id})
            cursor = db.server_backend.find({"serv_id": message.server.id})

            if cursor.count() == 0:
                welcome_message = ":loudspeaker: {{user.mention}}, welcome to `{}`. Hope you have a " \
                                  "good time :smile: ".format(message.server.name)
            else:
                for d in cursor:
                    try:
                        welcome_message = d['welcome_message']
                        nsfw_status = d['nsfw']['nsfw_status']
                        if nsfw_status == "on|channel":
                            nsfw_chan_name = d['nsfw']['nsfw_chan_name']
                        else:
                            nsfw_chan_name = ""

                    except KeyError:
                        welcome_message = ":loudspeaker: {{user.mention}}, welcome to `{}`. Hope you have a " \
                                          "good time :smile: ".format(message.server.name)
        else:
            chan = ctx.get_channel(an_s)
            if chan is not None:
                an_name = chan.name
            else:
                an_name = ""

            # cursor = db.servers.find({"serv_id": message.server.id})
            cursor = db.server_backend.find({"serv_id": message.server.id})
            if cursor.count() == 0:
                welcome_message = ":loudspeaker: {{user.mention}}, welcome to `{}`. Hope you have a " \
                                  "good time :smile: ".format(message.server.name)
            else:
                for d in cursor:
                    try:
                        welcome_message = d['welcome_message']
                        nsfw_status = d['nsfw']['nsfw_status']
                        if nsfw_status == "on|channel":
                            nsfw_chan_name = d['nsfw']['nsfw_chan_name']
                        else:
                            nsfw_chan_name = ""
                    except KeyError:
                        welcome_message = ":loudspeaker: {{user.mention}}, welcome to `{}`. Hope you have a " \
                                          "good time :smile: ".format(message.server.name)
    else:
        an_n = "OFF"
        an_name = ""
        welcome_message = ""

    # -=============================-
    # Remove @everyone from the roles
    # -=============================-
    role = ''
    for r in roles:
        if not str(r) == '@everyone':
            r = str(r.name) + ', '
            role += r
        elif str(r) == '@everyone':
            continue
    ret_str = "```ruby\n" \
              "{0}\n" \
              "        Server ID: {1} | Server Region: {2}\n" \
              "     Server Owner: {3} | Channels: {4}\n" \
              "            Roles: \n" \
              "              {5}\n" \
              "          Members: {6}\n" \
              "    Announcements: {7} | Channel: #{8}\n" \
              "  Welcome Message: {9}\n" \
              "             NSFW: {10} | Channel: #{11}\n```" \
              .format(name, idss, str(region), owner, str(len(channels)), role, str(len(members)), an_n,
                      an_name, welcome_message, nsfw_status, nsfw_chan_name)
    await ctx.send_message(message.channel, ret_str)
