#!./env/bin/python3.11
import discord
from discord.ext import commands, tasks
import database
import patreon
import os
import time
from handy import *

Patreon_color = 0xf96854


# ----------------------LOGGING-Config--------------------#
import logging
import traceback

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
formatter = logging.Formatter("%(asctime)s:%(created)f:%(filename)s:%(levelname)s:%(funcName)s:%(lineno)d:%(message)s")
file_handler = logging.FileHandler(os.path.abspath(f"LOGS/{__name__}.log"))
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def make_log(function):
    def make_log_wrap(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            logger.exception(f"{e} : args {args}, kwargs {kwargs}\n{''.join(traceback.format_exception(e))}")
    return make_log_wrap

# --------------------------------------------------------#


class Patreon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("Creating patreon client")
        PATREON_TOKEN = os.environ.get("PATREON")
        assert PATREON_TOKEN
        self.patreon_client = patreon.API(PATREON_TOKEN)
        campaing_response = self.patreon_client.fetch_campaign()
        self.campaign_id = campaing_response.data()[0].id()

    async def get_all_patreon(self):
        patreon_data = []
        all_pledges = []
        cursor = None
        while True:
            pledges_response = self.patreon_client.fetch_page_of_pledges(self.campaign_id, 25, cursor=cursor, fields={'pledge': ['amount_cents', 'declined_since', 'total_historical_amount_cents', 'status', 'created_at'], 'reward': ['amount', 'title'], })
            all_pledges += pledges_response.data()
            cursor = self.patreon_client.extract_cursor(pledges_response)
            if not cursor:
                break

        for pledge in all_pledges:
            try:
                patreon_data.append({
                    'email': pledge.relationship('patron').attributes()['email'],
                    'discord': int(pledge.relationship('patron').attributes()['social_connections']['discord']['user_id']) if pledge.relationship('patron').attributes()['social_connections']['discord'] is not None else None,
                    'pledge_amount': pledge.attributes()['amount_cents'],
                    'pledge_created_at': pledge.attributes()['created_at'],
                    'status': pledge.attributes()['status'],  # (valid, declined, pending, disabled)
                    'declined_since': pledge.attributes()['declined_since'],
                    'total_historical_amount_cents': pledge.attributes()['total_historical_amount_cents'],
                    'tier_amount': pledge.relationship('reward').attributes()['amount'],
                    'tier_title': pledge.relationship('reward').attributes()['title']
                })
            except Exception as error:
                logger.exception(error)
        return patreon_data

    @tasks.loop(seconds=86400)  # everyday
    async def update_patreon_databese(self):
        logger.info("updating patreon database")
        patreon_data = await self.get_all_patreon()
        patreon_data = [x for x in patreon_data if x['discord'] is not None]

        for patron in patreon_data:
            patron_old = await database.get_patreon(patron['discord'])
            if patron_old is not None:
                amount = patron['total_historical_amount_cents'] - patron_old['total_historical_amount']
                await database.add_credit(patron['discord'], calculate_credit(amount))
                await database.update_patreon(patron)
            else:
                await database.insert_patreon(patron)

    @commands.Cog.listener()
    async def on_ready(self):
        self.update_patreon_databese.start()

    @discord.slash_command(name="patreon", description=f"Link your Patreon Subscription with the bot.")
    @commands.cooldown(6, 60 * 60 * 24, commands.BucketType.user)
    async def patreon(self, ctx: discord.ApplicationContext):
        searching_embed = discord.Embed(description="I am searching for your Patreon subscription. This could take a while.", color=Patreon_color)
        subscription_not_found = discord.Embed(description=f"I did't find your Patreon subscription.\nMake sure your **Discord account is linked to your Patreon account,** then try again.", color=discord.Color.red())
        subscription_not_found.set_author(name="Patreon", url="https://www.patreon.com/DiscordPaperBot",
                             icon_url="https://global.discourse-cdn.com/standard10/uploads/patreondevelopers/original/1X/f322686dafa6d6d5f6de4ba9f0648fe930f904f6.png")

        def patreon_status(patreon: dict) -> discord.Embed:
            response = {
                'valid': f"Your Patreon subscription is linked with the bot. Thank you so much for suporting me, enjoy your perks.\n**Tier**\n> {patreon['tier_title']}",
                'declined': f"Your Patreon subscription status is **Declined** Please validate your patreon subscription and try again",
                'pending': f"Your Patreon subscription status is **Pending** Please validate your patreon subscription and try again",
                'disabled': f"Your Patreon subscription status is **Disabled** Please validate your patreon subscription and try again",
            }
            embed = discord.Embed(description=response[patreon['status']], color=Patreon_color)
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1018529603901468803.gif" if patreon["status"] == 'valid' else "https://cdn.discordapp.com/emojis/797493957931434044.gif")
            embed.set_author(name="Patreon", url="https://www.patreon.com/DiscordPaperBot",
                             icon_url="https://global.discourse-cdn.com/standard10/uploads/patreondevelopers/original/1X/f322686dafa6d6d5f6de4ba9f0648fe930f904f6.png")
            return embed

        m = await ctx.send_response(embed=searching_embed)
        patreon_data = await self.get_all_patreon()
        for patron in patreon_data:
            if patron['discord'] == ctx.author.id:
                patron_old = await database.get_patreon(patron['discord'])
                if patron_old is not None:
                    amount = patron['total_historical_amount_cents'] - patron_old['total_historical_amount']
                    await database.add_credit(patron['discord'], calculate_credit(amount))
                    await database.update_patreon(patron)
                else:
                    await database.insert_patreon(patron)
                await m.edit_original_response(embed=patreon_status(patron))
        await m.edit_original_response(embed=subscription_not_found)

    @patreon.error
    async def patreon_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(description=f"you are on cooldown try again <t:{int(error.retry_after + time.time())}:R> :timer:", color=discord.Colour.embed_background())
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
            await ctx.send_response(embed=embed)
        else:
            logger.exception(error)
            raise(error)


def setup(bot):
    bot.add_cog(Patreon(bot))
