import discord
from discord import app_commands
import random, json, os, asyncio
from dotenv import load_dotenv
from datetime import datetime

# Importazione del battle system personalizzato
try:
    from battle_system import TERRENI, DOTTRINE, genera_divisione, calcola_battaglia_tick
except ImportError:
    # Fallback di sicurezza se il file battle_system.py manca
    TERRENI = {"pianura": {"nome": "Pianura", "width": 120, "atk_mod": 1, "def_mod": 1, "desc": ""}}
    DOTTRINE = {"blitzkrieg": {"nome": "Blitz", "tipo": "off", "bonus_atk": 0.3, "bonus_def": 0, "desc": ""}}
    def genera_divisione(tipo, tech=1): return {}
    def calcola_battaglia_tick(att, dif, terr, dott_a, dott_d): return "Simulazione base"

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

MASTER_ROLE_ID = 1547815830430032013
MASTER_ROLES = ["Master", "Amministratore PROELIUM", "Admin", "PROELIUM Master"]

DB_FILE = "nazioni.json"
DEFCON_FILE = "defcon.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# --- FUNZIONI DATABASE ---
def load_db():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)

def load_defcon():
    if not os.path.exists(DEFCON_FILE): return {"level": 4, "history": []}
    with open(DEFCON_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_defcon(data):
    with open(DEFCON_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)

def is_master(member: discord.Member):
    if not hasattr(member, 'roles'): return False
    if member.guild.owner_id == member.id: return True
    if any(r.id == MASTER_ROLE_ID for r in member.roles): return True
    user_roles = [r.name for r in member.roles]
    return any(m in user_roles for m in MASTER_ROLES)

async def log_action(interaction: discord.Interaction, text: str):
    if LOG_CHANNEL_ID:
        try:
            ch = client.get_channel(int(LOG_CHANNEL_ID))
            if ch:
                await ch.send(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {text}")
        except:
            pass

# --- EVENTI BOT ---
@client.event
async def on_ready():
    print(f"PROELIUM SECURE online come {client.user}")
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            tree.copy_global_to(guild=guild)
            synced = await tree.sync(guild=guild)
            print(f"Sync guild {GUILD_ID} -> {len(synced)} comandi")
        else:
            synced = await tree.sync()
            print(f"Sync globale -> {len(synced)} comandi")
    except Exception as e:
        print(f"Sync error: {e}")

@client.event
async def on_message(message):
    if message.author.bot: return
    
    if message.content.strip() == "!force_sync" and is_master(message.author):
        try:
            if GUILD_ID:
                guild = discord.Object(id=int(GUILD_ID))
                synced = await tree.sync(guild=guild)
                await message.channel.send(f"✅ Force sync GUILD {GUILD_ID} -> {len(synced)} comandi")
            else:
                synced = await tree.sync()
                await message.channel.send(f"✅ Force sync GLOBALE -> {len(synced)} comandi")
        except Exception as e:
            await message.channel.send(f"❌ Sync error: {e}")

    if message.content.strip() == "!debug_guilds" and is_master(message.author):
        txt = f"Bot in {len(client.guilds)} server:\n"
        for g in client.guilds: txt += f"- {g.name} ID {g.id}\n"
        await message.channel.send(f"{txt[:1800]}")

# --- COMANDI SLASH ---

@tree.command(name="proelium_ping", description="Test slash commands")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 PONG - Proelium operativo!", ephemeral=True)

@tree.command(name="proelium_crea", description="[MASTER] Crea o aggiorna nazione")
@app_commands.describe(
    nome="Nome nazione es ITALIA", soldi="SOLDI 1-5", stabilita="STABILITA 1-5",
    esercito="ESERCITO 1-5", tecnologia="TECNOLOGIA 1-5", influenza="INFLUENZA 1-5",
    blocco="NATO / PATTO / NEUTRALE", nucleare="Ha nucleare?"
)
async def crea(interaction: discord.Interaction, nome: str, soldi: int, stabilita: int, esercito: int, tecnologia: int, influenza: int, blocco: str, nucleare: bool = False):
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}> o Master autorizzati.", ephemeral=True); return
    
    nome = nome.upper()
    if not (1 <= soldi <= 5 and 1 <= stabilita <= 5 and 1 <= esercito <= 5 and 1 <= tecnologia <= 5 and 1 <= influenza <= 5):
        await interaction.response.send_message("⚠️ I valori statistici devono essere compresi tra 1 e 5.", ephemeral=True); return
    
    total = soldi + stabilita + esercito + tecnologia + influenza
    if total > 20:
        await interaction.response.send_message(f"⚠️ Totale punti {total} > 20 (Max 18 normali, 20 superpotenze).", ephemeral=True); return
    
    db = load_db()
    ap = 2 + (1 if stabilita >= 3 else 0)
    budget = soldi * 10
    
    db[nome] = {
        "nome": nome, "soldi": soldi, "stabilita": stabilita, "esercito": esercito,
        "tecnologia": tecnologia, "influenza": influenza, "blocco": blocco.upper(),
        "nucleare": nucleare, "budget": budget, "ap": ap, "debito": 0,
        "stabilita_attuale": stabilita, "soldi_attuale": soldi
    }
    save_db(db)
    await log_action(interaction, f"CREA {nome} S:{soldi} ST:{stabilita} ES:{esercito} T:{tecnologia} INF:{influenza} Blocco:{blocco}")
    await interaction.response.send_message(f"✅ Nazione **{nome}** creata/aggiornata con successo!\nBudget: {budget} | AP: {ap} | Blocco: {blocco.upper()}")

@tree.command(name="proelium_scheda", description="Mostra scheda dossier nazione")
async def scheda(interaction: discord.Interaction, nome: str):
    db = load_db(); nome = nome.upper()
    if nome not in db:
        await interaction.response.send_message(f"❌ Nazione {nome} non trovata.", ephemeral=True); return
    
    n = db[nome]
    embed = discord.Embed(title=f"🛡️ DOSSIER PROELIUM: {n['nome']}", color=0x2f3136)
    embed.add_field(name="SOLDI", value=f"{n.get('soldi_attuale', n['soldi'])}/{n['soldi']}", inline=True)
    embed.add_field(name="STABILITA", value=f"{n.get('stabilita_attuale', n['stabilita'])}/{n['stabilita']}", inline=True)
    embed.add_field(name="ESERCITO", value=str(n['esercito']), inline=True)
    embed.add_field(name="TECNOLOGIA", value=str(n['tecnologia']), inline=True)
    embed.add_field(name="INFLUENZA", value=str(n['influenza']), inline=True)
    embed.add_field(name="Budget / Debito", value=f"{n.get('budget', 0)} / {n.get('debito', 0)}", inline=True)
    embed.add_field(name="Blocco", value=n['blocco'], inline=True)
    embed.add_field(name="Nucleare", value="SI" if n['nucleare'] else "NO", inline=True)
    embed.set_footer(text=f"AP per turno: {n.get('ap', 2)}")
    await interaction.response.send_message(embed=embed)

@tree.command(name="proelium_lista", description="Lista tutte le nazioni registrate")
async def lista(interaction: discord.Interaction):
    db = load_db()
    if not db:
        await interaction.response.send_message("Nessuna nazione registrata.", ephemeral=True); return
    
    txt = "\n".join([f"• **{k}**: S{v['soldi']} ST{v.get('stabilita_attuale',v['stabilita'])}/{v['stabilita']} ES{v['esercito']} T{v['tecnologia']} [{v['blocco']}]" for k, v in db.items()])
    if len(txt) > 1900: txt = txt[:1900] + "..."
    await interaction.response.send_message(embed=discord.Embed(title=f"🌍 Elenco Nazioni ({len(db)})", description=txt, color=0x3498DB))

@tree.command(name="proelium_battaglia", description="[MASTER] Simula battaglia avanzata HOI4 style")
@app_commands.describe(
    attaccante="Nome nazione attaccante",
    difensore="Nome nazione difensore",
    terreno="Tipo di terreno (es. pianura)",
    dottrina_att="Dottrina attaccante (es. blitzkrieg)"
)
async def battaglia(interaction: discord.Interaction, attaccante: str, difensore: str, terreno: str = "pianura", dottrina_att: str = "blitzkrieg"):
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}> può avviare battaglie.", ephemeral=True); return
    
    terr_data = TERRENI.get(terreno.lower(), TERRENI.get("pianura", {}))
    dott_data = DOTTRINE.get(dottrina_att.lower(), DOTTRINE.get("blitzkrieg", {}))
    
    db = load_db()
    att_info = db.get(attaccante.upper(), {"esercito": 3, "tecnologia": 1})
    dif_info = db.get(difensore.upper(), {"esercito": 3, "tecnologia": 1})
    
    # Generazione divisioni basate su tecnologia ed esercito
    div_a = genera_divisione("fanteria", tech=att_info.get("tecnologia", 1))
    div_d = genera_divisione("fanteria", tech=dif_info.get("tecnologia", 1))
    
    # Calcolo scontro tramite battle_system
    res_battaglia = calcola_battaglia_tick(div_a, div_d, terr_data, dott_data, {})
    
    embed = discord.Embed(title=f"⚔️ Battaglia: {attaccante.upper()} vs {difensore.upper()}", color=0xE74C3C)
    embed.add_field(name="Terreno & Dottrina", value=f"Terreno: **{terr_data.get('nome', terreno)}**\nDottrina Att: **{dott_data.get('nome', dottrina_att)}**", inline=False)
    embed.add_field(name="Esito / Report", value=str(res_battaglia)[:1000], inline=False)
    embed.set_footer(text=f"Master console ID: {MASTER_ROLE_ID}")
    
    await log_action(interaction, f"BATTAGLIA {attaccante} vs {difensore} su {terreno}")
    await interaction.response.send_message(embed=embed)

