
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
import json
import os
import aiohttp

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Store for temporary data (in production, use a database)
warned_users = {}
muted_users = {}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# Kick command
@bot.tree.command(name="kick", description="Kick a member from the server")
@app_commands.describe(member="The member to kick", reason="Reason for kicking")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("❌ You don't have permission to kick members!", ephemeral=True)
        return
    
    try:
        await member.kick(reason=reason)
        embed = discord.Embed(title="Member Kicked", color=0xff6b6b)
        embed.add_field(name="Member", value=f"{member.mention} ({member})", inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to kick this member!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

# Ban command
@bot.tree.command(name="ban", description="Ban a member from the server")
@app_commands.describe(member="The member to ban", reason="Reason for banning", delete_messages="Days of messages to delete (0-7)")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided", delete_messages: int = 0):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ You don't have permission to ban members!", ephemeral=True)
        return
    
    if delete_messages < 0 or delete_messages > 7:
        await interaction.response.send_message("❌ Delete messages days must be between 0-7!", ephemeral=True)
        return
    
    try:
        await member.ban(reason=reason, delete_message_days=delete_messages)
        embed = discord.Embed(title="Member Banned", color=0xff0000)
        embed.add_field(name="Member", value=f"{member.mention} ({member})", inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to ban this member!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

# Warn command
@bot.tree.command(name="warn", description="Warn a member")
@app_commands.describe(member="The member to warn", reason="Reason for warning")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("❌ You don't have permission to warn members!", ephemeral=True)
        return
    
    user_id = str(member.id)
    guild_id = str(interaction.guild.id)
    
    if guild_id not in warned_users:
        warned_users[guild_id] = {}
    if user_id not in warned_users[guild_id]:
        warned_users[guild_id][user_id] = []
    
    warning = {
        "reason": reason,
        "moderator": str(interaction.user),
        "timestamp": datetime.datetime.now().isoformat()
    }
    warned_users[guild_id][user_id].append(warning)
    
    embed = discord.Embed(title="Member Warned", color=0xffa500)
    embed.add_field(name="Member", value=f"{member.mention} ({member})", inline=False)
    embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Total Warnings", value=len(warned_users[guild_id][user_id]), inline=False)
    
    await interaction.response.send_message(embed=embed)
    
    # Send DM to warned user
    try:
        dm_embed = discord.Embed(title="You've been warned", color=0xffa500)
        dm_embed.add_field(name="Server", value=interaction.guild.name, inline=False)
        dm_embed.add_field(name="Reason", value=reason, inline=False)
        await member.send(embed=dm_embed)
    except:
        pass  # Ignore if DM fails

# Timeout command
@bot.tree.command(name="timeout", description="Timeout a member")
@app_commands.describe(member="The member to timeout", duration="Duration in minutes", reason="Reason for timeout")
async def timeout(interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("❌ You don't have permission to timeout members!", ephemeral=True)
        return
    
    if duration <= 0 or duration > 40320:  # Max 28 days
        await interaction.response.send_message("❌ Duration must be between 1 minute and 28 days (40320 minutes)!", ephemeral=True)
        return
    
    try:
        until = discord.utils.utcnow() + datetime.timedelta(minutes=duration)
        await member.timeout(until, reason=reason)
        
        embed = discord.Embed(title="Member Timed Out", color=0x808080)
        embed.add_field(name="Member", value=f"{member.mention} ({member})", inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
        embed.add_field(name="Duration", value=f"{duration} minutes", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to timeout this member!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

# Clear messages command
@bot.tree.command(name="clear", description="Clear messages from a channel")
@app_commands.describe(amount="Number of messages to delete (1-100)")
async def clear(interaction: discord.Interaction, amount: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You don't have permission to manage messages!", ephemeral=True)
        return
    
    if amount <= 0 or amount > 100:
        await interaction.response.send_message("❌ Amount must be between 1-100!", ephemeral=True)
        return
    
    try:
        deleted = await interaction.channel.purge(limit=amount)
        embed = discord.Embed(title="Messages Cleared", color=0x00ff00)
        embed.add_field(name="Amount", value=f"{len(deleted)} messages", inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
        embed.add_field(name="Channel", value=interaction.channel.mention, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to delete messages!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

# Warnings check command
@bot.tree.command(name="warnings", description="Check warnings for a member")
@app_commands.describe(member="The member to check warnings for")
async def warnings(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("❌ You don't have permission to view warnings!", ephemeral=True)
        return
    
    user_id = str(member.id)
    guild_id = str(interaction.guild.id)
    
    if guild_id not in warned_users or user_id not in warned_users[guild_id]:
        await interaction.response.send_message(f"✅ {member.mention} has no warnings!", ephemeral=True)
        return
    
    warnings_list = warned_users[guild_id][user_id]
    embed = discord.Embed(title=f"Warnings for {member.display_name}", color=0xffa500)
    
    for i, warning in enumerate(warnings_list[-10:], 1):  # Show last 10 warnings
        embed.add_field(
            name=f"Warning {i}",
            value=f"**Reason:** {warning['reason']}\n**Moderator:** {warning['moderator']}\n**Date:** {warning['timestamp'][:10]}",
            inline=False
        )
    
    embed.add_field(name="Total Warnings", value=len(warnings_list), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Server info command
@bot.tree.command(name="serverinfo", description="Get server information")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"Server Info - {guild.name}", color=0x0099ff)
    
    embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%B %d, %Y"), inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Boost Level", value=guild.premium_tier, inline=True)
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    await interaction.response.send_message(embed=embed)

# User info command
@bot.tree.command(name="userinfo", description="Get user information")
@app_commands.describe(member="The member to get info about")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    if member is None:
        member = interaction.user
    
    embed = discord.Embed(title=f"User Info - {member.display_name}", color=member.color)
    
    embed.add_field(name="Username", value=str(member), inline=True)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%B %d, %Y") if member.joined_at else "Unknown", inline=True)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%B %d, %Y"), inline=True)
    embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
    embed.add_field(name="Status", value=str(member.status).title(), inline=True)
    
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    
    await interaction.response.send_message(embed=embed)

# Lock channel command
@bot.tree.command(name="lock", description="Lock a channel")
@app_commands.describe(reason="Reason for locking the channel")
async def lock(interaction: discord.Interaction, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ You don't have permission to manage channels!", ephemeral=True)
        return
    
    try:
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        
        embed = discord.Embed(title="🔒 Channel Locked", color=0xff0000)
        embed.add_field(name="Channel", value=interaction.channel.mention, inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

# Unlock channel command
@bot.tree.command(name="unlock", description="Unlock a channel")
@app_commands.describe(reason="Reason for unlocking the channel")
async def unlock(interaction: discord.Interaction, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ You don't have permission to manage channels!", ephemeral=True)
        return
    
    try:
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        
        embed = discord.Embed(title="🔓 Channel Unlocked", color=0x00ff00)
        embed.add_field(name="Channel", value=interaction.channel.mention, inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

# Store for AFK users
afk_users = {}

# Search scripts command
@bot.tree.command(name="search-scripts", description="Search for scripts on ScriptBlox")
@app_commands.describe(query="Search query for scripts")
async def search_scripts(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://scriptblox.com/api/script/search?q={query}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if not data.get('result') or not data['result'].get('scripts'):
                        embed = discord.Embed(title="🔍 Script Search", description=f"No scripts found for: **{query}**", color=0xff0000)
                        await interaction.followup.send(embed=embed)
                        return
                    
                    scripts = data['result']['scripts']
                    await send_script_results(interaction, scripts, query, 0)
                    
                else:
                    embed = discord.Embed(title="❌ Error", description="Failed to fetch scripts from ScriptBlox API", color=0xff0000)
                    await interaction.followup.send(embed=embed)
                    
    except Exception as e:
        embed = discord.Embed(title="❌ Error", description=f"An error occurred: {str(e)}", color=0xff0000)
        await interaction.followup.send(embed=embed)

async def send_script_results(interaction, scripts, query, page=0):
    scripts_per_page = 5
    start_idx = page * scripts_per_page
    end_idx = start_idx + scripts_per_page
    page_scripts = scripts[start_idx:end_idx]
    
    if not page_scripts:
        embed = discord.Embed(title="📄 No More Results", description="You've reached the end of the search results.", color=0x808080)
        await interaction.followup.send(embed=embed)
        return
    
    embed = discord.Embed(
        title=f"🔍 Script Search Results - Page {page + 1}",
        description=f"Search query: **{query}**\nShowing {start_idx + 1}-{min(end_idx, len(scripts))} of {len(scripts)} results",
        color=0x0099ff
    )
    
    for i, script in enumerate(page_scripts, start_idx + 1):
        title = script.get('title', 'Untitled Script')[:100]
        game = script.get('game', {}).get('name', 'Unknown Game')
        views = script.get('views', 0)
        verified = "✅" if script.get('isVerified') else "❌"
        
        script_info = f"**Game:** {game}\n**Views:** {views:,}\n**Verified:** {verified}"
        embed.add_field(name=f"{i}. {title}", value=script_info, inline=False)
    
    view = ScriptSearchView(scripts, query, page)
    
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed, view=view)

class ScriptSearchView(discord.ui.View):
    def __init__(self, scripts, query, current_page):
        super().__init__(timeout=300)
        self.scripts = scripts
        self.query = query
        self.current_page = current_page
        self.scripts_per_page = 5
        
        # Disable buttons if at boundaries
        if current_page == 0:
            self.previous_button.disabled = True
        
        max_pages = (len(scripts) - 1) // self.scripts_per_page
        if current_page >= max_pages:
            self.next_button.disabled = True
    
    @discord.ui.button(label='◀️ Previous', style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        new_page = max(0, self.current_page - 1)
        await self.update_page(interaction, new_page)
    
    @discord.ui.button(label='Next ▶️', style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        max_pages = (len(self.scripts) - 1) // self.scripts_per_page
        new_page = min(max_pages, self.current_page + 1)
        await self.update_page(interaction, new_page)
    
    async def update_page(self, interaction, new_page):
        start_idx = new_page * self.scripts_per_page
        end_idx = start_idx + self.scripts_per_page
        page_scripts = self.scripts[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"🔍 Script Search Results - Page {new_page + 1}",
            description=f"Search query: **{self.query}**\nShowing {start_idx + 1}-{min(end_idx, len(self.scripts))} of {len(self.scripts)} results",
            color=0x0099ff
        )
        
        for i, script in enumerate(page_scripts, start_idx + 1):
            title = script.get('title', 'Untitled Script')[:100]
            game = script.get('game', {}).get('name', 'Unknown Game')
            views = script.get('views', 0)
            verified = "✅" if script.get('isVerified') else "❌"
            
            script_info = f"**Game:** {game}\n**Views:** {views:,}\n**Verified:** {verified}"
            embed.add_field(name=f"{i}. {title}", value=script_info, inline=False)
        
        # Update button states
        self.previous_button.disabled = (new_page == 0)
        max_pages = (len(self.scripts) - 1) // self.scripts_per_page
        self.next_button.disabled = (new_page >= max_pages)
        
        self.current_page = new_page
        await interaction.edit_original_response(embed=embed, view=self)
    
    async def on_timeout(self):
        # Disable all buttons when view times out
        for item in self.children:
            item.disabled = True

# Help command
@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Bot Commands", description="Here are all available moderation commands:", color=0x0099ff)
    
    embed.add_field(
        name="🔨 Moderation Commands",
        value="`/kick` - Kick a member\n`/ban` - Ban a member\n`/warn` - Warn a member\n`/timeout` - Timeout a member\n`/clear` - Clear messages",
        inline=False
    )
    
    embed.add_field(
        name="🔒 Channel Management",
        value="`/lock` - Lock a channel\n`/unlock` - Unlock a channel",
        inline=False
    )
    
    embed.add_field(
        name="📊 Information Commands",
        value="`/userinfo` - Get user information\n`/serverinfo` - Get server information\n`/warnings` - Check member warnings\n`/stats` - Bot statistics",
        inline=False
    )
    
    embed.add_field(
        name="💤 Utility Commands",
        value="`/afk` - Set AFK status\n`/search-scripts` - Search ScriptBlox scripts\n/invite` - Get bot invite link\n`/ping` - Check bot latency\n`/uptime` - Check bot uptime\n`/help` - Show this help menu",
        inline=False
    )
    
    embed.set_footer(text="Use these commands responsibly!")
    await interaction.response.send_message(embed=embed)

# AFK command
@bot.tree.command(name="afk", description="Set your AFK status")
@app_commands.describe(reason="Reason for being AFK")
async def afk(interaction: discord.Interaction, reason: str = "No reason provided"):
    user_id = str(interaction.user.id)
    guild_id = str(interaction.guild.id)
    
    if guild_id not in afk_users:
        afk_users[guild_id] = {}
    
    afk_users[guild_id][user_id] = {
        "reason": reason,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    embed = discord.Embed(title="💤 AFK Status Set", color=0x808080)
    embed.add_field(name="User", value=interaction.user.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text="You will be marked as back when you send a message!")
    
    await interaction.response.send_message(embed=embed)

# AFK check on message
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)
    
    # Check if user was AFK and remove them
    if guild_id in afk_users and user_id in afk_users[guild_id]:
        afk_time = datetime.datetime.fromisoformat(afk_users[guild_id][user_id]["timestamp"])
        time_away = datetime.datetime.now() - afk_time
        
        del afk_users[guild_id][user_id]
        
        embed = discord.Embed(title="👋 Welcome Back!", color=0x00ff00)
        embed.add_field(name="Time Away", value=f"{time_away.seconds // 3600}h {(time_away.seconds // 60) % 60}m", inline=False)
        
        await message.channel.send(embed=embed, delete_after=10)
    
    # Check for mentions of AFK users
    for mention in message.mentions:
        mentioned_id = str(mention.id)
        if guild_id in afk_users and mentioned_id in afk_users[guild_id]:
            afk_data = afk_users[guild_id][mentioned_id]
            afk_time = datetime.datetime.fromisoformat(afk_data["timestamp"])
            time_away = datetime.datetime.now() - afk_time
            
            embed = discord.Embed(title="💤 User is AFK", color=0x808080)
            embed.add_field(name="User", value=mention.mention, inline=False)
            embed.add_field(name="Reason", value=afk_data["reason"], inline=False)
            embed.add_field(name="Time Away", value=f"{time_away.seconds // 3600}h {(time_away.seconds // 60) % 60}m", inline=False)
            
            await message.channel.send(embed=embed, delete_after=15)

# Store bot start time for uptime
bot_start_time = datetime.datetime.now()

# Invite command
@bot.tree.command(name="invite", description="Get the bot invite link")
async def invite(interaction: discord.Interaction):
    permissions = discord.Permissions(
        kick_members=True,
        ban_members=True,
        manage_messages=True,
        manage_channels=True,
        moderate_members=True,
        read_messages=True,
        send_messages=True,
        embed_links=True,
        read_message_history=True
    )
    
    invite_url = discord.utils.oauth_url(bot.user.id, permissions=permissions)
    
    embed = discord.Embed(title="🤖 Invite Bot", color=0x0099ff)
    embed.add_field(name="Invite Link", value=f"[Click here to invite me!]({invite_url})", inline=False)
    embed.add_field(name="Permissions Needed", value="• Kick Members\n• Ban Members\n• Manage Messages\n• Manage Channels\n• Moderate Members\n• Send Messages & Embeds", inline=False)
    embed.set_footer(text="Thank you for using our bot!")
    
    await interaction.response.send_message(embed=embed)

# Ping command
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    
    # Determine latency status
    if latency < 100:
        status = "🟢 Excellent"
        color = 0x00ff00
    elif latency < 200:
        status = "🟡 Good"
        color = 0xffff00
    elif latency < 300:
        status = "🟠 Fair"
        color = 0xff8000
    else:
        status = "🔴 Poor"
        color = 0xff0000
    
    embed = discord.Embed(title="🏓 Pong!", color=color)
    embed.add_field(name="Bot Latency", value=f"{latency}ms", inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    embed.set_footer(text="Response time to Discord API")
    
    await interaction.response.send_message(embed=embed)

# Uptime command
@bot.tree.command(name="uptime", description="Check bot uptime")
async def uptime(interaction: discord.Interaction):
    current_time = datetime.datetime.now()
    uptime_delta = current_time - bot_start_time
    
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_str = ""
    if days > 0:
        uptime_str += f"{days}d "
    if hours > 0:
        uptime_str += f"{hours}h "
    if minutes > 0:
        uptime_str += f"{minutes}m "
    uptime_str += f"{seconds}s"
    
    embed = discord.Embed(title="⏰ Bot Uptime", color=0x00ff00)
    embed.add_field(name="Current Uptime", value=uptime_str, inline=False)
    embed.add_field(name="Started At", value=bot_start_time.strftime("%B %d, %Y at %H:%M:%S UTC"), inline=False)
    embed.add_field(name="Status", value="🟢 Online & Running", inline=False)
    embed.set_footer(text="Bot has been running continuously")
    
    await interaction.response.send_message(embed=embed)

# Stats command
@bot.tree.command(name="stats", description="Show bot statistics")
async def stats(interaction: discord.Interaction):
    guild = interaction.guild
    total_warnings = 0
    total_afk = 0
    
    guild_id = str(guild.id)
    
    # Count warnings
    if guild_id in warned_users:
        for user_warnings in warned_users[guild_id].values():
            total_warnings += len(user_warnings)
    
    # Count AFK users
    if guild_id in afk_users:
        total_afk = len(afk_users[guild_id])
    
    embed = discord.Embed(title="📊 Bot Statistics", color=0x0099ff)
    embed.add_field(name="Server", value=guild.name, inline=False)
    embed.add_field(name="Total Members", value=guild.member_count, inline=True)
    embed.add_field(name="Bot Uptime", value="Online ✅", inline=True)
    embed.add_field(name="Commands Available", value="19", inline=True)
    embed.add_field(name="Total Warnings Issued", value=total_warnings, inline=True)
    embed.add_field(name="Currently AFK Users", value=total_afk, inline=True)
    embed.add_field(name="Bot Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.set_footer(text=f"Bot ID: {bot.user.id}")
    await interaction.response.send_message(embed=embed)

# Error handler
@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
    elif isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"❌ Command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ An unexpected error occurred!", ephemeral=True)
        print(f"Unhandled error: {error}")
        
bot.run('Token')
