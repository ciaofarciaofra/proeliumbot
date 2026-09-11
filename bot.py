import discord
from discord import app_commands
import json, os, asyncio, random
from dotenv import load_dotenv
from datetime import datetime
from battle_system import TERRENI, DOTTRINE, genera_divisione, calcola_battaglia_tick

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

MASTER_ROLE_ID = 1547815830430032013
MASTER_ROLES = ["Master", "Amministratore PROELIUM", "Admin", "PROELIUM Master", "Master Proelium"]

DB_FILE = "nazioni.json"
DEFCON_FILE = "defcon.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ===== DATABASE =====
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
    if not hasattr(member, 'roles'):
        return False
    if member.guild.owner_id == member.id:
        return True
    if any(r.id == MASTER_ROLE_ID for r in member.roles):
        return True
    user_roles = [r.name for r in member.roles]
    return any(m in user_roles for m in MASTER_ROLES)

async def log_action(interaction, text):
    if LOG_CHANNEL_ID:
        try:
            ch = client.get_channel(int(LOG_CHANNEL_ID))
            if ch:
                await ch.send(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {text}")
        except:
            pass

# ===== VIEW BLINDATA =====
class MasterOnlyView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_master(interaction.user):
            await interaction.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}> può usare la console.", ephemeral=True)
            return False
        return True

