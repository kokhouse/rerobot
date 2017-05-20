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
import re

db = mongo_manager.mongo_db.db
red = redis_manager.redis_manager.redis

async def fuck(ctx, message):
    """
    Fun with swearing

    :param ctx:
    :param message:
    :return:
    """
    a = message.content[6:]
    f_dict = {1: "***Fuck off, {}.***\n - {}",
              2: "***Fuck you, {}.***\n - {}",
              3: "'***{}, go and take a flying fuck at a rolling donut.***\n - {}",
              4: "***{}, Thou clay-brained guts, thou knotty-pated fool, thou whoreson obscene "
                 "greasy tallow-catch!***\n - {}",
              5: "***{}, there aren't enough swear-words in the English language, so now I'll have to call you "
                 "perkeleen vittupää just to express my disgust and frustration with this crap.***\n - {}",
              6: "***Oh fuck off, just really fuck off you total dickface. "
                 "Christ {}, you are fucking thick.***\n - {}",
              7: "***Fuck me gently with a chainsaw, {}. Do I look like Mother Teresa?***\n - {}",
              8: "***{}, why don't you go outside and play hide-and-go-fuck-yourself?***\n - {}",
              9: "***Fuck {}   ͡° ͜ʖ ͡°.***\n - {}",
              10: "***Fuck you very much {}.***\n - {}",
              11: "***Fascinating story, {}. In what chapter do you shut the fuck up?***\n - {}"
              }
    r = random.randint(1, 11)
    await ctx.send_message(message.channel, str(f_dict[r]).format(a, message.author.name))

async def rip(ctx, message):
    """
    Generates a link to http://ripme.xyz/

    :param ctx:
    :param message:
    :return:
    """
    ctx.usage_track['user'] += 1
    ctx.usage_track['RIP'] += 1

    cont = message.content[5:]
    cont_s = str(cont).rstrip()
    cont_safe = cont_s.replace(" ", "%20")

    name = message.author.name
    name_safe = name.replace(" ", "%20")
    men = message.mentions
    if men:
        await ctx.send_message(message.channel, "(◡‿◡✿) too lazy to RIP...")
        return

    if cont_s == "":
        await ctx.send_message(message.channel, "¯\_(ツ)_/¯ RIP you!!!")
        return
    elif cont_s == "me":
        await ctx.send_message(message.channel, "http://ripme.xyz/{}".format(name_safe))
        return
    else:
        await ctx.send_message(message.channel, "http://ripme.xyz/{}".format(cont_safe))
        return

async def memes(ctx, message, meme_type: str="lenny"):
    """
    Shows a lenny face

    :param meme_type:
    :param ctx:
    :param message:
    :return:
    """
    if meme_type == "lenny":
        await ctx.send_message(message.channel, "( ͡° ͜ʖ ͡°)")
    if meme_type == 'lewd':
        r = random.randint(0, 7)
        choice = {0: "./static/lewd.png",
                  1: "./static/lewd1.png",
                  2: "./static/lewd2.jpg",
                  3: "./static/lewd3.png",
                  4: "./static/lewd4.gif",
                  5: "./static/lewd5.png",
                  6: "./static/lewd6.gif",
                  7: "./static/lewd7.gif"}
        await ctx.send_file(destination=message.channel, fp=choice[r], filename='lewd.png')

    if meme_type == 'pogchamp':
        await ctx.send_file(destination=message.channel, fp='./static/pogchamp.png', filename='pogchamp.png')

    if meme_type =='opieop':
        await ctx.send_file(destination=message.channel, fp='./static/opieop.png', filename='opieop.png')

    if meme_type == 'wolfiesgame':
        await ctx.send_file(destination=message.channel, fp='./static/wolfiesgame.png', filename='wolfiesgame.png')

    if meme_type == 'megunuke':
        await ctx.send_file(destination=message.channel, fp='./static/megunuke.jpg', filename='megunuke.jpg')

    if meme_type == 'kappa':
        await ctx.send_file(destination=message.channel, fp='./static/kappa.png', filename='kappa.png')

    if meme_type == 'feelsbadman':
        await ctx.send_file(destination=message.channel, fp='./static/feelsbadman.png', filename='feelsbadman.png')

    if meme_type == 'feelsgoodman':
        await ctx.send_file(destination=message.channel, fp='./static/feelsgoodman.png', filename='feelsgoodman.png')

    if meme_type == 'rero':
        await ctx.send_file(destination=message.channel, fp='./static/rero.png', filename='rero.png')

