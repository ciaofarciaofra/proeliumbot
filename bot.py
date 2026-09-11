
import discord
from discord import app_commands
import json, os, asyncio, random
from dotenv import load_dotenv
from datetime import datetime

try:
    from battle_system import TERRENI, DOTTRINE, genera_divisione, calcola_battaglia_tick
except:
    TERRENI = {
        "pianura": {"nome": "Pianura", "atk_mod": 1.0, "def_mod": 1.0, "width": 120, "desc": "Pianura 120"},
        "collina": {"nome": "Collina", "atk_mod": 0.85, "def_mod": 1.15, "width": 100, "desc": "Collina 100"},
        "foresta": {"nome": "Foresta", "atk_mod": 0.70, "def_mod": 1.30, "width": 80, "desc": "Foresta 80"},
        "montagna": {"nome": "Montagna", "atk_mod": 0.55, "def_mod": 1.50, "width": 60, "desc": "Montagna 60"},
        "urbano": {"nome": "Urbano", "atk_mod": 0.50, "def_mod": 1.60, "width": 50, "desc": "Urbano 50"},
        "deserto": {"nome": "Deserto", "atk_mod": 1.15, "def_mod": 0.80, "width": 140, "desc": "Deserto 140"},
        "fortificato": {"nome": "Fortificato", "atk_mod": 0.40, "def_mod": 2.0, "width": 80, "desc": "Fortificato 80"},
    }
    DOTTRINE = {
        "blitzkrieg": {"nome": "Blitzkrieg", "tipo": "off", "bonus_atk": 0.35, "bonus_def": -0.1, "bonus_org": -5, "desc": "Blitz"},
        "fortificata": {"nome": "Difesa Fortificata", "tipo": "def", "bonus_atk": -0.05, "bonus_def": 0.5, "bonus_org": 25, "desc": "Fortificata"},
        "airland": {"nome": "AirLand Battle", "tipo": "off", "bonus_atk": 0.25, "bonus_def": 0.05, "bonus_org": 10, "desc": "AirLand"},
        "difesa_elastica": {"nome": "Difesa Elastica", "tipo": "def", "bonus_atk": 0.1, "bonus_def": 0.3, "bonus_org": 20, "desc": "Elastica"},
    }
    from dataclasses import dataclass
    @dataclass
    class Divisione:
        nome: str; atk: int; defe: int; org: float; org_max: float; width: int; equip: int; supply: int; tipo: str; numero: int
    def genera_divisione(stats, tipo="fanteria", numero=None):
        if numero is None: numero = random.randint(1,200)
        return Divisione(f"{numero} Div", 100, 100, 100, 100, 20, 80, 80, tipo, numero)
    def calcola_battaglia_tick(a,b,t,da,dd,tick):
        return {"atk_tot":100,"def_tot":50,"advantage":20,"att_percent":70,"def_percent":30,"ratio":2.0,"att_width":40,"def_width":20,"max_width":120,"att_engaged":a,"def_engaged":b,"att_reserves":[],"def_reserves":[],"dmg_att":5,"dmg_def":10}

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
MASTER_ROLE_ID = 1547815830430032013
MASTER_ROLES = ["Master", "Amministratore PROELIUM", "Admin", "PROELIUM Master"]

DB_FILE = "nazioni.json"
GUERRE_FILE = "guerre.json"
DEFCON_FILE = "defcon.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_db(d):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(d, f, indent=2, ensure_ascii=False)

