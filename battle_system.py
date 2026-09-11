
"""
PROELIUM - BATTLE SYSTEM V3 COMPAT - HOI4
Supporta genera_divisione(stats, tipo) e genera_divisione(stats, tipo, numero)
"""
import random
from dataclasses import dataclass

TERRENI = {
    "pianura": {"nome": "Pianura", "atk_mod": 1.0, "def_mod": 1.0, "width": 120, "desc": "Nessun malus - 120 width"},
    "collina": {"nome": "Collina", "atk_mod": 0.85, "def_mod": 1.15, "width": 100, "desc": "-15% ATK +15% DEF"},
    "foresta": {"nome": "Foresta", "atk_mod": 0.70, "def_mod": 1.30, "width": 80, "desc": "Carri -30%"},
    "montagna": {"nome": "Montagna", "atk_mod": 0.55, "def_mod": 1.50, "width": 60, "desc": "-45% ATK"},
    "urbano": {"nome": "Urbano", "atk_mod": 0.50, "def_mod": 1.60, "width": 50, "desc": "Stalingrado +60% DEF"},
    "deserto": {"nome": "Deserto Aperto", "atk_mod": 1.15, "def_mod": 0.80, "width": 140, "desc": "Carri +15%"},
    "giungla": {"nome": "Giungla", "atk_mod": 0.60, "def_mod": 1.40, "width": 60, "desc": "-40% ATK"},
    "palude": {"nome": "Palude", "atk_mod": 0.65, "def_mod": 1.25, "width": 70, "desc": "Impaludato"},
    "fiume": {"nome": "Fiume", "atk_mod": 0.60, "def_mod": 1.40, "width": 90, "desc": "Attraversamento"},
    "fortificato": {"nome": "Linea Fortificata", "atk_mod": 0.40, "def_mod": 2.0, "width": 80, "desc": "Bunker"},
}

DOTTRINE = {
    "airland": {"nome": "AirLand Battle (NATO 1982)", "tipo": "offensiva", "bonus_atk": 0.25, "bonus_def": 0.05, "bonus_org": 10, "desc": "+25% ATK TEC 4+"},
    "blitzkrieg": {"nome": "Blitzkrieg Meccanizzato", "tipo": "offensiva", "bonus_atk": 0.35, "bonus_def": -0.10, "bonus_org": -5, "desc": "+35% ATK primi 2min"},
    "shock": {"nome": "Shock & Awe", "tipo": "offensiva", "bonus_atk": 0.15, "bonus_def": 0.10, "bonus_org": 5, "desc": "+15% ATK +10% DEF"},
    "infiltrazione": {"nome": "Infiltrazione SpecOps", "tipo": "offensiva", "bonus_atk": 0.20, "bonus_def": 0.20, "bonus_org": 15, "desc": "Ignora 30% terreno"},
    "difesa_elastica": {"nome": "Difesa Elastica (Manstein)", "tipo": "difensiva", "bonus_atk": 0.10, "bonus_def": 0.30, "bonus_org": 20, "desc": "+30% DEF contrattacco 3min"},
    "fortificata": {"nome": "Difesa Fortificata", "tipo": "difensiva", "bonus_atk": -0.05, "bonus_def": 0.50, "bonus_org": 25, "desc": "+50% DEF +25 ORG"},
    "deep_battle": {"nome": "Deep Battle Sovietica", "tipo": "offensiva", "bonus_atk": 0.30, "bonus_def": 0.15, "bonus_org": 0, "desc": "+30% ATK ignora 20% width"},
    "difesa_mobile": {"nome": "Difesa Mobile NATO", "tipo": "difensiva", "bonus_atk": 0.15, "bonus_def": 0.25, "bonus_org": 10, "desc": "+25% DEF +15% ATK"},
    "guerriglia": {"nome": "Guerriglia", "tipo": "difensiva", "bonus_atk": 0.05, "bonus_def": 0.40, "bonus_org": 30, "desc": "+40% DEF foresta/montagna"},
    "uman_wave": {"nome": "Human Wave", "tipo": "offensiva", "bonus_atk": 0.10, "bonus_def": -0.20, "bonus_org": -20, "desc": "Massa -20 ORG"},
}

@dataclass
class Divisione:
    nome: str
    atk: int
    defe: int
    org: float
    org_max: float
    width: int
    equip: int
    supply: int
    tipo: str
    numero: int

