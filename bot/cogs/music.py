# You can ignore all the commented out codes. They are all for eperimental purposes.

#Imports
import discord
from discord.ext import commands
import wavelink
import typing as t
import re
import datetime as dt
import asyncio
import random
# import time
from enum import Enum
import aiohttp

# Constants
URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
LYRICS_URL = "https://some-random-api.ml/lyrics?title="
HZ_BANDS = (20, 40, 63, 100, 150, 250, 400, 450, 630, 1000, 1600, 2500, 4000, 10000, 16000)
TIME_REGEX = r"([0-9]{1,2})[:ms](([0-9]{1,2})s?)?"
OPTIONS = {
    "1️⃣": 0,
    "2⃣": 1,
    "3⃣": 2,
    "4⃣": 3,
    "5⃣": 4,
}

# Classes for error handling
class AlreadyConnectedToChannel(commands.CommandError):
    pass

class NoVoiceChannel(commands.CommandError):
    pass

class QueueIsEmpty(commands.CommandError):
    pass

class NoTracksFound(commands.CommandError):
    pass

class PlayerIsAlreadyPaused(commands.CommandError):
    pass

class PlayerIsAlreadyPlaying(commands.CommandError):
    pass

class NoMoreTracks(commands.CommandError):
    pass

class NoPreviousTracks(commands.CommandError):
    pass

class InvalidRepeatMode(commands.CommandError):
    pass

class VolumeTooLow(commands.CommandError):
    pass

class VolumeTooHigh(commands.CommandError):
    pass

class MaxVolume(commands.CommandError):
    pass

class MinVolume(commands.CommandError):
    pass

class NoLyricsFound(commands.CommandError):
    pass

class InvalidEqPreset(commands.CommandError):
    pass

class NonExistentEQBand(commands.CommandError):
    pass

class EQGainOutOfBounds(commands.CommandError):
    pass

class InvalidTimeString(commands.CommandError):
    pass

class AlreadyDisconnected(commands.CommandError):
    pass

class AloneInVC(commands.CommandError):
    pass

# Effective classes start from here
class RepeatMode(Enum):
    NONE = 0
    ONE = 1
    ALL = 2

class Queue:
    # Initializing the queue
    def __init__(self):
        self._queue = []
        self.position = 0
        self.repeat_mode = RepeatMode.NONE # Initially no repeat mode will be called

    @property
    def is_empty(self):
        return not self._queue # Called when there is no items in the '_queue' list

    # Experimental purpose
    # @property
    # def first_track(self):
    #     if not self._queue:
    #         raise QueueIsEmpty

    #     return self._queue[0]

    @property
    def current_track(self):
        if not self._queue:
            raise QueueIsEmpty

        # If the position is within the list then returns that [position]th item from the list
        if self.position <= len(self._queue) - 1:
            return self._queue[self.position]

    @property
    def all_tracks(self):
        if not self._queue:
            raise QueueIsEmpty

        # Returns the whole list
        return self._queue

    @property
    def upcoming(self):
        if not self._queue:
            raise QueueIsEmpty

        # Gets from the next item of the current item to the last item of the list
        return self._queue[self.position + 1:]

    @property
    def history(self):
        if not self._queue:
            raise QueueIsEmpty

        # Gets the current item & the items before the current item from the list
        return self._queue[:self.position]

    @property
    def length(self):
        return len(self._queue) # Returns the queue length

    def add(self, *args):
        self._queue.extend(args) # Inserts new *args(arguments) into the list

    def get_next_track(self):
        if not self._queue:
            raise QueueIsEmpty

        self.position += 1

        if self.position < 0:
            return None
        elif self.position > len(self._queue) - 1:
            # If the postion value is greater than the length of the list & repeat mode is set to all we set the position to 0 so that the playlist can start over
            if self.repeat_mode == RepeatMode.ALL:
                self.position = 0
            else:
                return None
        
        return self._queue[self.position] # This gets the next track as the positoin is increased by 1

    def shuffle(self):
        if not self._queue:
            raise QueueIsEmpty

        # Only shuffles the upcoming tracks not the currently playing one
        upcoming = self.upcoming
        random.shuffle(upcoming)
        self._queue = self._queue[:self.position + 1]
        self._queue.extend(upcoming)

    def set_repeat_mode(self, mode):
        if mode == "none":
            self.repeat_mode = RepeatMode.NONE
        elif mode == "1":
            self.repeat_mode = RepeatMode.ONE
        elif mode == "all":
            self.repeat_mode = RepeatMode.ALL

    def empty(self):
        self._queue.clear() # Clears the whole queue

