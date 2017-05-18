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
from Rero.Modules import error_messages
import discord
import asyncio
import datetime
import time
import aiohttp
import json
import feedparser
from io import BytesIO

db = mongo_manager.mongo_db.db
red = redis_manager.redis_manager.redis

with open("config/settings.yaml") as file:
    settings_file = file.read()
file.close()
settings = yaml.load(settings_file)

async def mute(ctx, user, message):
    """
    Command for muting users.

    :param ctx:
    :param user:
    :param message:
    :return:
    """
    if user is None:
        await ctx.send_message(message.channel, "**Error**: User not mentioned."
                                                "\nUsage: `;;mute @user`")
        return
    overwrite = discord.PermissionOverwrite()
    overwrite.send_messages = False
    try:
        # TODO maybe change this to use Roles instead?
        for channel in message.server.channels:
            await ctx.edit_channel_permissions(channel, user, overwrite)
        await ctx.send_message(message.channel, "**Success**: `Muted {}`".format(user.name))
        await ctx.send_message(user, "You are now muted in the server **{}**\n"
                                     "For more details, talk to the Server Admins / Moderators\n\n"
                                     "*I am a bot. Please don't reply to this message.*".format(message.server.name))
        return
    except Exception as e:
        if error_messages.error_message(e, "mute"):
            await ctx.send_message(message.channel, "**Error**: `{}`".format(error_messages.error_message(e, "mute")))
            return
        else:
            print(e)


async def unmute(ctx, user, message):
    """
    Command for muting users.

    :param ctx:
    :param user:
    :param message:
    :return:
    """
    if user is None:
        await ctx.send_message(message.channel, "**Error**: User not mentioned."
                                                "\nUsage: `;;unmute @user`")
        return
    try:
        # TODO maybe change this to use Roles instead?
        for channel in message.server.channels:
            await ctx.delete_channel_permissions(channel, user)
        await ctx.send_message(message.channel, "**Success**: `Un-Muted {}`".format(user.name))
        await ctx.send_message(user, "You are now un-muted in the server **{}**".format(message.server.name))
        return
    except Exception as e:
        if error_messages.error_message(e, "unmute"):
            await ctx.send_message(message.channel, "**Error**: `{}`".format(error_messages.error_message(e, "unmute")))
            return
        else:
            print(e)

async def prune(ctx, user, amount: int, message):
    """
    Command for muting users.

    :param amount:
    :param ctx:
    :param user:
    :param message:
    :return:
    """
    try:
        if not 2 <= amount <= 100:
            await ctx.send_message(message.channel, "**Error**: `Amount of messages must be specified and it "
                                                    "must be between 2 and 100`")
            return

        counter = 0
        # If user is mentioned then we delete the users
        # messages. Else we delete messages from the channel
        if user is not None:
            message_bucket = []
            async for entry in ctx.logs_from(message.channel):
                if entry.author.id == user.id:
                    message_bucket.append(entry)

            # sort the messages by time so that we can delete starting from
            # the latest first. Also gives a very clean effect :v
            sorted_messages = sorted(message_bucket, key=lambda message_bucket: message_bucket.timestamp, reverse=True)

            # If the amount is more than the total amount of
            # messages that exists (which is always the case btw),
            # then we delete whatever we can. Else we delete the
            # exact amount
            if amount > len(message_bucket):
                for msg in sorted_messages:
                    if counter < len(message_bucket):
                        await ctx.delete_message(msg)
                        await asyncio.sleep(0.2)
                        counter += 1
            else:
                for msg in sorted_messages:
                    if counter < amount:
                        await ctx.delete_message(msg)
                        await asyncio.sleep(0.2)
                        counter += 1

            await ctx.send_message(message.channel, ":wind_blowing_face: `Pruned '{}'s last '{}' messages.`"
                                                    .format(str(user.name), str(counter)))
            return

        else:
            message_bucket = []
            async for entry in ctx.logs_from(message.channel, limit=amount):
                message_bucket.append(entry)
                counter += 1
            await ctx.delete_messages(message_bucket)
            await ctx.send_message(message.channel, ":wind_blowing_face: `Pruned the last '{}' messages.`"
                                                    .format(str(counter)))
            return

    except Exception as e:
        if error_messages.error_message(e, "prune"):
            await ctx.send_message(message.channel, "**Error**: `{}`".format(error_messages.error_message(e, "prune")))
            return
        else:
            print(e)

async def purge(ctx, amount: int, message):
    """

    :param ctx:
    :param amount:
    :param message:
    :return:
    """
    try:
        if not 1 <= amount <= 100:
            await ctx.send_message(message.channel, "**Error**: `Amount of messages must be specified and it "
                                                    "must be between 1 and 100.`")
            return

        await ctx.purge_from(message.channel, limit=amount)
    except Exception as e:
        if error_messages.error_message(e, "purge"):
            await ctx.send_message(message.channel, "**Error**: `{}`".format(error_messages.error_message(e, "purge")))
            return
        else:
            print(e)

