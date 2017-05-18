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
from Rero import mongo_manager, redis_manager
from Rero.Modules import reporting
import datetime
import math


def xp_to_level(xp: float):
    """
    Converts XP to Float

    :type xp: float
    :param xp: XP
    :return: Level
    """
    level = -6 + (math.sqrt(xp + 80) / math.sqrt(5))
    level_normalized = 0 if level <= 0 else math.floor(level)
    return level_normalized


def level_to_xp(level: int):
    """

    :type level: int
    :param level: Level
    :return: XP
    """
    if level == 0:
        return 0
    xp = (5 * (level ** 2)) + (60 * level) + 100
    return xp


def get_xp_info(level, user_id, user_name, server_id, xp_s, msg_count):
    """
    Outputs XP info

    :return:
    """
    if level == 0:
        prev_xp = 0
    else:
        prev_xp = level_to_xp(level)
    next_xp = level_to_xp(level + 1)

    diff = float(next_xp - xp_s)
    diff_per = (1 - (diff / (next_xp - prev_xp))) * 100

    global_rank = redis_manager.redis_manager.redis.zrevrank("global_leaderboard", user_id) + 1
    server_rank = redis_manager.redis_manager.redis.zrevrank("server_leaderboard_{}".format(server_id), user_id) + 1
    global_xp = float(redis_manager.redis_manager.redis.zscore("global_leaderboard", user_id))

    op_str = "**{0}** ( Server Rank **#{1}** ) \n" \
             "(*Global Rank #{2} , {3:.1f} TXP*)\n" \
             "XP: `{4:.1f}` | LvL: `{5}` | Msgs: `{6}`\n" \
             "`{7:.1f}` XP required for level {8} ( {9:.1f}% progress )".format(user_name, server_rank, global_rank,
                                                                                global_xp, xp_s, level, msg_count,
                                                                                diff, level + 1, diff_per)
    return op_str


def xp_calculation(length: int):
    """
    Calculate the XP for the given message length

    :param length:
    :return:
    """
    if length <= 10:
        xp = 0.1
    elif 10 < length <= 200:
        xp = ((length / 200) * 2.5) + 0.5
    elif 200 < length <= 400:
        xp = 2.5
    elif 400 < length <= 600:
        xp = 2
    elif 600 < length <= 800:
        xp = 1.5
    elif 800 < length <= 1000:
        xp = 1
    else:
        xp = 0

    return xp


