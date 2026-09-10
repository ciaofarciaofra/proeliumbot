# PROELIUM BOT - Guida Installazione VERA
Questo bot funziona davvero.

## COSA FA
- Solo Master e Admin con ruolo Master, Amministratore PROELIUM, Admin possono tirare dadi. Anti-cheat totale.
- Gestisce schede, guerre, influenza, embargo, DEFCON, log.
- Salva su nazioni.json e defcon.json

## INSTALLAZIONE 3 MINUTI

1. Crea Bot Discord:
   https://discord.com/developers/applications -> New App -> Bot -> Add Bot -> Copia Token
   Attiva MESSAGE CONTENT INTENT e SERVER MEMBERS INTENT

2. Invita Bot:
   OAuth2 -> URL Generator -> Scopes: bot + applications.commands
   Permissions: Administrator per test, poi Send Messages, Embed Links, Manage Roles
   Copia URL e invita

3. Host Gratis:
   REPLIT: replit.com -> Create Repl -> Upload files -> Secrets DISCORD_TOKEN -> Run
   RAILWAY: railway.app -> New Project -> Deploy from GitHub -> Variabile DISCORD_TOKEN

4. Configura .env:
   Copia .env.example in .env e incolla token
   DISCORD_TOKEN=xxx
   GUILD_ID=id_tuo_server (tasto destro server -> Copia ID con modalita sviluppatore)
   LOG_CHANNEL_ID=id_canale log

## COME FUNZIONA - FLUSSO REALE

Ticket -> Gioco:
1. Utente apre ticket con template
2. Master fa /proelium_crea nome:ITALIA soldi:3 stabilita:3 esercito:3 tecnologia:3 influenza:2 blocco:NATO nucleare:False
3. Guerra: Utente dichiara in #guerre, Master fa /proelium_guerra attaccante:ITALIA punti_att:5 difensore:LIBIA punti_dif:4 logistica:False
4. Bot tira d6 pubblico, toglie STAB/SOLDI automatico, logga in #proelium-log

Comandi:
- /proelium_crea
- /proelium_scheda nome
- /proelium_guerra
- /proelium_influenza
- /proelium_defcon
- /proelium_embargo
- /proelium_lista
- /proelium_reset

## ANTI-ARCADE
- Max 18 punti normali, 20 superpotenze
- Guerra >2 turni = -1 STAB/turno effetto Vietnam
- Debito da embargo
- DEFCON parte da 4, ogni proxy USA-URSS -1
