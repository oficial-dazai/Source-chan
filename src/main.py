import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Evento para verificar se a Source-chan foi conectada com sucesso
@bot.event
async def on_ready():
    print(f'Bot conectado com sucesso como: {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro na sincronização: {e}")

# Comando para verificar a latência da Source-chan
@bot.command(name='ping')
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f'Pong! Latência {latency}ms')

# Evento para dar boas-vindas a novos membros
@bot.event
async def on_member_join(member):
    guild = member.guild
    if guild.system_channel:
        embed = discord.Embed(
            title='Bem-vindo a Source BR Community!',
            description=f'Olá {member.mention}, seja bem-vindo a **{guild.name}**!',
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else bot.user.avatar.url)
        await guild.system_channel.send(embed=embed)

# Comando para exibir informações sobre a Source-chan
@bot.command(name='sobre')
async def sobre(ctx):
    embed = discord.Embed(
        title='Sobre mim',
        description=f'Meu nome é Yumi Takahashi, mas você pode me chamar de Source-chan!',
        color=discord.Color.green()
    )
    embed.add_field(name='comandos disponiveis', value="`!ping`, `!sobre`", inline=False)
    embed.set_footer(text='Fui desenvolvida por: Dazai')
    await ctx.send(embed=embed)

bot.run(TOKEN)