#!./env/bin/python3.11

import discord
from discord.ext import commands
import os
import logging
import traceback

# ----------------------LOGGING-Config--------------------#
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
formatter = logging.Formatter("%(asctime)s:%(created)f:%(filename)s:%(levelname)s:%(funcName)s:%(message)s")
file_handler = logging.FileHandler(os.path.abspath(f"LOGS/{__name__}.log"))
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
# --------------------------------------------------------#


TOKEN = os.environ.get("PAPERBOT")
intents = discord.Intents.all()

bot = commands.Bot(intents=intents)
bot.remove_command("help")


@bot.event
async def on_ready():
    logger.info(f"{bot.user} is ready and online!")
    print(f"{bot.user} is ready and online!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/help"))


@bot.event
async def on_application_command_error(ctx, error):
    assert bot.user
    if isinstance(error, commands.CommandOnCooldown):
        pass
    elif isinstance(error, commands.errors.MissingPermissions):
        pass
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send_response(f"this command should be used in server not in Dms")
    elif isinstance(error, commands.NotOwner):
        await ctx.send_response(f"You are {bot.user.mention}'s owner, only bot owner can run this command.", ephemeral=True)
    else:
        logger.exception('\n' + ''.join(traceback.format_exception(error)))
        raise error

print("loading cogs...")
for filename in os.listdir("./Cogs"):
    if filename.endswith(".py"):
        try:
            bot.load_extension("Cogs." + filename[:-3])
            print(f"{filename} is loaded.")
        except Exception as e:
            logger.exception(e)
            raise e

bot.run(TOKEN)
