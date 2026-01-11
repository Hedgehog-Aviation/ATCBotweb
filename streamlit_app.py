import discord
import requests
import streamlit as st
from discord.ext import tasks

# =======================
# BOT CONFIGURATION
# =======================
DISCORD_TOKEN = st.secrets["BOT_TOKEN"]

GUILD_ID = 1355444614664032256
CHANNEL_ID = 1444943107471970344

WATCHED_ATC = ["ML_GND", "SY_GND"]
ROLE_ID = 1445293106403737650  # "ATC Bot Ping" role

VATSIM_JSON_URL = "https://data.vatsim.net/v3/vatsim-data.json"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
active_atcs = set()

# =======================
# VATSIM FETCH
# =======================
async def fetch_vatsim_atcs():
    """Fetch list of currently online ATC positions we're watching."""
    try:
        r = requests.get(VATSIM_JSON_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        atcs = set()
        for atc in data.get("controllers", []):
            if atc["callsign"] in WATCHED_ATC:
                atcs.add(atc["callsign"])
        return atcs
    except Exception as e:
        print(f"Error fetching VATSIM data: {e}")
        return set()

# =======================
# NORMAL ATC WATCHER
# =======================
@tasks.loop(seconds=30)
async def watch_vatsim_atc():
    global active_atcs
    atcs_now = await fetch_vatsim_atcs()
    guild = client.get_guild(GUILD_ID)
    if not guild:
        print("Guild not found!")
        return

    channel = guild.get_channel(CHANNEL_ID)
    if not channel:
        print("Channel not found!")
        return

    logged_on = atcs_now - active_atcs
    logged_off = active_atcs - atcs_now

    for callsign in logged_on:
        await channel.send(
            f":green_circle: {callsign} has just logged **ON**! <@&{ROLE_ID}>"
        )
    for callsign in logged_off:
        await channel.send(
            f":red_circle: {callsign} has just logged **OFF**! <@&{ROLE_ID}>"
        )

    active_atcs = atcs_now

# =======================
# DEBUG TASK (PING EVERY 10 SECONDS)
# COMMENT THIS OUT WHEN DONE TESTING
# =======================
@tasks.loop(seconds=10)
async def debug_ping():
    guild = client.get_guild(GUILD_ID)
    if not guild:
        print("[DEBUG] Guild not found")
        return

    channel = guild.get_channel(CHANNEL_ID)
    if not channel:
        print("[DEBUG] Channel not found")
        return

    await channel.send(
        f":warning: **DEBUG MODE** – bot heartbeat ping <@&{ROLE_ID}>"
    )
    print("[DEBUG] Sent debug ping")

# =======================
# BOT READY
# =======================
@client.event
async def on_ready():
    print(f"{client.user} logged in - starting monitor.")
    watch_vatsim_atc.start()

    # 🔧 DEBUG MODE ENABLED
    #debug_ping.start()
    # 🔧 COMMENT OUT THE LINE ABOVE TO DISABLE DEBUG MODE

# =======================
# RUN BOT
# =======================
if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
