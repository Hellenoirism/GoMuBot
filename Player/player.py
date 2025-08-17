import pomice
import discord
import json
import aiohttp
from pomice.spotify.exceptions import SpotifyRequestException, InvalidSpotifyURL
import time
from urllib.parse import quote
from discord.ext import commands 
from Player.queue import GomuQueue
from pomice.spotify.client import Client
from pomice import TrackType, PlaylistType, Playlist, Track, TrackType
from contextlib import suppress
from utils.utillity import format_duration, get_thumbnail, build_progress_bar, logger


class GomuPlayer(pomice.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = GomuQueue()
        self.ctx: commands.Context = None
        self.controller: discord.Message = None
        self.autoplay = False

    async def get_recommendations(self, track: Track) -> Playlist | None:
            return await self._get_spotify_recommendations()
    

    
    async def get_spotify_recommendations_custom(self, track: pomice.Track, market: str = "ID", limit: int = 5):
        """Mengambil rekomendasi Spotify dengan parameter market."""
        spotify_client = self.bot.spotify_client
        if not spotify_client:
            logger.error("SpotifyClient tidak tersedia")
            return []

        if not spotify_client._bearer_token or time.time() >= spotify_client._expiry:
            await spotify_client._fetch_bearer_token()

        track_id = track.uri.split("/")[-1]  # Ambil ID dari URI
        logger.debug(f"Requesting Spotify recommendations for track_id: {track_id}, market: {market}")
        async with spotify_client.session.get(
            f"https://api.spotify.com/v1/recommendations?seed_tracks={track_id}&market={market}&limit={limit}",
            headers=spotify_client._bearer_headers
        ) as resp:
            if resp.status != 200:
                logger.error(f"Error while fetching recommendations: {resp.status} {resp.reason}")
                raise SpotifyRequestException(f"Error while fetching results: {resp.status} {resp.reason}")
            data = await resp.json()
            tracks = [
                pomice.Track(
                    track_id=track["id"],
                    info={
                        "title": track["name"],
                        "author": ", ".join(artist["name"] for artist in track["artists"]),
                        "uri": track["uri"],
                        "identifier": track["id"],
                        "length": track["duration_ms"],
                        "is_stream": False,
                        "source_name": "spotify",
                        "artwork_url": track.get("album", {}).get("images", [{}])[0].get("url"),
                        "isrc": track.get("external_ids", {}).get("isrc")
                    }
                )
                for track in data["tracks"]
            ]
            logger.info(f"Retrieved {len(tracks)} Spotify recommendations")
            return tracks
    

    async def _get_youtube_recommendations(self) -> Playlist:
        identifier = self.current.identifier
        uri = f"https://www.youtube.com/watch?v={identifier}&list=RD{identifier}"
        query = f"identifier={quote(uri)}"

        data = await self.node.send(
            method="GET",
            path="loadtracks",
            query=query,
        )

        track_data = data['data']['tracks'][1:]
        tracks = [
            Track(
                track_id=track["encoded"],
                info=track["info"],
                track_type=TrackType(track["info"]["sourceName"]),
            )
            for track in track_data
        ]

        return Playlist(
            playlist_info=data.get('playlistInfo', {}),
            tracks=tracks,
            playlist_type=PlaylistType(tracks[0].track_type.value),
            thumbnail=tracks[0].thumbnail,
            uri=uri,
        )
    
    async def set_context(self, ctx: commands.Context):
        self.ctx = ctx
        self.dj = ctx.author


    async def get_controler(self):
        return self.controller
    
    async def do_next(self) -> None:
        try:
            track : pomice.Track = self.queue.get()
        except pomice.QueueEmpty:
            if self.ctx:
                embed = discord.Embed(
                    description="Tidak ada lagu tersisa. Gunakan `g!play` untuk menambahkan lagu.",
                    color=discord.Color.blurple()
                )
                await self.ctx.send(embed=embed, delete_after=8)
                self.controller = None
            return

        await self.play(track)
        if self.ctx:
            embed = await self.create_now_playing_embed(track)

            if self.controller:
                try:
                    await self.controller.delete()
                except discord.NotFound:
                    pass

            self.controller = await self.ctx.send(embed=embed)
            logger.info('Embed diperbarui')

    async def teardown(self):
        """Clear internal states, remove player controller and disconnect."""
        with suppress((discord.HTTPException), (KeyError)):
            await self.destroy()

    async def create_now_playing_embed(self, track: pomice.Track) -> discord.Embed:
        position_ms = self.position
        duration_ms = track.length

        progress_bar = build_progress_bar(position_ms, duration_ms)
        position_str = format_duration(position_ms)
        duration_str = format_duration(duration_ms)

        loop_mode = self.queue.loop_mode
        if loop_mode is pomice.LoopMode.TRACK:
            loop_mode = "Track"
        elif loop_mode is pomice.LoopMode.QUEUE:
            loop_mode = "Queue"
        else:
            loop_mode = "Off"

        embed = discord.Embed(
            description=f"{track.title} - {track.author}",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Track Length", value=f"{progress_bar}\n `{position_str} / {duration_str}`", inline=False)
        embed.set_author(name="GoMu Player", icon_url="https://media.giphy.com/media/gahyl3UyyjdLhg0KoR/giphy.gif")
        embed.add_field(name="Volume", value=f"{self.volume}%", inline=True)
        embed.add_field(name="🔁 Status Loop", value=f"{loop_mode}", inline=True)
        embed.set_footer(text=f"Requested by {self.ctx.author}", icon_url=self.ctx.author.display_avatar.url)

        thumbnail = get_thumbnail(track)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        return embed