async def ignore(ctx, message):
    """
    For ignoring channels. This basically blocks people from using
    user commands in channels

    :param ctx:
    :param message:
    :return:
    """
    chan = message.channel_mentions
    if len(chan) == 0:
        await ctx.send_message(message.channel, "**Error**: Channel not mentioned."
                                                "\nUsage: `;;ignore #channel_name`"
                                                "\nExample: `?ignore #general`")
        return

    for chan_n in chan:
        try:
            cursor = db.server_backend.find({"serv_id": message.server.id})
            if cursor.count() == 0:
                new_record = {
                    "serv_id": message.server.id,
                    "ignored_channels": [chan_n.id],
                    "last_updated": datetime.datetime.utcnow()
                }
                db.server_backend.insert_one(new_record)

                await ctx.send_message(message.channel, "**Added**: `#{}` to ignore list.".format(chan_n.name))
                return

            else:
                field = {"serv_id": message.server.id}
                update = {
                    "$push": {
                        "ignored_channels": chan_n.id
                    },
                    "$currentDate": {
                        "last_updated": {"$type": "date"}
                    }
                }
                db.server_backend.update_one(field, update)
                await ctx.send_message(message.channel, "**Added**: `#{}` to ignore list.".format(chan_n.name))
                return
        except AttributeError:
            pass

async def unignore(ctx, message):
    """
    For un-ignoring channels.

    :param ctx:
    :param message:
    :return:
    """
    chan = message.channel_mentions
    if len(chan) == 0:
        await ctx.send_message(message.channel, "**Error**: Channel not mentioned."
                                                "\nUsage: `;;unignore #channel_name`"
                                                "\nExample: `?unignore #general`")
        return

    for chan_n in chan:
        try:
            cursor = db.server_backend.find({"serv_id": message.server.id})
            if cursor.count() == 0:
                await ctx.send_message(message.channel, "You need to **ignore** a channel first "
                                                        "before using this.")
                return

            else:
                field = {"serv_id": message.server.id}
                update = {
                    "$pull": {
                        "ignored_channels": chan_n.id
                    },
                    "$currentDate": {
                        "last_updated": {
                            "$type": "date"
                        }
                    }
                }
                db.server_backend.update_one(field, update)
                await ctx.send_message(message.channel, "**Removed**: `#{}` from ignore list.".format(chan_n.name))
                return
        except AttributeError:
            pass

async def auto_role(ctx, message):
    """
    Set Auto_Upgrade Role whenever a user enters a server

    :param ctx:
    :param message:
    :return:
    """
    role_s = message.content[11:]
    role = discord.utils.get(message.server.roles, name=role_s)
    if role is None:
        await ctx.send_message(message.channel, "**Error**: That role does not exist."
                                                "\nUsage: `;;auto_role RoleName`"
                                                "\nExample: `?auto_role NewMember`")
        return
    try:
        cursor = db.server_backend.find({"serv_id": message.server.id})
        if cursor.count() == 0:
            new_record = {
                "serv_id": message.server.id,
                "auto_up_role": role.id,
                "last_updated": datetime.datetime.utcnow()
            }
            db.server_backend.insert_one(new_record)
            await ctx.send_message(message.channel, "**Success**: All new members who join *{}* "
                                                    "server will be upgraded to *Role*: `{}`"
                                                    .format(message.server.name, role.name))
            return

        else:
            field = {"serv_id": message.server.id}
            update = {
                "$set": {
                    "auto_up_role": role.id
                },
                "$currentDate": {
                    "last_updated": {
                        "$type": "date"
                    }
                }
            }

            db.server_backend.update_one(field, update)

            await ctx.send_message(message.channel, "**Success**: `All new members who join '{}'"
                                                    " will be upgraded to Role: '{}'`"
                                                    .format(message.server.name, role.name))
            return
    except AttributeError:
        pass

async def auto_reset(ctx, message):
    """
    Resets Auto Role

    :param ctx:
    :param message:
    :return:
    """
    try:
        cursor = db.server_backend.find({"serv_id": message.server.id})

        if cursor.count() == 0:
            await ctx.send_message(message.channel, "**Error**: No auto upgrade roles are set.")
            return

        else:
            field = {"serv_id": message.server.id}
            update = {
                "$set": {
                    "auto_up_role": ""
                },
                "$currentDate": {
                    "last_updated": {
                        "$type": "date"
                    }
                }
            }
            db.server_backend.update_one(field, update)
            await ctx.send_message(message.channel, "**Success**: `New members will 'not' be auto "
                                                    "upgraded.`")

            return
    except AttributeError:
        pass

async def set_welcome(ctx, message):
    """
    Set the welcome message

    :param ctx:
    :param message:
    :return:
    """
    msg_str = message.content[13:]
    if msg_str == "":
        await ctx.send_message(message.channel, "**Error**: Message not specified."
                                                "\nUsage: `;;set_welcome your message goes here`"
                                                "\nExample: `?set_welcome welcome to our server.`"
                                                "\n*This command can be further personalized using these plugs*: "
                                                "`{{user.name}}`, `{{user.mention}}`")
        return
    try:
        cursor = db.server_backend.find({"serv_id": str(message.server.id)})
        if cursor.count() == 0:
            new_record = {
                "serv_id": message.server.id,
                "welcome_message": msg_str,
                "last_updated": datetime.datetime.utcnow()
            }
            db.server_backend.insert_one(new_record)

            plug_name = msg_str.replace("{{user.name}}", "Example User")
            plug_name_mention = plug_name.replace("{{user.mention}}", "@Example User")
            await ctx.send_message(message.channel, "**Success**: The following message will be shown to new members."
                                                    "\n{}".format(plug_name_mention))
            return

        else:
            field = {"serv_id": str(message.server.id)}
            update = {
                "$set": {
                    "welcome_message": msg_str
                },
                "$currentDate": {
                    "last_updated": {
                        "$type": "date"
                    }
                }
            }
            db.server_backend.update_one(field, update)
            plug_name = msg_str.replace("{{user.name}}", "Example User")
            plug_name_mention = plug_name.replace("{{user.mention}}", "@Example User")
            await ctx.send_message(message.channel, "**Success**: The following message will be shown to new members."
                                                    "\n{}".format(plug_name_mention))
            return
    except AttributeError:
        pass

