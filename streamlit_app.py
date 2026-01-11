import discord
import requests
import streamlit as st
from discord.ext import tasks
from discord import app_commands

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
tree = app_commands.CommandTree(client)

active_atcs = set()

# user_id -> set of callsigns
user_monitors = {}

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
# SLASH COMMANDS
# =======================
@tree.command(name="monitor", description="Monitor a custom ATC station")
@app_commands.describe(callsign="ATC callsign (e.g. ML_TWR) or 'clear'")
async def monitor(interaction: discord.Interaction, callsign: str):
    user_id = interaction.user.id
    callsign = callsign.upper()

    if user_id not in user_monitors:
        user_monitors[user_id] = set()

    if callsign == "CLEAR":
        user_monitors[user_id].clear()
        await interaction.response.send_message(
            "✅ Your monitored ATC stations have been cleared.",
            ephemeral=True
        )
        return

    user_monitors[user_id].add(callsign)
    await interaction.response.send_message(
        f"📡 You are now monitoring **{callsign}**.\n"
        f"You will be notified when it logs on or off.",
        ephemeral=True
    )

# =======================
# ATC WATCHER
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

    # ATC LOGGED ON
    for callsign in logged_on:
        await channel.send(
            f":green_circle: {callsign} has just logged **ON**! <@&{ROLE_ID}>"
        )

        for user_id, stations in user_monitors.items():
            if callsign in stations:
                await channel.send(
                    f"🔔 <@{user_id}> — **{callsign}** you are monitoring is now **ONLINE**"
                )

    # ATC LOGGED OFF
    for callsign in logged_off:
        await channel.send(
            f":red_circle: {callsign} has just logged **OFF**! <@&{ROLE_ID}>"
        )

        for user_id, stations in user_monitors.items():
            if callsign in stations:
                await channel.send(
                    f"🔕 <@{user_id}> — **{callsign}** you are monitoring is now **OFFLINE**"
                )

    active_atcs = atcs_now

# =======================
# DEBUG TASK (DISABLED)
# =======================
# @tasks.loop(seconds=10)
# async def debug_ping():
#     guild = client.get_guild(GUILD_ID)
#     if not guild:
#         return
#     channel = guild.get_channel(CHANNEL_ID)
#     if not channel:
#         return
#     await channel.send(":warning: DEBUG heartbeat ping")

# =======================
# BOT READY
# =======================
@client.event
async def on_ready():
    print(f"{client.user} logged in.")

    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print("Slash commands synced.")

    watch_vatsim_atc.start()

    # debug_ping.start()  # intentionally disabled

# =======================
# RUN BOT
# =======================
if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
