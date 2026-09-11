
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
MASTER_ROLES = ["Master", "Amministratore PROELIUM", "Admin", "PROELIUM Master"]

DB_FILE = "nazioni.json"
DEFCON_FILE = "defcon.json"
GUERRE_FILE = "guerre.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def load_db():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_db(d):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(d, f, indent=2, ensure_ascii=False)

def load_defcon():
    if not os.path.exists(DEFCON_FILE): return {"level": 4, "history": []}
    with open(DEFCON_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_defcon(d):
    with open(DEFCON_FILE, "w", encoding="utf-8") as f: json.dump(d, f, indent=2, ensure_ascii=False)

def load_guerre():
    if not os.path.exists(GUERRE_FILE): return []
    with open(GUERRE_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_guerre(d):
    with open(GUERRE_FILE, "w", encoding="utf-8") as f: json.dump(d, f, indent=2, ensure_ascii=False)

def is_master(m):
    if not hasattr(m, 'roles'): return False
    if m.guild.owner_id == m.id: return True
    if any(r.id == MASTER_ROLE_ID for r in m.roles): return True
    return any(r.name in MASTER_ROLES for r in m.roles)

async def log_action(inter, text):
    if LOG_CHANNEL_ID:
        try:
            ch = client.get_channel(int(LOG_CHANNEL_ID))
            if ch: await ch.send(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {text}")
        except: pass

# VIEW
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
        self.att = att
        self.dif = dif
        self.prov = prov
        self.aborted = False

    @discord.ui.button(label="ABORTI MISSIONE", style=discord.ButtonStyle.danger, emoji="🛑")
    async def abort(self, inter, btn):
        self.aborted = True
        await inter.response.send_message(f"🛑 Battaglia di {self.prov} abortita da {inter.user.mention}", ephemeral=False)
        self.stop()

    @discord.ui.button(label="RAPPORTO INTELLIGENCE", style=discord.ButtonStyle.secondary, emoji="📋")
    async def intel(self, inter, btn):
        db = load_db()
        att_s = db.get(self.att, {})
        dif_s = db.get(self.dif, {})
        embed = discord.Embed(title=f"📋 INTELLIGENCE - {self.prov}", color=0x2f3136)
        embed.add_field(name=f"{att_s.get('flag','')} {self.att}", value=f"ES: {att_s.get('esercito')} TEC: {att_s.get('tecnologia')} STAB: {att_s.get('stabilita_attuale')}", inline=True)
        embed.add_field(name=f"{dif_s.get('flag','')} {self.dif}", value=f"ES: {dif_s.get('esercito')} TEC: {dif_s.get('tecnologia')} STAB: {dif_s.get('stabilita_attuale')}", inline=True)
        await inter.response.send_message(embed=embed, ephemeral=True)

# UTILS
def make_bar(att_percent):
    # Barra proporzionale 20 blocchi come HOI4
    filled = int(att_percent // 5)
    empty = 20 - filled
    return "🟦"*filled + "🟥"*empty

def stato_battaglia(adv):
    if adv > 15: return "🔵 AVANZATA NEMICO IN RITIRATA"
    if adv < -15: return "🔴 RESISTENZA - FRONTE TIENE"
    return "⚖️ STALLO - NESSUNO SFONDA"

def fmt_div(div):
    org_perc = int(div.org / max(div.org_max,1) * 100)
    barra_org = "▓"*(org_perc//10) + "░"*(10-org_perc//10)
    tipo_icon = {"fanteria":"🪖","corazzata":"🛡️","meccanizzata":"🚚","paracadutisti":"🪂"}.get(div.tipo,"🎖️")
    return f"{tipo_icon} {div.numero}ª Div. {div.tipo.capitalize()}\n`{barra_org}` {org_perc}% ORG {int(div.org)}/{int(div.org_max)}\n⚔️ {div.atk} | 🛡️ {div.defe} | 📦 {div.equip}% | ⛽ {div.supply}% | W:{div.width}"

# ON READY - FIX GEMINI
@client.event
async def on_ready():
    print(f"PROELIUM ITALIANO V3 - {client.user} - {len(tree.get_commands())} comandi")
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
    if msg.content.strip() == "!debug_guilds" and is_master(msg.author):
        txt = f"Tree: {len(tree.get_commands())}\n"
        for g in client.guilds:
            txt += f"- {g.name} {g.id}\n"
        await msg.channel.send(f"```{txt[:1800]}```")

# COMANDI BASE
@tree.command(name="proelium_ping", description="Verifica sistema operativo")
async def ping(inter):
    await inter.response.send_message(f"🏓 Sistema guerra V3 operativo - Master ID {MASTER_ROLE_ID}", ephemeral=True)

@tree.command(name="proelium_crea", description="[MASTER] Crea nazione max 20 punti")
async def crea(inter, nome: str, soldi: int, stabilita: int, esercito: int, tecnologia: int, influenza: int, blocco: str, nucleare: bool=False):
    if not is_master(inter.user):
        await inter.response.send_message(f"⛔ Solo Master", ephemeral=True); return
    nome = nome.upper()
    if not all(1<=x<=5 for x in [soldi,stabilita,esercito,tecnologia,influenza]):
        await inter.response.send_message("Valori 1-5", ephemeral=True); return
    if sum([soldi,stabilita,esercito,tecnologia,influenza])>20:
        await inter.response.send_message("Totale >20", ephemeral=True); return
    db=load_db()
    db[nome]={"nome":nome,"soldi":soldi,"stabilita":stabilita,"esercito":esercito,"tecnologia":tecnologia,"influenza":influenza,"blocco":blocco.upper(),"nucleare":nucleare,"stabilita_attuale":stabilita,"soldi_attuale":soldi,"flag":db.get(nome,{}).get("flag","🏳️")}
    save_db(db)
    await inter.response.send_message(embed=discord.Embed(title=f"✅ {db[nome]['flag']} {nome} registrata", description=f"{blocco.upper()} | Tot {sum([soldi,stabilita,esercito,tecnologia,influenza])}/20", color=0x00FF00))

@tree.command(name="proelium_bandiera", description="[MASTER] Imposta bandiera es 🇮🇹")
async def bandiera(inter, nome: str, flag: str):
    if not is_master(inter.user):
        await inter.response.send_message("⛔ Solo Master", ephemeral=True); return
    db=load_db(); nome=nome.upper()
    if nome not in db:
        await inter.response.send_message("Non trovata", ephemeral=True); return
    db[nome]['flag']=flag; save_db(db)
    await inter.response.send_message(f"{flag} Bandiera {nome} aggiornata")

@tree.command(name="proelium_scheda", description="Dossier nazione")
async def scheda(inter, nome: str):
    db=load_db(); nome=nome.upper()
    if nome not in db:
        await inter.response.send_message("Non trovata", ephemeral=True); return
    n=db[nome]
    embed=discord.Embed(title=f"{n.get('flag','🏳️')} DOSSIER {n['nome']}", color=0x2f3136)
    embed.add_field(name="💰 SOLDI", value=f"{n.get('soldi_attuale',n['soldi'])}/{n['soldi']}", inline=True)
    embed.add_field(name="🏛️ STABILITA", value=f"{n.get('stabilita_attuale',n['stabilita'])}/{n['stabilita']}", inline=True)
    embed.add_field(name="⚔️ ESERCITO", value=str(n['esercito']), inline=True)
    embed.add_field(name="🔬 TECNOLOGIA", value=str(n['tecnologia']), inline=True)
    embed.add_field(name="🌍 INFLUENZA", value=str(n['influenza']), inline=True)
    embed.add_field(name="🏴 BLOCCO", value=n['blocco'], inline=True)
    await inter.response.send_message(embed=embed)

@tree.command(name="proelium_lista", description="Lista nazioni")
async def lista(inter):
    db=load_db()
    if not db:
        await inter.response.send_message("Nessuna", ephemeral=True); return
    txt="\n".join([f"{v.get('flag','')} **{k}** - ES:{v['esercito']} TEC:{v['tecnologia']} STAB:{v.get('stabilita_attuale',v['stabilita'])} [{v['blocco']}]" for k,v in db.items()])
    await inter.response.send_message(embed=discord.Embed(title=f"🌍 {len(db)} Nazioni", description=txt[:4000], color=0x3498DB))

@tree.command(name="proelium_terreni", description="Lista terreni con width")
async def terreni(inter):
    txt="\n".join([f"**{k}** - {v['nome']} | Larghezza: {v['width']} | {v['desc']}" for k,v in TERRENI.items()])
    await inter.response.send_message(embed=discord.Embed(title="🌍 TERRENI DI GUERRA", description=txt[:4000], color=0x2ECC71))

@tree.command(name="proelium_dottrine", description="Lista dottrine 1983")
async def dottrine(inter):
    txt="\n".join([f"**{k}** - {v['nome']} ({v['tipo']})\n> {v['desc']}\n" for k,v in DOTTRINE.items()])
    await inter.response.send_message(embed=discord.Embed(title="📜 DOTTRINE MILITARI", description=txt[:4000], color=0xF1C40F))

# ===== SISTEMA GUERRA =====
@tree.command(name="proelium_guerra_dichiara", description="[MASTER] Dichiara guerra - inizia conflitto")
@app_commands.describe(attaccante="Chi attacca", difensore="Chi difende", motivo="Casus belli", provincia_obiettivo="Provincia obiettivo")
async def guerra_dichiara(inter, attaccante: str, difensore: str, motivo: str, provincia_obiettivo: str="Capitale"):
    if not is_master(inter.user):
        await inter.response.send_message("⛔ Solo Master", ephemeral=True); return
    db=load_db()
    att=attaccante.upper(); dif=difensore.upper()
    if att not in db or dif not in db:
        await inter.response.send_message("Nazione non trovata", ephemeral=True); return
    
    guerre=load_guerre()
    # Controlla se già in guerra
    for g in guerre:
        if g['status']=='attiva' and ((g['attaccante']==att and g['difensore']==dif) or (g['attaccante']==dif and g['difensore']==att)):
            await inter.response.send_message(f"⚠️ Guerra già attiva tra {att} e {dif}", ephemeral=True); return
    
    nuova={
        "id": len(guerre)+1,
        "attaccante": att,
        "difensore": dif,
        "motivo": motivo,
        "provincia": provincia_obiettivo,
        "inizio": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "status": "attiva",
        "battaglie": 0,
        "vittorie_att": 0,
        "vittorie_dif": 0
    }
    guerre.append(nuova)
    save_guerre(guerre)
    
    embed=discord.Embed(title=f"📢 DICHIARAZIONE DI GUERRA N°{nuova['id']}", description=f"**{db[att].get('flag','')} {att} DICHIARA GUERRA A {db[dif].get('flag','')} {dif}**", color=0xFF0000)
    embed.add_field(name="📜 Casus Belli", value=motivo, inline=False)
    embed.add_field(name="📍 Obiettivo", value=provincia_obiettivo, inline=True)
    embed.add_field(name="📅 Data", value=nuova['inizio'], inline=True)
    embed.add_field(name="📊 Fronte", value=f"Usa /proelium_battaglia per combattere\n/proelium_guerra_lista per vedere guerre", inline=False)
    embed.set_footer(text=f"Dichiarata da {inter.user.display_name} | Master ID {MASTER_ROLE_ID}")
    await log_action(inter, f"GUERRA {att} vs {dif} - {motivo}")
    await inter.response.send_message(embed=embed)

@tree.command(name="proelium_guerra_lista", description="Lista guerre attive")
async def guerra_lista(inter):
    guerre=load_guerre()
    db=load_db()
    if not guerre:
        await inter.response.send_message("☮️ Nessuna guerra attiva", ephemeral=True); return
    attive=[g for g in guerre if g['status']=='attiva']
    if not attive:
        await inter.response.send_message("☮️ Nessuna guerra attiva - solo pace", ephemeral=True); return
    txt=""
    for g in attive:
        att_f=db.get(g['attaccante'],{}).get('flag','')
        dif_f=db.get(g['difensore'],{}).get('flag','')
        txt+=f"**#{g['id']}** {att_f} {g['attaccante']} vs {dif_f} {g['difensore']} | {g['provincia']} | Battaglie: {g['battaglie']} | {g['inizio']}\n> {g['motivo']}\n\n"
    await inter.response.send_message(embed=discord.Embed(title=f"⚔️ {len(attive)} Guerre Attive", description=txt[:4000], color=0xFF0000))

@tree.command(name="proelium_guerra_pace", description="[MASTER] Firma pace - termina guerra")
async def guerra_pace(inter, id_guerra: int, condizioni: str="Resa incondizionata"):
    if not is_master(inter.user):
        await inter.response.send_message("⛔ Solo Master", ephemeral=True); return
    guerre=load_guerre()
    for g in guerre:
        if g['id']==id_guerra and g['status']=='attiva':
            g['status']='conclusa'
            g['fine']=datetime.now().strftime("%d/%m/%Y %H:%M")
            g['condizioni']=condizioni
            save_guerre(guerre)
            embed=discord.Embed(title=f"🕊️ PACE FIRMATA - GUERRA #{id_guerra}", description=f"{g['attaccante']} e {g['difensore']} firmano la pace", color=0x00FF00)
            embed.add_field(name="📜 Condizioni", value=condizioni, inline=False)
            embed.add_field(name="📊 Bilancio", value=f"Battaglie: {g['battaglie']} | Vittorie ATT: {g['vittorie_att']} | Vittorie DIF: {g['vittorie_dif']}", inline=False)
            await inter.response.send_message(embed=embed)
            await log_action(inter, f"PACE Guerra #{id_guerra} {g['attaccante']} vs {g['difensore']} - {condizioni}")
            return
    await inter.response.send_message(f"Guerra #{id_guerra} non trovata o già conclusa", ephemeral=True)

# ===== BATTAGLIA V3 ITALIANA BELLA =====
@tree.command(name="proelium_battaglia", description="[MASTER] Battaglia HOI4 5min - ITALIANO con freccia proporzionale")
@app_commands.describe(attaccante="Sigla ATT", difensore="Sigla DIF", terreno="Terreno", dottrina_att="Dottrina ATT", dottrina_dif="Dottrina DIF", provincia="Provincia battaglia")
@app_commands.choices(
    terreno=[app_commands.Choice(name=f"{v['nome']} - W:{v['width']} - {v['desc'][:35]}", value=k) for k,v in TERRENI.items()],
    dottrina_att=[app_commands.Choice(name=f"{v['nome']}", value=k) for k,v in DOTTRINE.items()],
    dottrina_dif=[app_commands.Choice(name=f"{v['nome']}", value=k) for k,v in DOTTRINE.items()]
)
async def battaglia(inter, attaccante: str, difensore: str, terreno: str, dottrina_att: str, dottrina_dif: str, provincia: str="Fronte Principale"):
    if not is_master(inter.user):
        await inter.response.send_message(f"⛔ Accesso negato - Solo ruolo Master ID {MASTER_ROLE_ID}", ephemeral=True); return
    db=load_db()
    att=attaccante.upper(); dif=difensore.upper()
    if att not in db or dif not in db:
        await inter.response.send_message(f"Nazione non trovata. Usa /proelium_lista", ephemeral=True); return
    
    # Verifica guerra attiva
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
    await inter.response.defer()
    view=BattleControlView(att,dif,provincia)
    
    flag_att=att_stats.get('flag','🏳️'); flag_dif=def_stats.get('flag','🏳️')
    
    # Embed iniziale dichiarazione battaglia
    embed_start=discord.Embed(title=f"⚔️ INIZIO BATTAGLIA - {provincia.upper()}", color=0xFF4500)
    embed_start.add_field(name="📍 Teatro Operativo", value=f"**Provincia:** {provincia}\n**Terreno:** {t_info['nome']} - {t_info['desc']}\n**Larghezza Max Fronte:** {t_info['width']}", inline=False)
    if guerra_attiva:
        embed_start.add_field(name="📢 Contesto", value=f"Guerra #{guerra_attiva['id']}: {guerra_attiva['motivo']}", inline=False)
    embed_start.add_field(name=f"{flag_att} {att} - Attaccante", value=f"Generale: {att}\nDottrina: {d_att['nome']}\nDivisioni: {len(att_divs)}", inline=True)
    embed_start.add_field(name=f"{flag_dif} {dif} - Difensore", value=f"Generale: {dif}\nDottrina: {d_dif['nome']}\nDivisioni: {len(def_divs)}", inline=True)
    msg=await inter.followup.send(embed=embed_start, view=view)
    
    total_dmg_att=0; total_dmg_def=0
    for tick in range(30):
        if view.aborted:
            await msg.edit(embed=discord.Embed(title="🛑 Battaglia abortita", description=f"Abortita da {inter.user.mention} - Nessuna conseguenza", color=0x808080), view=None)
            return
        res=calcola_battaglia_tick(att_divs, def_divs, terreno, dottrina_att, dottrina_dif, tick)
        total_dmg_att+=res['dmg_att']; total_dmg_def+=res['dmg_def']
        bar=make_bar(res['att_percent'])
        stato=stato_battaglia(res['advantage'])
        
        # EMBED ITALIANO BELLO CON SEPARATORI
        embed=discord.Embed(title=f"⚔️ BATTAGLIA DI {provincia.upper()} - T+{tick*10}s", color=0x2f3136 if res['att_percent']==50 else (0x3498DB if res['att_percent']>50 else 0xE74C3C))
        
        # Sezione 1 - Info generali
        embed.add_field(name="📍 TEATRO E CONDIZIONI", value=f"**Provincia:** {provincia}\n**Terreno:** {t_info['nome']} ({t_info['width']} larghezza max)\n**Dottrine:** `{d_att['nome']}` vs `{d_dif['nome']}`", inline=False)
        
        # Sezione 2 - Fronte con freccia proporzionale
        embed.add_field(name="━━━━━━━━━━━ FRONTE DI COMBATTIMENTO ━━━━━━━━━━━", value=f"**{flag_att} {att} Largh: {res['att_width']}**\n{bar}\n**{flag_dif} {dif} Largh: {res['def_width']}**\n**Max Fronte:** {res['max_width']} | **Stato:** {stato}\n**Vantaggio:** {res['att_percent']}% vs {res['def_percent']}% | **Ratio:** {res['ratio']}", inline=False)
        
        # Sezione 3 - Perdite come nella foto
        embed.add_field(name="📊 PERDITE E DANNI", value=f"🔵 {att}: Perdite tot: {total_dmg_def//10} | Danno tick: {res['dmg_def']}\n🔴 {dif}: Perdite tot: {total_dmg_att//10} | Danno tick: {res['dmg_att']}", inline=False)
        
        # Sezione 4 - Divisioni attaccante
        if res['att_engaged']:
            txt_att="\n\n".join([fmt_div(d) for d in res['att_engaged']])
        else:
            txt_att="Nessuna divisione al fronte"
        embed.add_field(name=f"🔵 {flag_att} {att} - {len(res['att_engaged'])} Divisioni al Fronte - Generale {att}", value=txt_att[:1024], inline=False)
        
        # Sezione 5 - Divisioni difensore
        if res['def_engaged']:
            txt_dif="\n\n".join([fmt_div(d) for d in res['def_engaged']])
        else:
            txt_dif="Nessuna divisione al fronte"
        embed.add_field(name=f"🔴 {flag_dif} {dif} - {len(res['def_engaged'])} Divisioni al Fronte - Generale {dif}", value=txt_dif[:1024], inline=False)
        
        # Sezione 6 - Riserve
        embed.add_field(name=f"📦 Riserve {att}: {len(res['att_reserves'])}", value="\n".join([f"{d.numero}ª {d.tipo} ORG {int(d.org)}%" for d in res['att_reserves']]) if res['att_reserves'] else "Nessuna riserva", inline=True)
        embed.add_field(name=f"📦 Riserve {dif}: {len(res['def_reserves'])}", value="\n".join([f"{d.numero}ª {d.tipo} ORG {int(d.org)}%" for d in res['def_reserves']]) if res['def_reserves'] else "Nessuna riserva", inline=True)
        
        embed.set_footer(text=f"T+{tick*10}s / 300s | Guerra: #{guerra_attiva['id'] if guerra_attiva else 'Scaramuccia'} | Master: {inter.user.display_name}")
        
        try: await msg.edit(embed=embed, view=view)
        except: pass
        
        if all(d.org<=0 for d in att_divs):
            embed_win=discord.Embed(title=f"🛡️ VITTORIA DIFENSIVA - {dif} {flag_dif}", description=f"**{dif} resiste eroicamente a {provincia}!**\n{att} esaurito - Tutte le divisioni a 0 ORG", color=0x0000FF)
            embed_win.add_field(name="Esito", value=f"{att} -1 STABILITA\nPerdite ATT: {total_dmg_att} DIF: {total_dmg_def}", inline=False)
            await msg.edit(embed=embed_win, view=None)
            db[att]['stabilita_attuale']=max(0, db[att].get('stabilita_attuale',db[att]['stabilita'])-1)
            save_db(db)
            if guerra_attiva:
                guerra_attiva['battaglie']+=1; guerra_attiva['vittorie_dif']+=1; save_guerre(guerre)
            return
        if all(d.org<=0 for d in def_divs):
            embed_win=discord.Embed(title=f"🏆 VITTORIA SCHIACCIANTE - {att} {flag_att}", description=f"**{att} conquista {provincia}!**\n{dif} rotto - Fronte sfondato\nFreccia finale: {bar} {res['att_percent']}%", color=0x00FF00)
            embed_win.add_field(name="Esito", value=f"{dif} -1 STABILITA\nPerdite totali: {total_dmg_att+total_dmg_def}", inline=False)
            await msg.edit(embed=embed_win, view=None)
            db[dif]['stabilita_attuale']=max(0, db[dif].get('stabilita_attuale',db[dif]['stabilita'])-1)
            save_db(db)
            if guerra_attiva:
                guerra_attiva['battaglie']+=1; guerra_attiva['vittorie_att']+=1; save_guerre(guerre)
            return
        await asyncio.sleep(10)
    
    embed_stallo=discord.Embed(title=f"⚖️ STALLO - {provincia.upper()} - 5 MINUTI", description="Nessuno sfonda dopo 5 minuti di combattimento intenso", color=0x808080)
    embed_stallo.add_field(name="Esito", value="Entrambi -1 STABILITA per logoramento", inline=False)
    await msg.edit(embed=embed_stallo, view=None)
    db[att]['stabilita_attuale']=max(0, db[att].get('stabilita_attuale',db[att]['stabilita'])-1)
    db[dif]['stabilita_attuale']=max(0, db[dif].get('stabilita_attuale',db[dif]['stabilita'])-1)
    save_db(db)

@tree.command(name="proelium_defcon", description="[MASTER] Cambia DEFCON")
async def defcon(inter, livello: int=None):
    data=load_defcon()
    if livello is None:
        await inter.response.send_message(f"🚨 DEFCON: {data['level']} - 5 Pace 1 Guerra Totale")
        return
    if not is_master(inter.user):
        await inter.response.send_message("⛔ Solo Master", ephemeral=True); return
    if not 1<=livello<=5:
        await inter.response.send_message("1-5", ephemeral=True); return
    old=data['level']; data['level']=livello
    data['history'].append(f"{datetime.now().strftime('%d/%m %H:%M')} {old}->{livello}")
    save_defcon(data)
    await inter.response.send_message(f"DEFCON {old} -> {livello}")

@tree.command(name="proelium_mobilitazione", description="[MASTER] Mobilitazione - bonus temporaneo")
async def mobilitazione(inter, nome: str, tipo: str="parziale"):
    if not is_master(inter.user):
        await inter.response.send_message("⛔ Solo Master", ephemeral=True); return
    db=load_db(); nome=nome.upper()
    if nome not in db:
        await inter.response.send_message("Non trovata", ephemeral=True); return
    bonus={"parziale":1,"totale":2,"blitz":3}.get(tipo,1)
    db[nome]['esercito']=min(5, db[nome]['esercito']+bonus)
    save_db(db)
    await inter.response.send_message(embed=discord.Embed(title=f"📢 Mobilitazione {tipo} {nome}", description=f"Esercito +{bonus} -> {db[nome]['esercito']}", color=0xFFA500))

if __name__=="__main__":
    client.run(TOKEN)