@tree.command(name="proelium_defcon", description="[MASTER] Gestione livello DEFCON")
async def defcon_cmd(interaction: discord.Interaction, livello: int = None):
    data = load_defcon()
    if livello is None:
        await interaction.response.send_message(f"🚨 **DEFCON Attuale: {data['level']}**\n(5=Pace, 4=Normale, 3=Crisi, 2=Pronti, 1=Guerra Totale)")
        return
    if not is_master(interaction.user):
        await interaction.response.send_message("⛔ Solo Master.", ephemeral=True); return
    if not 1 <= livello <= 5:
        await interaction.response.send_message("⚠️ Il livello DEFCON deve essere tra 1 e 5.", ephemeral=True); return
    
    old = data['level']
    data['level'] = livello
    data['history'].append(f"{datetime.now().strftime('%d/%m %H:%M')} {old}->{livello} da {interaction.user}")
    save_defcon(data)
    
    alert = ""
    if livello <= 2: alert = "\n⚠️ **ALLERTA CRITICA - RESTRIZIONI MILITARI ATTIVE**"
    if livello == 1: alert = "\n☢️ **DEFCON 1 - GUERRA NUCLEARE IMMINENTE O IN ATTO!**"
    
    await log_action(interaction, f"DEFCON {old}->{livello}")
    await interaction.response.send_message(f"🔄 Livello DEFCON modificato: **{old}** ➡️ **{livello}**{alert}")

@tree.command(name="proelium_reset", description="[MASTER] Resetta stabilità e soldi attuali")
async def reset_stab(interaction: discord.Interaction, nome: str):
    if not is_master(interaction.user):
        await interaction.response.send_message("⛔ Solo Master.", ephemeral=True); return
    db = load_db(); nome = nome.upper()
    if nome not in db:
        await interaction.response.send_message(f"❌ Nazione {nome} non trovata.", ephemeral=True); return
    
    db[nome]['stabilita_attuale'] = db[nome]['stabilita']
    db[nome]['soldi_attuale'] = db[nome]['soldi']
    save_db(db)
    await interaction.response.send_message(f"✅ Risorse e stabilità di **{nome}** resettate ai valori massimi per il nuovo turno.")

# Avvio del Bot
if __name__ == "__main__":
    if not TOKEN:
        print("ERRORE: Manca DISCORD_TOKEN nel file .env")
    else:
        client.run(TOKEN)