def load_guerre():
    if not os.path.exists(GUERRE_FILE): return []
    try:
        with open(GUERRE_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return []

def save_guerre(d):
    with open(GUERRE_FILE, "w", encoding="utf-8") as f: json.dump(d, f, indent=2, ensure_ascii=False)

def load_defcon():
    if not os.path.exists(DEFCON_FILE): return {"level": 4, "history": []}
    try:
        with open(DEFCON_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {"level": 4, "history": []}

def save_defcon(d):
    with open(DEFCON_FILE, "w", encoding="utf-8") as f: json.dump(d, f, indent=2, ensure_ascii=False)

def is_master(m):
    if not hasattr(m, 'roles'): return False
    if m.guild.owner_id == m.id: return True
    if any(r.id == MASTER_ROLE_ID for r in m.roles): return True
    return any(r.name in MASTER_ROLES for r in m.roles)

# ===== AUTOCOMPLETE =====
async def autocomplete_nazione(interaction: discord.Interaction, current: str):
    db = load_db()
    if not db: return []
    current = current.lower()
    choices = []
    for k,v in db.items():
        flag = v.get('flag','🏳️')
        display = f"{flag} {k} - ES:{v.get('esercito',0)} TEC:{v.get('tecnologia',0)}"
        if current in k.lower() or current in flag.lower() or current == "":
            choices.append(app_commands.Choice(name=display[:100], value=k))
        if len(choices) >= 25: break
    return choices

async def autocomplete_guerra(interaction: discord.Interaction, current: str):
    guerre = load_guerre()
    db = load_db()
    attive = [g for g in guerre if g['status']=='attiva']
    if not attive: return []
    current = current.lower()
    choices = []
    for g in attive:
        att_f = db.get(g['attaccante'],{}).get('flag','')
        dif_f = db.get(g['difensore'],{}).get('flag','')
        display = f"#{g['id']} {att_f} {g['attaccante']} vs {dif_f} {g['difensore']} | {g['provincia']}"
        if current in str(g['id']) or current in g['attaccante'].lower() or current in g['difensore'].lower() or current == "":
            choices.append(app_commands.Choice(name=display[:100], value=g['id']))
        if len(choices) >= 25: break
    return choices

class MasterOnlyView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)
    async def interaction_check(self, inter):
        if not is_master(inter.user):
            await inter.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}>", ephemeral=True)
            return False
        return True

class BattleControlView(MasterOnlyView):
    def __init__(self, att, dif, prov):
        super().__init__(timeout=400)
        self.att = att; self.dif = dif; self.prov = prov; self.aborted = False
    @discord.ui.button(label="ABORTI MISSIONE", style=discord.ButtonStyle.danger, emoji="🛑")
    async def abort(self, inter, btn):
        self.aborted = True
        await inter.response.send_message(f"🛑 Battaglia di {self.prov} abortita da {inter.user.mention}", ephemeral=False)
        self.stop()
    @discord.ui.button(label="RAPPORTO INTELLIGENCE", style=discord.ButtonStyle.secondary, emoji="📋")
    async def intel(self, inter, btn):
        db = load_db()
        att_s = db.get(self.att, {}); dif_s = db.get(self.dif, {})
        embed = discord.Embed(title=f"📋 INTELLIGENCE - {self.prov}", color=0x2f3136)
        embed.add_field(name=f"{att_s.get('flag','')} {self.att}", value=f"ES:{att_s.get('esercito')} TEC:{att_s.get('tecnologia')} STAB:{att_s.get('stabilita_attuale')}", inline=True)
        embed.add_field(name=f"{dif_s.get('flag','')} {self.dif}", value=f"ES:{dif_s.get('esercito')} TEC:{dif_s.get('tecnologia')} STAB:{dif_s.get('stabilita_attuale')}", inline=True)
        await inter.response.send_message(embed=embed, ephemeral=True)