async def set_leave(ctx, message):
    """
    Set the leave message

    :param ctx:
    :param message:
    :return:
    """
    msg_str = message.content[11:]
    if msg_str == "":
        await ctx.send_message(message.channel, "**Error**: Message not specified."
                                                "\nUsage: `;;set_leave your message goes here`"
                                                "\nExample: `?set_leave good bye...`"
                                                "\n*This command can be further personalized using these plugs*: "
                                                "`{{user.name}}`, `{{user.mention}}`")
        return
    try:

        cursor = db.server_backend.find({"serv_id": message.server.id})
        if cursor.count() == 0:
            new_record = {"serv_id": message.server.id,
                          "leave_message": msg_str,
                          "last_updated": datetime.datetime.utcnow()}
            db.server_backend.insert_one(new_record)

            plug_name = msg_str.replace("{{user.name}}", "Example User")
            plug_name_mention = plug_name.replace("{{user.mention}}", "@Example User")
            await ctx.send_message(message.channel, "**Success**: The following message will be shown when a member "
                                                    "leaves.\n{}".format(plug_name_mention))
            return

        else:
            field = {"serv_id": message.server.id}
            update = {
                "$set": {
                    "leave_message": msg_str
                },
                "$currentDate": {
                    "last_updated": {
                        "$type": "date"
                    }
                }
            }
            db.server_backend.update_one(field, update)

            plug_name = msg_str.replace("{{user.name}}", "Example User")
            plug_name_mention = plug_name.replace("{{user.mention}}", "@Example User")
            await ctx.send_message(message.channel,  "**Success**: The following message will be shown when a member "
                                                     "leaves.\n{}".format(plug_name_mention))
            return
    except AttributeError:
        pass


async def cc(ctx, message):
    """
    Turn custom commands on/off

    :param ctx:
    :param message:
    :return:
    """
    cont = message.content[4:]
    if str(cont).lower() == "on":
        cursor = db.custom_commands_new.find({"serv_id": message.server.id})
        if cursor.count() == 0:
            new_record = {"serv_id": message.server.id,
                          "status": "ON",
                          "access_control_role_id": "",
                          "commands_list": [],
                          "last_updated": datetime.datetime.utcnow()}
            db.custom_commands_new.insert_one(new_record)
        else:
            field = {"serv_id": message.server.id}
            update = {
                "$set": {
                    "status": "ON",
                    "access_control_role_id": ""
                },
                "$currentDate": {
                    "last_updated": {
                        "$type": "date"
                    }
                }
            }
            db.custom_commands_new.update_one(field, update)
        await ctx.send_message(message.channel, "**Success**: `'Custom Commands' are now enabled.`")
        return

    elif str(cont).lower() == "off":
        cursor = db.custom_commands_new.find({"serv_id": message.server.id})
        if cursor.count() == 0:
            new_record = {"serv_id": message.server.id,
                          "status": "OFF",
                          "commands_list": [],
                          "last_updated": datetime.datetime.utcnow()}
            db.custom_commands_new.insert_one(new_record)
        else:
            field = {"serv_id": message.server.id}
            update = {
                "$set": {
                    "status": "OFF"
                },
                "$currentDate": {
                    "last_updated": {
                        "$type": "date"
                    }
                }
            }
            db.custom_commands_new.update_one(field, update)
        await ctx.send_message(message.channel, "**Success**: `'Custom Commands' are now disabled.`")
        return

    else:
        await ctx.send_message(message.channel, "**Error**: Incorrect usage of command.\n"
                                                "**Command**: `?cc on` or `?cc off`")
        return

async def restrict_cc(ctx, message):
    """
    Restrict the use of add_cc to one specific role
    :param ctx:
    :param message:
    :return:
    """
    role_name = message.content[8:]
    role = discord.utils.get(message.server.roles, name=role_name)
    if role:
        cursor = db.custom_commands_new.find({"serv_id": message.server.id})
        if cursor.count() == 0:
            new_record = {"serv_id": message.server.id,
                          "status": "RESTRICTED",
                          "access_control_role_id": role.id,
                          "commands_list": [],
                          "last_updated": datetime.datetime.utcnow()}
            db.custom_commands_new.insert_one(new_record)
        else:
            field = {"serv_id": message.server.id}
            update = {
                "$set": {
                    "status": "RESTRICTED",
                    "access_control_role_id": role.id
                },
                "$currentDate": {
                    "last_updated": {
                        "$type": "date"
                    }
                }
            }
            db.custom_commands_new.update_one(field, update)
        await ctx.send_message(message.channel, "**Success**: `'Custom Commands' creation are now "
                                                "restricted to people with '{}' role.`".format(role.name))
        return
    else:
        await ctx.send_message(message.channel, "**Error**: `Role does not exist.`")
        return

