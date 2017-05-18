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
import xml
import aiohttp
import html
import re

with open("config/settings.yaml") as file:
    settings_file = file.read()
file.close()
settings = yaml.load(settings_file)

class Weeb:
    """
    Contains anime/manga related commands
    """
    def __init__(self, context):
        super().__init__()
        self.ctx = context

    async def anime_parser(self, message):
        """
        Fetch anime from MAL

        :param message:
        :return:
        """
        q = message.content[7:]
        if q == "":
            await self.ctx.send_message(message.channel, "(◕ᴗ◕✿) `You need to specify a anime.`")
            return
        switch = str(q).split('$')
        if len(switch) == 2:
            q_clean = switch[0].replace(" ", "+")
            with aiohttp.ClientSession(auth=aiohttp.BasicAuth(login=settings["MAL_ID"],
                                                              password=settings["MAL_PASSWORD"])) as session:
                async with session.get(
                        'http://myanimelist.net/api/anime/search.xml?q={}'.format(q_clean)) as resp:
                    data = await resp.read()
            try:
                dats = xml.etree.ElementTree.fromstring(data)
                title = dats[0][1].text
                episodes = dats[0][4].text
                score = dats[0][5].text
                synopsis = dats[0][10].text
                image = dats[0][11].text

                s_clean = html.unescape(synopsis)
                ss_clean = re.sub("[\[,\]]", "", s_clean)
                ss_clean_s = ss_clean.replace("<br />", '')
                await self.ctx.send_message(message.channel, "**{}**"
                                                             "\nEpisodes: `{}`"
                                                             "\nScore: `{}`"
                                                             "\nExcerpt: ```{}``` "
                                                             "{}"
                                                             .format(title, episodes, score, ss_clean_s, image))
            except xml.etree.ElementTree.ParseError:
                await self.ctx.send_message(message.channel, "Anime not found. Try again!")
            except AttributeError:
                await self.ctx.send_message(message.channel, "Anime not found. Try again!")
        else:
            q_clean = str(q).replace(" ", "+")
            with aiohttp.ClientSession(auth=aiohttp.BasicAuth(login=settings["MAL_ID"],
                                                              password=settings["MAL_PASSWORD"])) as session:
                async with session.get(
                        'http://myanimelist.net/api/anime/search.xml?q={}'.format(q_clean)) as resp:
                    data = await resp.read()
            try:
                dats = xml.etree.ElementTree.fromstring(data)
                title = dats[0][1].text
                episodes = dats[0][4].text
                score = dats[0][5].text
                image = dats[0][11].text

                await self.ctx.send_message(message.channel, "**{}**"
                                                             "\nEpisodes: `{}`"
                                                             "\nScore: `{}`"
                                                             "\n{}"
                                                             "\n*If you want summary, use* `?anime {}$`"
                                                             .format(title, episodes, score, image, str(q)))
            except xml.etree.ElementTree.ParseError:
                await self.ctx.send_message(message.channel, "Anime not found. Try again!")
            except AttributeError:
                await self.ctx.send_message(message.channel, "Anime not found. Try again!")

    async def manga_parser(self, message):
        """
        Fetch manga from MAL

        :param message:
        :return:
        """
        q = message.content[7:]
        if q == "":
            await self.ctx.send_message(message.channel, "(◕ᴗ◕✿) `You need to specify a manga.`")
            return
        switch = str(q).split('$')
        if len(switch) == 2:
            q_clean = switch[0].replace(" ", "+")
            with aiohttp.ClientSession(auth=aiohttp.BasicAuth(login=settings["MAL_ID"],
                                                              password=settings["MAL_PASSWORD"])) as session:
                async with session.get(
                        'http://myanimelist.net/api/manga/search.xml?q={}'.format(q_clean)) as resp:
                    data = await resp.read()
            try:
                dats = xml.etree.ElementTree.fromstring(data)
                title = dats[0][1].text
                chapters = dats[0][4].text
                score = dats[0][6].text
                synopsis = dats[0][11].text
                image = dats[0][12].text

                s_clean = html.unescape(synopsis)
                ss_clean = re.sub("[\[,\]]", "", s_clean)
                ss_clean_s = ss_clean.replace("<br />", '')
                await self.ctx.send_message(message.channel, "**{}**"
                                                             "\nChapters: `{}`"
                                                             "\nScore: `{}`"
                                                             "\nExcerpt: ```{}``` "
                                                             "{}"
                                                             .format(title, chapters, score, ss_clean_s, image))
            except xml.etree.ElementTree.ParseError:
                await self.ctx.send_message(message.channel, "Manga not found. Try again!")
            except AttributeError:
                await self.ctx.send_message(message.channel, "Manga not found. Try again!")
        else:
            q_clean = str(q).replace(" ", "+")
            with aiohttp.ClientSession(auth=aiohttp.BasicAuth(login=settings["MAL_ID"],
                                                              password=settings["MAL_PASSWORD"])) as session:
                async with session.get(
                        'http://myanimelist.net/api/manga/search.xml?q={}'.format(q_clean)) as resp:
                    data = await resp.read()
            try:
                dats = xml.etree.ElementTree.fromstring(data)
                title = dats[0][1].text
                chapters = dats[0][4].text
                score = dats[0][6].text
                image = dats[0][12].text

                await self.ctx.send_message(message.channel, "**{}**"
                                                             "\nChapters: `{}`"
                                                             "\nScore: `{}`"
                                                             "\n{}"
                                                             "\n*If you want summary, use* `?manga {}$`"
                                                             .format(title, chapters, score, image, str(q)))
            except xml.etree.ElementTree.ParseError:
                await self.ctx.send_message(message.channel, "Manga not found. Try again!")
            except AttributeError:
                await self.ctx.send_message(message.channel, "Manga not found. Try again!")
