import os
import dotenv
import discord
import datetime

from utils.database import initialize_database

dotenv.load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)


@bot.event
async def on_ready():

    print("--------------------------------")
    print("----- + LOADED PoraHobe  + -----")
    print("--------------------------------")

    await bot.change_presence(activity=discord.Game(name="With Life"))

    start_time = datetime.datetime.now()
    bot.start_time = start_time

    print("----- + LOADING COMMANDS + -----")
    print("--------------------------------")

    for command in bot.walk_application_commands():
        print(f"----- + Loaded : {command.name} ")

    print("--------------------------------")
    print(f"---- + Loaded : {len(list(bot.walk_application_commands()))}  Commands + -")
    print("--------------------------------")

    print("------- + LOADING COGS + -------")
    print(f"----- + Loaded : {len(bot.cogs)} Cogs + ------")
    print("--------------------------------")

    initialize_database()

    print("----- + Database Initialized + -----")


@bot.command(name="ping", description="Check The Bot's Latency")
async def ping(ctx):
    latency = bot.latency * 1000
    uptime = datetime.datetime.now() - bot.start_time

    uptime_seconds = uptime.total_seconds()
    uptime_str = str(datetime.timedelta(seconds=uptime_seconds)).split(".")[0]

    embed = discord.Embed(
        title=":ping_pong: _*Pong !*_",
        description=f"Uptime : {uptime_str}\nLatency : {latency:.2f} ms",
        color=0x2F3136,
    )

    await ctx.respond(embed=embed)


bot.load_extension("cogs.notes")

bot.run(TOKEN)