class Rankings:
    """
    Rero Rankings System
    """
    def __init__(self, context, current_shard):
        super().__init__()
        self.ctx = context
        self.current_shard = current_shard
        self.redis = redis_manager.redis_manager.redis
        self.mongo_ranking = mongo_manager.mongo_db.db_ranking

    def new_user_entry(self, message, xp):
        """
        Inserts a new user to our Database

        :param xp:
        :param message:
        :return:
        """
        key_d = str(datetime.datetime.utcnow().date())
        new_record = {
            "user_id": message.author.id,
            "user_name": message.author.name,
            "past_names": [message.author.name],
            "avatar_url": message.author.avatar_url,
            "bot": message.author.bot,
            "discriminator": str(message.author.discriminator),
            "oauth": {
                "access_token": "",
                "token_type": "",
                "refresh_token": "",
                "time_issued": "",
                "expires_after": ""
            },
            "profile": {
                "badges": [],
                "heading": "",
                "about_me_box": "",
                "featured_server_link": "",
                "hearts": ""
            },
            "supporter": {
                "status": False,
                "mode": "",
                "amount": "",
                "recurring": ""
            },
            "members_of": [{
                "server_id": message.server.id
            }],
            "dashboard_access": [],
            "total_XP": xp,
            "metrics": {
                "txp_growth": [{
                    "date": key_d,
                    "xp": 0
                }]
            },
            "experience_per_server": [{
                "server_id": message.server.id,
                "xp": xp,
                "level": 0,
                "last_an": 0,
                "message_count": 1
            }],
            "last_updated": datetime.datetime.utcnow()
        }
        self.mongo_ranking.user_db_new.insert_one(new_record)
        self.redis.zadd("global_leaderboard", 0, message.author.id)

    def user_metrics(self, user_id, total_c_xp, xp):
        """
        Update the user metrics

        :return:
        """
        key_d = str(datetime.datetime.utcnow().date())
        cursor_metric = self.mongo_ranking.user_db_new.find({
            "user_id": user_id,
            "metrics.txp_growth": {
                "$elemMatch": {
                    "date": key_d
                }
            }
        })
        if cursor_metric.count() == 0:
            field_m = {"user_id": user_id}
            update_m = {
                "$push": {
                    "metrics.txp_growth": {
                        "date": key_d,
                        "xp": total_c_xp + xp
                    }
                },
                "$currentDate": {
                    "last_updated": {
                        "$type": "date"
                    }
                }
            }
            self.mongo_ranking.user_db_new.update_one(field_m, update_m)
        else:
            field_m = {"user_id": user_id, "metrics.txp_growth.date": key_d}
            update_m = {
                "$set": {
                    "metrics.txp_growth.$.xp": total_c_xp + xp
                },
                "$currentDate": {
                    "last_updated": {
                        "$type": "date"
                    }
                }
            }
            self.mongo_ranking.user_db_new.update_one(field_m, update_m)

    def insert_server_user(self, user_id, message, xp, total_c_xp):
        """
        Insert a new server User's XP

        :return:
        """
        field = {"user_id": user_id}
        update = {
            "$push": {
                "experience_per_server": {
                    "server_id": message.server.id,
                    "xp": xp,
                    "level": 0,
                    "last_an": 0,
                    "message_count": 1
                }
            },
            "$set": {
                "total_XP": total_c_xp + xp
            },
            "$currentDate": {
                "last_updated": {
                    "$type": "date"
                }
            }
        }
        self.mongo_ranking.user_db_new.update_one(field, update)
        self.redis.zadd("server_leaderboard_{}".format(message.server.id), xp, message.author.id)
        self.redis.zadd("global_leaderboard", total_c_xp + xp, message.author.id)

    def update_server_user(self, user_id, message, total_c_xp, xp, xp_s, level, last_an, message_count):
        """
        Update a server users XP

        :return:
        """
        field = {
            "user_id": user_id,
            "experience_per_server.server_id": message.server.id
        }
        update = {
            "$set": {
                "total_XP": total_c_xp + xp,
                "experience_per_server.$.xp": xp_s,
                "experience_per_server.$.level": level,
                "experience_per_server.$.last_an": last_an,
                "experience_per_server.$.message_count": message_count + 1
            },
            "$currentDate": {
                "last_updated": {
                    "$type": "date"
                }
            }
        }
        self.mongo_ranking.user_db_new.update_one(field, update)
        self.redis.zadd("server_leaderboard_{}".format(message.server.id), xp_s, message.author.id)
        self.redis.zadd("global_leaderboard", total_c_xp + xp, message.author.id)

    def xp_abuse_detection(self, msg_len: int, anti_length_key, anti_spam_key):
        """
        Got to keep XP fair and square yeah

        :return:
        """
        # TODO Maybe get a better way to do these checks and possible add more
        # --- Anti length
        # max_length = 18000
        l_count = 0
        if self.redis.exists(anti_length_key):
            ttl = self.redis.ttl(anti_length_key)
            l_count = int(self.redis.get(anti_length_key).decode("utf-8"))
            if ttl <= -1:
                self.redis.delete(anti_length_key)
                self.redis.setex(anti_length_key, 3600, msg_len)
            else:
                self.redis.incrby(anti_length_key, msg_len)
        else:
            self.redis.setex(anti_length_key, 3600, msg_len)

        # --- Anti SPAM
        count = 0
        if self.redis.exists(anti_spam_key):
            ttl = self.redis.ttl(anti_spam_key)
            count = int(self.redis.get(anti_spam_key).decode("utf-8"))
            if ttl <= -1:
                self.redis.delete(anti_spam_key)
                self.redis.setex(anti_spam_key, 60, 1)
            else:
                self.redis.incr(anti_spam_key)
        else:
            self.redis.setex(anti_spam_key, 60, 1)

        return l_count, count

    async def ranking_handler(self, message):
        """
        :param message:
        :return:
        """
        server_id = message.server.id
        is_bot = message.author.bot
        xp_blacklist = self.redis.lrange("xp_black_list", 0, -1)
        if not is_bot and message.author.id.encode() not in xp_blacklist:
            key = server_id + "lvl_track"
            if self.redis.exists(key):
                user_id = message.author.id
                msg_len = len(message.content)

                anti_length_key = message.author.id + "anti_length"
                anti_spam_key = message.author.id + "anti_spam"

                # Lets set flags for potential abusers hue-hue-hue
                l_count, count = self.xp_abuse_detection(msg_len, anti_length_key, anti_spam_key)

                if count < 60 and l_count <= 18000:
                    xp = xp_calculation(msg_len)
                elif 60 < count < 80 and l_count <= 18000:
                    xp = 0
                elif l_count > 18000:
                    xp = 0
                    self.redis.delete(anti_length_key)
                    self.redis.lpush("xp_black_list", user_id)
                    # await reporting.report("`>18000 Chars / hour`", self.ctx, message)

                elif count > 80:
                    xp = 0
                    self.redis.delete(anti_spam_key)
                    self.redis.lpush("xp_black_list", user_id)
                    # await reporting.report("`>80 Msgs / min`", self.ctx, message)
                else:
                    xp = 0
                    self.redis.delete(anti_length_key)
                    self.redis.delete(anti_spam_key)
                    self.redis.lpush("xp_black_list", user_id)
                    # await reporting.report("`>18000 Chars / hour` **and** `>80 Msgs / min`", self.ctx, message)

                cursor_d = self.mongo_ranking.user_db_new.find({"user_id": user_id})
                if cursor_d.count() == 0:
                    # If this user does not exists in our 'database'
                    # we insert a new user
                    self.new_user_entry(message, xp)
                else:
                    # Now we try and find out if this user is present
                    # in the current server
                    cursor_mem = self.mongo_ranking.user_db_new.find({
                        "user_id": user_id,
                        "experience_per_server": {
                            "$elemMatch": {
                                "server_id": message.server.id
                            }
                        }
                    })

                    # Hold the 'Total XP' of the user
                    # Total XP is the combined XP of the user
                    # across all the servers
                    total_c_xp = 0

                    # If previous XP exists then we assign that
                    # else keep it 0
                    for cur_xp in cursor_d:
                        try:
                            total_c_xp = float(cur_xp['total_XP'])
                        except KeyError:
                            total_c_xp = 0

                    # If this user doesn't exist in this server
                    # we update normally :v
                    if cursor_mem.count() == 0:
                        # Lets update the user metrics
                        self.user_metrics(user_id, total_c_xp, xp)

                        # And update the user profiles
                        self.insert_server_user(user_id, message, xp, total_c_xp)

                    else:
                        for i in cursor_mem:
                            for j in i['experience_per_server']:
                                if j["server_id"] == message.server.id:
                                    try:
                                        message_count = int(j['message_count'])
                                    except KeyError:
                                        message_count = 0

                                    xp_s = float(j['xp']) + xp
                                    level = xp_to_level(xp_s)

                                    try:
                                        last_an = j['last_an']
                                    except KeyError:
                                        last_an = 0

                                    # Lets update the user metrics
                                    self.user_metrics(user_id, total_c_xp, xp)

                                    # And then we update the user's XP
                                    self.update_server_user(user_id, message, total_c_xp, xp, xp_s, level,
                                                            last_an, message_count)

    async def level_up_announcer(self, message):
        """
        Handles the level up announcements

        :param message:
        :return:
        """
        # Lets find out if level up announcements
        # are enabled or not. We don't wanna annoy
        # users after all ;)
        key_an = message.server.id + "lvl_track_an"
        if self.redis.exists(key_an):
            server_id = message.server.id
            user_id = message.author.id

            # Find out the if the users records exists for
            # the current server
            cursor_mem = self.mongo_ranking.user_db_new.find({
                "user_id": user_id,
                "experience_per_server": {
                    "$elemMatch": {
                        "server_id": message.server.id
                    }
                }
            })

            if cursor_mem.count() != 0:
                for i in cursor_mem:
                    for j in i['experience_per_server']:

                        # Lets get the current level of the user
                        # for this server and the last level for
                        # which there was a level up announcement
                        if j["server_id"] == message.server.id:
                            try:
                                last_an = int(j['last_an'])
                            except KeyError:
                                last_an = 0

                            try:
                                level = int(j['level'])
                            except KeyError:
                                level = 0

                            try:
                                # If Last announced level is the same as the current
                                # level, it means that we have already made the
                                # announcement. Duh!
                                if level != last_an:
                                    channel = self.ctx.get_channel(server_id)
                                    try:
                                        await self.ctx.send_message(channel,
                                                                    "⭐ **Congrats** {}. You have just reached LvL **{}**.".
                                                                    format(message.author.mention, str(level)))
                                        field = {"user_id": user_id,
                                                 "experience_per_server.server_id": message.server.id}
                                        update = {
                                            "$set": {
                                                "experience_per_server.$.last_an": level
                                            },
                                            "$currentDate": {
                                                "last_updated": {
                                                    "$type": "date"
                                                }
                                            }
                                        }
                                        self.mongo_ranking.user_db_new.update_one(field, update)

                                    # TODO: Maybe integrate this part with the error reporting module
                                    # Maybe we should make error reporting a option within Rero?
                                    except AttributeError:
                                        return
                            except KeyError:
                                return


# A few things that can be done better:
# 1. Add better support for showing error's
# 2. Add better checks to prevent XP abuse

