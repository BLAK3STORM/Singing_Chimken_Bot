from pathlib import Path
import discord
from discord.ext import commands

class MusicBot(commands.Bot):
    def __init__(self):
        self._cogs = [p.stem for p in Path(".").glob("./bot/cogs/*.py")] # Accessing all the cogs
        super().__init__(command_prefix= self.prefix, case_insensitive= True, intents=discord.Intents.all())

    def setup(self):
        print("Running Setup...")

        # Loading the accessed cogs
        for cog in self._cogs:
            self.load_extension(f"bot.cogs.{cog}")
            print(f" Loaded `{cog}` cog")
        
        print("Setup Complete!")

    def run(self):
        self.setup()

        # Loading the token
        with open("data/token.0", "r", encoding="utf-8") as f:
            TOKEN = f.read()

        print("Running the BOT...")
        super().run(TOKEN, reconnect=True) # Bot of this token will run

# Some auxiliary functions
    async def shutdown(self):
        print("Closing connection to Discord...")
        await super().close()

    async def close(self):
        print("Closing on keyboard interrupt...")
        await self.shutdown()

    async def on_connect(self):
        print(f" Connected to Discord (latency: {self.latency*1000:,.0f} ms)")

    async def on_resumed(self):
        print("Bot resumed.")
    
    async def on_disconnect(self):
        print("Bot disconnected.")

    async def on_error(self, err, *args, **kwargs):
        raise

    async def on_command_error(self, ctx, exc):
        raise getattr(exc, "original", exc)

    async def on_ready(self):
        self.client_id = (await self.application_info()).id
        print("Bot is powered up & ready to do some COOL STUFFS!!!")

        # Discord RPC & activity status
        await self.change_presence(status=discord.Status.do_not_disturb, activity=discord.Game(name="A Cool Chicken"))

    # Command prefix
    async def prefix(self, bot, msg):
        return commands.when_mentioned_or(">>")(bot, msg)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=commands.Context)

        if ctx.command is not None:
            await self.invoke(ctx)

    # Will only read the messages which starts with the command prefix
    async def on_message(self, message):
        if not message.author.bot:
            await self.process_commands(message)