async def nsfw(ctx, message):
    """
    Turn NSFW on/off for a server

    :param ctx:
    :param message:
    :return:
    """
    cont = message.content[6:]
    if str(cont).lower() == "on":
        cursor = db.server_backend.find({"serv_id": message.server.id})
        if cursor.count() == 0:
            new_record = {"serv_id": message.server.id,
                          "serv_name": message.server.name,
                          "owner_name": message.server.owner.name,
                          "owner_id": message.server.owner.id,
                          "nsfw": {"nsfw_status": "on|global",
                                   "nsfw_chan_id": "--N/A--",
                                   "nsfw_chan_name": "--N/A--"},
                          "last_updated": datetime.datetime.utcnow()}
            db.server_backend.insert_one(new_record)

        else:
            field = {"serv_id": message.server.id}
            update = {
                "$set": {
                    "serv_id": message.server.id,
                    "serv_name": message.server.name,
                    "owner_name": message.server.owner.name,
                    "owner_id": message.server.owner.id,
                    "nsfw.nsfw_status": "on|global",
                    "nsfw.nsfw_chan_id": "--N/A--",
                    "nsfw.nsfw_chan_name": "--N/A--"
                },
                "$currentDate":
                    {"last_updated": {"$type": "date"}}
                }
            db.server_backend.update_one(field, update)

        await ctx.send_message(message.channel, ":loudspeaker: NSFW searches are now **ENABLED**")
        return
    elif str(cont).lower() == "off":
        serv_id = message.server.id
        key = serv_id + "nsfw"
        red.delete(key)

        cursor = db.server_backend.find({"serv_id": message.server.id})
        if cursor.count() == 0:
            new_record = {"serv_id": message.server.id,
                          "serv_name": message.server.name,
                          "owner_name": message.server.owner.name,
                          "owner_id": message.server.owner.id,
                          "nsfw": {"nsfw_status": "off",
                                   "nsfw_chan_id": "--N/A--",
                                   "nsfw_chan_name": "--N/A--"},
                          "last_updated": datetime.datetime.utcnow()}
            db.server_backend.insert_one(new_record)

        else:
            field = {"serv_id": message.server.id}
            update = {
                "$set": {
                    "serv_id": message.server.id,
                    "serv_name": message.server.name,
                    "owner_name": message.server.owner.name,
                    "owner_id": message.server.owner.id,
                    "nsfw.nsfw_status": "off",
                    "nsfw.nsfw_chan_id": "--N/A--",
                    "nsfw.nsfw_chan_name": "--N/A--"
                },
                "$currentDate": {
                    "last_updated": {
                        "$type": "date"
                    }
                }
            }
            db.server_backend.update_one(field, update)

        await ctx.send_message(message.channel, ":loudspeaker: NSFW searches are now **DISABLED**")
        return

    else:
        await ctx.send_message(message.channel, "**Error**: `Available options are '?nsfw on' and '?nsfw off' only.`")
        return

async def set_nsfw(ctx, message):
    """
    Set a specific channel for NSFW Access

    :param ctx:
    :param message:
    :return:
    """
    mentioned_channels = message.channel_mentions
    if not mentioned_channels:
        return
    cursor = db.server_backend.find({"serv_id": message.server.id})
    if cursor.count() == 0:
        new_record = {"serv_id": message.server.id,
                      "serv_name": message.server.name,
                      "owner_name": message.server.owner.name,
                      "owner_id": message.server.owner.id,
                      "nsfw": {"nsfw_status": "on|channel",
                               "nsfw_chan_id": mentioned_channels[0].id,
                               "nsfw_chan_name": mentioned_channels[0].name},
                      "last_updated": datetime.datetime.utcnow()}
        db.server_backend.insert_one(new_record)

    else:
        field = {"serv_id": message.server.id}
        update = {
            "$set": {
                "serv_id": message.server.id,
                "serv_name": message.server.name,
                "owner_name": message.server.owner.name,
                "owner_id": message.server.owner.id,
                "nsfw.nsfw_status": "on|channel",
                "nsfw.nsfw_chan_id": mentioned_channels[0].id,
                "nsfw.nsfw_chan_name": mentioned_channels[0].name
            },
            "$currentDate": {
                "last_updated": {
                    "$type": "date"
                }
            }
        }
        db.server_backend.update_one(field, update)

    await ctx.send_message(message.channel, ":loudspeaker: NSFW searches are now **ENABLED** in {}"
                                            .format(mentioned_channels[0].mention))
    return

async def add_sar(ctx, message):
    """
    Add a new Self Assigned Role
    :param ctx:
    :param message:
    :return:
    """
    cont = message.content[9:]
    switch = cont.split(";", maxsplit=1)
    if not len(switch) == 2:
        await ctx.send_message(message.channel, "**Error**: Role and Alias not mentioned."
                                                "\nUsage: `;;add_sar role;alias`"
                                                "\nExample: `?add_sar Pervert;perv`")
        return

    try:
        role = switch[0]
        alias = switch[1]
        get_role = discord.utils.get(message.server.roles, name=role)
        if not get_role:
            await ctx.send_message(message.channel, "**Error**: Role and Alias not mentioned."
                                                    "\nUsage: `;;add_sar role;alias`"
                                                    "\nExample: `?add_sar Pervert;perv`")
            return

        cursor = db.server_backend.find({"serv_id": message.server.id})

        if cursor.count() == 0:
            new_record = {"serv_id": message.server.id,
                          "self_assigned_roles": [{
                              "role_id": get_role.id,
                              "role_alias": alias
                          }],
                          "last_updated": datetime.datetime.utcnow()}
            db.server_backend.insert_one(new_record)

            await ctx.send_message(message.channel, "**Added**: `Role: {} | Alias: {}` to SAR list."
                                                    .format(get_role.name, alias))
            return

        else:
            for k in cursor:
                try:
                    avail_sar = k['self_assigned_roles']
                    for a in avail_sar:
                        if get_role.id == a['role_id']:
                            await ctx.send_message(message.channel, "**Error** `This role is already in the SAR list.`")
                            return
                except KeyError:
                    pass
            field = {"serv_id": str(message.server.id)}
            update = {
                "$push": {
                    "self_assigned_roles": {
                        "role_id": get_role.id,
                        "role_alias": alias
                    }
                },
                "$currentDate": {
                    "last_updated": {
                        "$type": "date"
                    }
                }
              }
            db.server_backend.update_one(field, update)

            await ctx.send_message(message.channel, "**Added**: `Role: {} | Alias: {}` to SAR list."
                                                    .format(get_role.name, alias))
            return
    except AttributeError:
        pass

