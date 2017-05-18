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
import redis
import yaml


class RedisManager(object):
    """
    REDIS connection manager
    """
    def __init__(self):

        # Lets get the REDIS password
        with open("config/settings.yaml") as file:
            settings_file = file.read()
        file.close()
        settings = yaml.load(settings_file)

        # Connect to redis etc
        self.redis = redis.StrictRedis(
            host=settings['VPS_IP_ADDRESS'],
            port=6379,
            db=0,
            password=settings['REDIS_PASSWORD'])


redis_manager = RedisManager()
