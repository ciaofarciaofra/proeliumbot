import discord
from discord import app_commands
import random, json, os, asyncio
from dotenv import load_dotenv
from datetime import datetime
from battle_system import TERRENI, DOTTRINE, genera_divisione, calcola_battaglia_tick

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

# ===== SICUREZZA HARD - SOLO ID RUOLO =====
MASTER_ROLE_ID = 1547815830430032013  # ID Ruolo Master Proelium - UNICO master vero

DB_FILE = "nazioni.json"
DEFCON_FILE = "defcon.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def load_db():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)
def load_defcon():
    if not os.path.exists(DEFCON_FILE): return {"level":4,"history":[]}
    with open(DEFCON_FILE, "r", encoding="utf-8") as f: return json.load(f)
def save_defcon(data):
    with open(DEFCON_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)

def is_master(member: discord.Member):
    """SICURO: controlla SOLO ID ruolo, non nome. Owner sempre master."""
    if not hasattr(member, 'roles'): return False
    if member.guild.owner_id == member.id: return True
    return any(r.id == MASTER_ROLE_ID for r in member.roles)

async def log_action(interaction, text):
    if LOG_CHANNEL_ID:
        try:
            ch = client.get_channel(int(LOG_CHANNEL_ID))
            if ch: await ch.send(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {text}")
        except: pass

# ===== VIEW BLINDATA - SOLO MASTER PUO CLICCARE BOTTONI =====
class MasterOnlyView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Questo blocca TUTTI i bottoni se non sei master
        if not is_master(interaction.user):
            await interaction.response.send_message(f"⛔ **Non sei Master Proelium.** Solo <@&{MASTER_ROLE_ID}> può usare questa console.\nIl tuo ruolo non ha ID {MASTER_ROLE_ID}.", ephemeral=True)
            return False
        return True

class BattleControlView(MasterOnlyView):
    def __init__(self, att, dif, db_ref):
        super().__init__(timeout=360) # 6 min
        self.att = att
        self.dif = dif
        self.db_ref = db_ref
        self.aborted = False

    @discord.ui.button(label="🛑 ABORT BATTLE", style=discord.ButtonStyle.danger, custom_id="abort_battle")
    async def abort_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.aborted = True
        await interaction.response.send_message(f"🛑 Battaglia {self.att} vs {self.dif} abortita da {interaction.user.mention}. Nessun effetto applicato.", ephemeral=False)
        self.stop()

    @discord.ui.button(label="📊 DETTAGLI", style=discord.ButtonStyle.secondary, custom_id="battle_details")
    async def details(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Solo master può vedere dettagli extra
        embed = discord.Embed(title="🔒 Console Master - Dettagli Riservati", color=0xFFD700, description=f"Battaglia: {self.att} vs {self.dif}\nMaster: {interaction.user.mention}\nRuolo verificato: <@&{MASTER_ROLE_ID}>\n\nI guest non vedono questo.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⚠️ CONFERMA VITTORIA ATT", style=discord.ButtonStyle.success, custom_id="confirm_att_win")
    async def confirm_att_win(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"✅ Vittoria {self.att} confermata manualmente da {interaction.user.mention}. Applico -1 STAB a {self.dif}", ephemeral=False)
        db = load_db()
        if self.dif in db:
            db[self.dif]['stabilita_attuale'] = max(0, db[self.dif].get('stabilita_attuale', db[self.dif]['stabilita'])-1)
            save_db(db)
        self.stop()

@client.event
async def on_ready():
    print(f"PROELIUM SECURE online come {client.user} in {len(client.guilds)} server")
    print(f"MASTER ROLE ID blindato: {MASTER_ROLE_ID}")
    for g in client.guilds:
        print(f" - {g.name} ID {g.id}")
        # Verifica se ruolo esiste
        role = g.get_role(MASTER_ROLE_ID)
        if role:
            print(f"   -> Ruolo Master Proelium TROVATO: {role.name} con {len(role.members)} membri")
        else:
            print(f"   -> ATTENZIONE: Ruolo ID {MASTER_ROLE_ID} NON TROVATO in questo server!")
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            synced = await tree.sync(guild=guild)
            print(f"Sync guild {GUILD_ID} -> {len(synced)} comandi")
        else:
            synced = await tree.sync()
            print(f"Sync globale -> {len(synced)}")
    except Exception as e:
        print(f"Sync error: {e}")

@client.event
async def on_message(message):
    if message.author.bot: return
    # Comandi debug solo master vero
    if message.content.strip() == "!force_sync":
        if is_master(message.author):
            try:
                if GUILD_ID:
                    guild = discord.Object(id=int(GUILD_ID))
                    synced = await tree.sync(guild=guild)
                    await message.channel.send(f"✅ Force sync GUILD {GUILD_ID} -> {len(synced)} comandi - Master: {message.author.mention}")
                else:
                    synced = await tree.sync()
                    await message.channel.send(f"✅ Force sync GLOBALE -> {len(synced)}")
            except Exception as e: await message.channel.send(f"❌ {e}")
        else:
            await message.channel.send(f"⛔ Solo <@&{MASTER_ROLE_ID}> può forzare sync. Tu non hai quel ruolo.", delete_after=10)
    if message.content.strip() == "!debug_guilds":
        if is_master(message.author):
            txt = f"Bot in {len(client.guilds)} server:\n"
            for g in client.guilds:
                txt += f"- {g.name} ID {g.id}\n"
                r = g.get_role(MASTER_ROLE_ID)
                if r: txt += f"  -> Master Role trovato: {r.name} ({len(r.members)} membri)\n"
                else: txt += f"  -> Master Role ID {MASTER_ROLE_ID} NON TROVATO!\n"
            txt += f"\nGUILD_ID env: {GUILD_ID}\nMASTER_ROLE_ID: {MASTER_ROLE_ID}"
            await message.channel.send(f"```{txt[:1800]}```")
        else:
            await message.channel.send(f"⛔ Solo Master.", delete_after=5)

# ================= COMANDI BASE =================
@tree.command(name="proelium_crea", description="[MASTER] Crea o aggiorna nazione")
@app_commands.describe(nome="Nome", soldi="1-5", stabilita="1-5", esercito="1-5", tecnologia="1-5", influenza="1-5", blocco="NATO/PATTO/NEUTRALE", nucleare="Ha nucleare?")
async def crea(interaction: discord.Interaction, nome: str, soldi: int, stabilita: int, esercito: int, tecnologia: int, influenza: int, blocco: str, nucleare: bool=False):
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}> può creare nazioni. Tu non hai quel ruolo ID.", ephemeral=True)
        return
    nome=nome.upper()
    if not (1<=soldi<=5 and 1<=stabilita<=5 and 1<=esercito<=5 and 1<=tecnologia<=5 and 1<=influenza<=5):
        await interaction.response.send_message("Valori 1-5", ephemeral=True); return
    total=soldi+stabilita+esercito+tecnologia+influenza
    if total>20: await interaction.response.send_message(f"Totale {total} >20", ephemeral=True); return
    db=load_db()
    db[nome]={"nome":nome,"soldi":soldi,"stabilita":stabilita,"esercito":esercito,"tecnologia":tecnologia,"influenza":influenza,"blocco":blocco.upper(),"nucleare":nucleare,"budget":soldi*10,"ap":2+(1 if stabilita>=3 else 0),"debito":0,"stabilita_attuale":stabilita,"soldi_attuale":soldi,"lore":db.get(nome,{}).get("lore",""),"flag":db.get(nome,{}).get("flag","")}
    save_db(db)
    embed=discord.Embed(title=f"✅ Nazione {nome} creata", description=f"S{soldi} ST{stabilita} ES{esercito} T{tecnologia} INF{influenza}", color=0x00FF00)
    embed.set_footer(text=f"Master: {interaction.user.display_name} | Ruolo verificato ID {MASTER_ROLE_ID}")
    await interaction.response.send_message(embed=embed)

@tree.command(name="proelium_scheda", description="Mostra scheda nazione (tutti possono vedere)")
async def scheda(interaction: discord.Interaction, nome: str):
    db=load_db(); nome=nome.upper()
    if nome not in db: await interaction.response.send_message(f"{nome} non trovata", ephemeral=True); return
    n=db[nome]; flag=n.get('flag','')
    title_flag = f"{flag} " if flag and len(flag)<=4 else ""
    embed=discord.Embed(title=f"{title_flag}DOSSIER PROELIUM: {n['nome']}", color=0x2f3136, description=n.get('lore','')[:4000] if n.get('lore') else None)
    if flag and flag.startswith("http"): embed.set_thumbnail(url=flag)
    embed.add_field(name="SOLDI", value=str(n['soldi']), inline=True)
    embed.add_field(name="STABILITA", value=f"{n.get('stabilita_attuale',n['stabilita'])}/{n['stabilita']}", inline=True)
    embed.add_field(name="ESERCITO", value=str(n['esercito']), inline=True)
    embed.add_field(name="TECNOLOGIA", value=str(n['tecnologia']), inline=True)
    embed.add_field(name="INFLUENZA", value=str(n['influenza']), inline=True)
    embed.add_field(name="Budget", value=str(n['budget']), inline=True)
    embed.add_field(name="Blocco", value=n['blocco'], inline=True)
    embed.add_field(name="Nucleare", value="SI" if n['nucleare'] else "NO", inline=True)
    await interaction.response.send_message(embed=embed)

@tree.command(name="proelium_lista", description="Lista nazioni (pubblico)")
async def lista(interaction: discord.Interaction):
    db=load_db()
    if not db: await interaction.response.send_message("Nessuna nazione", ephemeral=True); return
    txt = "\n".join([f"{k}: S{v['soldi']} ST{v.get('stabilita_attuale',v['stabilita'])}/{v['stabilita']} ES{v['esercito']} T{v['tecnologia']} I{v['influenza']}" for k,v in db.items()])
    embed=discord.Embed(title=f"NAZIONI ({len(db)})", description=f"```{txt[:3500]}```", color=0x2f3136)
    await interaction.response.send_message(embed=embed)

@tree.command(name="proelium_leaderboard", description="Classifica (pubblico)")
async def leaderboard(interaction: discord.Interaction, ordina_per: str="totale"):
    db=load_db()
    if not db: await interaction.response.send_message("Nessuna nazione", ephemeral=True); return
    def score(n): return n['soldi']+n['stabilita']+n['esercito']+n['tecnologia']+n['influenza']
    sorted_nations=sorted(db.items(), key=lambda x: score(x[1]), reverse=True)
    embed=discord.Embed(title=f"🏆 LEADERBOARD", color=0xFFD700)
    txt=""
    for i,(k,v) in enumerate(sorted_nations[:15],1):
        totale=score(v); med="🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
        flag=v.get('flag',''); 
        if flag and len(flag)<=4: k=f"{flag} {k}"
        txt+=f"{med} **{k}** Tot:{totale} S:{v['soldi']} ES:{v['esercito']} T:{v['tecnologia']}\n"
    embed.description=txt[:4000]
    await interaction.response.send_message(embed=embed)

@tree.command(name="proelium_terreni", description="Lista terreni (pubblico)")
async def terreni_cmd(interaction: discord.Interaction):
    embed=discord.Embed(title="🌍 TERRENI", color=0x2f3136)
    txt=""
    for k,v in TERRENI.items(): txt+=f"**{v['nome']}** `{k}` W:{v['width']} ATK x{v['atk_mod']} DEF x{v['def_mod']}\n> {v['desc']}\n\n"
    embed.description=txt[:4000]
    await interaction.response.send_message(embed=embed)

@tree.command(name="proelium_dottrine", description="Lista dottrine (pubblico)")
async def dottrine_cmd(interaction: discord.Interaction):
    embed=discord.Embed(title="📖 DOTTRINE 1983", color=0x8B0000)
    txt=""
    for k,v in DOTTRINE.items(): txt+=f"**{v['nome']}** `{k}` [{v['tipo']}] ATK {v['bonus_atk']:+.0%} DEF {v['bonus_def']:+.0%}\n> {v['desc'][:80]}\n\n"
    embed.description=txt[:4000]
    await interaction.response.send_message(embed=embed)

# ===== COMANDI MASTER BLINDATI =====
@tree.command(name="proelium_cancella", description="[MASTER] Cancella nazione")
@app_commands.describe(nome="Nazione", conferma="CONFERMA")
async def cancella(interaction: discord.Interaction, nome: str, conferma: str):
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}>", ephemeral=True); return
    if conferma!="CONFERMA": await interaction.response.send_message("Scrivi CONFERMA", ephemeral=True); return
    db=load_db(); nome=nome.upper()
    if nome not in db: await interaction.response.send_message("Non esiste", ephemeral=True); return
    del db[nome]; save_db(db)
    embed=discord.Embed(title=f"💀 {nome} cancellata", color=0xFF0000, description=f"Master: {interaction.user.mention}")
    await interaction.response.send_message(embed=embed)

