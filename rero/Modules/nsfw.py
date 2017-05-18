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
import aiohttp
import random
import xml
from Rero import mongo_manager

with open("config/settings.yaml") as file:
    settings_file = file.read()
file.close()
settings = yaml.load(settings_file)

class NSFW:
    """
    Handles the NSFW commands
    """
    def __init__(self, context):
        super().__init__()
        self.ctx = context
        self.db = mongo_manager.mongo_db.db

    async def baka(self, message):
        """
        The famous baka command

        :param message:
        :return:
        """
        cursor = self.db.server_backend.find({"serv_id": message.server.id})
        for c in cursor:
            nsfw_status = c['nsfw']['nsfw_status']
            nsfw_chan_id = c['nsfw']['nsfw_chan_id']

            if nsfw_status == "on|global" or nsfw_chan_id == message.channel.id:
                err_d = False
                err_g = False
                img_g = ""
                img_d = ""
                tag = message.content[6:]
                tags = str(tag).rstrip()
                with aiohttp.ClientSession() as session_g:
                    async with session_g.get(
                            "http://gelbooru.com/index.php?page=dapi""&s=post&q=index&tags=rating%3Aexplicit+{}".format(
                                tags)) as resp_g:
                        if resp_g.status == 200:
                            data_g = await resp_g.read()

                            if data_g:
                                dats = xml.etree.ElementTree.fromstring(data_g)
                                data_len = len(dats.getchildren())
                                if not data_len == 0:
                                    try:
                                        ran_g = random.randint(0, data_len - 1)
                                        # lucky_g = data_g[ran_g]
                                        img_g = dats[ran_g].get("file_url")
                                    except xml.etree.ElementTree.ParseError:
                                        err_g = True
                                    except IndexError:
                                        err_g = True
                                    except AttributeError:
                                        err_d = True

                                else:
                                    err_g = True
                            else:
                                err_g = True
                        else:
                            err_g = True

                with aiohttp.ClientSession(auth=aiohttp.BasicAuth(login=settings["DANBOORU_ID"], password=settings["DANBOORU_PASSWORD"])) as session_d:
                    async with session_d.get(
                            "https://danbooru.donmai.us/posts.json?tags=rating%3Aexplicit+{}".format(
                                tags)) as resp_d:
                        if resp_d.status == 200:
                            data_d = await resp_d.json()
                            if data_d:
                                data_len_d = len(data_d)
                                if not data_len_d == 0:
                                    try:
                                        ran_d = random.randint(0, data_len_d - 1)
                                        lucky_d = data_d[ran_d]
                                        a = "https://danbooru.donmai.us"
                                        img_d = a + lucky_d['file_url']
                                    except KeyError:
                                        err_d = True
                                    except IndexError:
                                        err_d = True
                                else:
                                    err_d = True
                            else:
                                err_d = True
                        else:
                            err_d = True

                if not err_g and not err_d:
                    ran = random.randint(0, 1)
                    img = {0: img_g,
                           1: img_d}
                    tag = {0: "**Gelbooru**",
                           1: "**Danbooru**"}

                    await self.ctx.send_message(message.channel, "{}\n{}".format(tag[ran], img[ran]))
                    return
                elif err_g and not err_d:
                    await self.ctx.send_message(message.channel, "{}\n{}".format("Danbooru", img_d))
                    return
                elif not err_g and err_d:
                    await self.ctx.send_message(message.channel, "{}\n{}".format("Gelbooru", img_g))
                    return
                elif err_g and err_d:
                    await self.ctx.send_message(message.channel,
                                                "**Error**: `Tag {} did not return any results.`".format(tags))
                    return

    async def danbooru(self, message):
        """
        Get a random image from Danbooru

        :param message:
        :return:
        """
        cursor = self.db.server_backend.find({"serv_id": message.server.id})
        for c in cursor:
            nsfw_status = c['nsfw']['nsfw_status']
            nsfw_chan_id = c['nsfw']['nsfw_chan_id']

            if nsfw_status == "on|global" or nsfw_chan_id == message.channel.id:
                tag = message.content[10:]
                tags = str(tag).rstrip()
                if tags == "":
                    with aiohttp.ClientSession(
                            auth=aiohttp.BasicAuth(
                                login=settings["DANBOORU_ID"], password=settings["DANBOORU_PASSWORD"])) as session:
                        async with session.get("https://danbooru.donmai.us/posts.json?") as resp:
                            if resp.status == 200:
                                data = await resp.json()
                            else:
                                return

                else:
                    with aiohttp.ClientSession(
                            auth=aiohttp.BasicAuth(
                                login=settings["DANBOORU_ID"], password=settings["DANBOORU_PASSWORD"])) as session:
                        async with session.get("https://danbooru.donmai.us/posts.json?tags={}".format(tag)) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                            else:
                                return
                if not data:
                    await self.ctx.send_message(message.channel,
                                                "**Error**: `Tag {} did not return any results.`".format(tag))
                    return

                data_len = len(data)
                if data_len == 0:
                    await self.ctx.send_message(message.channel,
                                                "**Error**: `Tag {} did not return any results.`".format(tag))
                    return
                try:
                    ran = random.randint(0, data_len - 1)
                    lucky = data[ran]
                    a = "https://danbooru.donmai.us"
                    img = a + lucky['file_url']
                    await self.ctx.send_message(message.channel, img)
                    return
                except KeyError:
                    pass
                except IndexError:
                    pass

    async def gelbooru(self, message):
        """
        Returns a random image from Gelbooru

        :param message:
        :return:
        """
        cursor = self.db.server_backend.find({"serv_id": message.server.id})
        for c in cursor:
            nsfw_status = c['nsfw']['nsfw_status']
            nsfw_chan_id = c['nsfw']['nsfw_chan_id']

            if nsfw_status == "on|global" or nsfw_chan_id == message.channel.id:
                tag = message.content[10:]
                tags = str(tag).rstrip()
                if tags == "":
                    with aiohttp.ClientSession() as session:
                        async with session.get("http://gelbooru.com/index.php?page=dapi&s=post&q=index") as resp:
                            if resp.status == 200:
                                data = await resp.read()
                            else:
                                return

                else:
                    with aiohttp.ClientSession() as session:
                        async with session.get(
                                "http://gelbooru.com/index.php?page=dapi&s=post&q=index&tags={}".format(
                                    tags)) as resp:
                            if resp.status == 200:
                                data = await resp.read()
                            else:
                                return
                if not data:
                    await self.ctx.send_message(message.channel,
                                                "**Error**: `Tag {} did not return any results.`".format(tags))
                    return

                dats = xml.etree.ElementTree.fromstring(data)
                data_len = len(dats.getchildren())
                if data_len == 0:
                    await self.ctx.send_message(message.channel,
                                                "**Error**: `Tag {} did not return any results.`".format(tags))
                    return

                try:
                    ran = random.randint(0, data_len - 1)
                    img = dats[ran].get("file_url")
                    await self.ctx.send_message(message.channel, img)
                    return
                except xml.etree.ElementTree.ParseError:
                    await self.ctx.send_message(message.channel,
                                                "**Error**: `Tag {} did not return any results.`".format(tags))
                except AttributeError:
                    await self.ctx.send_message(message.channel,
                                                "**Error**: `Tag {} did not return any results.`".format(tags))
                except Exception as e:
                    print(dats.getchildren())
                    await self.ctx.send_message(message.channel, e)

    async def rule34(self, message):
        """
        Returns a random image from rule34

        :param message:
        :return:
        """
        cursor = self.db.server_backend.find({"serv_id": message.server.id})
        for c in cursor:
            nsfw_status = c['nsfw']['nsfw_status']
            nsfw_chan_id = c['nsfw']['nsfw_chan_id']

            if nsfw_status == "on|global" or nsfw_chan_id == message.channel.id:
                tag = message.content[8:]
                tags = str(tag).rstrip()
                if tags == "":
                    with aiohttp.ClientSession() as session:
                        async with session.get("http://rule34.xxx/index.php?page=dapi&s=post&q=index") as resp:
                            if resp.status == 200:
                                data = await resp.read()
                            else:
                                return

                else:
                    with aiohttp.ClientSession() as session:
                        async with session.get(
                                "http://rule34.xxx/index.php?page=dapi&s=post&q=index&tags={}".format(
                                    tags)) as resp:
                            if resp.status == 200:
                                data = await resp.read()
                            else:
                                return
                if not data:
                    await self.ctx.send_message(message.channel,
                                                "**Error**: `Tag {} did not return any results.`".format(tags))
                    return

                dats = xml.etree.ElementTree.fromstring(data)
                data_len = len(dats.getchildren())
                if data_len == 0:
                    await self.ctx.send_message(message.channel,
                                                "**Error**: `Tag {} did not return any results.`".format(tags))
                    return

                try:
                    ran = random.randint(0, data_len - 1)
                    img = dats[ran].get("file_url")
                    await self.ctx.send_message(message.channel, "http:" + img)
                    return
                except xml.etree.ElementTree.ParseError:
                    await self.ctx.send_message(message.channel,
                                                "**Error**: `Tag {} did not return any results.`".format(tags))
                except AttributeError:
                    await self.ctx.send_message(message.channel,
                                                "**Error**: `Tag {} did not return any results.`".format(tags))
                except IndexError:
                    pass