# This player is actually the 'Lavalink' player. This is how to connect to the lavalink player.
class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = Queue()
        self.eq_levels = [0.] * 15 # Creating 15 '0.0' items in the list for making rooms for band levels

    # Connects the player to the VC
    async def connect(self, ctx, channel=None):
        if self.is_connected:
            raise AlreadyConnectedToChannel

        if (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            raise NoVoiceChannel

        await super().connect(channel.id)
        return channel

    # Disconnects the player from the VC
    async def tearDown(self):
        try:
            await self.destroy()
        except KeyError:
            pass

    # Adds tracks to the player
    async def add_tracks(self, ctx, tracks):
        if not tracks:
            raise NoTracksFound

        # For multiple tracks at a time
        if isinstance(tracks, wavelink.TrackPlaylist):
            self.queue.add(*tracks.tracks)
        # For single track at a time
        elif len(tracks) == 1:
            self.queue.add(tracks[0])
            await ctx.reply(f"Added {tracks[0].title} to the queue")
        else:
            # When a track is added using name
            if(track := await self.choose_track(ctx, tracks)) is not None:
                self.queue.add(track)
                await ctx.reply(f"Added {track.title} to the queue")
            # When a track is added using an url
            elif(track := await re.match(URL_REGEX, link)) is not None:
                self.queue.add(track)
                await ctx.reply(f"Added {track.title} to the queue")

        if not self.is_playing and not self.queue.is_empty:
            await self.start_playback()

    # Track search result choice by reacting the message
    async def choose_track(self, ctx, tracks):
        # r = reaction, u = user
        def _check(r, u):
            return (
                r.emoji in OPTIONS.keys() # Loading the emojies in 'r'
                and u == ctx.author # Assigning 'u' for the user
                and r.message.id == msg.id # Reacting to the message
            )

        # Sending the embeded search result
        embed = discord.Embed(
            title="Pick your song :relieved:",
            description=(
                "\n".join(
                    f"**{i+1}.** {t.title} ({t.length//60000}:{str(t.length%60).zfill(2)})"
                    for i, t in enumerate(tracks[:5]) # Assigning each serial number to each search result
                )
            ),
            colour=ctx.author.colour,
            timestamp=dt.datetime.utcnow()
        )
        embed.set_author(name="Search Results")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)

        # Emote react will be done to this embeded message
        msg = await ctx.reply(embed = embed)
        for emoji in list(OPTIONS.keys())[:min(len(tracks), len(OPTIONS))]:
            await msg.add_reaction(emoji)

        try:
            # Waits for the user to react for 60s. The reactions are assigned to the serial numbers.
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=_check)
        except asyncio.TimeoutError:
            # If no response is found from the user, the message gets deleted after 60s
            await msg.delete()
            await ctx.message.delete()
        else:
            # Gets instantly deleted if response found
            await msg.delete()
            return tracks[OPTIONS[reaction.emoji]] # Gets the track through reaction & adds to the queue

    async def start_playback(self):
        await self.play(self.queue.current_track)

    async def advance(self):
        try:
            if (track := self.queue.get_next_track()) is not None:
                await self.play(track)
        except QueueIsEmpty:
            pass
    # When the repeat mode is set to '1'
    async def repeat_track(self):
        await self.play(self.queue.current_track)

