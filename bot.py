import discord
import os
import chat_exporter
from discord_components import ComponentsBot
from discord.utils import get
from dotenv import load_dotenv
import requests

# Loads Environment Var2iables
load_dotenv()

intents = discord.Intents.default()
intents.members = True
bot = ComponentsBot(os.getenv("prefix"), intents=intents, activity=discord.Activity(type=discord.ActivityType.watching, name="For New Tickets"), status=discord.Status.online)
bot.remove_command('help')

# Event Starts When Bot Is Online
@bot.event
async def on_ready():
    print('Four Kings Bot online')
    chat_exporter.init_exporter(bot)

@bot.event
async def on_member_join(member):
    channel = await bot.fetch_channel(1031699448025321534)
    role = get(member.guild.roles, id=int(os.getenv("joinroleid")))
    await member.add_roles(role)
    embed = discord.Embed(title=f"{member.name}#{member.discriminator} Joined The Server", colour=0x0ed244)
    embed.set_thumbnail(url=member.avatar_url)
    await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = await bot.fetch_channel(1031699448025321534)
    embed = discord.Embed(title=f"{member.name}#{member.discriminator} Left The Server", colour=0xef4747)
    embed.set_thumbnail(url=member.avatar_url)
    await channel.send(embed=embed)

# Loads ALl Py Files On Startup.
for file in os.listdir('./cogs'):
    if file.endswith('.py'):
        bot.load_extension(f'cogs.{file[:-3]}')

bot.run(os.getenv('token'))