class BattleControlView(MasterOnlyView):
    def __init__(self, att, dif):
        super().__init__(timeout=400)
        self.att = att
        self.dif = dif
        self.aborted = False

    @discord.ui.button(label="🛑 ABORT BATTLE", style=discord.ButtonStyle.danger, custom_id="abort_battle")
    async def abort_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.aborted = True
        await interaction.response.send_message(f"🛑 Battaglia {self.att} vs {self.dif} abortita da {interaction.user.mention}. Nessun effetto.", ephemeral=False)
        self.stop()

    @discord.ui.button(label="📊 DETTAGLI MASTER", style=discord.ButtonStyle.secondary, custom_id="details")
    async def details(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🔒 Console Master - Dettagli", color=0xFFD700, description=f"Battaglia: {self.att} vs {self.dif}\nMaster: {interaction.user.mention}\nRuolo ID: {MASTER_ROLE_ID}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ===== UTILS BATTLE HOI4 =====
def make_bar(att_percent):
    att_blocks = int(att_percent // 5)
    def_blocks = 20 - att_blocks
    bar = "🟦"*att_blocks + "🟥"*def_blocks
    return f"◄{bar}►"

def format_divisione_hoi4(div, idx=1):
    # Formato simile allo screen: numero, nome, ATK, DEF, ORG
    org_perc = int((div.org / max(div.org_max,1)) * 100)
    org_bar = "🟩" if org_perc>60 else "🟨" if org_perc>30 else "🟥"
    tipo_icon = "🪖" if div.tipo=="fanteria" else "🛡️" if div.tipo=="corazzata" else "🚚" if div.tipo=="meccanizzata" else "🪂"
    
    # Simula numeri dello screen: ATK, breakthrough, DEF, ORG
    # Nello screen: 127 (ATK) 16 (breakthrough) / 2 / 93 etc
    return (
        f"{tipo_icon} **{div.numero}. {div.tipo.capitalize()}-Division** {org_bar}\n"
        f"`ATK:{div.atk:3d} ➔ {div.defe//6:2d}` `DEF:{div.defe:3d}` `ORG:{int(div.org):3d}/{int(div.org_max):3d}`\n"
        f"`EQUIP:{div.equip:2d}%` `SUPPLY:{div.supply:2d}%` `W:{div.width}`"
    )

def format_divisione_short(div):
    org_perc = int((div.org / max(div.org_max,1)) * 100)
    status = "💀" if div.org<=0 else "🟢"
    return f"{status} {div.numero}. {div.tipo[:4]} ORG:{int(div.org)}% W:{div.width}"

# ===== ON READY CON FIX GEMINI =====
@client.event
async def on_ready():
    print(f"PROELIUM HOI4 SUPER - {client.user} - Tree: {len(tree.get_commands())} comandi")
    for c in tree.get_commands():
        print(f" - {c.name}")
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            tree.copy_global_to(guild=guild)  # FIX GEMINI - copia globali in gilda
            synced = await tree.sync(guild=guild)
            print(f"SYNC GUILD {GUILD_ID} -> {len(synced)} comandi: {[c.name for c in synced]}")
        else:
            synced = await tree.sync()
            print(f"Sync globale -> {len(synced)}")
    except Exception as e:
        print(f"Sync error: {e}")

@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.strip() == "!force_sync" and is_master(message.author):
        try:
            if GUILD_ID:
                guild = discord.Object(id=int(GUILD_ID))
                tree.copy_global_to(guild=guild)  # FIX GEMINI
                synced = await tree.sync(guild=guild)
                await message.channel.send(f"✅ Force sync GUILD {GUILD_ID} -> {len(synced)} comandi: {[c.name for c in synced]} - Master: {message.author.mention}")
            else:
                synced = await tree.sync()
                await message.channel.send(f"✅ Force sync GLOBALE -> {len(synced)}")
        except Exception as e:
            await message.channel.send(f"❌ {e}")

    if message.content.strip() == "!debug_guilds" and is_master(message.author):
        txt = f"Bot in {len(client.guilds)} server - Tree: {len(tree.get_commands())}\n"
        for g in client.guilds:
            txt += f"- {g.name} ID {g.id}\n"
            r = g.get_role(MASTER_ROLE_ID)
            if r:
                txt += f"  -> Master Role: {r.name} ({len(r.members)} membri)\n"
        await message.channel.send(f"```{txt[:1800]}```")

# ===== COMANDI SLASH =====
@tree.command(name="proelium_ping", description="Test slash - verifica che funzioni")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 PONG - HOI4 Battle System V2 operativo! Master ID {MASTER_ROLE_ID} OK", ephemeral=True)

@tree.command(name="proelium_crea", description="[MASTER] Crea o aggiorna nazione - max 20 punti")
@app_commands.describe(nome="Sigla es ITALIA", soldi="1-5", stabilita="1-5", esercito="1-5", tecnologia="1-5", influenza="1-5", blocco="NATO/PATTO/NEUTRALE", nucleare="Ha nucleare?")
async def crea(interaction: discord.Interaction, nome: str, soldi: int, stabilita: int, esercito: int, tecnologia: int, influenza: int, blocco: str, nucleare: bool=False):
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}>", ephemeral=True)
        return
    nome = nome.upper()
    if not all(1 <= x <= 5 for x in [soldi, stabilita, esercito, tecnologia, influenza]):
        await interaction.response.send_message("⚠️ Valori 1-5", ephemeral=True)
        return
    total = soldi+stabilita+esercito+tecnologia+influenza
    if total > 20:
        await interaction.response.send_message(f"⚠️ Totale {total} > 20 max", ephemeral=True)
        return
    db = load_db()
    db[nome] = {"nome": nome, "soldi": soldi, "stabilita": stabilita, "esercito": esercito, "tecnologia": tecnologia, "influenza": influenza, "blocco": blocco.upper(), "nucleare": nucleare, "stabilita_attuale": stabilita, "soldi_attuale": soldi, "flag": db.get(nome, {}).get("flag","🏳️")}
    save_db(db)
    await log_action(interaction, f"CREA {nome} S:{soldi} ST:{stabilita} ES:{esercito} T:{tecnologia}")
    await interaction.response.send_message(embed=discord.Embed(title=f"✅ {db[nome]['flag']} {nome} creata", description=f"Blocco: {blocco.upper()} | Punti: {total}/20 | Nuc: {'SI' if nucleare else 'NO'}", color=0x00FF00))

@tree.command(name="proelium_bandiera", description="[MASTER] Imposta bandiera nazione (emoji o :flag_it:)")
@app_commands.describe(nome="Sigla nazione", flag="Emoji bandiera es 🇮🇹 o 🏳️")
async def bandiera(interaction: discord.Interaction, nome: str, flag: str):
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}>", ephemeral=True)
        return
    db = load_db()
    nome = nome.upper()
    if nome not in db:
        await interaction.response.send_message("Non esiste", ephemeral=True)
        return
    db[nome]['flag'] = flag
    save_db(db)
    await interaction.response.send_message(embed=discord.Embed(title=f"🏳️ {nome} bandiera {flag}", color=0x00FF00))

