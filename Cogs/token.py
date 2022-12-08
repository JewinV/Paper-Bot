#!./env/bin/python3.11
import discord
from discord.ext import commands
from discord.ui import View, Modal, InputText
import database
import os


# ----------------------LOGGING-Config--------------------#
import logging
import traceback

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
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


class Token(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="replicate_token", description="Use your replicate token to generate images", guild_ids=[1014935887383101612])
    async def replicate_token(self, ctx: discord.ApplicationContext):
        token = await database.get_token(ctx.author.id)
        no_token_embed = discord.Embed(title="Replicate Token", description=f"{self.bot.user.display_name} does not have your ***replicate token*** to generate images for you.", color=discord.Color.embed_background())

        class GetToken(Modal):
            def __init__(self, ctx, bot):
                super().__init__(title="Replicate Token")
                self.ctx = ctx
                self.bot = bot
                self.add_item(InputText(label="Enter your Replicate Token", max_length=40, min_length=40, required=True))

            async def callback(self, interaction):
                token = self.children[0].value
                if token is not None:
                    token_added_embed = discord.Embed(title="Replicate Token", description=f"{self.bot.user.display_name} will use this token to generate images for {ctx.author.mention}\n> ***||{token}||***", color=discord.Color.green())
                    await database.insert_token(self.ctx.author.id, token)
                    await interaction.response.defer()
                    await self.ctx.edit(embed=token_added_embed, view=None)

        class TokenView(View):
            def __init__(self, bot):
                super().__init__(disable_on_timeout=True)
                self.bot = bot

            @discord.ui.button(label="Add Token" if token is None else "Edit Token", style=discord.ButtonStyle.green)
            async def on_add_edit(self, button, interaction: discord.Interaction):
                modal = GetToken(ctx, self.bot)
                await interaction.response.send_modal(modal)

            @discord.ui.button(label="Remove Token", style=discord.ButtonStyle.red, disabled=token is None)
            async def on_remove(self, button, interaction):
                token_removed_embed = discord.Embed(title="Replicate Token", description=f"{self.bot.user.display_name} removed your ***Replicate Token*** from database", color=discord.Color.green())
                await database.remove_token(ctx.author.id)
                await ctx.edit(embed=token_removed_embed, view=None)

        view = TokenView(self.bot)
        if token is None:
            await ctx.send_response(embed=no_token_embed, ephemeral=True, view=view)
        else:
            token = token["replicate_token"]
            has_token_embed = discord.Embed(title="Replicate Token", description=f"Your Replicate Token : ***||{token}||***")
            await ctx.send_response(embed=has_token_embed, ephemeral=True, view=view)


def setup(bot):
    bot.add_cog(Token(bot))
