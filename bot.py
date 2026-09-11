import discord
from discord import app_commands
import random, json, os, asyncio
from dotenv import load_dotenv
from datetime import datetime
try:
    from battle_system import TERRENI, DOTTRINE, genera_divisione, calcola_battaglia_tick
except:
    TERRENI={"pianura":{"nome":"Pianura","width":120,"atk_mod":1,"def_mod":1,"desc":""}}
    DOTTRINE={"blitzkrieg":{"nome":"Blitz","tipo":"off","bonus_atk":0.3,"bonus_def":0,"desc":""}}

load_dotenv()
TOKEN=os.getenv("DISCORD_TOKEN")
GUILD_ID=os.getenv("GUILD_ID")
MASTER_ROLE_ID=1547815830430032013
DB_FILE="nazioni.json"

intents=discord.Intents.default()
intents.members=True
intents.message_content=True
client=discord.Client(intents=intents)
tree=app_commands.CommandTree(client)

def load_db():
    if not os.path.exists(DB_FILE): return {}
    import json
    with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
def save_db(d):
    import json
    with open(DB_FILE,"w",encoding="utf-8") as f: json.dump(d,f,indent=2,ensure_ascii=False)
def is_master(m):
    if not hasattr(m,'roles'): return False
    if m.guild.owner_id==m.id: return True
    return any(r.id==MASTER_ROLE_ID for r in m.roles)

@client.event
async def on_ready():
    print(f"PROELIUM SECURE {client.user} - {len(tree.get_commands())} comandi")
    if GUILD_ID:
        guild=discord.Object(id=int(GUILD_ID))
        synced=await tree.sync(guild=guild)
        print(f"SYNC GUILD {GUILD_ID} -> {len(synced)}: {[c.name for c in synced]}")

@client.event
async def on_message(message):
    if message.author.bot: return
    if message.content.strip()=="!force_sync" and is_master(message.author):
        guild=discord.Object(id=int(GUILD_ID))
        synced=await tree.sync(guild=guild)
        await message.channel.send(f"✅ Force sync GUILD {GUILD_ID} -> {len(synced)} comandi - Master: {message.author.mention}")
    if message.content.strip()=="!debug_guilds" and is_master(message.author):
        txt=f"Bot in {len(client.guilds)} server - Tree: {len(tree.get_commands())}\n"
        for g in client.guilds: txt+=f"- {g.name} {g.id}\n"
        await message.channel.send(f"```{txt[:1800]}```")

@tree.command(name="proelium_ping", description="Test slash")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 PONG - slash OK", ephemeral=True)

@tree.command(name="proelium_crea", description="[MASTER] Crea nazione")
async def crea(interaction: discord.Interaction, nome: str, soldi: int, stabilita: int, esercito: int, tecnologia: int, influenza: int):
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}>", ephemeral=True); return
    db=load_db(); nome=nome.upper(); db[nome]={"nome":nome,"soldi":soldi,"stabilita":stabilita,"esercito":esercito,"tecnologia":tecnologia,"influenza":influenza,"stabilita_attuale":stabilita,"soldi_attuale":soldi,"blocco":"NEUTRALE","nucleare":False,"flag":""}
    save_db(db); await interaction.response.send_message(embed=discord.Embed(title=f"✅ {nome} creata", color=0x00FF00))

@tree.command(name="proelium_scheda", description="Scheda nazione")
async def scheda(interaction: discord.Interaction, nome: str):
    db=load_db(); nome=nome.upper()
    if nome not in db: await interaction.response.send_message("Non trovata", ephemeral=True); return
    n=db[nome]; e=discord.Embed(title=n["nome"], color=0x2f3136); e.add_field(name="Stats", value=f"S{n['soldi']} ST{n['stabilita']} ES{n['esercito']} T{n['tecnologia']} I{n['influenza']}")
    await interaction.response.send_message(embed=e)

@tree.command(name="proelium_lista", description="Lista nazioni")
async def lista(interaction: discord.Interaction):
    db=load_db(); txt="\n".join(db.keys()) or "Nessuna"
    await interaction.response.send_message(embed=discord.Embed(title="Nazioni", description=f"```{txt[:3000]}```"))

@tree.command(name="proelium_battaglia", description="[MASTER] Battaglia HOI4 - solo ID 1547815830430032013")
async def battaglia(interaction: discord.Interaction, attaccante: str, difensore: str):
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}>", ephemeral=True); return
    await interaction.response.send_message(embed=discord.Embed(title=f"⚔️ {attaccante} vs {difensore}", description=f"Master: {interaction.user.mention} - Console blindata ID {MASTER_ROLE_ID}", color=0xFF4500))

if __name__=="__main__":
    client.run(TOKEN)