async def announce(ctx, message):
    """
    Set the server announcement status for showing
    Join/Leave messages

    :param ctx:
    :param message:
    :return:
    """
    if message.content[10:].lower() == "on":
        # We use REDIS to hold the flag value since
        # this will be referred to quite a lot
        red.set(message.server.id, "Announcements: ON")

        # And we store the message body in MongoDB so that
        # it can be called as and when required
        field = {"serv_id": message.server.id}
        update = {"$set": {"welcome_message": ":loudspeaker: {{user.mention}}, welcome to our server. "
                                              "Hope you have a good time :smile:"},
                  "$currentDate":
                      {"last_updated": {"$type": "date"}}
                  }
        db.server_backend.update_one(field, update)

        await ctx.send_message(message.channel, ":loudspeaker: **Announcements** are now **ON** for `{}`."
                                                .format(str(message.server.name)))
        return
    elif message.content[10:].lower() == "off":
        red.delete(message.server.id)

        field = {"serv_id": message.server.id}
        update = {"$set": {"welcome_message": ""},
                  "$currentDate":
                      {"last_updated": {"$type": "date"}}
                  }
        db.server_backend.update_one(field, update)

        await ctx.send_message(message.channel, "**Announcements** are now **OFF** for `{}`."
                                                .format(message.server.name))
        return
    else:
        await ctx.send_message(message.channel, "**Error**: Usage `?announce on` or `?announce off`")
        return

async def set_announce(ctx, message):
    """
    Set the channel where all the announcement messages should go

    :param ctx:
    :param message:
    :return:
    """
    for channel in message.channel_mentions:
        red.set(message.server.id, channel.id)
        await ctx.send_message(message.channel, ":loudspeaker: **Announcements** are now **ON** for `{}` in {}."
                                                .format(message.server.name, channel.mention))
        return

async def color(ctx, message):
    """
    Change role color

    :param ctx:
    :param message:
    :return:
    """
    try:
        b = message.content[7:]
        val = str(b).split(";", maxsplit=1)
        if len(val) == 1:
            await ctx.send_message(message.channel, "**Error**`No color code provided.`"
                                                    "\n**Usage**: `?color RoleName;hexcode`"
                                                    "\n**Example**: `?color Member;ffdd00`, "
                                                    "`?color Bot Army;1a1a1a`")
            return

        role = val[0]
        try:
            colr_int = int(val[1], 16)
            discord_color = discord.Color(colr_int)
        except ValueError:
            await ctx.send_message(message.channel, "**Hex Error** `Make sure the hex is valid.`")
            return

        c = discord.utils.get(message.server.roles, name=role)
        if c is None:
            await ctx.send_message(message.channel, "**Error** `Role not found in this server.`")
            return
        await ctx.edit_role(message.author.server, role=c, colour=discord_color)
        await ctx.send_message(message.channel, "**Success** `Role color has been changed.`")
        return
    except AttributeError:
        await ctx.send_message(message.channel, "**Error** `Changing the color failed. Please retry.`")
        return
    except discord.Forbidden:
        await ctx.send_message(message.channel,  "**Error** `I do not have Manage Roles Permission.`")
        return
    except discord.HTTPException:
        await ctx.send_message(message.channel, "**Error** `Editing the role failed.`")
        return

async def role_add(ctx, message):
    """
    Add role to a member

    :param ctx:
    :param message:
    :return:
    """
    try:
        b = message.content[10:]
        val = str(b).split(" ", maxsplit=1)
        role_str = val[1]
        if not message.mentions:
            return
        role = discord.utils.get(message.server.roles, name=role_str)

        await ctx.add_roles(message.mentions[0], role)
        await ctx.send_message(message.channel, "**Added the role**: `{}` to `{}` :thumbsup:"
                                                .format(str(role.name), str(message.mentions[0].name)))
        return
    except AttributeError:
        await ctx.send_message(message.channel, ":scream: **Error** `This role is not found in your server.`")
        return
    except discord.Forbidden:
        await ctx.send_message(message.channel, "**Error** `I do not have 'Manage Roles' Permission.`")
        return
    except discord.HTTPException:
        await ctx.send_message(message.channel, "**Error** `Adding the role failed.`")
        return

async def role_remove(ctx, message):
    """
    Remove a role from a Member

    :param ctx:
    :param message:
    :return:
    """
    try:
        b = message.content[13:]
        val = str(b).split(" ", maxsplit=1)

        membs = message.mentions
        if not membs:
            return
        m = membs[0]
        role_str = val[1]

        # memb = discord.utils.get(message.server.members, id=name_clean)
        role = discord.utils.get(message.server.roles, name=role_str)

        await ctx.remove_roles(m, role)
        await ctx.send_message(message.channel, "**Removed the role**: `{}` from `{}` :thumbsup:"
                                                .format(str(role.name), str(m.name)))
        return
    except AttributeError:
        await ctx.send_message(message.channel, ":scream: **Error** `This role is not found in your server.`")
        return
    except discord.Forbidden:
        await ctx.send_message(message.channel, "**Error** `I do not have 'Manage Roles' Permission.`")
        return
    except discord.HTTPException:
        await ctx.send_message(message.channel, "**Error** `Adding the role failed.`")
        return