def genera_divisione(nazione_stats, tipo="fanteria", numero=None):
    # COMPAT: accetta 2 o 3 args, numero opzionale
    if numero is None:
        numero = random.randint(1, 200)
    esercito = nazione_stats.get('esercito', 3)
    tec = nazione_stats.get('tecnologia', 2)
    soldi = nazione_stats.get('soldi', 2)
    stab = nazione_stats.get('stabilita', 3)
    
    base_atk = 20 + esercito*15 + tec*10
    base_def = 25 + esercito*10 + tec*8
    base_org = 60 + esercito*10 + (5 if stab>=3 else -10)
    
    if tipo == "corazzata":
        base_atk = int(base_atk * 1.6)
        base_def = int(base_def * 0.8)
        base_org = int(base_org * 0.85)
        w = 30
    elif tipo == "meccanizzata":
        base_atk = int(base_atk * 1.4)
        w = 25
    elif tipo == "paracadutisti":
        base_atk = int(base_atk * 1.2)
        base_org = int(base_org * 1.1)
        w = 20
    else:
        w = 20

    org_val = base_org + random.randint(-5, 10)
    return Divisione(
        nome=f"{numero}. {tipo.capitalize()} Div.",
        atk=base_atk + random.randint(-10,10),
        defe=base_def + random.randint(-5,5),
        org=float(org_val),
        org_max=float(org_val),
        width=w,
        equip=min(100, 70 + soldi*6 + random.randint(-5,10)),
        supply=min(100, 75 + random.randint(-10,15)),
        tipo=tipo,
        numero=numero
    )

def calcola_battaglia_tick(att_divs, def_divs, terreno, dottrina_att, dottrina_dif, tick):
    t_mod = TERRENI.get(terreno, TERRENI["pianura"])
    d_att = DOTTRINE.get(dottrina_att, DOTTRINE["blitzkrieg"])
    d_def = DOTTRINE.get(dottrina_dif, DOTTRINE["fortificata"])
    
    max_width = t_mod['width']
    if dottrina_att == "deep_battle":
        max_width = int(max_width * 1.2)
    
    att_width_used = 0
    def_width_used = 0
    att_engaged = []
    def_engaged = []
    
    for d in att_divs:
        if d.org > 0 and att_width_used + d.width <= max_width:
            att_engaged.append(d)
            att_width_used += d.width
    
    for d in def_divs:
        if d.org > 0 and def_width_used + d.width <= max_width:
            def_engaged.append(d)
            def_width_used += d.width
    
    atk_tot = sum(d.atk * (d.org/max(d.org_max,1)) * (d.supply/100) * (d.equip/100) for d in att_engaged) if att_engaged else 1
    def_tot = sum(d.defe * (d.org/max(d.org_max,1)) * (d.supply/100) * (d.equip/100) for d in def_engaged) if def_engaged else 1
    
    atk_tot *= t_mod['atk_mod'] * (1 + d_att['bonus_atk'])
    def_tot *= t_mod['def_mod'] * (1 + d_def['bonus_def'])
    
    if dottrina_att == "blitzkrieg" and tick < 12:
        atk_tot *= 1.4
    if dottrina_att == "blitzkrieg" and tick >= 12:
        atk_tot *= 0.9
    
    ratio = atk_tot / max(def_tot,1)
    dmg_to_def_org = (atk_tot * 0.08) * random.uniform(0.8,1.2)
    dmg_to_att_org = (def_tot * 0.06) * random.uniform(0.8,1.2)
    
    if att_engaged:
        for d in att_engaged:
            d.org = max(0, d.org - dmg_to_att_org / len(att_engaged))
            d.supply = max(10, d.supply - random.randint(0,3))
    
    if def_engaged:
        for d in def_engaged:
            d.org = max(0, d.org - dmg_to_def_org / len(def_engaged))
            d.supply = max(10, d.supply - random.randint(0,2))
    
    advantage = (atk_tot - def_tot) / max(atk_tot+def_tot,1) * 100
    att_percent = max(5, min(95, 50 + advantage/2))
    def_percent = 100 - att_percent
    
    att_reserves = [d for d in att_divs if d not in att_engaged and d.org>0]
    def_reserves = [d for d in def_divs if d not in def_engaged and d.org>0]
    
    return {
        "atk_tot": int(atk_tot),
        "def_tot": int(def_tot),
        "advantage": int(advantage),
        "att_percent": int(att_percent),
        "def_percent": int(def_percent),
        "ratio": round(ratio,2),
        "att_width": att_width_used,
        "def_width": def_width_used,
        "max_width": max_width,
        "att_engaged": att_engaged,
        "def_engaged": def_engaged,
        "att_reserves": att_reserves,
        "def_reserves": def_reserves,
        "dmg_att": int(dmg_to_att_org),
        "dmg_def": int(dmg_to_def_org)
    }
