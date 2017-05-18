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
import datetime
import time
import urllib
import re
import aiohttp
import asyncio
import json
import yaml
import io
import discord

class Osu:
    """
    OSU API functionality for rero

    This module does the following:
        -Stats : Retrieves osu profile statistics of players for 4 game modes- std, taiko, mania, ctb
        -Top : Retrieves
        -Scans all the message of osu based links and if found, shows related data.

    """

    def __init__(self, context):
        super().__init__()
        self.ctx = context
        self.db = mongo_manager.mongo_db.db

        self.URL_REGEX = re.compile(r'(?P<url>https?://osu\.ppy\.sh/\S+)')
        self.MODES = {
            'osu': '0',
            'taiko': '1',
            'ctb': '2',
            'mania': '3'
        }

        with open("config/settings.yaml") as file:
            settings_file = file.read()
        file.close()
        settings = yaml.load(settings_file)

        # Get the required keys from settings.yaml
        self.API_KEY = settings['OSU_API_KEY']
        self.Tillerino_Key = settings['TILLERINO_KEY']

        # We don't use 'settings' again. Might as well
        # delete it.
        del settings

    async def get_pp(self, message):
        """

        :return:
        """
        switch = message.content[4:]
        switch_s = str(switch).split("|")
        if not 1 <= len(switch_s) <= 2 or switch == "":
            await self.ctx.send_message(message.channel, "**Error**: `Invalid syntax used.`"
                                                         "\n**Usage**: `?pp beatmapid| mod1,mod2,..`"
                                                         "\n**Example**: `?pp 859246| hd,hr`")
            return
        beat_id = switch_s[0]
        beat_id_post = beat_id.strip(" ")
        # -------------------Querying Osu Api --------------------------------
        pep_e = "https://osu.ppy.sh/api/get_beatmaps"
        pay_l = {"k": self.API_KEY, "b": beat_id_post}
        with aiohttp.ClientSession() as session:
            async with session.get(url=pep_e, params=pay_l) as resp:
                data_s = await resp.read()

        data_s_json = json.loads(data_s.decode("utf-8"))
        try:
            op_till = "**{0[artist]} - {0[title]}** [{0[version]}] by {0[creator]}" \
                      "\nDifficulty: {1:.2f} ★".format(data_s_json[0],
                                                       float(data_s_json[0]['difficultyrating']))
        except KeyError:
            await self.ctx.send_message(message.channel, "**Error**`This beatmap ID does not exist. Retry with a "
                                                         "proper ID.`")
            return

        # -------------------Querying Tillerino --------------------------------
        endpoint = "http://bot.tillerino.org:1666/beatmapinfo?"
        if len(switch_s) == 1:
            params = {"k": self.Tillerino_Key,
                      "wait": 2000,
                      "beatmapid": beat_id_post,
                      "mods": "0"}
            try:
                with aiohttp.Timeout(2):
                    async with aiohttp.get(url=endpoint, params=params) as resp:
                        data = await resp.read()
            except asyncio.TimeoutError:
                await self.ctx.send_message(message.channel, "**Error**`Tillerino's server seems to be down right now. "
                                                             "Try again later.")
                return

            if resp.status == 202:
                await self.ctx.send_message(message.channel, "This beatmap's PP value has not been calculated yet. "
                                                             "Check back soon.")
                return
            elif resp.status == 200:
                pp_str = ""
                p = json.loads(data.decode("utf-8"))
                for entry in p['ppForAcc']['entry']:
                    if entry['key'] in [0.95, 0.97, 0.98, 0.985, 0.99, 0.995, 1]:
                        pp_str += "`{0}%: {1:.2f}PP` | ".format(str(entry['key'] * 100), float(entry['value']))

                await self.ctx.send_message(message.channel, "{}"
                                                             "\nBeatmap ID: {}"
                                                             "\nSelected Mods: None"
                                                             "\n{}".format(op_till, beat_id_post, pp_str))
                return
            else:
                await self.ctx.send_message(message.channel, "Beatmap ID not found. Make sure you use the id from "
                                                             "/b/ and not /s/")
                return

        else:
            mods = switch_s[1]
            mods_post = mods.strip(" ")

            mod_comb = {"NF": "1",
                        "EZ": "2",
                        "NV": "4",
                        "HD": "8",
                        "HR": "16",
                        "SD": "32",
                        "DT": "64",
                        "RX": "128",
                        "HT": "256",
                        "NC": "512",
                        "FL": "1024",
                        "AP": "2048",
                        "SO": "4096",
                        "PF": "16384"}
            mods_ava = mods_post.split(",")
            if len(mods_ava) == 0:
                params = {"k": self.Tillerino_Key,
                          "wait": 2000,
                          "beatmapid": beat_id_post,
                          "mods": "0"}
                try:
                    with aiohttp.Timeout(2):
                        async with aiohttp.get(url=endpoint, params=params) as resp:
                            data = await resp.read()
                except asyncio.TimeoutError:
                    await self.ctx.send_message(message.channel, "**Error**`Tillerino's server seems to be down right "
                                                                 "now. Try again later.")
                    return

                if resp.status == 202:
                    await self.ctx.send_message(message.channel, "This beatmap's PP value has not been calculated yet. "
                                                                 "Check back soon.")
                    return
                elif resp.status == 200:
                    pp_str = ""
                    p = json.loads(data.decode("utf-8"))
                    for entry in p['ppForAcc']['entry']:
                        if entry['key'] in [0.95, 0.97, 0.98, 0.985, 0.99, 0.995, 1]:
                            pp_str += "`{0}%: {1:.2f}PP` | ".format(str(entry['key'] * 100), float(entry['value']))

                    await self.ctx.send_message(message.channel, "{}"
                                                                 "\nBeatmap ID: {}"
                                                                 "\nSelected Mods: {}"
                                                                 "\n{}".format(op_till, beat_id_post, mods_post,
                                                                               pp_str))
                    return
                else:
                    await self.ctx.send_message(message.channel, "Beatmap ID not found. Make sure you use the id from "
                                                                 "/b/ and not /s/")
                    return

            else:
                mod_enum = 0
                for i in mods_ava:
                    try:
                        i_strip = i.strip(" ")
                        i_upper = i_strip.upper()
                        val = int(mod_comb[i_upper])
                        mod_enum += val
                    except KeyError:
                        await self.ctx.send_message(message.channel, "**Error**: `Mod not recognized. Supported mods "
                                                                     "are: NF, EZ, HD, HR, SD, DT, HT, NC, FL, SO, PF.`"
                                                                     "\nThis error can also happen if you add a `,` "
                                                                     "after the last mod.")
                        return
                params = {"k": self.Tillerino_Key,
                          "wait": 2000,
                          "beatmapid": beat_id_post,
                          "mods": str(mod_enum)}
                try:
                    with aiohttp.Timeout(2):
                        async with aiohttp.get(url=endpoint, params=params) as resp:
                            data = await resp.read()
                except asyncio.TimeoutError:
                    await self.ctx.send_message(message.channel, "**Error**`Tillerino's server seems to be down right "
                                                                 "now. Try again later.")
                    return
                if resp.status == 202:
                    await self.ctx.send_message(message.channel, "This beatmap's PP value has not been calculated yet. "
                                                                 "Check back soon.")
                    return
                elif resp.status == 200:
                    pp_str = ""
                    p = json.loads(data.decode("utf-8"))
                    if p['mods'] == mod_enum:
                        for entry in p['ppForAcc']['entry']:
                            if entry['key'] in [0.95, 0.97, 0.98, 0.985, 0.99, 0.995, 1]:
                                pp_str += "`{0}%: {1:.2f}PP` | ".format(str(entry['key'] * 100), float(entry['value']))

                        await self.ctx.send_message(message.channel, "{}"
                                                                     "\nBeatmap ID: {}"
                                                                     "\nSelected Mods: {}"
                                                                     "\n{}".format(op_till, beat_id_post, mods_post,
                                                                                   pp_str))
                        return
                    else:
                        await self.ctx.send_message(message.channel, "**Error** `Can't calculate PP for the given mod "
                                                                     "combination.`")

                else:
                    await self.ctx.send_message(message.channel, "Beatmap ID not found. Make sure you use the id from "
                                                                 "/b/ and not /s/.")
                    return

    async def stats(self, uname, mode):
        """
        This function uses the OSU API to return user statistics.

        :param mode:
        :param uname:
        :return: User stats
        :rtype: str
        """
        mode_sel = {"0": "osu!",
                    "1": "Taiko",
                    "2": "CtB",
                    "3": "osu! Mania"}

        endpoint = "https://osu.ppy.sh/api/get_user?"
        params = {"k": self.API_KEY,
                  "u": uname,
                  "m": mode,
                  "type": "string"}
        try:
            with aiohttp.Timeout(3):
                async with aiohttp.get(url=endpoint, params=params) as resp:
                    data = await resp.json()
        except asyncio.TimeoutError:
            return "**Error** `osu! API just timed out. Please retry.`"
        if resp.status == 200:
            try:
                for player in data:
                    op_str = "**{0}** (*{1}*)\n" \
                             "https://a.ppy.sh/{2} \n" \
                             "PP: {3:.2f}, Rank: #{4} (#{5} in {6})\n" \
                             "Accuracy: {7:.2f}%, PlayCount: {8}\n" \
                             "https://osu.ppy.sh/u/{2}"\
                        .format(player['username'], mode_sel[mode], player['user_id'], float(player['pp_raw']), player['pp_rank'],
                                player['pp_country_rank'], player['country'], float(player['accuracy']), player['playcount'])

                    result = op_str
                    return result
            except UnboundLocalError:
                    return str('```Username doesnt exist. Try again.```')
                    # NOTE:- if the result is 'string indices must be integers' that means the API key is wrong
            except TypeError:
                return
            except Exception as e:
                return str(e)

    async def top(self, uname, mode):
        """
        This function uses the OSU API to return user top 5 plays.

        :param mode:
        :param uname:
        :return: User top plays
        :rtype: str
        """
        mod_comb = {"0": "No Mod",
                    "1": "NF",
                    "2": "EZ",
                    "4": "NoVideo",
                    "8": "HD",
                    "16": "HR",
                    "24": "HD, HR",
                    "32": "SD",
                    "64": "DT",
                    "72": "HD, DT",
                    "88": "HD, HR, DT",
                    "128": "RX",
                    "256": "HT",
                    "512": "NC",
                    "1024": "FL",
                    "2048": "Autoplay",
                    "4096": "SO",
                    "8192": "AP",
                    "16384": "PF",
                    "32768": "4K",
                    "65536": "5K",
                    "131072": "6K",
                    "262144": "7K",
                    "524288": "8K",
                    "1048576": "FadeIn",
                    "2097152": "Random",
                    "4194304": "LastMod",
                    "16777216": "9K",
                    "33554432": "10K",
                    "67108864": "1K",
                    "134217728": "2K",
                    "268435456": "3K",
                    }
        start_time = time.time()
        endpoint = "https://osu.ppy.sh/api/get_user_best?"
        params = {"k": self.API_KEY,
                  "u": uname,
                  "m": mode,
                  "limit": "5"}
        try:
            with aiohttp.Timeout(3):
                async with aiohttp.get(url=endpoint, params=params) as resp:
                    data = await resp.json()
        except asyncio.TimeoutError:
            return "**Error** `osu! API just timed out. Please retry.`"
        if resp.status == 200:
            msg = ''
            try:
                for player in data:
                    mod = player['enabled_mods']
                    mods = ''
                    for m in mod_comb:
                        if int(mod) == int(m):
                            mods = " | {}".format(mod_comb[m])

                    thr = int(player['count300'])
                    hun = int(player['count100'])
                    fif = int(player['count50'])
                    miss = int(player['countmiss'])
                    tph = int(300 * thr + 100 * hun + 50 * fif)
                    tnh = int(thr + hun + fif + miss)
                    acc = float(tph / (tnh * 3))

                    try:
                        url = "https://osu.ppy.sh/api/get_beatmaps?k=" + self.API_KEY + '&b=' + player['beatmap_id']
                        with aiohttp.Timeout(3):
                            async with aiohttp.get(url=url) as resp:
                                data = await resp.json()
                    except asyncio.TimeoutError:
                        continue

                    tits = '{0} - {1} [{2}]'.format(data[0]['artist'], data[0]['title'], data[0]['version'])
                    msg += str("▶ " + tits + ' | ' + "%.2f" % float(acc) + '% | ' + player['rank'] + ' | ' + player['pp'] +
                               'pp' + mods + ' \n')

                result = str(msg + '\nThis request took `' + "%.2f" % (
                    time.time() - start_time) + ' seconds` to process.')

            except UnboundLocalError:
                    return str('```Username doesnt exist. Try again.```')
                    # NOTE:- if the result is 'string indices must be integers' that means the API key is wrong
            except TypeError:
                return
            except Exception as e:
                return str(e)
            return result

    async def get_beatmap_info(self, map_tuple):
        """
        This function is used to get beatmap information

        :param map_tuple:
        :return:
        """
        try:
            map_type, map_id = map_tuple
        except TypeError:
            print('Screen shot links are not supported.')
            return

        payload = {"k": self.API_KEY, map_type: map_id}
        url = "https://osu.ppy.sh/api/get_beatmaps"

        try:
            with aiohttp.Timeout(3):
                async with aiohttp.get(url=url, params=payload) as resp:
                    data = await resp.json()
        except asyncio.TimeoutError:
            return "**Error** `The osu! API timed out. Can't display beatmap info.`"
        if resp.status == 200:
            if "error" in data:
                return 'osu!api returned an error: ' + data['error']

            if map_type == 'b':
                for z in data:
                    pp = ""
                    endpoint = "http://bot.tillerino.org:1666/beatmapinfo?"
                    params = {"k": self.Tillerino_Key,
                              "wait": 2000,
                              "beatmapid": map_id,
                              "mods": "0"}
                    try:
                        with aiohttp.Timeout(3):
                            async with aiohttp.get(url=endpoint, params=params) as resp:
                                data_beat_map = await resp.json()
                        if resp.status == 200:
                            pp = ""
                            for entry in data_beat_map['ppForAcc']['entry']:
                                if entry['key'] in [0.95, 0.97, 0.98, 0.985, 0.99, 0.995, 1]:
                                    pp += "`{0}%: {1:.2f}PP` | ".format(str(entry['key'] * 100), float(entry['value']))
                    except asyncio.TimeoutError:
                        pp = ""

                    return "**{0[artist]} - {0[title]}** [{0[version]}] by {0[creator]}\n*Difficulty* : `{1:.2f}` ★ " \
                           "*BPM* : `{0[bpm]}` *Length* : `{2}` \n*AR* : `{0[diff_approach]}` *OD* : `{0[diff_overall]}` " \
                           "*HP* : `{0[diff_drain]}`\n{3}"\
                        .format(z, float(z['difficultyrating']), self.seconds_to_string(z['total_length']), pp)

            if map_type == 's':
                diffs = ''
                for z in data:
                    diffs += '`' + z['version'] + '`, '
                return "**{0[artist]} - {0[title]}** by {0[creator]}\n*BPM* : `{0[bpm]}` *Length* : `{1}` *Favourites* : " \
                       "`{0[favourite_count]}` ♥\n*Difficulties* : {2}\n*Last Updated* : `{0[last_update]}`"\
                    .format(data[0], self.seconds_to_string(data[0]['total_length']), diffs)

    async def setosu(self, message):
        """
        Link osu username against discord account

        :param message:
        :return:
        """
        key = message.content[8:]
        user_id = message.author.id

        cursor = self.db.osu.find({"user_id": str(user_id)})
        if cursor.count() == 0:
            new_record = {"user_id": str(user_id),
                          "user_name": str(key),
                          "last_updated": datetime.datetime.utcnow()}
            self.db.osu.insert_one(new_record)

            await self.ctx.send_message(message.channel,
                                        "**Success**: `{}` is now linked to your Discord account."
                                        .format(str(key)))

        else:
            field = {"user_id": str(user_id)}
            update = {"$set":
                          {"user_name": str(key)},
                      "$currentDate":
                          {"last_updated": {"$type": "date"}}
                      }
            self.db.osu.update_one(field, update)
            await self.ctx.send_message(message.channel,
                                        "**Updated**: `{}` is now linked to your Discord account."
                                        .format(str(key)))

    async def signature_gen(self, message):
        """
        osu@next sig generator

        :param message:
        :return:
        """
        endpoint = "http://lemmmy.pw/osusig/sig.php?"
        chart = {"std": 0,
                 "taiko": 1,
                 "ctb": 2,
                 "mania": 3}
        switch = str(message.content[5:]).split(";", maxsplit=1)
        if len(switch) == 2:
            user = switch[0]
            try:
                mode = chart[str(switch[1]).lower()]
            except KeyError:
                await self.ctx.send_message(message.channel,
                                            "**Error** `Available modes are: std, taiko, mania "
                                            "and ctb.`")
                return
        else:
            await self.ctx.send_message(message.channel, "**Error** `Incorrect usage.`\n"
                                                         "**Usage** `?sig user_name;mode`\n"
                                                         "**Example** `?sig Lapoozza;mania`")
            return
        params = {"colour": "pink",
                  "uname": user,
                  "mode": mode,
                  "pp": "2"}
        try:
            with aiohttp.Timeout(5):
                async with aiohttp.get(url=endpoint, params=params) as resp:
                    data_s = await resp.read()
                fis = io.BytesIO(data_s)
            await self.ctx.send_file(message.channel, fis, filename="sig.png")
        except asyncio.TimeoutError:
            await self.ctx.send_message(message.channel,
                                        "**Error** `Something went horribly wrong. Try again later.`")
            return

    async def osu(self, message):
        """


        :param message:
        :return:
        """
        cont = message.content[5:]
        if str(cont) == '':
            cursor = self.db.osu.find({"user_id": str(message.author.id)})
            if cursor.count() == 0:
                await self.ctx.send_message(message.channel,
                                            "No accounts linked ._. Use `?setosu username` to link.")
            else:
                for docs in cursor:
                    user_name = docs['user_name']
                    await self.ctx.send_message(message.channel, await self.stats(user_name, mode="0"))
        else:
            m = discord.utils.get(message.server.members, display_name=str(cont))
            if not m:
                await self.ctx.send_message(message.channel, "Discord member not found. Make sure you type the "
                                                             "current Discord name only. Also, don't use `@`.")
                return

            cursor = self.db.osu.find({"user_id": str(m.id)})
            if cursor.count() == 0:
                await self.ctx.send_message(message.channel,
                                            "No accounts linked ._. Use `?setosu username` to link.")
            else:
                for docs in cursor:
                    user_name = docs['user_name']
                    await self.ctx.send_message(message.channel, await self.stats(user_name, mode="0"))

    async def taiko(self, message):
        """


        :param message:
        :return:
        """
        cont = message.content[7:]
        if str(cont) == '':
            cursor = self.db.osu.find({"user_id": str(message.author.id)})
            if cursor.count() == 0:
                await self.ctx.send_message(message.channel,
                                            "No accounts linked ._. Use `?setosu username` to link.")
            else:
                for docs in cursor:
                    user_name = docs['user_name']
                    await self.ctx.send_message(message.channel, await self.stats(user_name, mode="1"))
        else:
            m = discord.utils.get(message.server.members, display_name=str(cont))
            if m is None:
                await self.ctx.send_message(message.channel, "Discord member not found. Make sure you type the "
                                                             "current Discord name only. Also, don't use `@`.")
                return

            cursor = self.db.osu.find({"user_id": str(m.id)})
            if cursor.count() == 0:
                await self.ctx.send_message(message.channel,
                                            "No accounts linked ._. Use `?setosu username` to link.")
            else:
                for docs in cursor:
                    user_name = docs['user_name']
                    await self.ctx.send_message(message.channel, await self.stats(user_name, mode="1"))

    async def ctb(self, message):
        """


        :param message:
        :return:
        """
        cont = message.content[5:]
        if str(cont) == '':
            cursor = self.db.osu.find({"user_id": str(message.author.id)})
            if cursor.count() == 0:
                await self.ctx.send_message(message.channel,
                                            "No accounts linked ._. Use `?setosu username` to link.")
            else:
                for docs in cursor:
                    user_name = docs['user_name']
                    await self.ctx.send_message(message.channel, await self.stats(user_name, mode="2"))
        else:
            m = discord.utils.get(message.server.members, display_name=str(cont))
            if m is None:
                await self.ctx.send_message(message.channel, "Discord member not found. Make sure you type the "
                                                             "current Discord name only. Also, don't use `@`.")
                return

            cursor = self.db.osu.find({"user_id": str(m.id)})
            if cursor.count() == 0:
                await self.ctx.send_message(message.channel,
                                            "No accounts linked ._. Use `?setosu username` to link.")
            else:
                for docs in cursor:
                    user_name = docs['user_name']
                    await self.ctx.send_message(message.channel, await self.stats(user_name, mode="2"))

    async def mania(self, message):
        """


        :param message:
        :return:
        """
        cont = message.content[7:]
        if str(cont) == '':
            cursor = self.db.osu.find({"user_id": str(message.author.id)})
            if cursor.count() == 0:
                await self.ctx.send_message(message.channel,
                                            "No accounts linked ._. Use `?setosu username` to link.")
            else:
                for docs in cursor:
                    user_name = docs['user_name']
                    await self.ctx.send_message(message.channel, await self.stats(user_name, mode="3"))
        else:
            m = discord.utils.get(message.server.members, display_name=str(cont))
            if m is None:
                await self.ctx.send_message(message.channel, "Discord member not found. Make sure you type the "
                                                             "current Discord name only. Also, don't use `@`.")
                return

            cursor = self.db.osu.find({"user_id": str(m.id)})
            if cursor.count() == 0:
                await self.ctx.send_message(message.channel,
                                            "No accounts linked ._. Use `?setosu username` to link.")
            else:
                for docs in cursor:
                    user_name = docs['user_name']
                    await self.ctx.send_message(message.channel, await self.stats(user_name, mode="3"))

    async def stats_parser(self, message):
        """


        :param message:
        :return:
        """
        user_name = message.content[7:]
        switch = str(user_name).split(";")
        if len(switch) == 1:
            await self.ctx.send_message(message.channel, "Usage: `;;stats username;mode` "
                                                         "\nExample: `?stats Lapoozza;std`"
                                                         "\nAvailable modes: `std`, `taiko`, `ctb`, `mania` ")
            return

        if switch[1] == "std":
            await self.ctx.send_message(message.channel, await self.stats(switch[0], mode="0"))
            return
        elif switch[1] == "taiko":
            await self.ctx.send_message(message.channel, await self.stats(switch[0], mode="1"))
            return
        elif switch[1] == "ctb":
            await self.ctx.send_message(message.channel, await self.stats(switch[0], mode="2"))
            return
        elif switch[1] == "mania":
            await self.ctx.send_message(message.channel, await self.stats(switch[0], mode="3"))
            return
        else:
            await self.ctx.send_message(message.channel, "Usage: `;;stats username;mode` "
                                                         "\nExample: `?stats Lapoozza;std`"
                                                         "\nAvailable modes: `std`, `taiko`, `ctb`, `mania` ")
            return

    async def top_parser(self, message):
        """

        :param message:
        :return:
        """
        user_name = message.content[5:]
        switch = str(user_name).split(";")
        if len(switch) == 1:
            await self.ctx.send_message(message.channel, "Usage: `;;top username;mode` "
                                                         "\nExample: `?top Lapoozza;std`"
                                                         "\nAvailable modes: `std`, `taiko`, `ctb`, `mania` ")
            return

        if switch[1] == "std":
            await self.ctx.send_message(message.channel, await self.top(switch[0], mode="0"))
            return
        elif switch[1] == "taiko":
            await self.ctx.send_message(message.channel, await self.top(switch[0], mode="1"))
            return
        elif switch[1] == "ctb":
            await self.ctx.send_message(message.channel, await self.top(switch[0], mode="2"))
            return
        elif switch[1] == "mania":
            await self.ctx.send_message(message.channel, await self.top(switch[0], mode="3"))
            return
        else:
            await self.ctx.send_message(message.channel, "Usage: `;;top username;mode` "
                                                         "\nExample: `?top Lapoozza;std`"
                                                         "\nAvailable modes: `std`, `taiko`, `ctb`, `mania` ")
            return

    @staticmethod
    def parse_url(url):
        """
        Returns a tuple of (map_type, map_id) or False if URL is invalid.
        Possible URL formats:
            https://osu.ppy.sh/p/beatmap?b=115891&m=0#
            https://osu.ppy.sh/b/244182
            https://osu.ppy.sh/p/beatmap?s=295480
            https://osu.ppy.sh/s/295480

        :param url:
        :return:
        """
        parsed = urllib.parse.urlparse(url)

        map_type, map_id = None, None
        # if parsed.path.startswith("/u/"):
        #     map_type, map_id = "u", parsed.path[3:]
        if parsed.path.startswith("/b/"):
            map_type, map_id = "b", parsed.path[3:]
        elif parsed.path.startswith("/s/"):
            map_type, map_id = "s", parsed.path[3:]
        elif parsed.path == "/p/beatmap":
            query = urllib.parse.parse_qs(parsed.query)
            if "b" in query:
                map_type, map_id = "b", query["b"][0]
            elif "s" in query:
                map_type, map_id = "s", query["s"][0]
        if map_id is not None and "&" in map_id:
            map_id = map_id[:map_id.index("&")]
        if map_type and map_id:
            return map_type, map_id
        return False

    async def parse_message(self, message):
        """
        Scans a message(plain text) for osu.ppy.sh links
        and returns Beatmap/User statistics.
        Returns `False` if no valid links exist in the message.


        :param message: The text content of the message
        :return:
        """
        if 'osu.ppy.sh' not in message.content:
            return

        reply = ''
        for z in self.get_links(message.content):
            try:
                reply += await self.get_beatmap_info(self.parse_url(z))
                reply += "\n\n"
            except TypeError:
                pass

        if reply:
            await self.ctx.send_message(message.channel, reply.strip())

    def get_links(self, message):
        """
        Returns a list of all osu! URLs from a message.

        :param message:
        """
        return [z for z in self.URL_REGEX.findall(message)]

    @staticmethod
    def seconds_to_string(seconds):
        """
        Returns a m:ss representation of a time in seconds.

        :param seconds:
        """
        return "{0}:{1:0>2}".format(*divmod(int(seconds), 60))