async def kick(ctx, message):
    """
    Kick a member

    :param ctx:
    :param message:
    :return:
    """
    if not message.mentions:
        await ctx.send_message(message.channel, "**Error** `Need to mention a user.`")
        return
    try:
        await ctx.kick(message.mentions[0])
        await ctx.send_message(message.channel, "**Kicked**: `{}` from `{}` :thumbsup:"
                                                .format(message.mentions[0].name, message.server.name))
        return
    except discord.Forbidden:
        await ctx.send_message(message.channel, "**Error** `I do not have 'Kick Users' Permission.`")
        return
    except discord.HTTPException:
        await ctx.send_message(message.channel, "**Error* `Kicking failed.`")
        return

async def ban(ctx, message):
    """
    Ban a member
    :param ctx:
    :param message:
    :return:
    """
    if not message.mentions:
        await ctx.send_message(message.channel, "**Error** `Need to mention a user.`")
        return
    try:
        await ctx.ban(message.mentions[0])
        await ctx.send_message(message.channel, "**Banned**: `{}` from `{}` :thumbsup:"
                                                .format(message.mentions[0].name, message.server.name))
        return
    except discord.Forbidden:
        await ctx.send_message(message.channel, "**Error** `I do not have 'Ban Users' Permission.`")
        return
    except discord.HTTPException:
        await ctx.send_message(message.channel, "**Error** `Banning failed.`")
        return

async def unban(ctx, message):
    """
    Unban a member

    :param ctx:
    :param message:
    :return:
    """
    try:
        ban_list = await ctx.get_bans(message.server)
        for m in ban_list:
            if m.display_name == message.content[7:]:
                await ctx.unban(message.server, m)
                await ctx.send_message(message.channel, "**Unbanned**: `{}` from `{}` :thumbsup:"
                                                        .format(str(m.name), str(message.server.name)))
                return

        await ctx.send_message(message.channel, "**Error** `User not found`. Make sure the name is "
                                                "correct. Don't use @ while typing the users name.")
        return
    except discord.Forbidden:
        await ctx.send_message(message.channel, "**Error** `I do not have 'Ban Users' Permission.`")
        return
    except discord.HTTPException:
        await ctx.send_message(message.channel, "**Error** `Banning failed.`")
        return

async def levels(ctx, message):
    """
    Enable Member Rankings and XP

    :param ctx:
    :param message:
    :return:
    """
    cont = message.content[8:]
    if cont.lower() == "on":
        key = str(message.server.id) + "lvl_track"
        red.set(key, "Member Levels: ON")
        await ctx.send_message(message.channel, ":loudspeaker: Member Levels are `ON` for `{}`."
                                                .format(str(message.server.name)))
        return
    elif cont.lower() == "off":
        key = message.server.id + "lvl_track"
        if red.exists(key):
            red.delete(key)
            await ctx.send_message(message.channel, "Member Levels are `OFF` for `{}`."
                                                    .format(str(message.server.name)))
        else:
            await ctx.send_message(message.channel, "**Error** `'Member Rankings and Levels' are "
                                                    "already turned 'OFF' for your server.`")
    else:
        await ctx.send_message(message.channel, "Error: Usage `?levels on` or `?levels off`")
        return

async def set_levels_an(ctx, message):
    """
    Enable/Disable level up announcements

    :param ctx:
    :param message:
    :return:
    """
    cont = message.content[15:]
    if cont.lower() == "on":
        key = str(message.server.id) + "lvl_track_an"
        red.set(key, "Member Levels: ON")
        await ctx.send_message(message.channel, ":loudspeaker: Member Levels Announcements are `ON` "
                                                "for `{}`.".format(message.server.name))
    elif cont.lower() == "off":
        key = message.server.id + "lvl_track_an"
        if red.exists(key):
            red.delete(key)
            await ctx.send_message(message.channel, "Member Levels Announcements are `OFF` for `{}`."
                                                    .format(message.server.name))
        else:
            await ctx.send_message(message.channel, "**Error** `'Member Levels Announcements' are "
                                                    "already turned 'OFF' for your server.`")
    else:
        await ctx.send_message(message.channel, "Error: Usage `?set_levels_an on` or "
                                                "`?set_levels_an off`")

async def set_xp_roles(ctx, message):
    """
    For osu! Discord Fleet only. Enable xp and leaderboard commands
    for specific roles
    :param ctx:
    :param message:
    :return:
    """
    cont = message.content[14:]
    if cont.lower() == "off":
        key = message.server.id + "xp_roles"
        red.delete(key)
        await ctx.send_message(message.channel, "**Success** `Anyone can use XP and Leaderboards now.`"
                                                .format(message.server.name))
    else:
        key = message.server.id + "xp_roles"
        r_c = discord.utils.get(message.server.roles, name=cont)
        if not r_c:
            await ctx.send_message(message.channel, "**Error**: `Role does not exist`")
            return
        red.lpush(key, str(r_c.id))
        await ctx.send_message(message.channel, "**Success**: `Role: {} has been added to XP "
                                                "white-list.`".format(r_c.name))
        return

