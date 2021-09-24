import discord
import os
import chat_exporter
from discord_components import ComponentsBot
from dotenv import load_dotenv

# Loads Environment Variables
load_dotenv()

intents = discord.Intents.default()
intents.members = True
bot = ComponentsBot(os.getenv("prefix"), intents=intents, activity=discord.Activity(type=discord.ActivityType.watching, name="For New Tickets"), status=discord.Status.online)
bot.remove_command('help')

# Event Starts When Bot Is Online
@bot.event
async def on_ready():
    print('Ticket Bot Online!')
    chat_exporter.init_exporter(bot)

# Loads ALl Py Files On Startup.
for file in os.listdir('./cogs'):
    if file.endswith('.py'):
        bot.load_extension(f'cogs.{file[:-3]}')

bot.run(os.getenv('token'))
