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
import random


class Games:
    """
    Handles the Games
    """
    def __init__(self, context):
        super().__init__()
        self.ctx = context

    async def roll(self, message):
        """
        Roll game

        :param message:
        :return:
        """
        cont = message.content[6:]
        try:
            if int(cont) >= 0:
                b = random.randint(0, int(cont))
                await self.ctx.send_message(message.channel,
                                            "{} `rolls '{}'`".format(message.author.mention, str(b)))
            elif int(cont) < 0:
                await self.ctx.send_message(message.channel, "Please enter a positive number.")
            else:
                b = random.randint(0, 100)
                await self.ctx.send_message(message.channel,
                                            "{} `rolls '{}'`".format(message.author.mention, str(b)))
        except ValueError:
            b = random.randint(0, 100)
            await self.ctx.send_message(message.channel,
                                        "{} `rolls '{}'`".format(message.author.mention, str(b)))
        except TypeError:
            b = random.randint(0, 100)
            await self.ctx.send_message(message.channel,
                                        "{} `rolls '{}'`".format(message.author.mention, str(b)))

    async def toss(self, message):
        """
        Toss game

        :param message:
        :return:
        """
        a = random.randint(0, 1)
        choice = {0: "Heads",
                  1: "Tails"}
        await self.ctx.send_message(message.channel, "{} `tosses the coin and it lands on: '{}'`"
                                    .format(message.author.mention, choice[a]))

    async def choose(self, message):
        """
        Choose game

        :param message:
        :return:
        """
        cont = message.content[8:]
        a = str(cont).split('|')
        num = len(a)
        strs = ""
        i = 0
        decs = random.randint(0, int(num - 1))

        for k in a:
            if i == 0:
                l = str(k).lstrip()
                r = str(l).rstrip()
                strs += r
                i += 1
            elif i == len(a) - 1:
                l = str(k).lstrip()
                r = str(l).rstrip()
                strs += " and " + r
            else:
                l = str(k).lstrip()
                r = str(l).rstrip()
                strs += ", " + r
                i += 1

        res = a[decs]

        await self.ctx.send_message(message.channel, "`Between {} >> {} chooses '{}'` :ok_hand:"
                                    .format(strs, message.author.display_name, res))

    async def guess(self, message):
        """
        Number guessing game.

        :param self: An instance of rero is passed onto this function.
        :param message: The message object while this function was called.

        :type self: discord.Client()
        :type message: discord.Message()

        :return: This function returns nothing.
        """
        await self.ctx.send_message(message.channel, 'Guess a number between 1 to 10')

        def guess_check(m1):
            """

            :param m1:
            :return:
            """
            return m1.content.isdigit()

        guesst = await self.ctx.wait_for_message(timeout=5.0, author=message.author, check=guess_check)
        answer = random.randint(1, 10)
        if guesst is None:
            fmt = 'Sorry, you took too long. It was {}.'
            await self.ctx.send_message(message.channel, fmt.format(answer))
            return
        if int(guesst.content) == answer:
            await self.ctx.send_message(message.channel, 'You are right!')
        else:
            await self.ctx.send_message(message.channel, 'Sorry. It is actually {}.'.format(answer))

    async def eightball(self, message):
        """
        8ball game. Ask any question to rero and it gives a randomly selected answer is given.

        :param self: An instance of rero is passed onto this function.
        :param message: The message object while this function was called.

        :type self: discord.Client()
        :type message: discord.Message()

        :return: Randomly generated answer
        :rtype: str
        """

        responses = [
            "It is certain  ͡° ͜ʖ ͡°",
            "It is decidedly so",
            "Without a doubt",
            "Yes, definitely :thumbsup:",
            "You may rely on it",
            "As I see it, yes",
            "Most likely",
            "Outlook good",
            "Yes",
            "Signs point to yes",
            "Reply hazy try again",
            "Ask again later",
            "Better not tell you now",
            "Cannot predict now",
            "Concentrate and ask again",
            "Don't count on it",
            "My reply is no",
            "My sources say no",
            "Outlook not so good",
            "Very doubtful"
        ]

        maxnum = len(responses) - 1
        rand = random.randint(0, maxnum)
        await self.send_message(message.channel, responses[rand])


