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


class Emojis:
    """
    Emojis Module
    """
    def __init__(self, context):
        super().__init__()
        self.ctx = context

    # TODO: re-add the fetch parameter
    def get_all_client_emojis(self):
        """
        Gets all emojis that the client can see
        :return whatever they asked for of all the emojis
        """
        return "\n".join([x.fetch for x in self.ctx.get_all_emojis()])

    @staticmethod
    def get_current_server_emojis(message):
        """
        Gets the emojis of the current server
        :returns a joined list of the current emojis for this server
        """
        return ", ".join([x.name for x in message.server.emojis])
