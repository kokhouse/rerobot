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
import random
import json
import aiohttp
import yaml


class Imgur:
    """
    Rero's Custom Imgur Async Library
    """
    __author__ = "Luxory#0018"
    __version__ = "0.0.1-beta-1"

    def __init__(self, context):
        super().__init__()
        self.ctx = context
        self.redis = redis_manager.redis_manager.redis
        self.db = mongo_manager.mongo_db.db
        self.sr_per_minute = 5

        with open("config/settings.yaml") as file:
            settings_file = file.read()
        file.close()
        settings = yaml.load(settings_file)
        self.headers = {"Authorization": "Client-ID {}".format(settings['IMGUR_CLIENT_ID'])}
        self.endpoint = "https://api.imgur.com/3/gallery/r/{}"
        del settings

    def check_nsfw_status(self, server_id: str):
        """
        Returns the NSFW status of the current server

        :param server_id:
        :return:
        """
        cursor = self.db.server_backend.find({"serv_id": server_id})
        for c in cursor:
            nsfw_status = c['nsfw']['nsfw_status']
            nsfw_chan_id = c['nsfw']['nsfw_chan_id']
            return nsfw_status, nsfw_chan_id

    async def request_imgur(self, subreddit):
        """

        :param subreddit:
        :return:
        """
        try:
            with aiohttp.ClientSession() as session:
                async with session.get(url=self.endpoint.format(subreddit), headers=self.headers) as response:
                    data = await response.json()

            self.redis.set("imgur_remain", str(response.headers['X-RATELIMIT-CLIENTREMAINING']))
            self.redis.set("imgur_limit", str(response.headers['X-RATELIMIT-CLIENTLIMIT']))
            self.redis.set("imgur_reset", str(response.headers['X-RATELIMIT-USERRESET']))
            self.redis.set("rero_remain", str(response.headers['X-RATELIMIT-USERREMAINING']))
            self.redis.set("rero_limit", str(response.headers['X-RATELIMIT-USERLIMIT']))

            if int(self.redis.get("rero_remain")) < 5:
                return False, "**Info**: API limit reached. Use this command again after 1 hour."

            if int(self.redis.get("imgur_remain")) < 100:
                return False, "**Warning** Can't do any more searches for some time (try after 5-10 mins)"

            return True, data
        except KeyError:
            return False, "**Error**: `JSON response missing a header. Please retry.`"
        except json.JSONDecodeError:
            return False, "**Error**: `couldn't decode JSON response. Please retry.`"

    async def sub_reddit_parser(self, message):
        """
        Handles the rate limits and returns images

        :param message:
        :return:
        """
        user_id = message.author.id
        server_id = message.server.id
        channel_id = message.channel.id
        if self.redis.exists(user_id):
            quota = int(self.redis.get(user_id))
            ttl = int(self.redis.ttl(user_id))
            if ttl > -1 and quota < self.sr_per_minute:
                sub = message.content[4:]
                link = await self.reddit_scrapper(sub, server_id, channel_id)
                self.redis.incr(user_id, amount=1)
                await self.ctx.send_message(message.channel, link)

            elif ttl > -1 and quota == self.sr_per_minute:
                await self.ctx.send_message(message.channel, "{},  please send *{}* `?sr` requests per min."
                                            .format(message.author.mention, str(self.sr_per_minute)))
            elif ttl == -1:
                self.redis.delete(user_id)
                self.redis.setex(user_id, 60, "1")
                sub = message.content[4:]
                link = await self.reddit_scrapper(sub, server_id, channel_id)
                await self.ctx.send_message(message.channel, link)

        else:
            self.redis.setex(user_id, 60, "1")
            sub = message.content[4:]
            link = await self.reddit_scrapper(sub, server_id, channel_id)
            await self.ctx.send_message(message.channel, link)

    async def reddit_scrapper(self, subreddit, server_id, ch_id):
        """

        :param ch_id:
        :param server_id:
        :param subreddit:
        :return:
        """
        cursor = self.db.server_backend.find({"serv_id": str(server_id)})
        for c in cursor:
            nsfw_status = c['nsfw']['nsfw_status']
            nsfw_chan_id = c['nsfw']['nsfw_chan_id']
            if nsfw_status == "on|global":
                status, data = await self.request_imgur(subreddit)
                if not status:
                    return data

                if data['status'] == 200:
                    items = data['data']
                    store = []
                    for item in items:
                        store.append(item['link'])
                    size = len(store)
                    if size == 0:
                        return "**Error**: subreddit `{}` returned 0 results. Try again.".format(subreddit)
                    max_range = size - 1
                    try:
                        x = random.randint(0, max_range)
                        return store[x]
                    except ValueError:
                        return "**Error**: subreddit `{}` could not be retrieved. Try again.".format(subreddit)
                else:
                    return "**Error**: Oops! something went wrong"

            elif nsfw_chan_id == ch_id:
                status, data = await self.request_imgur(subreddit)
                if not status:
                    return data

                if data['status'] == 200:
                    items = data['data']
                    store = []
                    for item in items:
                        store.append(item['link'])
                    size = len(store)
                    if size == 0:
                        return "**Error**: subreddit `{}` returned 0 results. Try again.".format(subreddit)
                    max_range = size - 1
                    try:
                        x = random.randint(0, max_range)
                        return store[x]
                    except ValueError:
                        return "**Error**: subreddit `{}` could not be retrieved. Try again.".format(subreddit)
                else:
                    return "**Error**: Oops! something went wrong"

            else:
                is_nsfw = self.redis.exists(str(subreddit).lower())
                if is_nsfw == 1:
                    return "**NSFW** content. Try searching something else."

                status, data = await self.request_imgur(subreddit)
                if not status:
                    return data

                if data['status'] == 200:
                    items = data['data']
                    store = []
                    for item in items:
                        if item['nsfw']:
                            self.redis.set(subreddit, "NSFW")
                            return "**NSFW** content. Try searching something else."
                        store.append(item['link'])
                    size = len(store)
                    if size == 0:
                        return "**Error**: subreddit `{}` returned 0 results. Try again.".format(subreddit)
                    max_range = size - 1
                    try:
                        x = random.randint(0, max_range)
                        return store[x]
                    except ValueError:
                        return "**Error**: subreddit `{}` could not be retrieved. Try again.".format(subreddit)
                else:
                    return "**Error**: Oops! something went wrong"

        # If the MongoDB flags don't exist, then we assume
        # that NSFW is disabled.
        is_nsfw = self.redis.exists(str(subreddit).lower())
        if is_nsfw == 1:
            return "**NSFW** content. Try searching something else."
        status, data = await self.request_imgur(subreddit)
        if not status:
            return data
        if data['status'] == 200:
            items = data['data']
            store = []
            for item in items:
                if item['nsfw']:
                    return "**NSFW** content. Try searching something else."
                store.append(item['link'])
            size = len(store)
            if size == 0:
                return "**Error**: subreddit `{}` returned 0 results. Try again.".format(subreddit)
            max_range = size - 1
            try:
                x = random.randint(0, max_range)
                return store[x]
            except ValueError:
                return "**Error**: subreddit `{}` could not be retrieved. Try again.".format(subreddit)
        else:
            return "**Error**: Oops! something went wrong"
