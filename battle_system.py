"""
PROELIUM - SISTEMA GUERRA AVANZATO V1
Minigame 5 minuti stile HOI4
- Dottrine reali 1983
- Terreno reale
- Freccia proporzionale
- Statistiche ATK / DEF / ORG / Supply
"""

import random
import math
from dataclasses import dataclass

# ================= TERRENI 1983 =================
TERRENI = {
    "pianura": {"nome": "Pianura", "atk_mod": 1.0, "def_mod": 1.0, "width": 120, "desc": "Nessun malus, guerra di manovra"},
    "collina": {"nome": "Collina", "atk_mod": 0.85, "def_mod": 1.15, "width": 100, "desc": "-15% ATK attaccante, +15% DEF difensore"},
    "foresta": {"nome": "Foresta", "atk_mod": 0.70, "def_mod": 1.30, "width": 80, "desc": "Fanteria domina, carri -30%"},
    "montagna": {"nome": "Montagna", "atk_mod": 0.55, "def_mod": 1.50, "width": 60, "desc": "Solo fanteria alpina, -45% ATK"},
    "urbano": {"nome": "Urbano", "atk_mod": 0.50, "def_mod": 1.60, "width": 50, "desc": "Stalingrado. Difensore +60%, org drain x2"},
    "deserto": {"nome": "Deserto Aperto", "atk_mod": 1.15, "def_mod": 0.80, "width": 140, "desc": "Carri +15%, supply drain se senza logistica"},
    "giungla": {"nome": "Giungla", "atk_mod": 0.60, "def_mod": 1.40, "width": 60, "desc": "-40% ATK, attrito alto"},
    "palude": {"nome": "Palude", "atk_mod": 0.65, "def_mod": 1.25, "width": 70, "desc": "Mezzi impantanati"},
    "fiume": {"nome": "Attraversamento Fiume", "atk_mod": 0.60, "def_mod": 1.40, "width": 90, "desc": "Penalita attraversamento"},
    "fortificato": {"nome": "Linea Fortificata", "atk_mod": 0.40, "def_mod": 2.0, "width": 80, "desc": "Bunker, mine, filo spinato. Serve artiglieria"}
}

