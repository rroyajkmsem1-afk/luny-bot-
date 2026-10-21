import discord
from discord.ext import commands
from datetime import timedelta
import logging
import re
import asyncio

# --- CONFIGURATION ---
TOKEN = "MTU2MjQ2MDM0ODIzNjQzNTQ2Ng.GvYHJ9.NFnavYjV5fWNlk1ObaCm47mEILzMgKKHY9N4Lg   "
WELCOME_CHANNEL_ID = 1562463479162609825 
ANTI_LINK_ENABLED = True                 
THEME_COLOR = discord.Color.from_str("#2b2d31") # Blends with Discord dark theme
# ---------------------
    
discord.utils.setup_logging(level=logging.INFO)

class PremiumBot(commands.Bot):
    def __init__(self):
        # Intents.all() is strictly required for text-based commands (Message Content)
        intents = discord.Intents.all()
        # Prefix set to $ as requested
        super().__init__(command_prefix="$", intents=intents, help_command=None)

    async def setup_hook(self):
        await self.add_cog(WelcomeCog(self))
        await self.add_cog(AutoModCog(self))
        await self.add_cog(ModerationCog(self))
        await self.add_cog(UtilityCog(self))
        await self.add_cog(HelpCog(self))
        logging.info("System modules loaded.")

    async def on_ready(self):
        logging.info(f"Logged in as {self.user}")
        activity = discord.Activity(type=discord.ActivityType.listening, name="$help")
        await self.change_presence(status=discord.Status.online, activity=activity)

    async def on_command_error(self, ctx, error):
        # Global error handler to prevent silent failures
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("SYSTEM // Insufficient permissions to execute this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"SYSTEM // Missing argument. Check `$help {ctx.command.name}`.")
        elif isinstance(error, commands.CommandNotFound):
            pass
        else:
            logging.error(f"Command error: {error}")

# ---------------------------------------------------------
# WELCOME & LEAVE COG
# ---------------------------------------------------------
class WelcomeCog(commands.Cog, name="System Events"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if not channel: return

        embed = discord.Embed(
            title="USER CONNECTION // ESTABLISHED",
            description=f"Welcome to the network, {member.mention}.",
            color=THEME_COLOR,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Registration", value=discord.utils.format_dt(member.created_at, "R"))
        embed.add_field(name="Designation", value=f"User #{member.guild.member_count}")
        embed.set_footer(text=f"UID: {member.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if not channel: return

        embed = discord.Embed(
            title="USER CONNECTION // TERMINATED",
            description=f"**{member.name}** has disconnected from the server.",
            color=THEME_COLOR,
            timestamp=discord.utils.utcnow()
        )
        await channel.send(embed=embed)

# ---------------------------------------------------------
# AUTOMOD COG
# ---------------------------------------------------------
class AutoModCog(commands.Cog, name="Automated Security"):
    def __init__(self, bot):
        self.bot = bot
        self.url_regex = re.compile(r"(https?://\S+)")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not ANTI_LINK_ENABLED:
            return

        if message.author.guild_permissions.manage_messages:
            return

        if self.url_regex.search(message.content):
            await message.delete()
            embed = discord.Embed(
                title="SECURITY OVERRIDE",
                description=f"{message.author.mention}, unauthorized hyperlinks are restricted.",
                color=discord.Color.dark_red()
            )
            warning = await message.channel.send(embed=embed)
            await asyncio.sleep(4)
            await warning.delete()

# ---------------------------------------------------------
# MODERATION COG
# ---------------------------------------------------------
class ModerationCog(commands.Cog, name="Moderation"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="timeout", description="Restrict a member's ability to communicate.")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, minutes: int, *, reason: str = "Unspecified"):
        duration = timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        
        embed = discord.Embed(title="MODERATION // TIMEOUT", color=THEME_COLOR, timestamp=discord.utils.utcnow())
        embed.add_field(name="Target", value=member.mention, inline=True)
        embed.add_field(name="Duration", value=f"{minutes}m", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="ban", description="Revoke a member's access to the server entirely.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Unspecified"):
        await member.ban(reason=reason)
        
        embed = discord.Embed(title="MODERATION // BAN", color=THEME_COLOR, timestamp=discord.utils.utcnow())
        embed.add_field(name="Target", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="purge", description="Clear a specified volume of messages.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        deleted = await ctx.channel.purge(limit=amount + 1)
        confirmation = await ctx.send(f"SYSTEM // Purged {len(deleted)-1} messages.")
        await asyncio.sleep(3)
        await confirmation.delete()

    @commands.command(name="lock", description="Engage channel lockdown protocols.")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        default_role = ctx.guild.default_role
        overwrite = ctx.channel.overwrites_for(default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(default_role, overwrite=overwrite)
        
        embed = discord.Embed(
            title="CHANNEL // LOCKED", 
            description="Communication in this sector has been temporarily suspended.", 
            color=THEME_COLOR
        )
        await ctx.send(embed=embed)

    @commands.command(name="unlock", description="Disengage channel lockdown protocols.")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        default_role = ctx.guild.default_role
        overwrite = ctx.channel.overwrites_for(default_role)
        overwrite.send_messages = None 
        await ctx.channel.set_permissions(default_role, overwrite=overwrite)
        
        embed = discord.Embed(
            title="CHANNEL // UNLOCKED", 
            description="Communication protocols restored.", 
            color=THEME_COLOR
        )
        await ctx.send(embed=embed)

    @commands.command(name="nuke", description="Permanently delete and reconstruct the channel.")
    @commands.has_permissions(manage_channels=True, manage_messages=True)
    async def nuke(self, ctx):
        channel = ctx.channel
        position = channel.position
        new_channel = await channel.clone(reason=f"Nuked by {ctx.author.name}")
        await channel.delete()
        await new_channel.edit(position=position)
        
        embed = discord.Embed(
            title="SYSTEM // NUKE EXECUTED",
            description="Channel history has been permanently wiped and reconstructed.",
            color=THEME_COLOR,
            timestamp=discord.utils.utcnow()
        )
        await new_channel.send(embed=embed)

# ---------------------------------------------------------
# UTILITY COG
# ---------------------------------------------------------
class UtilityCog(commands.Cog, name="Utility"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="userinfo", description="Extract detailed diagnostic data on a user.")
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        roles = [role.mention for role in member.roles[1:]]
        roles_str = " ".join(roles) if roles else "None"

        embed = discord.Embed(title="USER // DATA LOG", color=THEME_COLOR, timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Identifier", value=member.mention, inline=True)
        embed.add_field(name="UID", value=member.id, inline=True)
        embed.add_field(name="Account Creation", value=discord.utils.format_dt(member.created_at, "D"), inline=False)
        embed.add_field(name="Network Join", value=discord.utils.format_dt(member.joined_at, "D"), inline=False)
        embed.add_field(name=f"Clearance Levels [{len(member.roles)-1}]", value=roles_str, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="serverinfo", description="Extract server diagnostic data.")
    async def serverinfo(self, ctx):
        guild = ctx.guild
        embed = discord.Embed(title="SERVER // DATA LOG", color=THEME_COLOR, timestamp=discord.utils.utcnow())
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        embed.add_field(name="Network Name", value=guild.name, inline=True)
        embed.add_field(name="Administrator", value=guild.owner.mention, inline=True)
        embed.add_field(name="Total Units", value=str(guild.member_count), inline=True)
        embed.add_field(name="Role Count", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Initialization Date", value=discord.utils.format_dt(guild.created_at, "D"), inline=False)
        embed.set_footer(text=f"Network ID: {guild.id}")
            
        await ctx.send(embed=embed)

# ---------------------------------------------------------
# HELP COG
# ---------------------------------------------------------
class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", description="Display the system command directory.")
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="SYSTEM // COMMAND DIRECTORY",
            description="Execute any of the following modules using the $ prefix.",
            color=THEME_COLOR,
            timestamp=discord.utils.utcnow()
        )

        for cog_name, cog in self.bot.cogs.items():
            if cog_name in ["Help", "System Events", "Automated Security"]:
                continue
                
            commands_list = cog.get_commands()
            if not commands_list:
                continue
                
            command_text = ""
            for cmd in commands_list:
                command_text += f"`${cmd.name}` - {cmd.description}\n"
                
            embed.add_field(name=f"MODULE: {cog_name.upper()}", value=command_text, inline=False)

        embed.set_footer(text="System Modules Loaded")
        await ctx.send(embed=embed)

if __name__ == "__main__":
    bot = PremiumBot()
    bot.run(TOKEN)