def make_bar(p):
    filled = int(p // 5)
    return "🟦"*filled + "🟥"*(20-filled)

def stato_batt(adv):
    if adv > 15: return "🔵 AVANZATA - NEMICO IN RITIRATA"
    if adv < -15: return "🔴 RESISTENZA - FRONTE TIENE"
    return "⚖️ STALLO - NESSUNO SFONDA"

def fmt_div(d):
    org_perc = int(d.org / max(d.org_max,1) * 100)
    barra = "▓"*(org_perc//10) + "░"*(10-org_perc//10)
    icon = {"fanteria":"🪖","corazzata":"🛡️","meccanizzata":"🚚","paracadutisti":"🪂"}.get(d.tipo,"🎖️")
    return f"{icon} {d.numero}ª {d.tipo.capitalize()}\n`{barra}` {org_perc}% ORG {int(d.org)}/{int(d.org_max)}\n⚔️ {d.atk} | 🛡️ {d.defe} | 📦 {d.equip}% | ⛽ {d.supply}% | W:{d.width}"

@client.event
async def on_ready():
    print(f"PROELIUM V6 FLAG CUSTOM - {client.user} - {len(tree.get_commands())} comandi")
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            tree.copy_global_to(guild=guild)
            synced = await tree.sync(guild=guild)
            print(f"SYNC GUILD {GUILD_ID} -> {len(synced)}: {[c.name for c in synced]}")
        else:
            synced = await tree.sync()
            print(f"Sync globale {len(synced)}")
    except Exception as e:
        print(f"Sync error {e}")

@client.event
async def on_message(msg):
    if msg.author.bot: return
    if msg.content.strip() == "!force_sync" and is_master(msg.author):
        try:
            if GUILD_ID:
                guild = discord.Object(id=int(GUILD_ID))
                tree.copy_global_to(guild=guild)
                synced = await tree.sync(guild=guild)
                await msg.channel.send(f"✅ Force sync {GUILD_ID} -> {len(synced)}: {[c.name for c in synced]}")
            else:
                synced = await tree.sync()
                await msg.channel.send(f"✅ Sync globale {len(synced)}")
        except Exception as e:
            await msg.channel.send(f"❌ {e}")

@tree.command(name="proelium_ping", description="Verifica sistema")
async def ping(inter):
    db = load_db()
    await inter.response.send_message(f"🏓 V6 Bandiere custom - {len(db)} nazioni - Master ID {MASTER_ROLE_ID}", ephemeral=True)

@tree.command(name="proelium_crea", description="[MASTER] Crea nazione - bandiera rimane per sempre")
async def crea(inter, nome: str, soldi: int, stabilita: int, esercito: int, tecnologia: int, influenza: int, blocco: str, nucleare: bool=False):
    if not is_master(inter.user):
        await inter.response.send_message("⛔ Solo Master", ephemeral=True); return
    nome=nome.upper()
    if not all(1<=x<=5 for x in [soldi,stabilita,esercito,tecnologia,influenza]):
        await inter.response.send_message("Valori 1-5", ephemeral=True); return
    if sum([soldi,stabilita,esercito,tecnologia,influenza])>20:
        await inter.response.send_message("Tot >20", ephemeral=True); return
    db=load_db()
    old_flag = db.get(nome,{}).get('flag',"🏳️")  # bandiera rimane per sempre se già esiste
    db[nome]={"nome":nome,"soldi":soldi,"stabilita":stabilita,"esercito":esercito,"tecnologia":tecnologia,"influenza":influenza,"blocco":blocco.upper(),"nucleare":nucleare,"stabilita_attuale":stabilita,"soldi_attuale":soldi,"flag":old_flag}
    save_db(db)
    await inter.response.send_message(embed=discord.Embed(title=f"✅ {old_flag} {nome} registrata", description=f"Bandiera attuale: {old_flag} - rimane finché non elimini nazione. Usa /proelium_bandiera per cambiarla (anche emoji custom)", color=0x00FF00))

@tree.command(name="proelium_bandiera", description="[MASTER] Imposta bandiera - supporta emoji custom server <:nome:id>")
@app_commands.autocomplete(nome=autocomplete_nazione)
async def bandiera(inter, nome: str, flag: str):
    # flag può essere 🇮🇹 oppure <:italia:123456789> oppure <a:italia_animata:123>
    if not is_master(inter.user):
        await inter.response.send_message("⛔ Solo Master", ephemeral=True); return
    db=load_db(); nome=nome.upper()
    if nome not in db:
        await inter.response.send_message("Non trovata - usa dropdown", ephemeral=True); return
    # Salva esattamente come scritta, così custom emoji funzionano
    db[nome]['flag']=flag
    save_db(db)
    await inter.response.send_message(f"✅ Bandiera di {nome} impostata a {flag} - rimarrà per sempre fino a /proelium_elimina o /proelium_bandiera_rimuovi. Ora appare in tutti i dropdown e nelle battaglie")

@tree.command(name="proelium_bandiera_rimuovi", description="[MASTER] Rimuovi solo bandiera - nazione rimane neutra")
@app_commands.autocomplete(nome=autocomplete_nazione)
async def bandiera_rimuovi(inter, nome: str):
    if not is_master(inter.user):
        await inter.response.send_message("⛔ Solo Master", ephemeral=True); return
    db=load_db(); nome=nome.upper()
    if nome not in db:
        await inter.response.send_message("Non trovata", ephemeral=True); return
    db[nome]['flag']="🏳️"
    save_db(db)
    await inter.response.send_message(f"🏳️ Bandiera di {nome} rimossa - ora neutra")

@tree.command(name="proelium_elimina", description="[MASTER] Elimina nazione e bandiera per sempre")
@app_commands.autocomplete(nome=autocomplete_nazione)
async def elimina(inter, nome: str):
    if not is_master(inter.user):
        await inter.response.send_message("⛔ Solo Master", ephemeral=True); return
    db=load_db(); nome=nome.upper()
    if nome not in db:
        await inter.response.send_message("Non trovata", ephemeral=True); return
    flag = db[nome].get('flag','')
    del db[nome]
    save_db(db)
    await inter.response.send_message(f"🗑️ Nazione {nome} {flag} eliminata per sempre con bandiera")

@tree.command(name="proelium_scheda", description="Dossier nazione - dropdown")
@app_commands.autocomplete(nome=autocomplete_nazione)
async def scheda(inter, nome: str):
    db=load_db(); nome=nome.upper()
    if nome not in db:
        await inter.response.send_message("Non trovata - usa dropdown", ephemeral=True); return
    n=db[nome]
    embed=discord.Embed(title=f"{n.get('flag','🏳️')} DOSSIER {n['nome']}", description=f"Bandiera: {n.get('flag','🏳️')} - rimane per sempre", color=0x2f3136)
    embed.add_field(name="💰 SOLDI", value=f"{n.get('soldi_attuale',n['soldi'])}/{n['soldi']}", inline=True)
    embed.add_field(name="🏛️ STABILITA", value=f"{n.get('stabilita_attuale',n['stabilita'])}/{n['stabilita']}", inline=True)
    embed.add_field(name="⚔️ ESERCITO", value=str(n['esercito']), inline=True)
    embed.add_field(name="🔬 TECNOLOGIA", value=str(n['tecnologia']), inline=True)
    embed.add_field(name="🌍 INFLUENZA", value=str(n['influenza']), inline=True)
    embed.add_field(name="🏴 BLOCCO", value=n['blocco'], inline=True)
    await inter.response.send_message(embed=embed)

@tree.command(name="proelium_lista", description="Lista nazioni con bandiere")
async def lista(inter):
    db=load_db()
    if not db:
        await inter.response.send_message("Nessuna", ephemeral=True); return
    txt="\n".join([f"{v.get('flag','🏳️')} **{k}** - ES:{v['esercito']} TEC:{v['tecnologia']} STAB:{v.get('stabilita_attuale',v['stabilita'])} [{v['blocco']}]" for k,v in db.items()])
    await inter.response.send_message(embed=discord.Embed(title=f"🌍 {len(db)} Nazioni", description=txt[:4000], color=0x3498DB))

@tree.command(name="proelium_terreni", description="Lista terreni")
async def terreni(inter):
    txt="\n".join([f"**{k}** - {v['nome']} | W:{v['width']} | {v['desc']}" for k,v in TERRENI.items()])
    await inter.response.send_message(embed=discord.Embed(title="🌍 TERRENI", description=txt[:4000], color=0x2ECC71))

@tree.command(name="proelium_dottrine", description="Lista dottrine")
async def dottrine(inter):
    txt="\n".join([f"**{k}** - {v['nome']} ({v['tipo']})\n> {v['desc']}\n" for k,v in DOTTRINE.items()])
    await inter.response.send_message(embed=discord.Embed(title="📜 DOTTRINE", description=txt[:4000], color=0xF1C40F))

@tree.command(name="proelium_guerra_dichiara", description="[MASTER] Dichiara guerra - dropdown")
@app_commands.autocomplete(attaccante=autocomplete_nazione, difensore=autocomplete_nazione)
async def guerra_dichiara(inter, attaccante: str, difensore: str, motivo: str, provincia_obiettivo: str="Capitale"):
    await inter.response.defer()
    if not is_master(inter.user):
        await inter.followup.send("⛔ Solo Master", ephemeral=True); return
    db=load_db()
    att=attaccante.upper(); dif=difensore.upper()
    if att not in db or dif not in db:
        await inter.followup.send("Nazione non trovata - usa dropdown", ephemeral=True); return
    guerre=load_guerre()
    for g in guerre:
        if g['status']=='attiva' and ((g['attaccante']==att and g['difensore']==dif) or (g['attaccante']==dif and g['difensore']==att)):
            await inter.followup.send(f"⚠️ Guerra già attiva tra {att} e {dif}", ephemeral=True); return
    nuova={"id":len(guerre)+1,"attaccante":att,"difensore":dif,"motivo":motivo,"provincia":provincia_obiettivo,"inizio":datetime.now().strftime("%d/%m/%Y %H:%M"),"status":"attiva","battaglie":0,"vittorie_att":0,"vittorie_dif":0}
    guerre.append(nuova); save_guerre(guerre)
    embed=discord.Embed(title=f"📢 DICHIARAZIONE DI GUERRA N°{nuova['id']}", description=f"**{db[att].get('flag','')} {att} DICHIARA GUERRA A {db[dif].get('flag','')} {dif}**", color=0xFF0000)
    embed.add_field(name="📜 Casus Belli", value=motivo, inline=False)
    embed.add_field(name="📍 Obiettivo", value=provincia_obiettivo, inline=True)
    embed.add_field(name="ID Guerra", value=f"{nuova['id']} - usa dropdown in /proelium_guerra_pace", inline=True)
    await inter.followup.send(embed=embed)

@tree.command(name="proelium_guerra_lista", description="Lista guerre attive")
async def guerra_lista(inter):
    guerre=load_guerre(); db=load_db()
    attive=[g for g in guerre if g['status']=='attiva']
    if not attive:
        await inter.response.send_message("☮️ Nessuna guerra attiva", ephemeral=True); return
    txt=""
    for g in attive:
        att_f=db.get(g['attaccante'],{}).get('flag',''); dif_f=db.get(g['difensore'],{}).get('flag','')
        txt+=f"**#{g['id']}** {att_f} {g['attaccante']} vs {dif_f} {g['difensore']} | {g['provincia']} | Batt: {g['battaglie']}\n> {g['motivo']}\n\n"
    await inter.response.send_message(embed=discord.Embed(title=f"⚔️ {len(attive)} Guerre Attive", description=txt[:4000], color=0xFF0000))

@tree.command(name="proelium_guerra_pace", description="[MASTER] Firma pace - dropdown guerre")
@app_commands.autocomplete(id_guerra=autocomplete_guerra)
async def guerra_pace(inter, id_guerra: int, condizioni: str="Resa incondizionata"):
    if not is_master(inter.user):
        await inter.response.send_message("⛔ Solo Master", ephemeral=True); return
    guerre=load_guerre()
    for g in guerre:
        if g['id']==id_guerra and g['status']=='attiva':
            g['status']='conclusa'; g['fine']=datetime.now().strftime("%d/%m/%Y %H:%M"); g['condizioni']=condizioni
            save_guerre(guerre)
            embed=discord.Embed(title=f"🕊️ PACE FIRMATA - GUERRA #{id_guerra}", description=f"{g['attaccante']} e {g['difensore']} firmano pace", color=0x00FF00)
            embed.add_field(name="📜 Condizioni", value=condizioni, inline=False)
            await inter.response.send_message(embed=embed)
            return
    await inter.response.send_message(f"Guerra #{id_guerra} non trovata - usa dropdown", ephemeral=True)

@tree.command(name="proelium_battaglia", description="[MASTER] Battaglia HOI4 5min - dropdown")
@app_commands.autocomplete(attaccante=autocomplete_nazione, difensore=autocomplete_nazione)
@app_commands.describe(attaccante="Scegli dal menu", difensore="Scegli dal menu", terreno="Terreno", dottrina_att="Dottrina ATT", dottrina_dif="Dottrina DIF", provincia="Provincia")
@app_commands.choices(
    terreno=[app_commands.Choice(name=f"{v['nome']} - W:{v['width']} - {v['desc'][:35]}", value=k) for k,v in TERRENI.items()],
    dottrina_att=[app_commands.Choice(name=f"{v['nome']}", value=k) for k,v in DOTTRINE.items()],
    dottrina_dif=[app_commands.Choice(name=f"{v['nome']}", value=k) for k,v in DOTTRINE.items()]
)
async def battaglia(inter, attaccante: str, difensore: str, terreno: str, dottrina_att: str, dottrina_dif: str, provincia: str="Fronte Principale"):
    try:
        await inter.response.defer()
    except: pass
    if not is_master(inter.user):
        try:
            await inter.followup.send(f"⛔ Solo Master", ephemeral=True)
        except: pass
        return
    try:
        db=load_db()
        att=attaccante.upper(); dif=difensore.upper()
        if att not in db or dif not in db:
            await inter.followup.send("Non trovata - usa dropdown", ephemeral=True)
            return
        guerre=load_guerre()
        guerra_attiva=None
        for g in guerre:
            if g['status']=='attiva' and ((g['attaccante']==att and g['difensore']==dif) or (g['attaccante']==dif and g['difensore']==att)):
                guerra_attiva=g
                break
        att_stats=db[att]; def_stats=db[dif]
        att_divs=[genera_divisione(att_stats,"fanteria",71), genera_divisione(att_stats,"corazzata" if att_stats['tecnologia']>=3 else "fanteria",20)]
        if att_stats['esercito']>=4:
            att_divs.append(genera_divisione(att_stats,"meccanizzata",207))
        def_divs=[genera_divisione(def_stats,"fanteria",2)]
        if def_stats['esercito']>=3:
            def_divs.append(genera_divisione(def_stats,"fanteria",5))
        t_info=TERRENI[terreno]; d_att=DOTTRINE[dottrina_att]; d_dif=DOTTRINE[dottrina_dif]
        view=BattleControlView(att,dif,provincia)
        flag_att=att_stats.get('flag','🏳️'); flag_dif=def_stats.get('flag','🏳️')
        embed_start=discord.Embed(title=f"⚔️ INIZIO BATTAGLIA - {provincia.upper()}", color=0xFF4500)
        embed_start.add_field(name="📍 Teatro", value=f"Provincia: {provincia}\nTerreno: {t_info['nome']}\nLarghezza Max: {t_info['width']}", inline=False)
        if guerra_attiva:
            embed_start.add_field(name="📢 Guerra", value=f"#{guerra_attiva['id']}: {guerra_attiva['motivo']}", inline=False)
        embed_start.add_field(name=f"{flag_att} {att}", value=f"Dottrina: {d_att['nome']}\nDiv: {len(att_divs)}", inline=True)
        embed_start.add_field(name=f"{flag_dif} {dif}", value=f"Dottrina: {d_dif['nome']}\nDiv: {len(def_divs)}", inline=True)
        msg=await inter.followup.send(embed=embed_start, view=view)
        total_dmg_att=0; total_dmg_def=0
        for tick in range(30):
            if view.aborted:
                await msg.edit(embed=discord.Embed(title="🛑 Abortita", description=f"Abortita da {inter.user.mention}", color=0x808080), view=None)
                return
            res=calcola_battaglia_tick(att_divs, def_divs, terreno, dottrina_att, dottrina_dif, tick)
            total_dmg_att+=res['dmg_att']; total_dmg_def+=res['dmg_def']
            bar=make_bar(res['att_percent'])
            stato=stato_batt(res['advantage'])
            embed=discord.Embed(title=f"⚔️ BATTAGLIA DI {provincia.upper()} - T+{tick*10}s", color=0x2f3136 if res['att_percent']==50 else (0x3498DB if res['att_percent']>50 else 0xE74C3C))
            embed.add_field(name="📍 TEATRO E CONDIZIONI", value=f"Provincia: {provincia}\nTerreno: {t_info['nome']} ({t_info['width']} larghezza)\nDottrine: {d_att['nome']} vs {d_dif['nome']}", inline=False)
            embed.add_field(name="━━━━━━━━━━━ FRONTE ━━━━━━━━━━━", value=f"{flag_att} {att} Largh: {res['att_width']}\n{bar}\n{flag_dif} {dif} Largh: {res['def_width']} | Max: {res['max_width']}\nStato: {stato}\nVantaggio: {res['att_percent']}% vs {res['def_percent']}% | Ratio: {res['ratio']}", inline=False)
            embed.add_field(name="📊 PERDITE", value=f"🔵 {att}: Perdite {total_dmg_def//10} | Danno {res['dmg_def']}\n🔴 {dif}: Perdite {total_dmg_att//10} | Danno {res['dmg_att']}", inline=False)
            txt_att="\n\n".join([fmt_div(d) for d in res['att_engaged']]) if res['att_engaged'] else "Nessuna divisione"
            txt_dif="\n\n".join([fmt_div(d) for d in res['def_engaged']]) if res['def_engaged'] else "Nessuna divisione"
            embed.add_field(name=f"🔵 {flag_att} {att} - {len(res['att_engaged'])} Divisioni", value=txt_att[:1024], inline=False)
            embed.add_field(name=f"🔴 {flag_dif} {dif} - {len(res['def_engaged'])} Divisioni", value=txt_dif[:1024], inline=False)
            embed.add_field(name=f"📦 Riserve {att}: {len(res['att_reserves'])}", value="\n".join([f"{d.numero}ª {d.tipo} ORG {int(d.org)}%" for d in res['att_reserves']]) if res['att_reserves'] else "Nessuna", inline=True)
            embed.add_field(name=f"📦 Riserve {dif}: {len(res['def_reserves'])}", value="\n".join([f"{d.numero}ª {d.tipo} ORG {int(d.org)}%" for d in res['def_reserves']]) if res['def_reserves'] else "Nessuna", inline=True)
            embed.set_footer(text=f"T+{tick*10}s / 300s | Guerra #{guerra_attiva['id'] if guerra_attiva else 'Scaramuccia'}")
            try:
                await msg.edit(embed=embed, view=view)
            except: pass
            if all(d.org<=0 for d in att_divs):
                embed_win=discord.Embed(title=f"🛡️ VITTORIA DIFENSIVA - {dif} {flag_dif}", description=f"{dif} resiste a {provincia}!", color=0x0000FF)
                await msg.edit(embed=embed_win, view=None)
                db[att]['stabilita_attuale']=max(0, db[att].get('stabilita_attuale',db[att]['stabilita'])-1); save_db(db)
                if guerra_attiva: guerra_attiva['battaglie']+=1; guerra_attiva['vittorie_dif']+=1; save_guerre(guerre)
                return
            if all(d.org<=0 for d in def_divs):
                embed_win=discord.Embed(title=f"🏆 VITTORIA - {att} {flag_att}", description=f"{att} conquista {provincia}!", color=0x00FF00)
                await msg.edit(embed=embed_win, view=None)
                db[dif]['stabilita_attuale']=max(0, db[dif].get('stabilita_attuale',db[dif]['stabilita'])-1); save_db(db)
                if guerra_attiva: guerra_attiva['battaglie']+=1; guerra_attiva['vittorie_att']+=1; save_guerre(guerre)
                return
            await asyncio.sleep(10)
        embed_stallo=discord.Embed(title=f"⚖️ STALLO - {provincia.upper()}", description="5 minuti - Nessuno sfonda", color=0x808080)
        await msg.edit(embed=embed_stallo, view=None)
        db[att]['stabilita_attuale']=max(0, db[att].get('stabilita_attuale',db[att]['stabilita'])-1)
        db[dif]['stabilita_attuale']=max(0, db[dif].get('stabilita_attuale',db[dif]['stabilita'])-1)
        save_db(db)
    except Exception as e:
        try:
            await inter.followup.send(f"❌ Errore battaglia: {e}", ephemeral=True)
        except: pass

@tree.command(name="proelium_defcon", description="[MASTER] DEFCON")
async def defcon(inter, livello: int=None):
    data=load_defcon()
    if livello is None:
        await inter.response.send_message(f"🚨 DEFCON: {data['level']}")
        return
    if not is_master(inter.user):
        await inter.response.send_message("⛔ Solo Master", ephemeral=True); return
    if not 1<=livello<=5:
        await inter.response.send_message("1-5", ephemeral=True); return
    old=data['level']; data['level']=livello
    save_defcon(data)
    await inter.response.send_message(f"DEFCON {old} -> {livello}")

@tree.command(name="proelium_mobilitazione", description="[MASTER] Mobilitazione - dropdown")
@app_commands.autocomplete(nome=autocomplete_nazione)
async def mobilitazione(inter, nome: str, tipo: str="parziale"):
    if not is_master(inter.user):
        await inter.response.send_message("⛔ Solo Master", ephemeral=True); return
    db=load_db(); nome=nome.upper()
    if nome not in db:
        await inter.response.send_message("Non trovata - usa dropdown", ephemeral=True); return
    bonus={"parziale":1,"totale":2,"blitz":3}.get(tipo,1)
    db[nome]['esercito']=min(5, db[nome]['esercito']+bonus)
    save_db(db)
    await inter.response.send_message(embed=discord.Embed(title=f"📢 Mobilitazione {tipo} {nome} {db[nome]['flag']}", description=f"Esercito +{bonus} -> {db[nome]['esercito']}", color=0xFFA500))

if __name__=="__main__":
    client.run(TOKEN)