class RPS:
    """
    Rock Paper Scissors vs AI module

    The rock, paper and scissors images are displayed using Discord's built in emoticons.
    :fist: -> Rock
    :page_facing_up: -> Paper
    :scissors: -> Scissors
    """
    rero_instance = None
    message = None

    def __init__(self, author, author_id):
        self.player_choice = ''
        self.comp_choice = ''
        self.bot_name = 'AI'
        self.Rock = ':fist:'
        self.Paper = ':page_facing_up:'
        self.Scissors = ':scissors:'

        self.id = str(author_id)
        self.name = str(author)

    async def main(self):
        """
        Main function
        """
        await self.rero_instance.send_message(self.message.channel, self.message.author.mention +
                                              '\n***Rock, Paper and Scissors (vs AI)***')
        # call the user's guess function
        number = await self.user_guess()
        # call the computer's number function
        num = self.computer_number()
        # call the results function
        await self.results(num, number)

    def computer_number(self):
        """
        computer_number function
        get a random number in the range of 1 through 3

        :return:
        """
        num = random.randrange(1, 4)
        # if/elif statement
        if num == 1:
            self.comp_choice = self.Rock
        elif num == 2:
            self.comp_choice = self.Paper
        elif num == 3:
            self.comp_choice = self.Scissors
        # return the number
        return num

    async def user_guess(self):
        """
        get first guess
        :return:
        """
        await self.rero_instance.send_message(self.message.channel, self.message.author.mention +
                                              ' what is your choice? ( Enter: **r** or **p** or **s** )'
                                              '\n**r**: {}\n**p**: {}\n**s**: {}'
                                              .format(self.Rock, self.Paper, self.Scissors))
        guess = await self.rero_instance.wait_for_message(author=self.message.author, timeout=30)
        if guess is None:
            await self.rero_instance.send_message(self.message.channel,
                                                  "You took to long. Exiting game. Please restart.")
            return
        g_lower = str(guess.content).lower()
        # If that guess is invalid, loop until we get a valid guess.
        while g_lower not in ('r', 'p', 's'):
            await self.rero_instance.send_message(
                self.message.channel,
                self.message.author.mention +
                ' *invalid choice*. What is your choice?\n**r**: {}\n**p**: {}\n**s**: {}'.
                format(self.Rock, self.Paper, self.Scissors))
            guess = await self.rero_instance.wait_for_message(author=self.message.author, timeout=30)
            if guess is None:
                await self.rero_instance.send_message(self.message.channel,
                                                      "You took to long. Exiting game. Please restart.")
                return
            g_lower = str(guess.content).lower()

        # Now assign the (valid!) guess a number
        # This dictionary is just shorthand for your if/elif chain.
        guess_table = {
            'r': 1,
            'p': 2,
            's': 3
        }
        icon_table = {
            'r': self.Rock,
            'p': self.Paper,
            's': self.Scissors
        }
        self.player_choice = icon_table[g_lower]
        # Return the number associated with the guess.
        return guess_table[g_lower]

    async def restart(self):
        """
        Restart
        """
        await self.rero_instance.send_message(self.message.channel, self.message.author.mention +
                                              '\nWould you like to play again? (y/n)')
        answer = await self.rero_instance.wait_for_message(author=self.message.author, timeout=30)
        if answer is None:
            await self.rero_instance.send_message(self.message.channel,
                                                  "You took to long. Exiting game. Please restart.")
            return
        try:
            ans_l = str(answer.content).lower()
        except Exception as e:
            # print(e)
            await self.rero_instance.send_message(self.message.channel, self.message.author.mention +
                                                  '\nThanks for playing. \nCome play again soon!')
            return
        # if/elif statement
        if ans_l == 'y':
            await self.main()
        else:
            await self.rero_instance.send_message(self.message.channel, self.message.author.mention +
                                                  '\nThanks for playing. \nCome play again soon!')
            return

    async def results(self, num, number):
        """
        results function
        find the difference in the two numbers

        :param num:
        :param number:
        """
        difference = num - number
        await self.rero_instance.send_message(self.message.channel, self.message.author.mention + '\nYou: {} vs AI: {}'
                                              .format(self.player_choice, self.comp_choice))
        # if/elif statement
        if difference == 0:
            await self.rero_instance.send_message(self.message.channel, self.message.author.mention + '\n**TIE**')
            # Update Player DB
            await self.restart()
        elif difference % 3 == 1:
            await self.rero_instance.send_message(self.message.channel, self.message.author.mention + '**\nYou Lost**')
            await self.restart()
        elif difference % 3 == 2:
            await self.rero_instance.send_message(self.message.channel, self.message.author.mention + '\n**You Won**')
            await self.restart()
