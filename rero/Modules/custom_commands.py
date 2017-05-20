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
from Rero import mongo_manager
import discord


class CustomCommands:
    """
    Custom Commands Parser and Handler
    """
    def __init__(self, context):
        super().__init__()
        self.ctx = context
        self.db = mongo_manager.mongo_db.db

    async def cc_handler(self, message):
        """
        Handles the requests for custom commands

        :param message:
        :return:
        """
        name = message.content[2:]
        cursor = self.db.custom_commands_new.find(
            {"serv_id": str(message.server.id), "commands_list.command_name": name})
        if cursor.count() > 0:
            for i in cursor:
                commands_list = i['commands_list']
                for c in commands_list:
                    if c['command_name'] == name and (i['status'] == "ON" or i['status'] == "RESTRICTED"):
                        action = c['command']
                        cleaned_cmd_post = action.replace("@everyone", "*every* :one:")
                        await self.ctx.send_message(message.channel, cleaned_cmd_post)
                        return

    async def add_cc(self, message):
        """
        Add a new custom command

        :param message:
        :return:
        """
        command = message.content[8:]
        switch = str(command).split("|")
        if not len(switch) == 2:
            await self.ctx.send_message(message.channel, "**Error**: Bad request."
                                                         "\nUsage: `;;add_cc command name | command`"
                                                         "\nExample: `?add_cc hello | hello world`"
                                                         "\n*psst* be creative. You can add links.")
            return
        command_name = str(switch[0])
        clean_pre = command_name.lstrip()
        clean_post = clean_pre.rstrip()

        command = str(switch[1])
        cmd_pre = command.lstrip()
        cmd_post = cmd_pre.rstrip()
        if "@everyone" in clean_post:
            await self.ctx.send_message(message.channel, "**Error** `This can't be used as a command name.`")
            return
        cleaned_cmd_post = cmd_post.replace("@everyone", "*every* :one:")
        try:
            cursor = self.db.custom_commands_new.find({"serv_id": message.server.id})
            if cursor.count() == 0:
                await self.ctx.send_message(message.channel, "**Error**: `'Custom Command' module is not yet "
                                                             "activated.`")
                return

            else:
                for c in cursor:
                    commands_list = c['commands_list']
                    if c['status'] == "ON":
                        for k in commands_list:
                            if k['command_name'] == clean_post:
                                await self.ctx.send_message(message.channel, "**Error** `A command with that name "
                                                                             "already exists in this server. Choose a "
                                                                             "different name.`")
                                return
                        field = {"serv_id": message.server.id}
                        update = {
                            "$push": {
                                "commands_list": {
                                    "command_name": clean_post,
                                    "command": cleaned_cmd_post,
                                    "creator_id": message.author.id
                                }
                            },
                            "$currentDate": {
                                "last_updated": {
                                    "$type": "date"
                                }
                            }
                        }
                        self.db.custom_commands_new.update_one(field, update)
                        await self.ctx.send_message(message.channel, "**Success**: `Added '{}'`".format(clean_post))
                        return
                    elif c['status'] == "RESTRICTED":
                        try:
                            role_id = c['access_control_role_id']
                            role = discord.utils.get(message.server.roles, id=role_id)
                            if not role:
                                await self.ctx.send_message(message.channel,
                                                            "**Error**: `The role associated with 'RESTRICTED' mode "
                                                            "does not exist. Make sure you set a new role.`")
                                return
                        except KeyError:
                            await self.ctx.send_message(message.channel,
                                                        "**Error**: `The role associated with 'RESTRICTED' mode does "
                                                        "not exist. Make sure you set a new role.`")
                            return
                        # Access control based on role
                        try:
                            a = message.author.roles
                        except AttributeError:
                            await self.ctx.send_message(message.channel, "**Info**: `There was an error verifying if "
                                                                         "you have 'RERO' role. Please retry this "
                                                                         "command.`")
                            return
                        # print(a)
                        for i in a:
                            if i.name == role.name:
                                for k in commands_list:
                                    if k['command_name'] == clean_post:
                                        await self.ctx.send_message(message.channel,
                                                                    "**Error** `A command with that name already "
                                                                    "exists in this server. Choose a different name.`")
                                        return
                                field = {"serv_id": message.server.id}
                                update = {
                                    "$push": {
                                        "commands_list": {
                                            "command_name": clean_post,
                                            "command": cleaned_cmd_post,
                                            "creator_id": message.author.id
                                        }
                                    },
                                    "$currentDate": {
                                        "last_updated": {
                                            "$type": "date"
                                        }
                                    }
                                }
                                self.db.custom_commands_new.update_one(field, update)
                                await self.ctx.send_message(message.channel, "**Success**: `Added '{}'`"
                                                                             .format(clean_post))
                                return

        except AttributeError:
            pass

    async def del_cc(self, message):
        """
        Delete a custom command

        :param message:
        :return:
        """
        command = message.content[8:]
        server_id = message.server.id
        try:
            cursor_check = self.db.custom_commands_new.find({"serv_id": message.server.id})
            if cursor_check.count() == 0:
                await self.ctx.send_message(message.channel, "**Error**: `'Custom Command' module is not yet "
                                                             "activated.`")
                return

            else:
                for ooh in cursor_check:
                    if ooh['status'] == "ON" or ooh['status'] == "RESTRICTED":
                        cursor = self.db.custom_commands_new.find({"serv_id": str(message.server.id),
                                                                   "commands_list.command_name": command})
                        for i in cursor:
                            commands_list = i['commands_list']
                            for c in commands_list:
                                if c['command_name'] == command:
                                    creator_id = c['creator_id']
                                    rero = discord.utils.get(message.server.roles, name="RERO")
                                    if rero:
                                        if message.author.id == creator_id or rero in message.author.roles:
                                            field = {"serv_id": server_id}
                                            update = {"$pull": {"commands_list": {"command_name": command}},
                                                      "$currentDate":
                                                          {"last_updated": {"$type": "date"}}
                                                      }
                                            self.db.custom_commands_new.update_one(field, update)
                                            await self.ctx.send_message(message.channel,
                                                                        "**Success**: `Custom command is "
                                                                        "deleted. To create a new one use "
                                                                        "?add_cc`")
                                            return
                                        else:
                                            await self.ctx.send_message(message.channel,
                                                                        "**Error**: `Only the creator of this "
                                                                        "command or someone with RERO role "
                                                                        "can delete it.`")
                                    else:
                                        if message.author.id == creator_id:
                                            field = {"serv_id": server_id}
                                            update = {"$pull": {"commands_list": {"command_name": command}},
                                                      "$currentDate":
                                                          {"last_updated": {"$type": "date"}}
                                                      }
                                            self.db.custom_commands_new.update_one(field, update)
                                            await self.ctx.send_message(message.channel,
                                                                        "**Success**: `Custom command is "
                                                                        "deleted. To create a new one use "
                                                                        "?add_cc`")
                                            return
                                        else:
                                            await self.ctx.send_message(message.channel,
                                                                        "**Error**: `Only the creator of this "
                                                                        "command can delete it.`")

        except AttributeError:
            pass

    async def list_cc(self, message):
        """
        List all the custom commands

        :param message:
        :return:
        """
        try:
            cursor = self.db.custom_commands_new.find({"serv_id": message.server.id})
            if cursor.count() == 0:
                await self.ctx.send_message(message.channel, "**Error**: `No custom commands found in this server.`")
                return

            else:
                for i in cursor:
                    if i['status'] == "ON" or i['status'] == "RESTRICTED":
                        a = ""
                        commands_list = i['commands_list']
                        for j in commands_list:
                            command_name = j['command_name']
                            a += "{}\n".format(command_name)

                        if len(a) < 1999:
                            await self.ctx.send_message(message.channel, "```ruby\n"
                                                                         "{}```".format(a))
                            return
                        else:
                            n = 1800
                            splits = [a[j: j + n] for j in range(0, len(a), n)]
                            for stuff in splits:
                                await self.ctx.send_message(message.channel, "```ruby\n"
                                                                             "{}```".format(stuff))
                            return

        except AttributeError:
            pass