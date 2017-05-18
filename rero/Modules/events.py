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
import datetime
import discord


class Events:
    """
    Rero Event Handlers
    """
    def __init__(self, context):
        super().__init__()
        self.ctx = context
        self.db_events = mongo_manager.mongo_db.db_events
        self.redis = redis_manager.redis_manager.redis

    async def on_member_update(self, before, after):
        """

        :param before:
        :param after:
        :return:
        """
        before_id = str(before.id)

        before_name = str(before.name)
        before_av_url = str(before.avatar_url)

        after_av_url = str(after.avatar_url)
        after_name = str(after.name)

        # --- Mongo DB Member Update ---
        # -============================-
        # FIXME add a routine to transfer all these names to user_profile
        if before_name != after_name:
            cursor = self.db_events.user_db_new.find({"user_id": before_id})
            if not cursor.count() == 0:
                for l in cursor:
                    last_updated = l['last_updated']
                    now = datetime.datetime.utcnow()
                    delta = now - last_updated
                    if delta.days == 0:
                        if delta.seconds > 5:
                            field1 = {"user_id": before_id}
                            update1 = {"$set": {"user_name": after_name, "avatar_url": after_av_url},
                                       "$push": {"past_names": after_name},
                                       "$currentDate": {"last_updated": {"$type": "date"}}
                                       }
                            self.db_events.user_db_new.update_one(field1, update1)
                            return

                    elif delta.days > 0:
                        field1 = {"user_id": before_id}
                        update1 = {"$set": {"user_name": after_name, "avatar_url": after_av_url},
                                   "$push": {"past_names": after_name},
                                   "$currentDate": {"last_updated": {"$type": "date"}}
                                   }
                        self.db_events.user_db_new.update_one(field1, update1)
                        return

        # We always want the latest avatar
        # of the user after all
        elif before_av_url != after_av_url:
            cursor = self.db_events.user_db_new.find({"user_id": before_id})
            if not cursor.count() == 0:
                for l in cursor:
                    last_updated = l['last_updated']
                    now = datetime.datetime.utcnow()
                    delta = now - last_updated

                    if delta.days == 0:
                        if delta.seconds > 5:
                            field1 = {"user_id": before_id}
                            update1 = {"$set": {"avatar_url": after_av_url},
                                       "$currentDate": {"last_updated": {"$type": "date"}}
                                       }
                            self.db_events.user_db_new.update_one(field1, update1)
                            return

                    elif delta.days > 0:
                        field1 = {"user_id": before_id}
                        update1 = {"$set": {"avatar_url": after_av_url},
                                   "$currentDate": {"last_updated": {"$type": "date"}}
                                   }
                        self.db_events.user_db_new.update_one(field1, update1)
                        return

    async def on_member_join(self, member):
        """
        Called when rero joins a new server.

        :param member:
        """

        server_id = str(member.server.id)
        try:
            cursor = self.db_events.server_backend.find({"serv_id": server_id})
            if cursor.count() == 0:
                if self.redis.exists(server_id):
                    val = self.redis.get(server_id).decode('utf-8')
                    if val == "Announcements: ON":
                        chan = discord.Object(id=server_id)
                        await self.ctx.send_message(chan, ":loudspeaker: {}, welcome to `{}`. Hope you have a good time "
                                                          ":smile:".format(member.mention, member.server.name))
                    else:
                        chan = self.ctx.get_channel(val)
                        if chan is not None:
                            await self.ctx.send_message(chan, ":loudspeaker: {}, welcome to `{}`. Hope you have a good "
                                                              "time :smile:".format(member.mention, member.server.name))
            else:
                cursor_q = self.db_events.user_db_new.find({"user_id": member.id})

                # If we find a cursor, we will
                # update the Members_OF link
                if not cursor_q.count() == 0:
                    # This means that if this user already exists
                    # in the user database, then we simply push a link
                    # to the current server and create records in
                    # 'members_of' and 'experience_per_server'
                    field = {"user_id": member.id}
                    update = {"$push":
                                  {"members_of": {"server_id": server_id},
                                   "experience_per_server": {"server_id": server_id,
                                                             "xp": 0,
                                                             "level": 0,
                                                             "last_an": 0,
                                                             "message_count": 0}},
                              "$currentDate":
                                  {"last_updated": {"$type": "date"}}
                              }
                    self.db_events.user_db_new.update_one(field, update)

                    # Then we will update reference to the server database
                    field = {"serv_id": server_id}
                    update = {"$push": {"serv_members": {"m_id": member.id,
                                                         "m_name": member.name}},
                              "$currentDate":
                                  {"last_updated": {"$type": "date"}}
                              }
                    self.db_events.server_backend.update_one(field, update)

                # If we don't find a cursor, we will
                # just insert a whole document
                else:
                    # if this users does not already exist
                    # in our user database, we insert a new
                    # document for this user into the 'user_db_new'
                    # collection
                    new_record = {"user_id": member.id,
                                  "user_name": member.name,
                                  "past_names": [member.name],
                                  "avatar_url": member.avatar_url,
                                  "bot": member.bot,
                                  "discriminator": str(member.discriminator),
                                  "oauth": {"access_token": "",
                                            "token_type": "",
                                            "refresh_token": "",
                                            "time_issued": "",
                                            "expires_after": ""},
                                  "profile":
                                      {"badges": [],
                                       "heading": "",
                                       "about_me_box": "",
                                       "featured_server_link": "",
                                       "hearts": ""},
                                  "supporter": {
                                      "status": False,
                                      "mode": "",
                                      "amount": "",
                                      "recurring": ""},
                                  "members_of": [{"server_id": server_id}],
                                  "dashboard_access": [],
                                  "total_XP": 0,
                                  "experience_per_server": [{
                                      "server_id": server_id,
                                      "xp": 0,
                                      "level": 0,
                                      "last_an": 0,
                                      "message_count": 0}],
                                  "last_updated": datetime.datetime.utcnow()}
                    self.db_events.user_db_new.insert_one(new_record)

                    # Then we will update reference to the server database
                    field = {"serv_id": server_id}
                    update = {"$push": {"serv_members": {"m_id": member.id,
                                                         "m_name": member.name}},
                              "$currentDate":
                                  {"last_updated": {"$type": "date"}}
                              }
                    self.db_events.server_backend.update_one(field, update)

                # Welcome Messages and auto role
                # Routines
                for docs in cursor:
                    # Welcome message block
                    try:
                        # when turned on, welcome message = Default Message

                        # Also note, key error is not a possibility
                        if self.redis.exists(server_id):
                            val = self.redis.get(server_id).decode('utf-8')
                            if val == "Announcements: ON":
                                welcome_message = docs['welcome_message']
                                plug_name = str(welcome_message).replace("{{user.name}}", member.name)
                                plug_mention_name = plug_name.replace("{{user.mention}}", member.mention)

                                chan = discord.Object(id=server_id)
                                await self.ctx.send_message(chan, plug_mention_name)
                            else:
                                welcome_message = docs['welcome_message']
                                plug_name = str(welcome_message).replace("{{user.name}}", member.name)
                                plug_mention_name = plug_name.replace("{{user.mention}}", member.mention)

                                chan = self.ctx.get_channel(val)
                                if chan is not None:
                                    await self.ctx.send_message(chan, plug_mention_name)
                    except KeyError:
                        if self.redis.exists(server_id):
                            welcome_message = ":loudspeaker: {}, welcome to `{}`. Hope you have a good time :smile: " \
                                .format(member.mention, member.server.name)
                            chan = discord.Object(id=server_id)
                            await self.ctx.send_message(chan, welcome_message)
                    except Exception as e:
                        print("Error reading welcome message")
                        print(e)

                    # Auto role block
                    try:
                        # Also add a handler when auto_role = 'DEFAULT @Everyone'
                        auto_role = docs['auto_up_role']
                        # role = discord.utils.get(member.server.roles, name=auto_role)
                        role = discord.utils.get(member.server.roles, id=auto_role)
                        if role is not None:
                            try:
                                await self.ctx.add_roles(member, role)
                            except discord.Forbidden:
                                chan = discord.Object(id=server_id)
                                await self.ctx.send_message(chan,
                                                            "**Error**: I do not have `Manage Roles` Permission "
                                                            "for auto_role.")
                            except discord.HTTPException:
                                chan = discord.Object(id=server_id)
                                await self.ctx.send_message(chan, "**Error**: Adding the auto role failed. You are "
                                                                  "probably making me add a role that is placed higher "
                                                                  "than my highest role.")
                    except KeyError:
                        pass
                    except Exception as e:
                        print("Error reading auto_up_role")
                        print(e)
        except AttributeError:
            pass

    async def on_member_remove(self, member):
        """
        Called when rero joins a new server.

        :param member:
        """
        server_id = str(member.server.id)

        # --- Mongo DB Member Remove ---
        # -============================-
        # print(" --- Mongo DB Member Remove ---")
        field = {"serv_id": server_id}
        update = {"$pull": {"serv_members": {"m_id": member.id}},
                  "$currentDate":
                      {"last_updated": {"$type": "date"}}
                  }
        self.db_events.server_backend.update_one(field, update)

        # -============================-

        # ---=== We remove XP and Server references for a member when he or she leaves the server ===---
        field = {"user_id": member.id}
        update = {"$pull":
                      {"members_of": {"server_id": server_id},
                       "experience_per_server": {"server_id": server_id}},
                  "$currentDate":
                      {"last_updated": {"$type": "date"}}
                  }
        self.db_events.user_db_new.update_one(field, update)

        server_key = "server_leaderboard_{}".format(server_id)
        if self.redis.exists(server_key):
            self.redis.zrem(server_key, member.id)

        if self.redis.exists(server_id):
            val = self.redis.get(server_id).decode('utf-8')
            if val == "Announcements: ON":
                chan = discord.Object(id=server_id)
                cursor = self.db_events.server_backend.find({"serv_id": server_id})
                if not cursor.count == 0:
                    for docs in cursor:
                        try:
                            leave_message = docs['leave_message']
                        except Exception:
                            leave_message = ":loudspeaker: {}, left `{}`. Bye!".format(member.mention,
                                                                                       member.server.name)
                        plug_name = str(leave_message).replace("{{user.name}}", member.name)
                        plug_mention_name = plug_name.replace("{{user.mention}}", member.mention)
                        await self.ctx.send_message(chan, plug_mention_name)
                        return
                else:
                    await self.ctx.send_message(chan, ":loudspeaker: {}, left `{}`. Bye!"
                                                .format(member.mention, member.server.name))
                    return
            else:
                chan = self.ctx.get_channel(val)
                if chan is not None:
                    cursor = self.db_events.server_backend.find({"serv_id": server_id})
                    if not cursor.count == 0:
                        for docs in cursor:
                            try:
                                leave_message = docs['leave_message']
                            except Exception:
                                leave_message = ":loudspeaker: {}, left `{}`. Bye!".format(member.mention,
                                                                                           member.server.name)
                            plug_name = str(leave_message).replace("{{user.name}}", member.name)
                            plug_mention_name = plug_name.replace("{{user.mention}}", member.mention)
                            await self.ctx.send_message(chan, plug_mention_name)
                            return
                    else:
                        await self.ctx.send_message(chan, ":loudspeaker: {}, left `{}`. Bye!"
                                                          .format(member.mention, member.server.name))
                        return

    async def on_server_join(self, server):
        """
        Called when rero joins a new server.

        :param server:
        """
        # Send a Pusher event
        # pusher_client.trigger('global_notifications', 'server_join', {'server_name': server.name,
        #                                                               'server_avatar': server.icon_url})

        #  Then proceed normally
        # chnl = discord.Object(id=self.log_channel_id)
        msg_chan = discord.Object(id=server.id)
        self.redis.lpush("server_id_list", server.id)

        cursor = self.db_events.server_backend.find({"serv_id": server.id})
        # print("Server Insert for:  " + server.id)
        if cursor.count() == 0:
            # ======================================
            # --- Server Channel Retrieval ---
            # ======================================

            chan = server.channels
            chan_list = []
            for c in chan:
                if c.type == discord.ChannelType.text:
                    entry = {"chan_id": c.id,
                             "chan_name": c.name}
                    chan_list.append(entry)

            # ======================================
            # --- Server Roles Retrieval ---
            # ======================================

            roles = server.roles
            roles_list = []
            for r in roles:
                entry = {"role_id": r.id,
                         "role_name": r.name}
                roles_list.append(entry)

            # ======================================
            # --- Server Members Retrieval ---
            # ======================================

            membs = server.members
            mem_list = []
            for m in membs:
                # entry = {"m_id": m.id,
                #          "m_name": m.name,
                #          "m_avatar_url": m.avatar_url,
                #          "m_display_name": m.display_name,
                #          "m_bot": m.bot}
                entry = {"m_id": m.id,
                         "m_name": m.name}
                mem_list.append(entry)

            new_record = {"serv_id": server.id,
                          "serv_avatar": server.icon,
                          "serv_name": server.name,
                          "owner_name": server.owner.name,
                          "owner_id": server.owner.id,
                          "serv_channels": chan_list,
                          "serv_roles": roles_list,
                          "serv_members": mem_list,
                          "dashboard_users": [],
                          "welcome_message": "",
                          "auto_up_role": "",
                          "ignored_channels": [],
                          "self_assigned_roles": [],
                          "access": {"status": True,
                                     "about": True,
                                     "sar": True,
                                     "steam": True,
                                     "info": True,
                                     "fuck": True,
                                     "rip": True,
                                     "ud": True,
                                     "osu": True,
                                     "wikipedia": True,
                                     "anime": True,
                                     "manga": True,
                                     "quotes": True,
                                     "memes": True,
                                     "weather": True,
                                     "sr": True,
                                     "xkcd": True,
                                     "roll": True,
                                     "toss": True,
                                     "choose": True,
                                     "guess": True,
                                     "rps": True,
                                     "quiz": True,
                                     "8ball": True,
                                     "whoami/whois": True,
                                     "serverinfo": True,
                                     "twitch_manual": True,
                                     "translate": True,
                                     "giphy": True,
                                     "names": True,
                                     "clean": True},
                          "nsfw": {"nsfw_status": "off",
                                   "nsfw_chan_id": "--N/A--",
                                   "nsfw_chan_name": "--N/A--"},
                          "last_updated": datetime.datetime.utcnow()}
            self.db_events.server_backend.insert_one(new_record)

        try:
            await self.ctx.send_message(msg_chan, "Thank you for inviting me. Type `?help` to get started.")
            # await self.send_message(chnl, 'At {} GMT, I *joined* the **server**: `{}` with **server_id**: `{}`'
            #                         .format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), server, server.id))
            return
        except discord.Forbidden:
            # await self.send_message(chnl, 'At {} GMT, I *could not show Intro message to* the **server**: `{}` '
            #                               'with **server_id**: `{}`'
            #                         .format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), server, server.id))
            return

    async def on_server_remove(self, server):
        """
        Called when rero leaves a new server.

        1: nsfw         -- To track NSFW status of channels and/or store the specific channel for NSFW {{SERVERS}}
        2: pm           -- To send PM when highlighted for {{USERS}}
        3: spam         -- For spam status of {{SERVERS}}
        4: NIL          -- For announce status of {{SERVERS}}
        5: lvl_track    -- Member Level Track
        6: lvl_track_an -- Member level update announcement

        :param server:
        :return:
        """
        cursor = self.db_events.server_backend.find({"serv_id": server.id})
        # # print("Server Delete for:  " + server.id)
        if not cursor.count() == 0:
            self.db_events.server_backend.remove({"serv_id": server.id})

        # REDIS cleanup routine
        key_an = server.id
        key_nsfw = server.id + "nsfw"
        key_lvl = server.id + "lvl_track"
        key_lvl_an = server.id + "lvl_track_an"
        server_leaderboard = "server_leaderboard_{}".format(server.id)

        if self.redis.exists(key_an):
            self.redis.delete(key_an)
        if self.redis.exists(key_nsfw):
            self.redis.delete(key_nsfw)
        if self.redis.exists(key_lvl):
            self.redis.delete(key_lvl)
        if self.redis.exists(key_lvl_an):
            self.redis.delete(key_lvl_an)
        if self.redis.exists(server_leaderboard):
            self.redis.delete(server_leaderboard)
        self.redis.lrem("server_id_list", 0, server.id)

        # chnl = discord.Object(id=self.log_channel_id)
        #
        # await self.send_message(chnl, 'At {} GMT, I *left* the **server**: `{}` with **server_id**: `{}`'
        #                         .format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), server, server.id))
        return

    async def on_channel_delete(self, channel):
        """
        Called when a channel is deleted

        :param self:
        :param channel:
        :return:
        """
        if not channel.is_private:
            serv_id = channel.server.id
            chan_id = channel.id

            field = {"serv_id": serv_id}
            update = {"$pull": {"serv_channels": {"chan_id": chan_id}},
                      "$currentDate":
                          {"last_updated": {"$type": "date"}}
                      }
            self.db_events.server_backend.update_one(field, update)
            return

    async def on_channel_create(self, channel):
        """
        Called when a channel is created

        :param channel:
        :return:
        """
        if not channel.is_private:
            serv_id = channel.server.id
            chan_id = channel.id
            chan_name = channel.name

            field = {"serv_id": serv_id}
            update = {"$push": {"serv_channels": {"chan_id": chan_id, "chan_name": chan_name}},
                      "$currentDate":
                          {"last_updated": {"$type": "date"}}
                      }
            self.db_events.server_backend.update_one(field, update)
            return

    async def on_channel_update(self, before, after):
        """
        Called when a channel is updated

        :param after:
        :param before:
        :return:
        """
        if not before.is_private:
            serv_id = before.server.id
            chan_id = before.id
            chan_before_name = before.name
            chan_after_name = after.name

            if chan_before_name != chan_after_name:
                field = {"serv_id": serv_id, "serv_channels.chan_id": chan_id}
                update = {"$set": {"serv_channels.$.chan_name": chan_after_name},
                          "$currentDate":
                              {"last_updated": {"$type": "date"}}
                          }
                self.db_events.server_backend.update_one(field, update)
                return

    async def on_server_role_create(self, role):
        """
        This is called when a new role is created in the server

        :param role:
        :return:
        """
        server = role.server
        serv_id = server.id
        role_id = role.id
        role_name = role.name

        field = {"serv_id": serv_id}
        update = {"$push": {"serv_roles": {"role_id": role_id, "role_name": role_name}},
                  "$currentDate":
                      {"last_updated": {"$type": "date"}}
                  }
        self.db_events.server_backend.update_one(field, update)
        return

    async def on_server_role_delete(self, role):
        """
        Called when a role is deleted

        :param role:
        :return:
        """
        server = role.server
        serv_id = server.id
        role_id = role.id

        field = {"serv_id": serv_id}
        update = {"$pull": {"serv_roles": {"role_id": role_id}},
                  "$currentDate":
                      {"last_updated": {"$type": "date"}}
                  }
        self.db_events.server_backend.update_one(field, update)
        return

    async def on_server_role_update(self, before, after):
        """
        Called when a role is updated

        :param before:
        :param after:
        :return:
        """
        serv_id = before.server.id
        role_id = before.id
        role_before_name = before.name
        role_after_name = after.name

        if role_before_name != role_after_name:
            field = {"serv_id": serv_id, "serv_roles.role_id": role_id}
            update = {"$set": {"serv_roles.$.role_name": role_after_name},
                      "$currentDate":
                          {"last_updated": {"$type": "date"}}
                      }
            self.db_events.server_backend.update_one(field, update)
            return

    async def on_server_update(self, before, after):
        """
        Called when the server updates status
        :param before:
        :param after:
        :return:
        """

        serv_id = before.id
        owner_before_id = before.owner.id
        owner_after_id = after.owner.id
        before_icon = before.icon
        after_icon = after.icon
        if owner_before_id != owner_after_id or before_icon != after_icon:
            owner_name = after.owner.name
            field = {"serv_id": serv_id}
            update = {"$set": {"owner_name": owner_name,
                               "serv_avatar": after_icon},
                      "$currentDate":
                          {"last_updated": {"$type": "date"}}
                      }
            self.db_events.server_backend.update_one(field, update)
            return

