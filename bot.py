import discord
from discord import app_commands
import random
import json
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

MASTER_ROLES = ["Master", "Amministratore PROELIUM", "Admin", "PROELIUM Master"]

DB_FILE = "nazioni.json"
DEFCON_FILE = "defcon.json"

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_defcon():
    if not os.path.exists(DEFCON_FILE):
        return {"level": 4, "history": []}
    with open(DEFCON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_defcon(data):
    with open(DEFCON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_master(member: discord.Member):
    if member.guild.owner_id == member.id:
        return True
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

@client.event
async def on_ready():
    print(f"PROELIUM online come {client.user} in {len(client.guilds)} server")
    for g in client.guilds:
        print(f" - {g.name} ID {g.id}")
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            # Fix: sync diretto senza copy_global_to che buggava
            synced = await tree.sync(guild=guild)
            print(f"Sync guild {GUILD_ID} -> {len(synced)} comandi: {[c.name for c in synced]}")
        else:
            synced = await tree.sync()
            print(f"Sync globale -> {len(synced)} comandi - puo' metterci 1h")
    except Exception as e:
        print(f"Sync error: {e}")
        import traceback
        traceback.print_exc()

@tree.command(name="proelium_crea", description="[MASTER] Crea o aggiorna nazione")
@app_commands.describe(
    nome="Nome nazione es ITALIA",
    soldi="SOLDI 1-5",
    stabilita="STABILITA 1-5",
    esercito="ESERCITO 1-5",
    tecnologia="TECNOLOGIA 1-5",
    influenza="INFLUENZA 1-5",
    blocco="NATO / PATTO / NEUTRALE",
    nucleare="Ha nucleare?"
)
async def crea(interaction: discord.Interaction, nome: str, soldi: int, stabilita: int, esercito: int, tecnologia: int, influenza: int, blocco: str, nucleare: bool = False):
    if not is_master(interaction.user):
        await interaction.response.send_message("Solo Master e Amministratori scelti.", ephemeral=True)
        return
    nome = nome.upper()
    if not (1 <= soldi <= 5 and 1 <= stabilita <= 5 and 1 <= esercito <= 5 and 1 <= tecnologia <= 5 and 1 <= influenza <= 5):
        await interaction.response.send_message("Valori 1-5", ephemeral=True)
        return
    total = soldi+stabilita+esercito+tecnologia+influenza
    if total > 20:
        await interaction.response.send_message(f"Totale {total} > 20 troppo alto. Max 18 normali, 20 superpotenze.", ephemeral=True)
        return
    db = load_db()
    ap = 2 + (1 if stabilita >=3 else 0)
    budget = soldi * 10
    db[nome] = {
        "nome": nome,
        "soldi": soldi,
        "stabilita": stabilita,
        "esercito": esercito,
        "tecnologia": tecnologia,
        "influenza": influenza,
        "blocco": blocco.upper(),
        "nucleare": nucleare,
        "budget": budget,
        "ap": ap,
        "debito": 0,
        "stabilita_attuale": stabilita,
        "soldi_attuale": soldi
    }
    save_db(db)
    await log_action(interaction, f"CREA {nome} S:{soldi} ST:{stabilita} ES:{esercito} T:{tecnologia} INF:{influenza} Blocco:{blocco} N:{nucleare} da {interaction.user}")
    await interaction.response.send_message(f"**Nazione {nome} creata**\nSOLDI {soldi} | STABILITA {stabilita} | ESERCITO {esercito} | TECNOLOGIA {tecnologia} | INFLUENZA {influenza}\nBudget {budget} | AP {ap} | Blocco {blocco} | Nucleare {nucleare}")

@tree.command(name="proelium_scheda", description="Mostra scheda nazione")
async def scheda(interaction: discord.Interaction, nome: str):
    db = load_db()
    nome = nome.upper()
    if nome not in db:
        await interaction.response.send_message(f"{nome} non trovata. /proelium_lista", ephemeral=True)
        return
    n = db[nome]
    embed = discord.Embed(title=f"DOSSIER PROELIUM: {n['nome']}", color=0x2f3136)
    embed.add_field(name="SOLDI", value=str(n['soldi']), inline=True)
    embed.add_field(name="STABILITA", value=f"{n.get('stabilita_attuale', n['stabilita'])}/{n['stabilita']}", inline=True)
    embed.add_field(name="ESERCITO", value=str(n['esercito']), inline=True)
    embed.add_field(name="TECNOLOGIA", value=str(n['tecnologia']), inline=True)
    embed.add_field(name="INFLUENZA", value=str(n['influenza']), inline=True)
    embed.add_field(name="Budget", value=str(n['budget']), inline=True)
    embed.add_field(name="Blocco", value=n['blocco'], inline=True)
    embed.add_field(name="Nucleare", value="SI" if n['nucleare'] else "NO", inline=True)
    embed.add_field(name="Debito", value=str(n.get('debito',0)), inline=True)
    embed.set_footer(text=f"AP/turno: {n['ap']} | Totale punti: {n['soldi']+n['stabilita']+n['esercito']+n['tecnologia']+n['influenza']}")
    await interaction.response.send_message(embed=embed)

@tree.command(name="proelium_guerra", description="[MASTER] Risolvi battaglia")
@app_commands.describe(
    attaccante="Nome attaccante",
    punti_att="Punti base att (ESERCITO + truppe)",
    difensore="Nome difensore",
    punti_dif="Punti base dif (ESERCITO + difesa)",
    logistica="Problemi logistici? fuori continente senza marina"
)
async def guerra(interaction: discord.Interaction, attaccante: str, punti_att: int, difensore: str, punti_dif: int, logistica: bool = False):
    if not is_master(interaction.user):
        await interaction.response.send_message("Solo Master.", ephemeral=True)
        return
    da = random.randint(1,6)
    dd = random.randint(1,6)
    malus = 3 if logistica else 0
    totA = punti_att + da - malus
    totD = punti_dif + dd
    diff = totA - totD
    db = load_db()
    if diff >= 3:
        esito = f"VITTORIA DECISIVA di {attaccante}. {difensore} perde 1 SOLDI e 1 STABILITA' e deve ritirarsi."
        if difensore.upper() in db:
            db[difensore.upper()]['stabilita_attuale'] = max(0, db[difensore.upper()].get('stabilita_attuale', db[difensore.upper()]['stabilita']) -1)
            db[difensore.upper()]['soldi_attuale'] = max(0, db[difensore.upper()].get('soldi_attuale', db[difensore.upper()]['soldi']) -1)
    elif diff > 0:
        esito = f"Vittoria Tattica di {attaccante}. Guerra continua max 3 turni. Entrambi -1 STABILITA'. Effetto Vietnam."
        for k in [attaccante.upper(), difensore.upper()]:
            if k in db:
                db[k]['stabilita_attuale'] = max(0, db[k].get('stabilita_attuale', db[k]['stabilita']) -1)
    elif diff == 0:
        esito = "Stallo. Entrambi -1 STABILITA'"
        for k in [attaccante.upper(), difensore.upper()]:
            if k in db:
                db[k]['stabilita_attuale'] = max(0, db[k].get('stabilita_attuale', db[k]['stabilita']) -1)
    else:
        esito = f"Difesa di {difensore} riuscita. {attaccante} -1 STABILITA'"
        if attaccante.upper() in db:
            db[attaccante.upper()]['stabilita_attuale'] = max(0, db[attaccante.upper()].get('stabilita_attuale', db[attaccante.upper()]['stabilita']) -1)
    save_db(db)
    await log_action(interaction, f"GUERRA {attaccante} vs {difensore} {totA} vs {totD} diff {diff}")
    await interaction.response.send_message(f"**PROELIUM BATTLE LOG**\n{attaccante} {totA} ({punti_att}+d6:{da}{'-3 logistica' if logistica else ''}) vs {difensore} {totD} ({punti_dif}+d6:{dd})\nDiff {diff}\n> {esito}")

@tree.command(name="proelium_influenza", description="[MASTER] Operazione influenza/colpo di stato")
@app_commands.describe(attore="Chi lancia", bonus_tec="Bonus TECNOLOGIA", bersaglio="Bersaglio", tipo="influenza/sabotaggio/propaganda")
async def influenza_cmd(interaction: discord.Interaction, attore: str, bonus_tec: int, bersaglio: str, tipo: str = "influenza"):
    if not is_master(interaction.user):
        await interaction.response.send_message("Solo Master.", ephemeral=True)
        return
    dado = random.randint(1,6)
    tot = dado + bonus_tec
    db = load_db()
    if tipo == "sabotaggio":
        successo = tot >= 5
        msg = f"SABOTAGGIO RIUSCITO {bersaglio} -1 STAB" if successo else f"Fallito, scoperto!" if dado==1 else "Fallito"
        if successo and bersaglio.upper() in db:
            db[bersaglio.upper()]['stabilita_attuale'] = max(0, db[bersaglio.upper()].get('stabilita_attuale', db[bersaglio.upper()]['stabilita']) -1)
            save_db(db)
    elif tipo == "propaganda":
        successo = tot >= 4
        msg = f"PROPAGANDA OK {attore} +1 STAB" if successo else "Inefficace"
        if successo and attore.upper() in db:
            db[attore.upper()]['stabilita_attuale'] = min(db[attore.upper()]['stabilita'], db[attore.upper()].get('stabilita_attuale', db[attore.upper()]['stabilita'])+1)
            save_db(db)
    else:
        successo = tot >= 4
        msg = f"INFLUENZA OK {bersaglio} sotto {attore}" if successo else f"Influenza fallita su {bersaglio}"
    await log_action(interaction, f"{tipo.upper()} {attore}->{bersaglio} {dado}+{bonus_tec}={tot} {'OK' if successo else 'FAIL'}")
    await interaction.response.send_message(f"**PROELIUM {tipo.upper()}**\n{attore} -> {bersaglio}\nTiro d6:{dado}+Tec:{bonus_tec}=**{tot}**\n> {msg}")

@tree.command(name="proelium_defcon", description="[MASTER] Gestisci DEFCON")
async def defcon_cmd(interaction: discord.Interaction, livello: int = None):
    data = load_defcon()
    if livello is None:
        await interaction.response.send_message(f"**DEFCON {data['level']}**\n5 Pace - 4 Normale 1983 - 3 Crisi - 2 Pronti - 1 Missili\nStorico {data['history'][-5:]}")
        return
    if not is_master(interaction.user):
        await interaction.response.send_message("Solo Master.", ephemeral=True)
        return
    if not 1 <= livello <=5:
        await interaction.response.send_message("1-5", ephemeral=True)
        return
    old = data['level']
    data['level'] = livello
    data['history'].append(f"{datetime.now().strftime('%d/%m %H:%M')} {old}->{livello} da {interaction.user}")
    save_defcon(data)
    alert = ""
    if livello <=2:
        alert = "\n**ALLERTA DEFCON 2 - STOP GUERRE DIRETTE USA-URSS**"
    if livello ==1:
        alert = "\n**DEFCON 1 - CRISI MISSILISTICA - MASTER INTERVIENE**"
    await log_action(interaction, f"DEFCON {old}->{livello}")
    await interaction.response.send_message(f"**DEFCON {old} -> {livello}**{alert}")

@tree.command(name="proelium_embargo", description="[MASTER] Embargo")
async def embargo(interaction: discord.Interaction, attore: str, bersaglio: str):
    if not is_master(interaction.user):
        await interaction.response.send_message("Solo Master.", ephemeral=True)
        return
    db = load_db()
    if bersaglio.upper() in db:
        db[bersaglio.upper()]['soldi_attuale'] = max(0, db[bersaglio.upper()].get('soldi_attuale', db[bersaglio.upper()]['soldi'])-1)
        db[bersaglio.upper()]['debito'] = db[bersaglio.upper()].get('debito',0)+1
        save_db(db)
        await interaction.response.send_message(f"**EMBARGO** {attore} -> {bersaglio}\n{bersaglio} -1 SOLDI, +1 Debito. Servono 2 turni economia per recuperare.")
        await log_action(interaction, f"EMBARGO {attore}->{bersaglio}")
    else:
        await interaction.response.send_message("Bersaglio non in DB")

@tree.command(name="proelium_lista", description="Lista nazioni")
async def lista(interaction: discord.Interaction):
    db = load_db()
    if not db:
        await interaction.response.send_message("Nessuna nazione", ephemeral=True)
        return
    txt = "\n".join([f"{k}: S{v['soldi']} ST{v.get('stabilita_attuale',v['stabilita'])}/{v['stabilita']} ES{v['esercito']} T{v['tecnologia']} I{v['influenza']} {v['blocco']}" for k,v in db.items()])
    if len(txt) > 1900:
        txt = txt[:1900]
    await interaction.response.send_message(f"**NAZIONI ({len(db)})**\n```\n{txt}\n```")

@tree.command(name="proelium_reset", description="[MASTER] Reset STAB e SOLDI a max per nuovo turno")
async def reset_stab(interaction: discord.Interaction, nome: str):
    if not is_master(interaction.user):
        await interaction.response.send_message("Solo Master.", ephemeral=True)
        return
    db = load_db()
    nome = nome.upper()
    if nome not in db:
        await interaction.response.send_message("Non trovato", ephemeral=True)
        return
    db[nome]['stabilita_attuale'] = db[nome]['stabilita']
    db[nome]['soldi_attuale'] = db[nome]['soldi']
    save_db(db)
    await interaction.response.send_message(f"{nome} resettato a max")

if __name__ == "__main__":
    if not TOKEN:
        print("ERRORE manca DISCORD_TOKEN in .env")
    else:
        client.run(TOKEN)
