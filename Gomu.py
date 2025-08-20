import os
import asyncio
import discord
from utils.utillity import logger
from help import CustomHelpCommand
from discord.ext import commands
from dotenv import load_dotenv
from datetime import timedelta, timezone

WIB = timezone(timedelta(hours=7))

# === Load Environment Variables ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")


# === Intents ===
intents = discord.Intents.all()

def pre_ready():
        print("""


   ▄██████▄   ▄██████▄     ▄▄▄▄███▄▄▄▄   ███    █▄  
  ███    ███ ███    ███  ▄██▀▀▀███▀▀▀██▄ ███    ███ 
  ███    █▀  ███    ███  ███   ███   ███ ███    ███ 
 ▄███        ███    ███  ███   ███   ███ ███    ███ 
▀▀███ ████▄  ███    ███  ███   ███   ███ ███    ███ 
  ███    ███ ███    ███  ███   ███   ███ ███    ███ 
  ███    ███ ███    ███  ███   ███   ███ ███    ███ 
  ████████▀   ▀██████▀    ▀█   ███   █▀  ████████▀  
                                                    



""")

# === Custom Bot Class ===
class GOMU(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("g!", "G!"),
            intents=intents,
            help_command=CustomHelpCommand(),
            case_insensitive=True,
        )

    async def setup_hook(self):
        await self.load_extension("cog.lavalink")
        logger.info("Lavalink File Berhasil Di Load")
        await self.load_extension("cog.user")
        logger.info("User File Berhasil Di Load")
        await self.load_extension("cog.music")
        logger.info("Music File Berhasil Di Load")
        await self.load_extension("cog.search")
        logger.info("✅ Semua cog berhasil di-load")
        
    async def on_ready(self) -> None:
            logger.info(f"✅ Bot login sebagai {self.user} ({self.user.id})")
            activity = discord.Activity(type=discord.ActivityType.watching, name="Goverment")
            await self.change_presence(status=discord.Status.online, activity=activity)

    async def on_message(self,message: discord.Message):
        if message.author.bot:
            return
        logger.debug(f"Pesan diterima: {message.content}")
        await bot.process_commands(message)


# === Main Entry Point ===
bot = GOMU()

if __name__ == "__main__":
    try:
        pre_ready()
        logger.info(f'Welcome Mr Hellenoir')
        asyncio.run(bot.start(TOKEN))
    except KeyboardInterrupt:
        logger.info('Bot Memutuskan Konseksi')