# ================= DOTTRINE 1983 - REALI =================
DOTTRINE = {
    # NATO / OFFENSIVE
    "airland": {
        "nome": "AirLand Battle (NATO 1982)",
        "tipo": "offensiva",
        "bonus_atk": 0.25,
        "bonus_def": 0.05,
        "bonus_org": 10,
        "desc": "Dottrina USA 1982. Coordinamento aria-terra. +25% ATK se hai superiorità aerea (TEC 4+), +10 ORG. Debole se senza supporto aereo.",
        "requisito": "TEC >=3"
    },
    "blitzkrieg": {
        "nome": "Blitzkrieg Meccanizzato",
        "tipo": "offensiva",
        "bonus_atk": 0.35,
        "bonus_def": -0.10,
        "bonus_org": -5,
        "desc": "Concentrazione carri su punto debole. +35% ATK primi 2 minuti, poi -10% DEF se fallisce. Richiede ESERCITO 4+.",
        "requisito": "ESERCITO 4+"
    },
    "shock": {
        "nome": "Shock & Awe (Attrito)",
        "tipo": "offensiva",
        "bonus_atk": 0.15,
        "bonus_def": 0.10,
        "bonus_org": 5,
        "desc": "Bombardamento massiccio poi assalto. +15% ATK, +10% DEF, lento ma sicuro. +1 STAB drain per nemico.",
        "requisito": "Nessuno"
    },
    "infiltrazione": {
        "nome": "Infiltrazione / SpecOps",
        "tipo": "offensiva",
        "bonus_atk": 0.20,
        "bonus_def": 0.20,
        "bonus_org": 15,
        "desc": "Forze speciali dietro linee. Ignora 30% bonus terreno difensore. Perfetto per montagna/giungla.",
        "requisito": "TECNOLOGIA 4+"
    },
    # DIFENSIVE
    "difesa_elastica": {
        "nome": "Difesa Elastica (Manstein)",
        "tipo": "difensiva",
        "bonus_atk": 0.10,
        "bonus_def": 0.30,
        "bonus_org": 20,
        "desc": "Cedi terreno, contrattacca. +30% DEF, +20 ORG. Se resisti 3 min, +20% ATK contrattacco.",
        "requisito": "ESERCITO 3+"
    },
    "fortificata": {
        "nome": "Difesa Fortificata",
        "tipo": "difensiva",
        "bonus_atk": -0.05,
        "bonus_def": 0.50,
        "bonus_org": 25,
        "desc": "Trincee, bunker. +50% DEF, +25 ORG. Immobile, -5% ATK. Ideale urbano/fortificato.",
        "requisito": "Nessuno"
    },
    "deep_battle": {
        "nome": "Deep Battle Sovietica",
        "tipo": "offensiva",
        "bonus_atk": 0.30,
        "bonus_def": 0.15,
        "bonus_org": 0,
        "desc": "Dottrina URSS 1936-1983. Ondate successive. +30% ATK, ignora 20% larghezza fronte (più divisioni in campo).",
        "requisito": "Blocco PATTO"
    },
    "difesa_mobile": {
        "nome": "Difesa Mobile NATO",
        "tipo": "difensiva",
        "bonus_atk": 0.15,
        "bonus_def": 0.25,
        "bonus_org": 10,
        "desc": "Riserva corazzata contrattacca. +25% DEF, +15% ATK in controffensiva. Richiede SOLDI 3+ per carburante.",
        "requisito": "SOLDI 3+"
    },
    "guerriglia": {
        "nome": "Guerriglia / People's War",
        "tipo": "difensiva",
        "bonus_atk": 0.05,
        "bonus_def": 0.40,
        "bonus_org": 30,
        "desc": "Mao / Giap. +40% DEF in foresta/giungla/montagna/urbano, +30 ORG, supply nemico -30%. Debole in pianura.",
        "requisito": "STABILITA 2- (popolo motivato)"
    },
    "uman_wave": {
        "nome": "Human Wave",
        "tipo": "offensiva",
        "bonus_atk": 0.10,
        "bonus_def": -0.20,
        "bonus_org": -20,
        "desc": "Massa umana. +10% ATK ma -20 ORG, -20% DEF, perdite +50%. Solo se SOLDI 1-2 e STAB bassa.",
        "requisito": "Nessuno ma sconsigliata"
    }
}

@dataclass
class Divisione:
    nome: str
    atk: int  # attacco base
    defe: int # difesa base
    org: int  # organizzazione 0-120
    width: int # larghezza fronte che occupa
    equip: int # equipaggiamento %
    supply: int # rifornimenti %

def genera_divisione(nazione_stats, tipo="fanteria"):
    """Genera stat realistici basati su ESERCITO e TECNOLOGIA della nazione"""
    esercito = nazione_stats['esercito']
    tec = nazione_stats['tecnologia']
    soldi = nazione_stats['soldi']
    
    base_atk = 20 + esercito*15 + tec*10
    base_def = 25 + esercito*10 + tec*8
    base_org = 60 + esercito*10 + (5 if nazione_stats['stabilita']>=3 else -10)
    
    if tipo == "corazzata":
        base_atk = int(base_atk * 1.6)
        base_def = int(base_def * 0.8)
        base_org = int(base_org * 0.85)
    elif tipo == "paracadutisti":
        base_atk = int(base_atk * 1.2)
        base_org = int(base_org * 1.1)
    
    return Divisione(
        nome=f"{tipo.capitalize()} Div.",
        atk=base_atk + random.randint(-10,10),
        defe=base_def + random.randint(-5,5),
        org=base_org,
        width=20 if tipo!="corazzata" else 30,
        equip=70 + soldi*6 + random.randint(-5,10),
        supply=75 + random.randint(-10,15)
    )