@tree.command(name="proelium_lore", description="[MASTER] Imposta lore")
@app_commands.describe(nome="Nazione", testo="Testo lore")
async def lore_cmd(interaction: discord.Interaction, nome: str, testo: str=None):
    if not testo:
        db=load_db(); nome=nome.upper()
        if nome not in db: await interaction.response.send_message("Non trovata", ephemeral=True); return
        embed=discord.Embed(title=f"📜 LORE {nome}", description=db[nome].get('lore','Nessuna lore')[:4000], color=0x2f3136)
        await interaction.response.send_message(embed=embed); return
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}>", ephemeral=True); return
    db=load_db(); nome=nome.upper()
    if nome not in db: await interaction.response.send_message("Non esiste", ephemeral=True); return
    db[nome]['lore']=testo[:4000]; save_db(db)
    embed=discord.Embed(title=f"✅ Lore {nome} impostata", description=testo[:1000], color=0x00FF00)
    embed.set_footer(text=f"Master: {interaction.user.display_name} - Ruolo ID {MASTER_ROLE_ID} verificato")
    await interaction.response.send_message(embed=embed)

@tree.command(name="proelium_modifica", description="[MASTER] Modifica stat")
@app_commands.describe(nome="Nazione", campo="Campo", valore="Valore")
@app_commands.choices(campo=[
    app_commands.Choice(name="SOLDI 1-5", value="soldi"),
    app_commands.Choice(name="ESERCITO 1-5", value="esercito"),
    app_commands.Choice(name="TECNOLOGIA 1-5", value="tecnologia"),
    app_commands.Choice(name="INFLUENZA 1-5", value="influenza"),
    app_commands.Choice(name="STABILITA max", value="stabilita"),
    app_commands.Choice(name="STABILITA attuale", value="stabilita_attuale"),
    app_commands.Choice(name="BLOCCO", value="blocco"),
    app_commands.Choice(name="NUCLEARE", value="nucleare"),
    app_commands.Choice(name="FLAG", value="flag"),
])
async def modifica(interaction: discord.Interaction, nome: str, campo: str, valore: str):
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}>", ephemeral=True); return
    db=load_db(); nome=nome.upper()
    if nome not in db: await interaction.response.send_message("Non esiste", ephemeral=True); return
    n=db[nome]
    try:
        if campo in ["soldi","stabilita","esercito","tecnologia","influenza"]: n[campo]=int(valore)
        elif campo in ["stabilita_attuale"]: n[campo]=max(0,int(valore))
        elif campo=="blocco": n['blocco']=valore.upper()
        elif campo=="nucleare": n['nucleare']=valore.lower() in ["true","si","1"]
        elif campo=="flag": n['flag']=valore
        db[nome]=n; save_db(db)
        embed=discord.Embed(title=f"✅ {nome} {campo} -> {valore}", color=0x00FF00)
        embed.set_footer(text=f"Master verificato ID {MASTER_ROLE_ID}")
        await interaction.response.send_message(embed=embed)
    except: await interaction.response.send_message("Valore non valido", ephemeral=True)

