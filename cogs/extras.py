import discord
from datetime import datetime
from discord.ext import commands
from discord_components import *


class extras(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def rules(self, ctx):
        if not ctx.author.id == 750891444444725318:
            return

        rulesEmbed = discord.Embed(colour=0x202225, description=f"Please take some time to read our community's rules to ensure the safety of everyone! If you need anything feel free to make a ticket <#1031699028259385396> \n\n 1. Do not post anybodys personal information without permission. \n 2. Posting any type of harmful links/files will result in a permanent ban. \n 3. Any advertising will result in a permanent ban. \n 4. Any kind of NSFW content is not allowed. \n 5. Check out <#1031698835522736158> & <#1031788616491474984> to see player vouches and media.  \n 6. Message <@750891444444725318> & <@628039395752280065> or make a ticket for any purchases. ", timestamp=datetime.utcnow())
        await ctx.send(embed=rulesEmbed, file=discord.File('Rainbow_Line.gif'))
        await ctx.send(file=discord.File('Rainbow_Line.gif'))

    @commands.command()
    async def pricing(self, ctx):
        if not ctx.author.id == 750891444444725318:
            return

        embed = discord.Embed(title=f"Welcome To The Cash Corner", description="Welcome To Our Shop! If your interested head to <#1031699028259385396> and make a ticket. We Accept Paypal F&F & Crypto \n\n Max Clothes = $75 \n1 Million Chips = $15 \n VIP Level 3 = $15 \n 99 Spins = $10 \n 100k RP = $5", colour=0x2f3136)
        await ctx.send(embed=embed, file=discord.File('Rainbow_Line.gif'))
        await ctx.send(file=discord.File('Rainbow_Line.gif'))

    @commands.command()
    async def test(self, ctx):
        if not ctx.author.id == 750891444444725318:
            return

        selectOptions = []
        selectOptions.append(SelectOption(label="sus", value="12312412541212331"))
        finalPanelEmbed = discord.Embed(colour=0x2F3136, title="Cash Corner Ticket System", description=f'Feel Free To Create A Ticket By Selecting A Option Below!')
        components = Select(placeholder="Click Me To Select A Ticket Department!", options=selectOptions)
        finalPanelEmbed.set_image(url="https://cdn.discordapp.com/attachments/1032062622171926618/1032063931193245787/IMG_2082.jpg")
        await ctx.send(embed=finalPanelEmbed, components=[components],file=discord.File('Rainbow_Line.gif'))
        await ctx.send(file=discord.File('Rainbow_Line.gif'))

def setup(bot):
    bot.add_cog(extras(bot))