async def add_twitch(ctx, message):
    """
    Add a new twitch stream

    :param ctx:
    :param message:
    :return:
    """
    command = message.content[12:]
    switch = command.split(";")
    if not len(switch) == 2:
        await ctx.send_message(message.channel, "**Error**: Bad request."
                                                "\nUsage: `;;add_twitch #channel; name`"
                                                "\nExample: `?add_twitch #streams; monstercat`")
        return
    usr_name = switch[1]
    clean_pre = usr_name.lstrip()
    clean_post = clean_pre.rstrip()

    chan = message.channel_mentions
    alert_chan_id = chan[0].id

    endpoint = "https://api.twitch.tv/kraken/channels/{}".format(str(clean_post))
    headers = {"Client-ID": "gdo7uqrj9fvv2yvdg4w4ln6bmvke1kk",
               "Accept": "application/vnd.twitchtv.v3+json"}
    with aiohttp.ClientSession() as session:
        async with session.get(url=endpoint, headers=headers) as resp:
            data = await resp.read()

    r = json.loads(data.decode("utf-8"))
    try:
        chan_id = str(r['_id'])
    except KeyError:
        await ctx.send_message(message.channel, ":scream: **Error** `Invalid Channel...`")
        return

    chan_name = r['name']
    chan_url = r['url']

    try:
        cursor_n = db.stream_notifications.find({"serv_id": str(message.server.id)})
        cursor_t = db.twitch_streams.find({"chan_id": chan_id})

        # TODO add a cleanup service that removes unreferenced channel every 24 hours
        # --- Add data to the Central Twitch Database --- #
        if cursor_t.count() == 0:
            new_record = {"chan_id": chan_id,
                          "chan_name": chan_name,
                          "latest_stream_timestamp": "",
                          "latest_stream_id": "",
                          "game": "",
                          "status_text": "",
                          "url": chan_url,
                          "last_updated": datetime.datetime.utcnow()}
            db.twitch_streams.insert_one(new_record)

        # --- Add data to the Server Specific Feeds Database --- #
        if cursor_n.count() == 0:
            new_record = {"serv_id": str(message.server.id),
                          "twitch_streams": [{"chan_id": chan_id,
                                              "chan_name": chan_name,
                                              "last_stream_timestamp": "",
                                              "last_stream_id": "",
                                              "alert_chan_id": alert_chan_id}],
                          "last_updated": datetime.datetime.utcnow()}
            db.stream_notifications.insert_one(new_record)
            await ctx.send_message(message.channel, ":tv: **Success** `Stream: '{}' is added succesfully.`"
                                                    .format(chan_name))
            return

        else:
            for c in cursor_n:
                for j in c["twitch_streams"]:
                    if j['chan_id'] == chan_id:
                        await ctx.send_message(message.channel, "**Error** `This stream already exists.`")
                        return
            field = {"serv_id": str(message.server.id)}
            update = {"$push":
                          {"twitch_streams": {"chan_id": chan_id,
                                              "chan_name": chan_name,
                                              "last_stream_timestamp": "",
                                              "last_stream_id": "",
                                              "alert_chan_id": alert_chan_id}},
                      "$currentDate":
                          {"last_updated": {"$type": "date"}}
                      }
            db.stream_notifications.update_one(field, update)
            await ctx.send_message(message.channel, ":tv: **Success** `Stream: '{}' is added succesfully.`"
                                                    .format(chan_name))
            return
    except AttributeError:
        pass

