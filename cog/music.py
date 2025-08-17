import discord
import pomice
from discord.ext import commands
from pomice import Track, NodePool, TrackType
from Player.player import GomuPlayer
from utils.utillity import format_duration, get_thumbnail,logger
from utils.tracklist import QueuePagination
import os
import time
from dotenv import load_dotenv
from pomice import NodePool

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
SERVER_PASSWORD = os.getenv("LAVALINK_PASSWORD")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
HOST = os.getenv("SERVER_HOST")
SPOTIFY_CLIENT_SECRET = os.getenv("SPCLIENT_SECRET")
class MusicCog(commands.Cog):
    def __init__(self,bot: commands.Bot):
        self.bot = bot
        self.pomice = pomice.NodePool()
        self.colour = discord.Colour.from_str("#4a7d9a")

        bot.loop.create_task(self.connect_node())

    def get_node(self):
        node = NodePool.get_node(identifier='MAIN')
        if not node or not node.is_connected:
            logger.warning("❌ Node 'MAIN' tidak tersedia atau belum tersambung.")
            return None
        return node
    async def connect_voice(self, ctx, channel):
        node = self.get_node()
        if node is None:
            logger.info("Node gagal di load")
            return Exception       
        
        await ctx.author.voice.channel.connect(cls=GomuPlayer, self_deaf=True, reconnect=True)
        player: GomuPlayer = ctx.voice_client
        await player.set_context(ctx=ctx)
        logger.info(f"GoMu Player berhasil join ke : {channel}")
        embed = discord.Embed(
            title=f"GoMu Berhasil Join ke {channel}",
            description="Halo, Terimakasih telah menggunakan bot ini\nKetik g!help atau G!help untuk list command yang tersedia :wink:",
            color=self.colour
        )
        embed.set_author(name="GoMu", icon_url="https://media.giphy.com/media/gahyl3UyyjdLhg0KoR/giphy.gif")
        embed.set_footer(text=f"Powered by : @Hellenoirism")
        await ctx.send(embed=embed)

    async def connect_node(self, identifier="MAIN"):
        try:
            await self.pomice.create_node(
                bot=self.bot,
                host=HOST,
                port=433,
                password=SERVER_PASSWORD,
                identifier=identifier,
                spotify_client_id=SPOTIFY_CLIENT_ID,
                spotify_client_secret=SPOTIFY_CLIENT_SECRET,
            )
            logger.info("✅ Node Lavalink berhasil dibuat dan tersambung")

        except pomice.NodeConnectionFailure:
            logger.warning(f"❌ Gagal membuat node Lavalink")

        except pomice.LavalinkVersionIncompatible:
            logger.warning(f"Versi lavalink tidak compatible")


    @commands.Cog.listener()
    async def on_pomice_track_end(self, player: GomuPlayer, track: Track, reason: str):
        logger.info(f"Lagu: {track.info}")
    
        player.queue.history.append(track)
        if len(player.queue.history)>15:
            player.queue.history.pop(0)

        if getattr(player, 'autoplay', False):
            try:    
                if track.track_type == TrackType.SPOTIFY:
                    logger.info(f"{track.track_type}")
                else:
                    logger.info(f"Status Track Type")
                if hasattr(track, "identifier"):
                    related_tracks = await player.node.get_recommendations(track=track)
                    logger.info(f"Status Pencarian Track : {related_tracks}")
                    if related_tracks:
                            next_track = related_tracks[0]
                            player.queue.put(next_track)
                            track = next_track[0]
                            await player.play(track=next_track)
                            logger.info(f"Autoplay memasukan track ke queue dan diputar")
                else:
                    recommendations = await player.node.get_recommendations(track=track.uri)
                    if recommendations:
                        try:
                            next_track = recommendations[0]
                            player.queue.put(next_track)
                        except Exception as e:
                            logger.warning(f"{e}")
            except pomice.exceptions.NodeException as e:
                logger.error(f"Error saat mendapatkan rekomendasi: {e}")


        if not track or not isinstance(track, pomice.Track):
            logger.warning("Track is invalid or not a pomice.Track object, skipping recommendations.")
            return

        # Pengkondisian LooopMode pada event Handler
        if player.queue.loop_mode == pomice.LoopMode.TRACK:
            await player.play(track)
            return
        
        if player.queue.loop_mode == pomice.LoopMode.QUEUE:
            await player.do_next()
            return
        if reason != "FINISHED":
            await player.do_next()

        if reason == "FINISHED":
            await player.do_next()

    @commands.command("join", help="Memanggil bot ke voice channel")
    async def join(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        channel = getattr(ctx.author.voice, "channel", None)
        if not channel:

            embed = discord.Embed(
                title="Kamu Lagi Ga Masuk Voice",
                description="Enak aja mau make tapi ga dimasukin dulu, no no yaaa :3",
                color=colour
            )
            embed.set_author(name="GoMu", icon_url="https://media.giphy.com/media/gahyl3UyyjdLhg0KoR/giphy.gif")
            return await ctx.send(embed=embed)
        try:
            if ctx.author:
                await self.connect_voice(ctx, channel)
            else:
                if not ctx.author:
                    await ctx.send(embed=discord.Embed(description=f"Aku lagi sibuk, nanti dulu yaaa"))
        except discord.ClientException as e:
            return logger.info(f'Aku lagi ada di {ctx.channel}, kalo mau gabung boleh kok :D')
        
    @commands.command(name="play", aliases=['pl','p'], help="Let's Rock N Roll, putar dengan memasukan g!play \'Judul lagu'")
    async def play(self, ctx: commands.Context, * ,search: str) -> None:
        voice = ctx.author.voice
        if not voice or not voice.channel:
            embed = discord.Embed(
                title="Join Voicenya Dulu Yaaa",
                description=f"{ctx.author.mention} Enak aja, kalo mau denger musik bareng yuk join kesini {ctx.channel.mention}"
            )
            return await ctx.send(embed=embed)
        
        if not ctx.author.voice:
            await ctx.invoke(self.join)
        # Sambungkan bot jika belum terhubung
        player: GomuPlayer = ctx.voice_client
        if not player:
            await voice.channel.connect(cls=GomuPlayer, self_deaf=True, reconnect=True)
            player: GomuPlayer = ctx.voice_client
            await player.set_context(ctx)

        # Logging time pencarian
        start = time.perf_counter()

        query = search.strip()
        is_spotify_playlist = "open.spotify.com/playlist/" in query
        is_spotify_url = "open.spotify.com" in query

        results = None

        #Searching Lagu di Spotify Search
        if not is_spotify_playlist and not is_spotify_url:
            results = await player.get_tracks(query=f"spsearch:{query}",search_type=pomice.SearchType.spsearch,filters=[pomice.filters.Equalizer.boost()], ctx=ctx)
            if not results:
                return await ctx.send(embed=discord.Embed(description="Lagu tidak ditemukan/query salah"), delete_after=8)
        else:
            results = await player.get_tracks(query, ctx=ctx)
        
        end = time.perf_counter()
        logger.info(f"Query Lagu: '{search}' selesai dalam {round((end - start) * 1000)}ms")

        if isinstance(results, pomice.Playlist):
            await self._play_playlist(ctx, player, results, search)
        else:
            await self._play_single_track(ctx, player, results[0])

    async def _play_playlist(self, ctx, player: GomuPlayer, playlist: pomice.Playlist, uri: str):
        playlist_uri = getattr(playlist, 'uri', None) or uri
        for track in playlist.tracks:
            player.queue.put(track)

        # Mulai track jika tidak sedang memutar apapun
        if not player.current and not player.is_playing:
            next_track = player.queue.get()
            await player.play(next_track)

        total_duration = sum(t.length for t in playlist.tracks)

        embed = discord.Embed(title="🎧 Memuat Playlist", color=self.colour)
        embed.add_field(name="Playlist", value=f"[{playlist.name}]({playlist_uri})", inline=False)
        embed.add_field(name="Playlist Duration", value=format_duration(total_duration), inline=True)
        embed.add_field(name="Tracks", value=str(len(playlist.tracks)), inline=True)

        thumbnail = get_thumbnail(playlist.tracks[0])
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        await ctx.send(embed=embed)

    async def _play_single_track(self, ctx, player: GomuPlayer, track: pomice.Track):
        # Jika tidak ada lagu yang sedang diputar, mainkan langsung
        if not player.current:
            try:
                await player.play(track=track)
            except pomice.TrackLoadError as e:
                return await ctx.send(f"❌ Track tidak dapat diputar.{e}")
            embed = await player.create_now_playing_embed(track)
            return await ctx.send(embed=embed)

        # Tambah ke antrian
        player.queue.put(track)
        logger.info("Berhasil menambahkan lagu ke Queue")
        embed = discord.Embed(
            title="Antrian Ditambahkan",
            description=f"{track.title} - {track.author}",
            color=self.colour
        )
        embed.add_field(name="Track Length", value=format_duration(track.length), inline=True)
        embed.add_field(name="Posisi Antrian", value=str(player.queue.qsize()), inline=True)
        thumbnail = get_thumbnail(track)
        embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed, delete_after=10)
        
    @commands.command(name="queue", aliases=["q", "list"], help="Menampilkan antrian list lagu yang akan diputar")
    async def queue(self, ctx: commands.Context):
        player : GomuPlayer = ctx.voice_client
        if not player or not player.is_connected:

            embed= discord.Embed(
                title=f"Bot tidak ada di voice channel",
                description=f"Pastikan kamu ada di voice yang sama dengan bot ya",
                color=self.colour
            )
            return await ctx.send(embed=embed)
        player: GomuPlayer = ctx.voice_client
        queue = player.queue
        if queue.is_empty:
            embed = discord.Embed(
                title=f"Antrian Lagu Kosong",
                description=f"Maaf {ctx.author} saat ini antrianmu kosong, ketik g!play [judul lagu] untuk menambahkan lagu kedalam antrian"
            )
            return await ctx.send(embed=embed)
        
        view = QueuePagination(queue=player.queue, per_page=10)

        try:
            await ctx.send(embed=view.get_embed(), view=view)
        except Exception as e:
            logger.info(f"Ada masalah saat menampilkan Queue : {e}")

    @commands.command(name="skip", aliases=["s", ])
    async def skip(self, ctx: commands.Context):
        node = NodePool.get_node()
        player: GomuPlayer = node.get_player(ctx.guild.id)

        if not player or not player.is_playing:
            embed = discord.Embed(
                title=f"Tidak ada lagu",
                description=f"Maaf {ctx.author} saat ini antrianmu kosong, ketik g!play [judul lagu] untuk menambahkan lagu kedalam antrian"
            )
            return await ctx.send(embed=embed)
        embed = discord.Embed(
            title="Skipped",
            description=f"{player.current.title} berhasil di skip",
            color=self.colour
        )
        embed.set_footer(text=f"Requested by : {ctx.author}")
        await ctx.send(embed=embed, delete_after=10)
        await player.stop()

    @commands.command(name="stop", help="Menghentikan lagu dan keluar dari voice channel.")
    async def stop(self, ctx: commands.Context):
        player: GomuPlayer = ctx.voice_client

        if not player or not player.is_connected:
            return await ctx.send(embed=discord.Embed(
                title="Tidak Terhubung",
                description="Bot tidak sedang berada di voice channel.",
                color=self.colour
            ))
        
        player.queue.clear()
        await player.disconnect()

        await ctx.send(embed=discord.Embed(
            title="Pemutaran Dihentikan",
            description="Bot keluar dari voice channel dan antrian dibersihkan.",
            color=self.colour
        ))

    @commands.command(name="autoplay", aliases=["ap","auto"], help="Auotplay lagu yang telah berakhir dengan lagu terkait (Related Song)")
    async def autoplay(self, ctx: commands.Context):
        player : GomuPlayer = ctx.voice_client

        if not player or not player.is_connected:
            return await ctx.send(embed=discord.Embed(
            title="Tidak Terhubung",
            description="Bot tidak sedang berada di voice channel.",
            color=self.colour
        ))

        self.get_node()
        current_autoplay = getattr(player, 'autoplay', False)
        player.autoplay = not current_autoplay

        if player.autoplay:
            await ctx.send(embed=discord.Embed(
                description=f"Autoplay Diaktifkan"
            ))
            logger.info('Berhasil Set Autoplay')
        else:
            await ctx.send(embed=discord.Embed(
                description=f"Autoplay Dinonaktifkan"
            ))
            logger.info('Autoplay Dinonaktifkan')
        return bool
    
    @commands.command(name="clear", help="Membersihkan antrian lagu yang ada (Clear Queue)")
    async def clear_queue(self, ctx: commands.Context, channel: discord.VoiceChannel = None):

        channel = channel or getattr(ctx.author.voice, "channel", None)
        if not channel:
            embed = discord.Embed(
                title="Kamu Lagi Ga Masuk Voice",
                description="Enak aja mau make tapi ga dimasukin dulu, no no yaaa :3",
                color=self.colour
            )
            embed.set_author(name="GoMu", icon_url="https://media.giphy.com/media/gahyl3UyyjdLhg0KoR/giphy.gif")
            return await ctx.send(embed=embed)

        
        if not ctx.voice_client:
            await ctx.send(embed=discord.Embed(description="Kamu harus berada di voice yang sama" ,color=self.colour))
            return
        player : GomuPlayer = ctx.voice_client
        queue_list = player.queue.get_queue()
        if queue_list:
            player.queue.clear()
            await ctx.send(embed=discord.Embed(description=f"Queue berhasil dibersihkan", color=self.colour))
        else:
            embed = discord.Embed(
                title=f"Antrian Lagu Kosong",
                description=f"Maaf {ctx.author} saat ini antrianmu kosong, ketik g!play [judul lagu] untuk menambahkan lagu kedalam antrian"
            )
            return await ctx.send(embed=embed)


    @commands.command(name="loop", aliases=["l"], help="Loop track yang sedang diputar.\n Mode = Track, Queue, Off")
    async def loop(self, ctx: commands.Context, mode: str):
        player: GomuPlayer = ctx.voice_client

        if not player or not player.is_connected:
            return await ctx.send(embed=discord.Embed(description="Bot sedang tidak berada di voice channel"))

        if not player.current:
            return await ctx.send(embed=discord.Embed(description="Tidak ada lagu yang sedang diputar untuk di-loop."))

        if not hasattr(player.queue, "set_loop_mode") or not hasattr(player.queue, "disable_loop"):
            return await ctx.send(embed=discord.Embed(description="Fitur loop tidak tersedia untuk antrian ini."))
        try:
            mode = mode.lower()  # Normalisasi input mode
            if mode in ["track", "lagu"]:
                player.queue.set_loop_mode(mode=pomice.LoopMode.TRACK)
                logger.info(f'Status Loop : {mode}')
                status = "Track Loop Diaktifkan 🔁"
            elif mode in ["queue", "playlist"]:
                tracks = player._current
                player.queue.set_loop_mode(mode=pomice.LoopMode.QUEUE)
                status = "Queue Loop Diaktifkan 🔁"
                logger.info(f'Status Loop : {mode}')
            elif mode in ["off", "none"]:
                player.queue.disable_loop()
                status = "Loop Dinonaktifkan ⏹️"
                logger.info(f'Status Loop : {mode}')
            else:
                return await ctx.send(embed=discord.Embed(description="Mode tidak valid. Gunakan 'Track', 'Queue', atau 'Off'."))

            await ctx.send(embed=discord.Embed(
                title="Loop Status",
                description=f"**{status}**",
                color=self.colour
            ))
        except Exception as e:
            logger.error(f"Error: {e}")
            await ctx.send(embed=discord.Embed(description="Terjadi kesalahan saat mengatur mode loop. Silakan coba lagi."))        

            
            
            if player.queue.loop_mode  == pomice.LoopMode.TRACK:
                logger.info("Lagu berhasil di Loop ke Track")
            elif player.queue.loop_mode == pomice.LoopMode.QUEUE :
                logger.info("Lagu berhasil di Loop ke Queue")
            else:
                logger.info("Lagu gagal di set loop")


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot))