@tree.command(name="proelium_scheda", description="Dossier nazione")
async def scheda(interaction: discord.Interaction, nome: str):
    db = load_db()
    nome = nome.upper()
    if nome not in db:
        await interaction.response.send_message(f"❌ {nome} non trovata", ephemeral=True)
        return
    n = db[nome]
    embed = discord.Embed(title=f"{n.get('flag','🏳️')} DOSSIER: {n['nome']}", color=0x2f3136)
    embed.add_field(name="SOLDI", value=f"{n.get('soldi_attuale', n['soldi'])}/{n['soldi']}", inline=True)
    embed.add_field(name="STABILITA", value=f"{n.get('stabilita_attuale', n['stabilita'])}/{n['stabilita']}", inline=True)
    embed.add_field(name="ESERCITO", value=str(n['esercito']), inline=True)
    embed.add_field(name="TECNOLOGIA", value=str(n['tecnologia']), inline=True)
    embed.add_field(name="INFLUENZA", value=str(n['influenza']), inline=True)
    embed.add_field(name="Blocco", value=n['blocco'], inline=True)
    embed.set_footer(text=f"Generale: {n['nome']} | Flag: {n.get('flag','')} | Puoi cambiare bandiera con /proelium_bandiera")
    await interaction.response.send_message(embed=embed)

@tree.command(name="proelium_lista", description="Lista nazioni")
async def lista(interaction: discord.Interaction):
    db = load_db()
    if not db:
        await interaction.response.send_message("Nessuna nazione", ephemeral=True)
        return
    txt = "\n".join([f"{v.get('flag','🏳️')} **{k}**: S{v['soldi']} ST{v.get('stabilita_attuale',v['stabilita'])}/{v['stabilita']} ES{v['esercito']} T{v['tecnologia']} [{v['blocco']}]" for k,v in db.items()])
    await interaction.response.send_message(embed=discord.Embed(title=f"🌍 Nazioni ({len(db)})", description=txt[:4000], color=0x3498DB))

@tree.command(name="proelium_terreni", description="Lista terreni battaglia")
async def terreni_cmd(interaction: discord.Interaction):
    txt = "\n".join([f"**{k}** - {v['nome']} ({v['width']} width): {v['desc']} - ATK x{v['atk_mod']} DEF x{v['def_mod']}" for k,v in TERRENI.items()])
    await interaction.response.send_message(embed=discord.Embed(title="🌍 Terreni HOI4", description=txt[:4000], color=0x2ECC71))

@tree.command(name="proelium_dottrine", description="Lista dottrine battaglia")
async def dottrine_cmd(interaction: discord.Interaction):
    txt = "\n".join([f"**{k}** - {v['nome']} [{v['tipo']}]: {v['desc']}" for k,v in DOTTRINE.items()])
    await interaction.response.send_message(embed=discord.Embed(title="📜 Dottrine 1983", description=txt[:4000], color=0xF1C40F))