async def urban_dictionary(ctx, message):
    """
    Fetches Urban Dictionary Definitions

    :param ctx:
    :param message:
    :return:
    """
    word = message.content[4:]
    word_clean = str(word).replace(" ", "+")
    endpoint = "http://api.urbandictionary.com/v0/define?term={}".format(word_clean)
    # r = requests.get(endpoint)
    # data = r.json()
    with aiohttp.ClientSession() as session:
        async with session.get(url=endpoint) as resp:
            data = await resp.read()
    r = json.loads(data.decode("utf-8"))

    if r['result_type'] == "no_results":
        await ctx.send_message(message.channel, "No results found for: `{}`".format(word_clean))
    else:
        defi = r['list'][0]['definition']
        th_up = r['list'][0]['thumbs_up']
        th_down = r['list'][0]['thumbs_down']
        example = r['list'][0]['example']

        char_limit = len(defi) + len(str(th_up)) + len(str(th_down)) + len(example)
        if char_limit < 1900:
            ret_str = "**{}**" \
                      "\n*Definition*: ```{}```" \
                      "\n*Example*: ```{}```" \
                      "\n*Votes*: `{}` :thumbsup:  `{}` :thumbsdown:" \
                .format(str(word), defi, example, str(th_up), str(th_down))

            await ctx.send_message(message.channel, ret_str)
        else:
            endpoint = "http://hastebin.com/documents"
            headers = {"Content-Type": "text/plain",
                       "User-Agent": "Rero by Lapoozza (https://github.com/lapoozza/rero)"}
            defi_trim = re.sub("(.{100})", "\\1\n", defi, 0, re.DOTALL)
            example_trim = re.sub("(.{100})", "\\1\n", example, 0, re.DOTALL)
            data = "{}" \
                   "\nDefinition: {}" \
                   "\nExample: {}" \
                   "\nVotes: {} :thumbsup: {} :thumbsdown:" \
                .format(str(word), defi_trim, example_trim, str(th_up), str(th_down))

            with aiohttp.ClientSession() as session:
                async with session.post(url=endpoint, data=data, headers=headers) as resp:
                    data = await resp.read()

            r = json.loads(data.decode("utf-8"))
            template = "The message is quite big. So I made a hastebin paste: http://hastebin.com/{}" \
                       "\n*Click the link to view content.*" \
                .format(r['key'])
            await ctx.send_message(message.channel, template)

async def quotes(ctx, message):
    """
    Returns a random smart quote

    :param ctx:
    :param message:
    :return:
    """
    a = random.randint(1, 11)
    quot = {1: "*It Doesn’t Matter Where You Came From. All That Matters Is Where You Are Going.*",
            2: "*Think Big And Don’t Listen To People Who Tell You It Can’t Be Done. "
               "Life’s Too Short To Think Small.*",
            3: "*You Can Develop Any Habit Or Thought Or Behavior That You Consider Desirable Or Necessary.*",
            4: "*We Become What We Think About.*",
            5: "*A Clear Vision, Backed By Definite Plans, Gives You A Tremendous Feeling Of Confidence And "
               "Personal Power.*",
            6: "*The Person Who Says It Cannot Be Done Should Not Interrupt The Person Who Is Doing It.*",
            7: "*Everything You’ve Ever Wanted Is On The Other Side Of Fear.*",
            8: "*Success Is Getting What You Want, Happiness Is Wanting What You Get.*",
            9: "*Your Life Only Gets Better When You Get Better.*",
            10: "*Think Continually About What You Want, Not About The Things You Fear.*",
            11: "*Don't trouble trouble until trouble troubles you.*"}

    await ctx.send_message(message.channel, quot[a])

async def eightball(ctx, message):
    """
    8ball game. Ask any question to rero and it gives a randomly selected answer is given.

    :param ctx: An instance of rero is passed onto this function.
    :param message: The message object while this function was called.

    :return: Randomly generated answer
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
    await ctx.send_message(message.channel, responses[rand])
