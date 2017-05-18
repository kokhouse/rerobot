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
import pymongo
import yaml


class MongoDB(object):
    """
    MongoDB connection manager
    """
    def __init__(self):
        # Lets get the REDIS password
        with open("config/settings.yaml") as file:
            settings_file = file.read()
        file.close()
        settings = yaml.load(settings_file)

        self.connection = pymongo.MongoClient(settings['VPS_IP_ADDRESS'])

        # We initialize 4 cursors because we don't
        # want to get slowed down for other db uses
        # while logging messages.
        self.db = self.connection[settings['MONGO_DATABASE_NAME']]
        self.db.authenticate(settings['MONGO_USER_NAME'], settings['MONGO_PASSWORD'])
        self.db_ranking = self.connection[settings['MONGO_DATABASE_NAME']]
        self.db_ranking.authenticate(settings['MONGO_USER_NAME'], settings['MONGO_PASSWORD'])
        self.db_events = self.connection[settings['MONGO_DATABASE_NAME']]
        self.db_events.authenticate(settings['MONGO_USER_NAME'], settings['MONGO_PASSWORD'])
        self.db_messages = self.connection[settings['MONGO_DATABASE_NAME']]
        self.db_messages.authenticate(settings['MONGO_USER_NAME'], settings['MONGO_PASSWORD'])

mongo_db = MongoDB()