@tree.command(name="proelium_bandiera", description="[MASTER] Imposta bandiera")
@app_commands.describe(nome="Nazione", flag="Emoji o URL")
async def bandiera(interaction: discord.Interaction, nome: str, flag: str):
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}>", ephemeral=True); return
    db=load_db(); nome=nome.upper()
    if nome not in db: await interaction.response.send_message("Non esiste", ephemeral=True); return
    db[nome]['flag']=flag; save_db(db)
    embed=discord.Embed(title=f"🏳️ {nome} bandiera {flag}", color=0x00FF00)
    await interaction.response.send_message(embed=embed)

# ===== BATTAGLIA BLINDATA =====
def make_bar(att_percent):
    att_blocks = int(att_percent // 5)
    def_blocks = 20 - att_blocks
    bar = "🟦"*att_blocks + "🟥"*def_blocks
    return f"◄{bar}►"

@tree.command(name="proelium_battaglia", description="[MASTER] Avvia battaglia 5 min HOI4 - SOLO MASTER")
@app_commands.describe(attaccante="Attaccante", difensore="Difensore", terreno="Terreno", dottrina_att="Dottrina att", dottrina_dif="Dottrina dif", provincia="Provincia")
@app_commands.choices(
    terreno=[app_commands.Choice(name=f"{v['nome']}", value=k) for k,v in TERRENI.items()],
    dottrina_att=[app_commands.Choice(name=f"{v['nome']}", value=k) for k,v in DOTTRINE.items()],
    dottrina_dif=[app_commands.Choice(name=f"{v['nome']}", value=k) for k,v in DOTTRINE.items()]
)
async def battaglia_avanzata(interaction: discord.Interaction, attaccante: str, difensore: str, terreno: str, dottrina_att: str, dottrina_dif: str, provincia: str="Campo di Battaglia"):
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ **ACCESSO NEGATO** - Solo chi ha ruolo <@&{MASTER_ROLE_ID}> (ID: {MASTER_ROLE_ID}) può avviare battaglie.\nTu hai ruoli: {[r.name for r in interaction.user.roles]}", ephemeral=True)
        return
    db=load_db()
    att=attaccante.upper(); dif=difensore.upper()
    if att not in db or dif not in db: await interaction.response.send_message("Nazione non esiste", ephemeral=True); return

    att_stats=db[att]; def_stats=db[dif]
    att_divs = [genera_divisione(att_stats, "fanteria"), genera_divisione(att_stats, "corazzata" if att_stats['tecnologia']>=3 else "fanteria")]
    def_divs = [genera_divisione(def_stats, "fanteria")]
    t_info=TERRENI[terreno]; d_att_info=DOTTRINE[dottrina_att]; d_dif_info=DOTTRINE[dottrina_dif]

    await interaction.response.defer()
    view = BattleControlView(att, dif, db)
    
    embed=discord.Embed(title=f"⚔️ BATTLE: {att} vs {dif} [🔒 MASTER ONLY]", description=f"📍 {provincia} | 🌍 {t_info['nome']} | ⏱️ 5 min\nMaster: {interaction.user.mention} (<@&{MASTER_ROLE_ID}>)\nGuest non possono cliccare bottoni.", color=0xFF4500)
    embed.add_field(name=f"{att}", value=f"{att_stats.get('flag','')} {d_att_info['nome']}", inline=True)
    embed.add_field(name=f"{dif}", value=f"{def_stats.get('flag','')} {d_dif_info['nome']}", inline=True)
    embed.set_footer(text=f"Console blindata - Ruolo ID {MASTER_ROLE_ID} richiesto per bottoni")
    msg = await interaction.followup.send(embed=embed, view=view)

    for tick in range(30):
        if view.aborted:
            embed2=discord.Embed(title="🛑 Battaglia abortita da Master", color=0xFF0000)
            await msg.edit(embed=embed2, view=None)
            return
        res = calcola_battaglia_tick(att_divs, def_divs, terreno, dottrina_att, dottrina_dif, tick)
        bar = make_bar(res['att_percent'])
        momentum = "🟦 AVANZA" if res['advantage']>10 else "🟥 RESISTE" if res['advantage']<-10 else "⚖️ STALLO"
        
        embed2=discord.Embed(title=f"⚔️ {att} vs {dif} - T+{tick*10}s [🔒 SOLO MASTER {interaction.user.display_name}]", color=0xFF4500 if res['att_percent']>50 else 0x0000FF)
        embed2.description = f"📍 {provincia} | {t_info['nome']} | {momentum}\n\n**{bar}**\n**{att} {res['att_percent']}%** vs **{dif} {res['def_percent']}%** Adv {res['advantage']:+d}"
        att_txt="\n".join([f"{'💀' if d.org<=0 else '🟢'} {d.nome} ORG:{int(d.org)}%" for d in att_divs])
        def_txt="\n".join([f"{'💀' if d.org<=0 else '🔴'} {d.nome} ORG:{int(d.org)}%" for d in def_divs])
        embed2.add_field(name=f"🔵 {att}", value=att_txt[:1024], inline=False)
        embed2.add_field(name=f"🔴 {dif}", value=def_txt[:1024], inline=False)
        embed2.set_footer(text=f"🔒 Console Master ID {MASTER_ROLE_ID} - Guest bloccati")
        try: await msg.edit(embed=embed2, view=view)
        except: pass

        if all(d.org<=0 for d in def_divs):
            embed2.title=f"✅ VITTORIA {att}!"; embed2.color=0x00FF00
            await msg.edit(embed=embed2, view=None)
            db[dif]['stabilita_attuale']=max(0, db[dif].get('stabilita_attuale', db[dif]['stabilita'])-1)
            save_db(db)
            await interaction.followup.send(embed=discord.Embed(title=f"🏆 {att} vince {provincia}", description=f"{dif} -1 STAB", color=0x00FF00))
            return
        if all(d.org<=0 for d in att_divs):
            embed2.title=f"🛡️ DIFESA {dif}!"; embed2.color=0x0000FF
            await msg.edit(embed=embed2, view=None)
            db[att]['stabilita_attuale']=max(0, db[att].get('stabilita_attuale', db[att]['stabilita'])-1)
            save_db(db)
            await interaction.followup.send(embed=discord.Embed(title=f"🛡️ {dif} resiste!", description=f"{att} -1 STAB", color=0x0000FF))
            return
        await asyncio.sleep(10)

    await interaction.followup.send(embed=discord.Embed(title="⚖️ Stallo dopo 5 min", description="Entrambi -1 STAB", color=0x808080))

@tree.command(name="proelium_reset", description="[MASTER] Reset")
@app_commands.describe(nome="Nome o ALL")
async def reset_stab(interaction: discord.Interaction, nome: str):
    if not is_master(interaction.user):
        await interaction.response.send_message(f"⛔ Solo <@&{MASTER_ROLE_ID}>", ephemeral=True); return
    db=load_db()
    if nome.upper()=="ALL":
        for k in db: db[k]['stabilita_attuale']=db[k]['stabilita']; db[k]['soldi_attuale']=db[k]['soldi']
        save_db(db); await interaction.response.send_message(embed=discord.Embed(title=f"🔄 {len(db)} nazioni resettate", color=0x00FF00)); return
    nome=nome.upper()
    if nome not in db: await interaction.response.send_message("Non trovato", ephemeral=True); return
    db[nome]['stabilita_attuale']=db[nome]['stabilita']; db[nome]['soldi_attuale']=db[nome]['soldi']; save_db(db)
    await interaction.response.send_message(embed=discord.Embed(title=f"{nome} resettato", color=0x00FF00))

if __name__=="__main__":
    if not TOKEN: print("ERRORE manca TOKEN")
    else: client.run(TOKEN)