# ===== BATTAGLIA SUPER AVANZATA HOI4 =====
@tree.command(name="proelium_battaglia", description="[MASTER] Battaglia HOI4 5min - EMBED FIGO come foto - freccia proporzionale")
@app_commands.describe(attaccante="Sigla ATT (es ITALIA)", difensore="Sigla DIF (es FRANCIA)", terreno="Terreno", dottrina_att="Dottrina attaccante", dottrina_dif="Dottrina difensore", provincia="Nome provincia/battaglia")
@app_commands.choices(
    terreno=[app_commands.Choice(name=f"{v['nome']} - {v['width']}W - {v['desc'][:40]}", value=k) for k,v in TERRENI.items()],
    dottrina_att=[app_commands.Choice(name=f"{v['nome']}", value=k) for k,v in DOTTRINE.items()],
    dottrina_dif=[app_commands.Choice(name=f"{v['nome']}", value=k) for k,v in DOTTRINE.items()]
)
async def battaglia_hoi4(interaction: discord.Interaction, attaccante: str, difensore: str, terreno: str, dottrina_att: str, dottrina_dif: str, provincia: str="Campo di Battaglia"):
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ **ACCESSO NEGATO** - Solo <@&{MASTER_ROLE_ID}> può avviare battaglie", ephemeral=True)
        return

    db = load_db()
    att = attaccante.upper()
    dif = difensore.upper()
    if att not in db or dif not in db:
        await interaction.response.send_message(f"❌ Nazione non trovata - usa /proelium_lista\nAtt: {att} in DB? {att in db} - Dif: {dif} in DB? {dif in db}", ephemeral=True)
        return

    att_stats = db[att]
    def_stats = db[dif]
    
    # Genera divisioni realistiche basate su ESERCITO e TECNOLOGIA
    # Attaccante ha 2-3 divisioni, difensore 1-2 come nello screen 2 vs 1
    att_divs = [
        genera_divisione(att_stats, "fanteria", numero=71),
        genera_divisione(att_stats, "corazzata" if att_stats['tecnologia']>=3 else "fanteria", numero=20),
        genera_divisione(att_stats, "meccanizzata", numero=207) if att_stats['esercito']>=4 else None
    ]
    att_divs = [d for d in att_divs if d is not None]
    
    def_divs = [
        genera_divisione(def_stats, "fanteria", numero=2),
        genera_divisione(def_stats, "fanteria", numero=5) if def_stats['esercito']>=3 else None
    ]
    def_divs = [d for d in def_divs if d is not None]

    t_info = TERRENI[terreno]
    d_att_info = DOTTRINE[dottrina_att]
    d_dif_info = DOTTRINE[dottrina_dif]

    await interaction.response.defer()
    view = BattleControlView(att, dif)

    # EMBED INIZIALE COME FOTO
    flag_att = att_stats.get('flag','🏳️')
    flag_dif = def_stats.get('flag','🏳️')
    
    embed = discord.Embed(title=f"⚔️ BATTLE - {provincia.upper()}", description=f"📍 **{provincia}** | 🌍 **{t_info['nome']}** ({t_info['width']} width) | ⏱️ 5 min\nMaster: {interaction.user.mention}\n`{d_att_info['nome']}` vs `{d_dif_info['nome']}`", color=0xFF4500)
    embed.add_field(name=f"{flag_att} {att} - {att_stats['nome']}", value=f"Generale: **{att}**\nDottrina: {d_att_info['nome']}\n{len(att_divs)} Divisions", inline=True)
    embed.add_field(name=f"{flag_dif} {dif} - {def_stats['nome']}", value=f"Generale: **{dif}**\nDottrina: {d_dif_info['nome']}\n{len(def_divs)} Divisions", inline=True)
    embed.add_field(name="Terreno", value=f"{t_info['nome']}\n{t_info['desc']}", inline=False)
    embed.set_footer(text=f"🔒 Console Master ID {MASTER_ROLE_ID} - Freccia proporzionale attiva")
    
    msg = await interaction.followup.send(embed=embed, view=view)

    # LOOP BATTAGLIA 5 MINUTI = 30 tick * 10 sec
    total_dmg_att = 0
    total_dmg_def = 0
    
    for tick in range(30):
        if view.aborted:
            embed_abort = discord.Embed(title="🛑 BATTAGLIA ABORTITA", description=f"Abortita da {interaction.user.mention}\nNessun effetto", color=0xFF0000)
            await msg.edit(embed=embed_abort, view=None)
            return

        res = calcola_battaglia_tick(att_divs, def_divs, terreno, dottrina_att, dottrina_dif, tick)
        total_dmg_att += res['dmg_att']
        total_dmg_def += res['dmg_def']
        
        bar = make_bar(res['att_percent'])
        momentum = "🟦 **AVANZA**" if res['advantage']>15 else "🟥 **RESISTE**" if res['advantage']<-15 else "⚖️ **STALLO**"
        
        # EMBED COME NELLA FOTO HOI4
        embed_battle = discord.Embed(
            title=f"BATTLE - {provincia.upper()} - T+{tick*10}s",
            description=f"```\nTotal shot down: {total_dmg_def//10} | Total damage: {res['dmg_def']}\nTotal shot down: {total_dmg_att//10} | Total damage: {res['dmg_att']}\n```",
            color=0xFF4500 if res['att_percent']>50 else 0x0000FF
        )
        
        # RIGA FRECCIA COME SCREEN: 54 vs 6 con 120 al centro
        embed_battle.add_field(
            name=f"{flag_att} {att}  {res['att_width']}  {bar}  {res['def_width']}  {flag_dif} {dif}  | Max: {res['max_width']}",
            value=f"{momentum} | Ratio: {res['ratio']} | {t_info['nome']} | {res['att_percent']}% vs {res['def_percent']}%",
            inline=False
        )
        
        # DIVISIONI COME NELLO SCREEN
        if res['att_engaged']:
            att_text = "\n".join([format_divisione_hoi4(d) for d in res['att_engaged']])
        else:
            att_text = "Nessuna divisione ingaggiata"
        
        if res['def_engaged']:
            def_text = "\n".join([format_divisione_hoi4(d) for d in res['def_engaged']])
        else:
            def_text = "Nessuna divisione ingaggiata"
        
        embed_battle.add_field(
            name=f"🔵 {flag_att} {att} - {len(res['att_engaged'])} Divisions - Generale {att}",
            value=att_text[:1024],
            inline=True
        )
        embed_battle.add_field(
            name=f"🔴 {flag_dif} {dif} - {len(res['def_engaged'])} Divisions - Generale {dif}",
            value=def_text[:1024],
            inline=True
        )
        
        # RISERVE COME NELLO SCREEN: 1 Reserves 0 Reserves
        att_res_txt = "\n".join([format_divisione_short(d) for d in res['att_reserves']]) if res['att_reserves'] else "Nessuna riserva"
        def_res_txt = "\n".join([format_divisione_short(d) for d in res['def_reserves']]) if res['def_reserves'] else "Nessuna riserva"
        
        embed_battle.add_field(
            name=f"📦 {len(res['att_reserves'])} Reserves",
            value=att_res_txt[:1024],
            inline=True
        )
        embed_battle.add_field(
            name=f"📦 {len(res['def_reserves'])} Reserves",
            value=def_res_txt[:1024],
            inline=True
        )
        
        embed_battle.set_footer(text=f"⏱️ T+{tick*10}s/300s | Dottrine: {d_att_info['nome']} vs {d_dif_info['nome']} | 🔒 Master ID {MASTER_ROLE_ID} | {momentum}")
        
        try:
            await msg.edit(embed=embed_battle, view=view)
        except:
            pass

        # CHECK VITTORIA
        if all(d.org<=0 for d in att_divs):
            embed_win = discord.Embed(title=f"🛡️ DIFESA EROICA {dif} {flag_dif}!", description=f"**{dif} resiste a {provincia}!**\n{att} ha perso tutta ORG\n{flag_att} {att} -1 STABILITA", color=0x0000FF)
            embed_win.add_field(name="Esito", value=f"Width: {res['att_width']} vs {res['def_width']} | Danni totali ATT: {total_dmg_att} DIF: {total_dmg_def}", inline=False)
            await msg.edit(embed=embed_win, view=None)
            db[att]['stabilita_attuale'] = max(0, db[att].get('stabilita_attuale', db[att]['stabilita'])-1)
            save_db(db)
            await interaction.followup.send(embed=discord.Embed(title=f"🛡️ {dif} resiste!", color=0x0000FF))
            await log_action(interaction, f"BATTAGLIA {provincia} VITTORIA DIF {dif} vs {att}")
            return

        if all(d.org<=0 for d in def_divs):
            embed_win = discord.Embed(title=f"✅ VITTORIA SCHIACCIANTE {att} {flag_att}!", description=f"**{att} conquista {provincia}!**\n{dif} rotto - ORG a 0\n{flag_dif} {dif} -1 STABILITA", color=0x00FF00)
            embed_win.add_field(name="Esito", value=f"Freccia finale: {bar} {res['att_percent']}% vs {res['def_percent']}% | Width: {res['att_width']} vs {res['def_width']}", inline=False)
            await msg.edit(embed=embed_win, view=None)
            db[dif]['stabilita_attuale'] = max(0, db[dif].get('stabilita_attuale', db[dif]['stabilita'])-1)
            save_db(db)
            await interaction.followup.send(embed=discord.Embed(title=f"🏆 {att} vince {provincia}!", description=f"{flag_att} {att} conquista {provincia} - {flag_dif} {dif} -1 STAB", color=0x00FF00))
            await log_action(interaction, f"BATTAGLIA {provincia} VITTORIA ATT {att} vs {dif} - {res['att_percent']}%")
            return

        await asyncio.sleep(10)

    # STALLO DOPO 5 MIN
    embed_stallo = discord.Embed(title=f"⚖️ STALLO A {provincia.upper()} DOPO 5 MIN", description=f"Nessuno sfonda - 5 minuti di combattimento\nEntrambi -1 STABILITA\nFreccia finale: {make_bar(50)} 50% vs 50%", color=0x808080)
    await msg.edit(embed=embed_stallo, view=None)
    db[att]['stabilita_attuale'] = max(0, db[att].get('stabilita_attuale', db[att]['stabilita'])-1)
    db[dif]['stabilita_attuale'] = max(0, db[dif].get('stabilita_attuale', db[dif]['stabilita'])-1)
    save_db(db)
    await interaction.followup.send(embed=discord.Embed(title="⚖️ Stallo!", description=f"{att} e {dif} entrambi -1 STAB dopo 5 min a {provincia}", color=0x808080))

