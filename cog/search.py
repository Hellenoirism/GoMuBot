import discord
from discord.ext import commands
import wikipedia


class Searching(commands.Cog):
    def __init__(self,bot: commands.Bot):
        self.bot = bot
        wikipedia.set_lang("id")

    @commands.command(name="Wikipedia", aliases=["ask","tanya","w"], help="Mencari informasi berdasarkan query untuk penelusuran pada database wikipedia yaang tersedia dan dapat diakses")
    async def wikipedia(self, ctx, *, query: str) -> None :
        try:
            summary = wikipedia.summary(query, sentences=3)
            page = wikipedia.page(query)
            embed = discord.Embed(
                title=query.title(),
                description=f"{summary}\n\n[Baca selengkapnya di Wikipedia]({wikipedia.page(query).url})",
                url=wikipedia.page(query).url,
                color=discord.Color.blurple()
            )
            embed.set_author(name="GoMu Pedia", icon_url="https://media.giphy.com/media/gahyl3UyyjdLhg0KoR/giphy.gif")
            embed.set_footer(text=f"Searched By Wikipedia")
            embed.add_field(name="Page", value=page)
            await ctx.send(embed=embed)
        except wikipedia.DisambiguationError as e:
            await ctx.send(f"Terlalu banyak hasil ! coba beritahu saya dengan lebih spesifik, misalnya : `{e.options[0]}`")
        except wikipedia.PageError:
            await ctx.send(f"Maaf ya, aku lagi gaenak badan jadinya ganemu deh apa yang kamu pengen cari, nanti kalo udah mendingan pasti aku cariin deh :3")
        except Exception as e:
            await ctx.send(f"Error : {e}")

async def setup(bot):
    cog = Searching(bot)
    await bot.add_cog(cog)
    bot.searching_cog = cog  