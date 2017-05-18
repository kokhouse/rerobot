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
from Rero import rero
import yaml
import logging

with open("config/settings.yaml") as file:
    settings_file = file.read()
file.close()
settings = yaml.load(settings_file)

shard_id = 0
bot = rero.Rero(prefix=settings['PREFIX'],
                      shard_id=shard_id,
                      shard_count=3)

# Logging to save our ass in terms of
# emergencies :v
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='logs/discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

bot.run(settings['BOT_TOKEN'])