def calcola_battaglia_tick(att_divs, def_divs, terreno, dottr_att, dottr_def, tick):
    """Un tick di battaglia (10 secondi reali = 1 ora in game)"""
    t_mod = TERRENI.get(terreno, TERRENI["pianura"])
    d_att = DOTTRINE.get(dottr_att, DOTTRINE["shock"])
    d_def = DOTTRINE.get(dottr_def, DOTTRINE["fortificata"])
    
    # Somma attacchi
    atk_tot = sum(d.atk * (d.org/100) * (d.supply/100) * (d.equip/100) for d in att_divs if d.org>0)
    def_tot = sum(d.defe * (d.org/100) * (d.supply/100) * (d.equip/100) for d in def_divs if d.org>0)
    
    # Mod terreno + dottrina
    atk_tot *= t_mod['atk_mod'] * (1 + d_att['bonus_atk']) * (1 + d_def['bonus_atk']*0.3)
    def_tot *= t_mod['def_mod'] * (1 + d_def['bonus_def'])
    
    if def_tot == 0: def_tot = 1
    ratio = atk_tot / def_tot
    
    # Danni organizzazione e perdite
    dmg_to_def_org = (atk_tot * 0.08) * random.uniform(0.8,1.2)
    dmg_to_att_org = (def_tot * 0.06) * random.uniform(0.8,1.2)
    
    # Bonus blitzkrieg primi tick
    if dottr_att == "blitzkrieg" and tick < 12:
        dmg_to_def_org *= 1.4
    if dottr_def == "difesa_elastica" and tick > 18:
        dmg_to_att_org *= 1.3
        atk_tot *= 1.2
    
    # Applica danni org
    active_def = [x for x in def_divs if x.org>0]
    if active_def:
        for d in def_divs:
            if d.org>0:
                d.org = max(0, d.org - dmg_to_def_org / len(active_def))
                d.supply = max(10, d.supply - random.randint(0,2))
                
    active_att = [x for x in att_divs if x.org>0]
    if active_att:
        for d in att_divs:
            if d.org>0:
                d.org = max(0, d.org - dmg_to_att_org / len(active_att))
                d.supply = max(10, d.supply - random.randint(0,3))
    
    # Vantaggio battaglia per freccia
    advantage = (atk_tot - def_tot) / max(atk_tot+def_tot,1) * 100
    
    att_percent = 50 + advantage/2
    att_percent = max(5, min(95, att_percent))
    def_percent = 100 - att_percent
    
    return {
        "atk_tot": int(atk_tot),
        "def_tot": int(def_tot),
        "advantage": int(advantage),
        "att_percent": int(att_percent),
        "def_percent": int(def_percent),
        "dmg_att_org": int(dmg_to_att_org),
        "dmg_def_org": int(dmg_to_def_org),
        "ratio": round(ratio,2)
    }

# ESEMPIO SIMULAZIONE 5 MINUTI
if __name__ == "__main__":
    italia = {"soldi":3, "stabilita":3, "esercito":4, "tecnologia":4, "influenza":3}
    libia = {"soldi":2, "stabilita":2, "esercito":2, "tecnologia":2, "influenza":1}
    
    att_divs = [genera_divisione(italia, "paracadutisti"), genera_divisione(italia, "corazzata")]
    def_divs = [genera_divisione(libia, "fanteria")]
    
    print("=== PROELIUM BATTLE SIM 5 MIN ===")
    print(f"Terreno: {TERRENI['deserto']['nome']} - {TERRENI['deserto']['desc']}")
    print(f"Dottrine: IT AirLand vs LY Difesa Fortificata")
    print("")
    for tick in range(30):
        res = calcola_battaglia_tick(att_divs, def_divs, "deserto", "airland", "fortificata", tick)
        bar_att = "█" * (res['att_percent']//5)
        bar_def = "█" * (res['def_percent']//5)
        arrow = f"[ITALIA {bar_att} {res['att_percent']}% | {res['def_percent']}% {bar_def} LIBIA] Adv:{res['advantage']:+d}"
        print(f"T+{tick*10:03d}s {arrow} | ATK:{res['atk_tot']} DEF:{res['def_tot']} Ratio:{res['ratio']}")
        if all(d.org<=0 for d in def_divs):
            print(">>> DIFENSORE ROTTO - VITTORIA ATTACCANTE")
            break
        if all(d.org<=0 for d in att_divs):
            print(">>> ATTACCANTE ROTTO - DIFESA RIUSCITA")
            break