class Music(commands.Cog, wavelink.WavelinkMixin):
    msg_chnl = None
    
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.wavelink = wavelink.Client(bot=bot)
        self.bot.loop.create_task(self.start_nodes())

    @commands.command(name="connect", aliases=["join"])
    async def connect_command(self, ctx, *, channel: t.Optional[discord.VoiceChannel]):
        """=> Connects the bot to a VC.\n
         This command can also be accessed by using '>>join'\n
         Normally this command will connect the bot to the same VC of the commander.\n
         But specifying a VC name after the command syntax will make the bot to join the specified VC (e.g. >>join VC_name)"""
        self.msg_chnl = ctx.channel.id
        # print(self.msg_chnl)
        player = self.get_player(ctx)
        channel = await player.connect(ctx, channel)
        await ctx.reply(f"YAY, I'm connected to <#{channel.id}>! :partying_face:")

    @connect_command.error
    async def connect_command_error(self, ctx, exc):
        if isinstance(exc, AlreadyConnectedToChannel):
            await ctx.reply("I'm already connected to a VC! 😐")
        elif isinstance(exc, NoVoiceChannel):
            await ctx.reply("That VC is not very suitable for me! 😔")
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        channel = None
        
        # Gets the currently connected channel
        if self.msg_chnl is not None:    
            channel = discord.utils.get(member.guild.channels, id= self.msg_chnl)
            
        # If only the bot stays in the VC & no one else, bot will be disconnected within 300s
        if (not member.bot) and (after.channel is None):
            if len([m for m in before.channel.members]) == 1:
                await asyncio.sleep(300)
                await self.get_player(member.guild).tearDown()

                if channel is not None:    
                    await channel.send("No one was listening to my singing so I've disconnected myself from the VC! :unamused: ")

    # Configures the lavalink player from the informations of the nodes
    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node):
        print(f" Wavelink node `{node.identifier}` is ready!")

    # Player will be stopped for these reasons unless there is a repeat mode on.
    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self, node, payload):
        if payload.player.queue.repeat_mode == RepeatMode.ONE:
            await payload.player.repeat_track()
        else:
            await payload.player.advance()

    async def cog_check(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send(" :warning: **I'm not open for DM** :warning: ")
            await ctx.send("Go away, shooh! :stuck_out_tongue_closed_eyes: ")
            return False
        
        return True

    # Configuration of the lavalink player
    async def start_nodes(self):
        await self.bot.wait_until_ready()

        nodes = {
            "MAIN": {
                "host": "127.0.0.1",
                "port": 2333,
                "rest_uri": "http://127.0.0.1:2333",
                "password": "youshallnotpass",
                "identifier": "MAIN",
                "region": "bangladesh"
            }
        }

        for node in nodes.values():
            await self.wavelink.initiate_node(**node)

    # Setting up the player
    def get_player(self, obj):
        if isinstance(obj, commands.Context):
            return self.wavelink.get_player(obj.guild.id, cls=Player, context=obj)
        elif isinstance(obj, discord.Guild):
            return self.wavelink.get_player(obj.id, cls=Player)

    # @commands.command(name="connect", aliases=["join"])
    # async def connect_command(self, ctx, *, channel: t.Optional[discord.VoiceChannel]):
    #     """=> Connects the bot to a VC.\n
    #      This command can also be accessed by using '>>join'\n
    #      Normally this command will connect the bot to the same VC of the commander.\n
    #      But specifying a VC name after the command syntax will make the bot to join the specified VC (e.g. >>join VC_name)"""
    #     msg_chnl = ctx.channel.id
    #     print(msg_chnl)
    #     player = self.get_player(ctx)
    #     channel = await player.connect(ctx, channel)
    #     await ctx.reply(f"YAY, I'm connected to <#{channel.id}>! :partying_face:")

    # @connect_command.error
    # async def connect_command_error(self, ctx, exc):
    #     if isinstance(exc, AlreadyConnectedToChannel):
    #         await ctx.reply("I'm already connected to a VC! 😐")
    #     elif isinstance(exc, NoVoiceChannel):
    #         await ctx.reply("That VC is not very suitable for me! 😔")

    @commands.command(name="disconnect", aliases=["leave"])
    async def disconnect_command(self, ctx):
        """=> Disconnects the bot from the VC.\n
         This command can also be accessed by using '>>leave'"""
        player = self.get_player(ctx)

        if not player.is_connected:
            raise AlreadyDisconnected

        await player.tearDown()
        await ctx.reply("Okay, I've disconnected from the VC! 👌")

    @disconnect_command.error
    async def disconnect_command_error(self, ctx, exc):
        if isinstance(exc, AlreadyDisconnected):
            await ctx.reply("I'm already disconnected! :neutral_face: ")

    @commands.command(name="play", aliases=["p"])
    async def play_command(self, ctx, *, query: t.Optional[str]):
        """=> Plays the requested music.\n
         This command can also be accessed by using '>>p'.\n
         If a music is playing and a new music is requested to play, the new music will be queued.\n
         If this command is invoked without any query during a music is paused, this will work as 'resume'.\n
         This command can be either used with a link of the music or a name of the music.\n
         URL syntax: '>>play https://example.com/music_url/'\n
         Name syntax: '>>play music_name_with_music_author'\n
         After a name search, top 5(five) search results will be shown. Pick your desired music from them simply by reacting the number of the search results."""
        player = self.get_player(ctx)

        global link
        link = query

        if not player.is_connected:
            self.msg_chnl = ctx.channel.id
            await player.connect(ctx)

        if query is None:
            if player.is_playing and not player.is_paused:
                raise PlayerIsAlreadyPlaying

            if player.queue.is_empty:
                raise QueueIsEmpty
            
            await player.set_pause(False)
            await ctx.reply("Gladly resuming the music! 🤗")
        else:
            query = query.strip("<>")
            if not re.match(URL_REGEX, query):
                query = f"ytsearch:{query}"

            await player.add_tracks(ctx, await self.wavelink.get_tracks(query))

    @play_command.error
    async def play_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPlaying):
            await ctx.reply("Already singing something! 🧐")
        elif isinstance(exc, QueueIsEmpty):
            await ctx.reply("Nothing to sing as the queue is empty! :yawning_face: ")

    @commands.command(name="resume", aliases=["r"])
    async def resume_command(self, ctx):
        """=> Resumes the currently playing music.\n
         This command can aslo be accessed by using '>>r'.\n
         This is a typical resume command & does nothing special.\n"""
        player = self.get_player(ctx)

        if player.is_playing and not player.is_paused:
            raise PlayerIsAlreadyPlaying

        if player.queue.is_empty:
            raise QueueIsEmpty

        await player.set_pause(False)
        await ctx.reply("Gladly resuming the music! 🤗")

    @resume_command.error
    async def resume_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPlaying):
            await ctx.reply("Already singing something! 🧐")
        elif isinstance(exc, QueueIsEmpty):
            await ctx.reply("Nothing to sing as the queue is empty! :yawning_face: ")

    @commands.command(name="pause", aliases=["ps"])
    async def pause_command(self, ctx):
        """=> Pauses the currently playing music.\n
         This command can also be accessed by using '>>ps'.\n
         This is a typical pause command & does nothing special.\n"""
        player = self.get_player(ctx)

        if player.is_paused:
            raise PlayerIsAlreadyPaused

        await player.set_pause(True)
        await ctx.reply("Okay, paused! 👌")

    @pause_command.error
    async def pause_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPaused):
            await ctx.reply("Already paused! 😕")

    @commands.command(name="stop", aliases=["s"])
    async def stop_command(self, ctx):
        """=> Stops the currently playing music & clears the queue.\n
         This command can also accessed by using '>>s'.\n
         This stops the music & clears the queue to take a new playlist or new musics.\n"""
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty

        player.queue.empty()
        await player.stop()
        await ctx.reply("Bene, stopping singing & clearing your playlist. :innocent:")

    @stop_command.error
    async def stop_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.reply("Already stopped & queue is cleared! 😕")

    @commands.command(name="next", aliases=["skip"])
    async def next_command(self, ctx):
        """=> Plays the next music from the queue.\n
         This command can also be accessed by using '>>skip'.\n"""
        player = self.get_player(ctx)

        if not player.queue.upcoming:
            raise NoMoreTracks

        await player.stop()
        await ctx.reply("Singing next music of your playlist! :sunglasses: ")

    @next_command.error
    async def next_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.reply("Can't do that. The queue is empty! :woozy_face: ")
        elif isinstance(exc, NoMoreTracks):
            await ctx.reply("Can't do that. This is the last music of your playlist! :woozy_face: ")

    @commands.command(name="previous", aliases=["pr"])
    async def previous_command(self, ctx):
        """=> Plays the previous music of the currently playing music.\n
         This command can also be accessed by using '>>pr'.\n"""
        player = self.get_player(ctx)

        if not player.queue.history:
            raise NoPreviousTracks

        # Decreasing by 2 because when the player stops it advances by 1. So the previous track of the currently playing track will require 2 minus.
        player.queue.position -= 2
        await player.stop()
        await ctx.reply("Sure, singing the previous music of this one from your playlist! :sunglasses: ")

    @previous_command.error
    async def previous_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.reply("Can't do that. The queue is empty! :woozy_face: ")
        elif isinstance(exc, NoPreviousTracks):
            await ctx.reply("Can't do that. You haven't told me to sing anything before this music! :face_with_monocle: ")

    @commands.command(name="shuffle", aliases=["sf"])
    async def shuffle_command(self, ctx):
        """=> Shuffles the whole playlist.\n
         This command can also be accessed by using '>>sf'.\n"""
        player = self.get_player(ctx)

        player.queue.shuffle()
        await ctx.reply("Playlist shuffled! :love_you_gesture: ")

    @shuffle_command.error
    async def shuffle_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.reply("There is nothing in the queue to shuffle! :frowning2: ")

    @commands.command(name="repeat", aliases=["rp"])
    async def repeat_command(self, ctx, mode: str):
        """=> Sets a repeat mode.\n
         This command can also be accessed by using '>>rp'.\n
         Command syntax: >>repeat [repeat_mode]\n
         There are three repeat modes: 'none', '1', 'all'\n
         none = Repeats no music. Stops after the playlist is over.\n
         1 = Repeats the currently playing music.\n
         all = Repeats the entire playlist.\n
         Note that, these repeat modes are 'case sensitive'. So please use the repeat modes as shown.\n"""
        if mode not in ("none", "1", "all"):
            raise InvalidRepeatMode

        player = self.get_player(ctx)
        player.queue.set_repeat_mode(mode)

        await ctx.reply(f"Repeat mode has been set to {mode}. :boomerang: ")

    @repeat_command.error
    async def repeat_command_error(self, ctx, exc):
        if isinstance(exc, InvalidRepeatMode):
            await ctx.reply("I've never heard of that kinda repeat mode! :slight_frown: ")

    @commands.command(name="queue", aliases=["q"])
    async def queue_command(self, ctx, show: t.Optional[int] = 10):
        """=> Shows the queue of your added musics.\n
         This command can also be accessed by using '>>q'.\n
         By default this command will show the next 10 musics of the queue. But assigning a number[MAX upto 15 at a time] after the command will show up next that number of music(s) [e.g. >>queue 2, will show the next 2 musics of the queue].\n"""
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty

        embed = discord.Embed(
            title = "Queue",
            description = f"Showing up to next {show} tracks (If there is any 🙄)",
            colour = ctx.author.colour,
            timestamp = dt.datetime.utcnow()
        )
        embed.set_author(name="Here is your playlist")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
        embed.add_field(name="🎵Currently playing🎵", 
            value=getattr(player.queue.current_track, "title", "Currently singing nothing :grin: "), 
            inline=False)
        if upcoming := player.queue.upcoming:
            embed.add_field(
                name="Next up:",
                value="\n".join(str(t+2)+'. '+upcoming[t].title for t in range(min(len(upcoming), show))),
                inline=False
            )
        
        msg = await ctx.reply(embed = embed)

    @queue_command.error
    async def queue_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.reply("The queue is currently empty! 😟")

    @commands.command(name="playlist", aliases=["pl"])
    async def playlist_command(self, ctx):
        """=> Shows the full playlist of added musics.\n
         This command can also be accssed by using '>>pl'.\n"""
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty

        dscrption = ""
        i = 0

        while len(dscrption) <= 2000 and i < len(player.queue.all_tracks):
            dscrption += '**'+str(i+1)+"**. "+player.queue.all_tracks[i].title+'\n'
            i += 1

        if i < len(player.queue.all_tracks)-1:
            dscrption += f"and {str(len(player.queue.all_tracks)-(i+1))} more tracks..."

        embed = discord.Embed(
            title="Playlist",
            #description = "\n".join('**'+str(j+1)+"**. "+player.queue.all_tracks[j].title for j in range(len(player.queue.all_tracks))),
            description = dscrption,
            colour = ctx.author.colour,
            timestamp = dt.datetime.utcnow()
        )
        embed.set_author(name=str(len(player.queue.all_tracks))+" tracks")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
        
        # message = "\n".join(i.title for i in player.queue.all_tracks)

        await ctx.reply(embed = embed)

    @playlist_command.error
    async def playlist_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.reply("You haven't told me to sing anything yet! :stuck_out_tongue: ")

    @commands.group(name="volume", invoke_without_command=True, aliases=['v'])
    async def volume_group(self, ctx, volume: int):
        """=> Adjusts the volume.\n
         This command can also be accessed by using '>>v'.\n
         By default the volume should be set to 100\n
         Command syntax: '>>volume [any value from 0 to 200]'\n
         There are two additional sub-commands of this command.\n"""
        player = self.get_player(ctx)

        if volume < 0:
            raise VolumeTooLow
        
        if volume > 200:
            raise VolumeTooHigh

        await player.set_volume(volume)
        await ctx.reply(f"Sure, volume set to {volume:,}% :sound: ")

    @volume_group.error
    async def volume_group_error(self, ctx, exc):
        if isinstance(exc, VolumeTooLow):
            await ctx.reply("You're telling me to mutter??\nYou won't hear anything if i sing below **0** volume! :mute: ")
        elif isinstance(exc, VolumeTooHigh):
            await ctx.reply("I can't scream louder than **200** volume! :cold_face: ")

    @volume_group.command(name="up")
    async def volume_up_command(self, ctx):
        """=> Increases the volume by 10.\n
         Command syntax: '>>volume up'\n"""
        player = self.get_player(ctx)

        if player.volume == 200:
            raise MaxVolume

        await player.set_volume(value := min(player.volume +10, 200))
        await ctx.reply(f"Sure, volume set to {value:,}% :sound: ")

    @volume_up_command.error
    async def volume_up_command_error(self, ctx, exc):
        if isinstance(exc, MaxVolume):
            await ctx.reply("I'm already singing at my maximum volume! :smirk_cat: ")

    @volume_group.command(name="down")
    async def volume_down_command(self, ctx):
        """=> Decreases the volume by 10.\n
         Command syntax: '>>volume down'\n"""
        player = self.get_player(ctx)

        if player.volume == 0:
            raise MinVolume

        await player.set_volume(value := max(0, player.volume -10))
        await ctx.reply(f"Sure, volume set to {value:,}% :sound: ")

    @volume_down_command.error
    async def volume_down_command_error(self, ctx, exc):
        if isinstance(exc, MinVolume):
            await ctx.reply("If I sing less than this volume that will be below 20Hz & you will be hearing nothing! :mute: ")

    @commands.command(name="lyrics", aliases=["lr"])
    async def lyrics_command(self, ctx, *, name: t.Optional[str]):
        """=> Gets the lyrics of a music.\n
         This command can also be accssed by using '>>lr'.\n
         If only this command is called while a track is playing, lyrics of the current track will be shown.\n
         Another syntax: '>>lyrics [name_of_a_track]'\n
         This way lyrics of the track that is requesed will be shown.\n"""
        player = self.get_player(ctx)
        name = name or player.queue.current_track.title

        async with ctx.typing():
            async with aiohttp.request("GET", LYRICS_URL + name, headers={}) as r:
                if not 200 <= r.status <= 299:
                    raise NoLyricsFound

                data = await r.json()

                if len(data["lyrics"]) > 2000:
                    return await ctx.reply(f"<{data['links']['genius']}>")

                embed = discord.Embed(
                    title=data["title"],
                    description=data["lyrics"],
                    colour=ctx.author.colour,
                    timestamp=dt.datetime.utcnow()
                )
                embed.set_thumbnail(url=data["thumbnail"]["genius"])
                embed.set_author(name=data["author"])
                await ctx.reply(embed = embed)

    @lyrics_command.error
    async def lyrics_command_error(self, ctx, exc):
        if isinstance(exc, NoLyricsFound):
            await ctx.reply("I have no idea about the lyrics of this song! :pensive: ")

    @commands.command(name="equalizer", aliases=["eq"])
    async def equalizer_command(self, ctx, preset: str):
        """=> Sets a music preset.\n
         This command can also be accessed by using '>>eq'.\n
         This can set the player to 'flat', 'boost', 'metal' & 'piano' presets.\n
         Use 'flat' preset to reset the equalizer.\n"""
        player = self.get_player(ctx)

        eq = getattr(wavelink.eqs.Equalizer, preset, None)

        if not eq:
            raise InvalidEqPreset

        await player.set_eq(eq())
        await ctx.reply(f"Sugoi! I'll sing in {preset} preset. :control_knobs: ")

    @equalizer_command.error
    async def equalizer_command_error(self, ctx, exc):
        if isinstance(exc, InvalidEqPreset):
            await ctx.reply("I have no idea about that preset! :smiling_face_with_tear: ") # flat, boost, metal & piano default presets

    @commands.command(name="mixer", aliases=["mx"])
    async def mixer_command(self, ctx, band: int, gain: float):
        """=> Mixes the audio frequencies.\n
         This command can also be accssed by using '>>mx'.\n
         Command Syntax: '>>mixer [band] [gain]'\n
         Band List = [20, 40, 63, 100, 150, 250, 400, 450, 630, 1000, 1600, 2500, 4000, 10000, 16000]\n
         Any band from the list can be picked either by just typing the desired band or by their index.\n
         Gain will only work between -10 dB & 10 dB.\n
         N.B. 'This feature is highly recommended to use only if you know what you're doing!'\n"""
        player = self.get_player(ctx)

        if not 1 <= band <= 15 and band not in HZ_BANDS:
            raise NonExistentEQBand

        if band > 15:
            band = HZ_BANDS.index(band) + 1

        if abs(gain) > 10:
            raise EQGainOutOfBounds

        player.eq_levels[band - 1] = gain / 10
        eq = wavelink.eqs.Equalizer(levels=[(i, gain) for i, gain in enumerate(player.eq_levels)])
        await player.set_eq(eq)
        await ctx.reply("Cool, your customly mixed equalizer received! :musical_score: ")

    @mixer_command.error
    async def mixer_command_error(self, ctx, exc):
        if isinstance(exc, NonExistentEQBand):
            await ctx.reply("That band is out of my bounds!!! :face_with_spiral_eyes: ")
        elif isinstance(exc, EQGainOutOfBounds):
            await ctx.reply("You wanna blow your ears!? Keep the gain between 10 dB & -10 dB. :rolling_eyes: ")

    @commands.command(name="playing", aliases=["np"])
    async def playing_command(self, ctx):
        """=> Shows currently playing music with some info.\n
         This command can also be accessed by using '>>np'.\n"""
        player = self.get_player(ctx)

        if not player.is_playing:
            raise PlayerIsAlreadyPaused

        embed = discord.Embed(
            title=" :musical_note: Now Playing :musical_note: ",
            colour=ctx.author.colour,
            timestamp = dt.datetime.utcnow()
        )
        embed.set_author(name="Music Information")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
        embed.add_field(name="Track title", value=player.queue.current_track.title, inline=False)
        embed.add_field(name="Artist", value=player.queue.current_track.author, inline=False)

        position = divmod(player.position, 60000)
        length = divmod(player.queue.current_track.length, 60000)
        embed.add_field(
            name="Position",
            value=f"{int(position[0])}:{round(position[1]/1000):02}/{int(length[0])}:{round(length[1]/1000):02}",
            inline=False
        )

        await ctx.reply(embed=embed)

    @playing_command.error
    async def playing_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPaused):
            await ctx.reply("Currently I'm singing nothing! :sleeping: ")

    @commands.command(name="skipto", aliases=["playindex", "number", "num", "index", "idx"])
    async def skipto_command(self, ctx, index: int):
        """=> Skips to a certain index of the playlist.\n
         This command can also be accessed by using '>>playindex', '>>number', '>>num', '>>index' or '>>idx'.\n
         Command syntax: '>>skipto [index]'\n
         The first track of the playlist will be index 1 even if that is currently playing.\n"""
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty
        
        if not 0 <= index <= player.queue.length:
            raise NoMoreTracks

        player.queue.position = index - 2
        await player.stop()
        await ctx.reply(f"Alright, singing song number {index} from your playlist. :alien: ")

    @skipto_command.error
    async def skipto_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.reply("Check the queue, it's empty! :face_exhaling: ")
        elif isinstance(exc, NoMoreTracks):
            await ctx.reply("You haven't told me to add that much songs to the queue! :interrobang: ")

    @commands.command(name="restart", aliases=["rst"])
    async def restart_command(self, ctx):
        """=> Starts over the currently playing music.\n
         This command can also be accessed by using '>>rst'.\n"""
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty

        await player.seek(0)
        await ctx.reply("Daijoubu, I'll start over this track again. :cyclone: ")

    @restart_command.error
    async def restart_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.reply("Check the queue, it's empty! :face_exhaling: ")

    @commands.command(name="seek", aliases=["sk"])
    async def seek_command(self, ctx, position: str):
        """=> Seeks to a certain point of the currently playing music.\n
         This command can aslo be accessed by using '>>sk'.\n
         Command syntax: '>>seek [minute]m[second]'\n"""
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty

        if not (match := re.match(TIME_REGEX, position)):
            raise InvalidTimeString

        if match.group(3):
            secs = (int(match.group(1)) * 60) + (int(match.group(3)))
        else:
            secs = int(match.group(1))

        await player.seek(secs * 1000)
        await ctx.reply("Daijoubu, I'll sing from that part of the track. :smirk_cat: ")

    @seek_command.error
    async def seek_command_error(self, ctx, exc):
        if isinstance(exc, InvalidTimeString):
            await ctx.reply("That moment is not there in the track, check the duration! :face_with_monocle: ")
        elif isinstance(exc, QueueIsEmpty):
            await ctx.reply("Check the queue, it's empty! :face_exhaling: ")

# Sets the cogs for the bot
def setup(bot):
    bot.add_cog(Music(bot))