@tree.command(name="proelium_defcon", description="[MASTER] DEFCON 1-5")
async def defcon_cmd(interaction: discord.Interaction, livello: int=None):
    data = load_defcon()
    if livello is None:
        await interaction.response.send_message(f"🚨 **DEFCON Attuale: {data['level']}**\n5=Pace 4=Normale 3=Crisi 2=Pronti 1=Guerra Totale")
        return
    if not is_master(interaction.user):
        await interaction.response.send_message("⛔ Solo Master", ephemeral=True)
        return
    if not 1 <= livello <= 5:
        await interaction.response.send_message("1-5", ephemeral=True)
        return
    old = data['level']
    data['level'] = livello
    data['history'].append(f"{datetime.now().strftime('%d/%m %H:%M')} {old}->{livello} da {interaction.user}")
    save_defcon(data)
    alert = ""
    if livello <=2:
        alert = "\n⚠️ ALLERTA CRITICA"
    if livello==1:
        alert = "\n☢️ DEFCON 1 - GUERRA NUCLEARE!"
    await interaction.response.send_message(f"🔄 DEFCON {old} -> {livello}{alert}")

@tree.command(name="proelium_reset", description="[MASTER] Reset stabilità e soldi")
async def reset_stab(interaction: discord.Interaction, nome: str):
    if not is_master(interaction.user):
        await interaction.response.send_message("⛔ Solo Master", ephemeral=True)
        return
    db = load_db()
    nome = nome.upper()
    if nome=="ALL":
        for k in db:
            db[k]['stabilita_attuale']=db[k]['stabilita']
            db[k]['soldi_attuale']=db[k]['soldi']
        save_db(db)
        await interaction.response.send_message(embed=discord.Embed(title=f"🔄 {len(db)} nazioni resettate", color=0x00FF00))
        return
    if nome not in db:
        await interaction.response.send_message("Non trovata", ephemeral=True)
        return
    db[nome]['stabilita_attuale']=db[nome]['stabilita']
    db[nome]['soldi_attuale']=db[nome]['soldi']
    save_db(db)
    await interaction.response.send_message(embed=discord.Embed(title=f"🔄 {nome} resettata", color=0x00FF00))

if __name__ == "__main__":
    if not TOKEN:
        print("ERRORE: manca TOKEN")
    else:
        client.run(TOKEN)
