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
from io import BytesIO

# TODO: Change this to use sockets
# Sockets are required because due to shard-ing we wont be able
# to send message to a static channel as this channel may not be
# part of our shard
async def report(reason: str, ctx, message):
    """
    Send report to Spam Patrol for Review

    :param reason:
    :param ctx:
    :param message:
    :return:
    """
    channel = ctx.get_channel("315347852933201920")
    deliver_str = "Spam Records for '{}'\nServer: {} | Channel: {}\nGenerated at: {} UTC\n\n" \
        .format(message.author.name, message.server.name, message.channel.name,
                str(datetime.datetime.utcnow()))
    async for m in ctx.logs_from(message.channel):
        if m.author == message.author:
            deliver_str += "[{}] - [ {} ] - {}\n".format(m.timestamp, m.author.name, m.clean_content)
    op_file = BytesIO(deliver_str.encode("utf-8"))
    await ctx.send_file(channel, op_file, filename="logs_{}_{}.txt".
                        format(message.author.id, str(datetime.datetime.utcnow().date())))
    await ctx.send_message(channel, " <@&314778263966711809> : New Report. Please review. "
                                    "\nCause: {}"
                                    "\nUserID: `{}`".format(reason, message.author.id))