# TODO: fix this entire function.
# The entire function has a really messed up approach
# to validate feeds. It should be corrected ASAP.
async def add_feed(ctx, message):
    """
    Add a rss feed

    :param ctx:
    :param message:
    :return:
    """
    command = message.content[10:]
    switch = str(command).split(";")
    if not len(switch) == 2:
        await ctx.send_message(message.channel, "**Error**: Bad request."
                                                "\nUsage: `;;add_feed #channel; URL`"
                                                "\nExample: `?add_feed #feed; "
                                                "http://lapoozza.me/feed/atom`")
        return
    url_feed = str(switch[1])
    clean_pre = url_feed.lstrip()
    clean_post = clean_pre.rstrip()

    chan = message.channel_mentions
    chan_id = chan[0].id
    d = feedparser.parse(clean_post)
    if "links" not in d.feed:
        return
    links = d.feed.links
    feed_url = ""
    last_post_ids = []
    latest_publish = None
    # FIXME when no links are found in d.feed, there should be a error message
    # FIXME http://feeds.thescoreesports.com/lol.rss <<-- doesnt have links field but is perfectly valid
    for l in links:
        if l['type'] == "application/atom+xml":
            try:
                a_sort = []
                last_post_ids.clear()
                for p in d.entries:
                    last_post_ids.append(p.id)
                    a_sort.append(datetime.datetime.fromtimestamp(time.mktime(p.updated_parsed)))
                    b_sort = sorted(a_sort, reverse=True)
                    latest_publish = b_sort[0]
                    feed_url = l['href']
            except AttributeError:
                break
        elif l['type'] == "application/rss+xml":
            try:
                a_sort = []
                last_post_ids.clear()
                for p in d.entries:
                    last_post_ids.append(p.id)
                    a_sort.append(datetime.datetime.fromtimestamp(time.mktime(p.updated_parsed)))
                    b_sort = sorted(a_sort, reverse=True)
                    latest_publish = b_sort[0]
                    feed_url = l['href']
            except AttributeError:
                break

        else:
            try:
                a_sort = []
                last_post_ids.clear()
                for p in d.entries:
                    last_post_ids.append(p.id)
                    a_sort.append(datetime.datetime.fromtimestamp(time.mktime(p.updated_parsed)))
                    b_sort = sorted(a_sort, reverse=True)
                    latest_publish = b_sort[0]
                    feed_url = clean_post
            except AttributeError:
                continue

    if feed_url == "":
        await ctx.send_message(message.channel, "**Error** `Did not find any valid RSS/ATOM feeds "
                                                "in the given link.`")
        return
    if not latest_publish:
        await ctx.send_message(message.channel, ":warning: **Error** `Bad link.``")
        return
    title = d.feed.title
    try:
        cursor = db.feeds.find({"serv_id": str(message.server.id)})
        if cursor.count() == 0:
            new_record = {"serv_id": str(message.server.id),
                          "feed_stat": "on",
                          "feeds": [{"feed_url": feed_url,
                                     "channel_id": chan_id,
                                     "title": title,
                                     "last_post_ids": last_post_ids,
                                     "latest_publish": latest_publish}],
                          "last_updated": datetime.datetime.utcnow()}
            db.feeds.insert_one(new_record)
            await ctx.send_message(message.channel, ":mailbox: **Success** `Feed: '{}' is added "
                                                    "succesfully.`".format(title))
            return

        else:
            for c in cursor:
                for j in c["feeds"]:
                    if j['feed_url'] == feed_url:
                        await ctx.send_message(message.channel, "**Error** `This feed already exists.`")
                        return
            field = {"serv_id": message.server.id}
            update = {
                "$push": {
                    "feeds": {
                        "feed_url": feed_url,
                        "channel_id": chan_id,
                        "title": title,
                        "last_post_ids": last_post_ids,
                        "latest_publish": latest_publish

                    }
                },
                "$currentDate": {
                    "last_updated": {
                        "$type": "date"
                    }
                }
            }
            db.feeds.update_one(field, update)
            await ctx.send_message(message.channel, ":mailbox: **Success** `Feed: '{}' is added "
                                                    "succesfully.`".format(title))
            return
    except AttributeError:
        pass

async def del_feed(ctx, message):
    """
    Delete RSS feed

    :param ctx:
    :param message:
    :return:
    """
    url_feed = message.content[10:]
    clean_pre = url_feed.lstrip()
    clean_post = clean_pre.rstrip()

    try:
        cursor = db.feeds.find({"serv_id": message.server.id})
        if cursor.count() == 0:
            await ctx.send_message(message.channel, "**Error** `Currently 'no' feeds are active.`")
            return

        for c in cursor:
            for j in c["feeds"]:
                if j['feed_url'] == clean_post:
                    title = j['title']
                    field = {"serv_id": message.server.id}
                    update = {"$pull":
                                  {"feeds": {"feed_url": clean_post}},
                              "$currentDate":
                                  {"last_updated": {"$type": "date"}}
                              }
                    db.feeds.update_one(field, update)
                    await ctx.send_message(message.channel, ":mailbox: **Success**: `Feed: '{}' "
                                                            "removed succesfully.`".format(title))
                    return

        await ctx.send_message(message.channel, "**Error** `Feed URL not found. Use ?list_feed .`")
        return
    except AttributeError:
        pass

async def list_feed(ctx, message):
    """
    List the available RSS feeds

    :param ctx:
    :param message:
    :return:
    """
    try:
        cursor = db.feeds.find({"serv_id": str(message.server.id)})
        if cursor.count() == 0:
            await ctx.send_message(message.channel, "**Error** `Currently 'no' feeds are active.`")
            return
        a = ""
        for c in cursor:
            for j in c["feeds"]:
                feed_url = j['feed_url']
                a += "{}\n".format(feed_url)
        await ctx.send_message(message.channel, "```css\n{}```".format(a))
        return
    except AttributeError:
        pass

async def xp_blacklist(ctx, message):
    """
    Add/ Remove people from XP Blacklist

    :param ctx:
    :param message:
    :return:
    """
    allowed_ids = settings["XP_BLACKLIST_IDS"]
    if message.author.id in allowed_ids:
        switch = message.content[9:]
        splits = str(switch).split(";", maxsplit=1)
        user_id = splits[0]
        action = splits[1]
        if action == "add":
            red.lpush("xp_black_list", user_id)
            await ctx.send_message(message.channel, "**Added** : `{}` to the XP blacklist.".format(user_id))
        elif action == "remove":
            red.lrem("xp_black_list", 0, user_id)
            await ctx.send_message(message.channel, "**Removed** : `{}` from the XP blacklist.".format(user_id))
    else:
        await ctx.send_message(message.channel, '`This command is reserved for Team Rero only`')

async def list_xp_blacklist(ctx, message):
    """
    list

    :return:
    """
    allowed_ids = settings["XP_BLACKLIST_IDS"]

    if message.author.id in allowed_ids:
        banned_ids = red.lrange("xp_black_list", 0, -1)
        op_str = ""
        for b in banned_ids:
            op_str += b.decode('utf-8') + "\n"

        op_file = BytesIO(op_str.encode("utf-8"))
        await ctx.send_file(message.channel, op_file, filename="logs_{}_{}.txt"
                            .format(message.author.id, str(datetime.datetime.utcnow().date())))
        await ctx.send_message(message.channel, "Enjoy.")
    else:
        await ctx.send_message(message.channel, '`This command is reserved for Team Rero only`')
