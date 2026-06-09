import os
import time
import json
import random
import requests
import tweepy
import pytz
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CREDENCIALES
# ─────────────────────────────────────────────
API_KEY             = os.environ.get("API_KEY")
API_SECRET          = os.environ.get("API_SECRET")
ACCESS_TOKEN        = os.environ.get("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")

ARGENTINA_TZ       = pytz.timezone("America/Argentina/Buenos_Aires")
INTERVALO_MINUTOS  = 2
ARCHIVO_PUBLICADOS = "publicados.json"
ARCHIVO_ESTADO     = "estado.json"

HASHTAGS = "#Padel #PremierPadel #FIP #PadelArgentino"
LINK_WEB = "Enterate de todo en: www.padelargentina.com.ar"

# ─────────────────────────────────────────────
# SOFASCORE — IDs de torneos Premier Padel 2026
# ─────────────────────────────────────────────
SOFASCORE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept":     "application/json",
}

TORNEOS_PREMIER = [
    {
        "nombre":        "Premier Padel P1 Valencia",
        "ciudad":        "Valencia",
        "bandera":       "🇪🇸",
        "tz_local":      "Europe/Madrid",
        "emoji":         "🏟️",
        "categoria":     "P1",
        "ss_id_men":     35317,
        "ss_id_women":   35318,
    },
]

TORNEOS_FIP = [
    {
        "nombre":    "FIP Bronze Eslovenia",
        "ciudad":    "Ljubljana",
        "bandera":   "🇸🇮",
        "emoji":     "🎾",
        "categoria": "FIP Bronze",
        "url_fip":   "https://www.padelfip.com/es/events/fip-bronze-slovenia-2026/",
    },
]

# ─────────────────────────────────────────────
# JUGADORES ARGENTINOS
# ─────────────────────────────────────────────
ARGENTINOS = {
    "Agustin Tapia":              "Agustín Tapia",
    "Federico Chingotto":         "Federico Chingotto",
    "Franco Stupaczuk":           "Franco Stupaczuk",
    "Leandro Augsburger":         "Leandro Augsburger",
    "Martin Di Nenno":            "Martín Di Nenno",
    "Gonzalo Alfonso":            "Gonzalo Alfonso",
    "Leonel Aguirre":             "Leonel Aguirre",
    "Juan Tello":                 "Juan Tello",
    "Maximiliano Arce":           "Maxi Arce",
    "Luciano Capra":              "Luciano Capra",
    "Ignacio Piotto":             "Ignacio Piotto",
    "Juan Cruz Belluati":         "Juan Cruz Belluati",
    "Juan Ignacio Rubini":        "Juan I. Rubini",
    "Federico Mourino":           "Federico Mouriño",
    "Valentino Libaak":           "Valentino Libaak",
    "Alex Chozas":                "Alex Chozas",
    "Carlos Gutierrez":           "Carlos Gutiérrez",
    "Maximiliano Sanchez Blasco": "Maxi Sánchez Blasco",
    "Agustin Torre":              "Agustín Torre",
    "Juan Cruz Forastello":       "Juan Cruz Forastello",
    "Juan Ignacio De Pascual":    "Juan I. De Pascual",
    "Maximiliano Sanchez Aguero": "Maxi Sánchez Agüero",
    "Delfina Brea":               "Delfina Brea",
    "Ariana Sanchez":             "Ariana Sánchez",
    "Sofia Araujo":               "Sofía Araújo",
}

TOP3 = ["coello", "tapia", "chingotto", "galan", "lebron", "stupaczuk"]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def hora_arg():
    return datetime.now(ARGENTINA_TZ)

def es_argentino(nombre):
    return any(k.lower() in nombre.lower() for k in ARGENTINOS)

def nombre_display(nombre):
    for k, v in ARGENTINOS.items():
        if k.lower() in nombre.lower():
            return f"🇦🇷 {v}"
    return nombre

def apellido(nombre):
    partes = nombre.strip().split()
    return partes[-1] if partes else nombre

def es_upset(ganadores, perdedores):
    perd_str = " ".join(perdedores).lower()
    gan_str  = " ".join(ganadores).lower()
    return any(t in perd_str for t in TOP3) and not any(t in gan_str for t in TOP3)

def cargar_json(archivo):
    if os.path.exists(archivo):
        with open(archivo) as f:
            return json.load(f)
    return {}

def guardar_json(archivo, data):
    with open(archivo, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def cargar_publicados():
    d = cargar_json(ARCHIVO_PUBLICADOS)
    return set(d.get("ids", []))

def guardar_publicado(pid):
    d = cargar_json(ARCHIVO_PUBLICADOS)
    ids = set(d.get("ids", []))
    ids.add(pid)
    guardar_json(ARCHIVO_PUBLICADOS, {"ids": list(ids)})

def ya_hecho_hoy(tarea):
    estado = cargar_json(ARCHIVO_ESTADO)
    return estado.get(tarea) == hora_arg().strftime("%Y-%m-%d")

def marcar_hecho_hoy(tarea):
    estado = cargar_json(ARCHIVO_ESTADO)
    estado[tarea] = hora_arg().strftime("%Y-%m-%d")
    guardar_json(ARCHIVO_ESTADO, estado)

def convertir_a_arg(hora_utc_str, tz_local):
    """Convierte hora local del torneo a hora argentina"""
    try:
        tz = pytz.timezone(tz_local)
        hoy = datetime.now(tz).date()
        h, m = map(int, hora_utc_str.split(":"))
        dt = tz.localize(datetime(hoy.year, hoy.month, hoy.day, h, m))
        return dt.astimezone(ARGENTINA_TZ).strftime("%H:%M")
    except:
        return hora_utc_str

# ─────────────────────────────────────────────
# SOFASCORE API
# ─────────────────────────────────────────────

def ss_get(path):
    url = f"https://api.sofascore.com/api/v1{path}"
    try:
        r = requests.get(url, headers=SOFASCORE_HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[SS ERROR] {path}: {e}")
    return None

def obtener_partidos_torneo(ss_id):
    """Trae todos los partidos (pasados y próximos) de un torneo"""
    data = ss_get(f"/unique-tournament/{ss_id}/events/last/0")
    partidos = []
    if data and "events" in data:
        partidos.extend(data["events"])
    data2 = ss_get(f"/unique-tournament/{ss_id}/events/next/0")
    if data2 and "events" in data2:
        partidos.extend(data2["events"])
    return partidos

def obtener_orden_dia(ss_id, tz_local):
    """Devuelve los partidos del día siguiente organizados por pista"""
    manana = (hora_arg() + timedelta(days=1)).date()
    partidos = obtener_partidos_torneo(ss_id)
    pistas = {}

    for p in partidos:
        ts = p.get("startTimestamp", 0)
        if not ts:
            continue
        tz = pytz.timezone(tz_local)
        dt_local = datetime.fromtimestamp(ts, tz=tz)
        if dt_local.date() != manana:
            continue

        hora_local = dt_local.strftime("%H:%M")
        hora_argentina = datetime.fromtimestamp(ts, tz=ARGENTINA_TZ).strftime("%H:%M")

        pista = p.get("venue", {}).get("name") or p.get("roundInfo", {}).get("name") or "Pista"
        home = p.get("homeTeam", {})
        away = p.get("awayTeam", {})

        j1 = home.get("name", "—")
        j2 = home.get("subTeamName", "")
        j3 = away.get("name", "—")
        j4 = away.get("subTeamName", "")

        if pista not in pistas:
            pistas[pista] = []
        pistas[pista].append({
            "hora_arg":   hora_argentina,
            "hora_local": hora_local,
            "j1": j1, "j2": j2,
            "j3": j3, "j4": j4,
        })

    # Ordenar cada pista por hora
    for pista in pistas:
        pistas[pista].sort(key=lambda x: x["hora_arg"])

    return pistas

def obtener_partidos_finalizados(ss_id):
    """Trae partidos finalizados hoy"""
    data = ss_get(f"/unique-tournament/{ss_id}/events/last/0")
    if not data or "events" not in data:
        return []
    hoy = hora_arg().date()
    finalizados = []
    for p in data["events"]:
        status = p.get("status", {}).get("type", "")
        if status != "finished":
            continue
        ts = p.get("startTimestamp", 0)
        dt = datetime.fromtimestamp(ts, tz=ARGENTINA_TZ)
        if dt.date() == hoy:
            finalizados.append(p)
    return finalizados

def parsear_partido(p):
    """Extrae datos estructurados de un partido de Sofascore"""
    home = p.get("homeTeam", {})
    away = p.get("awayTeam", {})
    score = p.get("homeScore", {}), p.get("awayScore", {})

    # Jugadores
    j1 = home.get("name", "")
    j2 = home.get("subTeamName", "") or ""
    j3 = away.get("name", "")
    j4 = away.get("subTeamName", "") or ""

    # Sets
    sets_home = [score[0].get(f"period{i}", None) for i in range(1, 6)]
    sets_away = [score[1].get(f"period{i}", None) for i in range(1, 6)]

    sets_jugados = []
    for sh, sa in zip(sets_home, sets_away):
        if sh is not None and sa is not None:
            sets_jugados.append(f"{sh}-{sa}")

    marcador = " / ".join(sets_jugados) if sets_jugados else "—"

    # Ganador
    winner = p.get("winnerCode", 0)
    if winner == 1:
        ganadores  = [j1, j2]
        perdedores = [j3, j4]
    else:
        ganadores  = [j3, j4]
        perdedores = [j1, j2]

    # Ronda
    ronda = p.get("roundInfo", {}).get("name", "")

    # Tiempo de juego (minutos)
    tiempo_min = p.get("time", {}).get("played", None)
    tiempo_str = f"{tiempo_min // 60}h {tiempo_min % 60}min" if tiempo_min else None

    return {
        "id":         str(p.get("id", "")),
        "ganadores":  ganadores,
        "perdedores": perdedores,
        "marcador":   marcador,
        "ronda":      ronda,
        "tiempo":     tiempo_str,
    }

# ─────────────────────────────────────────────
# TEMPLATES DE TWEETS
# ─────────────────────────────────────────────

def tweet_premier_resultado(torneo, ganadores, perdedores, marcador,
                             tiempo, ronda, ronda_sig, proximos):
    arg_gana = any(es_argentino(j) for j in ganadores)
    upset    = es_upset(ganadores, perdedores)

    lineas = []
    if upset:
        lineas.append(random.choice(["¡¡SORPRESÓN!! 😱🎾", "¡¡CACHETAZO AL CIRCUITO!! 😱🔥", "¡¡NADIE LO ESPERABA!! 😱⚡"]))
    if arg_gana:
        lineas.append(random.choice(["🇦🇷🔥 ¡VICTORIA ARGENTINA!", "🇦🇷💪 ¡LOS PIBES LO HICIERON!", "🇦🇷⚡ ¡ARRIBA ARGENTINA!"]))

    lineas.append(f"{torneo['emoji']} {torneo['nombre'].upper()} | {ronda.upper()}")
    lineas.append(f"📍 {torneo['ciudad']} {torneo['bandera']}")
    lineas.append("")
    lineas.append(f"✅ {nombre_display(ganadores[0])} / {nombre_display(ganadores[1])}")
    lineas.append(f"❌ {nombre_display(perdedores[0])} / {nombre_display(perdedores[1])}")
    lineas.append(f"🎯 {marcador}")
    if tiempo:
        lineas.append(f"⏱️ {tiempo}")
    lineas.append("")
    if ronda_sig:
        lineas.append(f"➡️ Avanzan a {ronda_sig}")
    if proximos:
        lineas.append(f"🆚 vs {proximos}")
    lineas.append("")
    lineas.append(HASHTAGS)
    lineas.append(LINK_WEB)

    return "\n".join(lineas)[:280]

def tweet_fip_resultado(torneo, ganadores, perdedores, marcador, ronda, arg_gana):
    lugar = torneo["nombre"].split()[-1]
    if arg_gana:
        cabecera = "🎾🇦🇷 VICTORIA ARGENTINA:"
    else:
        cabecera = f"🎾🇦🇷 Derrota argentina en el FIP de {lugar}"

    lineas = [
        cabecera,
        f"{torneo['emoji']} {torneo['nombre'].upper()} | {ronda.upper()}",
        f"📍 {torneo['ciudad']} {torneo['bandera']}",
        "",
        f"✅ {nombre_display(ganadores[0])} / {nombre_display(ganadores[1])}",
        f"❌ {nombre_display(perdedores[0])} / {nombre_display(perdedores[1])}",
        f"🎯 {marcador}",
        "",
        HASHTAGS,
        LINK_WEB,
    ]
    return "\n".join(lineas)[:280]

def tweet_campeon_premier(torneo, campeones, finalistas, marcador, es_arg):
    if es_arg:
        cab = random.choice([
            "👑🇦🇷 ¡¡CAMPEONES ARGENTINOS!! ¡¡LOS PIBES SE LLEVARON EL TÍTULO!!",
            "🏆🇦🇷 ¡¡ARGENTINA GRITA CAMPEÓN!!",
        ])
    else:
        ap1 = apellido(campeones[0])
        ap2 = apellido(campeones[1])
        cab = f"🏆 ¡CAMPEONES! {ap1} y {ap2}"

    lineas = [
        cab,
        f"{torneo['emoji']} {torneo['nombre'].upper()} — FINAL",
        f"📍 {torneo['ciudad']} {torneo['bandera']}",
        "",
        f"🥇 {nombre_display(campeones[0])} / {nombre_display(campeones[1])}",
        f"🥈 {nombre_display(finalistas[0])} / {nombre_display(finalistas[1])}",
        f"🎯 {marcador}",
        "",
        HASHTAGS,
        LINK_WEB,
    ]
    return "\n".join(lineas)[:280]

def tweet_orden_dia(torneo, pistas):
    """Tweet con orden del día siguiente, pista por pista"""
    manana = (hora_arg() + timedelta(days=1)).strftime("%d/%m/%Y")
    lineas = []
    lineas.append(f"🗓️ MAÑANA EN {torneo['nombre'].upper()} — {manana}")
    lineas.append(f"📍 {torneo['ciudad']} {torneo['bandera']}")
    lineas.append("")

    for pista, partidos in pistas.items():
        lineas.append(f"🎾 {pista}")
        for p in partidos[:4]:  # máx 4 por pista para no exceder 280
            hora_arg_str = p["hora_arg"]
            hora_local   = p["hora_local"]
            j1 = nombre_display(p["j1"])
            j3 = nombre_display(p["j3"])
            lineas.append(f"  🇦🇷⏰{hora_arg_str} ({torneo['bandera']}{hora_local})")
            lineas.append(f"  {j1} vs {j3}")
        lineas.append("")

    lineas.append(HASHTAGS)
    lineas.append(LINK_WEB)
    return "\n".join(lineas)[:280]

def tweet_cuadro(torneo, genero, tipo, parejas):
    """Tweet con cuadro qualifying o principal"""
    emoji_gen = "👨" if genero == "Masculino" else "👩"
    tipo_str  = "QUALIFYING" if tipo == "qualy" else "CUADRO PRINCIPAL"

    lineas = []
    lineas.append(f"📋 {tipo_str} {genero.upper()} {emoji_gen}")
    lineas.append(f"{torneo['emoji']} {torneo['nombre'].upper()}")
    lineas.append(f"📍 {torneo['ciudad']} {torneo['bandera']}")
    lineas.append("")

    for i, (j1, j2, j3, j4) in enumerate(parejas[:6]):  # máx 6 cruces
        lineas.append(f"  {nombre_display(j1)}/{nombre_display(j2)} vs {nombre_display(j3)}/{nombre_display(j4)}")

    if len(parejas) > 6:
        lineas.append(f"  + {len(parejas)-6} partidos más...")

    lineas.append("")
    lineas.append(HASHTAGS)
    lineas.append(LINK_WEB)
    return "\n".join(lineas)[:280]

# ─────────────────────────────────────────────
# PUBLICAR EN X
# ─────────────────────────────────────────────

def publicar_tweet(texto):
    try:
        client = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True,
        )
        client.create_tweet(text=texto)
        print(f"✅ Tweet: {texto[:70]}...")
        return True
    except Exception as e:
        print(f"❌ Error tweet: {e}")
        return False

# ─────────────────────────────────────────────
# OBTENER CUADROS DE SOFASCORE
# ─────────────────────────────────────────────

def obtener_cuadros_ss(ss_id):
    """Obtiene los cruces del cuadro desde Sofascore"""
    data = ss_get(f"/unique-tournament/{ss_id}/events/next/0")
    if not data or "events" not in data:
        return []
    parejas = []
    for p in data["events"]:
        home = p.get("homeTeam", {})
        away = p.get("awayTeam", {})
        j1 = home.get("name", "")
        j2 = home.get("subTeamName", "") or ""
        j3 = away.get("name", "")
        j4 = away.get("subTeamName", "") or ""
        if j1 and j3:
            parejas.append((j1, j2, j3, j4))
    return parejas

# ─────────────────────────────────────────────
# MONITOREO FIP (scraping noticias)
# ─────────────────────────────────────────────

def obtener_noticias_fip():
    from bs4 import BeautifulSoup
    try:
        r = requests.get("https://www.padelfip.com/es/noticias/",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        noticias, vistos = [], set()
        for a in soup.find_all("a", href=True):
            href  = a.get("href", "")
            texto = a.get_text(strip=True)
            if "/2026/" in href and len(texto) > 25 and href not in vistos:
                vistos.add(href)
                noticias.append({"titulo": texto, "url": href})
        return noticias
    except Exception as e:
        print(f"[FIP ERROR] {e}")
        return []

# ─────────────────────────────────────────────
# TAREAS PROGRAMADAS
# ─────────────────────────────────────────────

def tarea_cuadros():
    """Publica cuadros de qualifying y principal al inicio del torneo"""
    for torneo in TORNEOS_PREMIER:
        pid = f"cuadros_{torneo['nombre']}"
        if ya_hecho_hoy(pid):
            continue

        for ss_id, genero in [(torneo["ss_id_men"], "Masculino"),
                               (torneo["ss_id_women"], "Femenino")]:
            # Qualifying
            parejas_q = obtener_cuadros_ss(ss_id)[:8]
            if parejas_q:
                tw = tweet_cuadro(torneo, genero, "qualy", parejas_q)
                publicar_tweet(tw)
                time.sleep(5)

            # Principal
            parejas_p = obtener_cuadros_ss(ss_id)
            if parejas_p:
                tw = tweet_cuadro(torneo, genero, "principal", parejas_p)
                publicar_tweet(tw)
                time.sleep(5)

        marcar_hecho_hoy(pid)

def tarea_orden_dia():
    """Al terminar el último partido del día, publica el orden del día siguiente"""
    for torneo in TORNEOS_PREMIER:
        tid = f"orden_dia_{torneo['nombre']}"
        if ya_hecho_hoy(tid):
            continue

        # Chequear si ya terminaron todos los partidos de hoy
        finalizados = obtener_partidos_finalizados(torneo["ss_id_men"])
        proximos    = ss_get(f"/unique-tournament/{torneo['ss_id_men']}/events/next/0")
        hay_hoy     = False
        if proximos and "events" in proximos:
            hoy = hora_arg().date()
            for p in proximos["events"]:
                ts = p.get("startTimestamp", 0)
                dt = datetime.fromtimestamp(ts, tz=ARGENTINA_TZ)
                if dt.date() == hoy:
                    hay_hoy = True
                    break

        if hay_hoy:
            return  # Todavía quedan partidos hoy

        # Publicar orden del día siguiente
        pistas = obtener_orden_dia(torneo["ss_id_men"], torneo["tz_local"])
        if pistas:
            tw = tweet_orden_dia(torneo, pistas)
            if publicar_tweet(tw):
                marcar_hecho_hoy(tid)

# ─────────────────────────────────────────────
# MONITOREO DE RESULTADOS
# ─────────────────────────────────────────────

def monitorear_premier():
    publicados = cargar_publicados()

    for torneo in TORNEOS_PREMIER:
        for ss_id in [torneo["ss_id_men"], torneo["ss_id_women"]]:
            partidos = obtener_partidos_finalizados(ss_id)
            for p in partidos:
                datos = parsear_partido(p)
                pid   = f"premier_{datos['id']}"

                if pid in publicados:
                    continue

                # Tweet resultado
                tw = tweet_premier_resultado(
                    torneo,
                    datos["ganadores"],
                    datos["perdedores"],
                    datos["marcador"],
                    datos["tiempo"],
                    datos["ronda"],
                    "",   # ronda siguiente (Sofascore no siempre la da)
                    "",   # próximos rivales
                )
                if publicar_tweet(tw):
                    guardar_publicado(pid)
                    time.sleep(5)

def monitorear_fip():
    publicados = cargar_publicados()
    noticias   = obtener_noticias_fip()

    for noticia in noticias:
        url    = noticia["url"]
        titulo = noticia["titulo"]

        if url in publicados:
            continue

        tiene_arg = any(a.lower() in titulo.lower() for a in ARGENTINOS)
        es_result = any(kw in titulo.lower() for kw in [
            "vence", "gana", "triunfa", "campeón", "resultado",
            "derrota", "elimina", "avanza", "final", "día"
        ])

        if not tiene_arg or not es_result:
            continue

        torneo = TORNEOS_FIP[0]  # ajustar si hay varios
        lugar  = torneo["nombre"].split()[-1]
        arg_gana = any(kw in titulo.lower() for kw in
                       ["vence", "gana", "triunfa", "campeón", "avanza"])

        if arg_gana:
            cab = "🎾🇦🇷 VICTORIA ARGENTINA:"
        else:
            cab = f"🎾🇦🇷 Derrota argentina en el FIP de {lugar}"

        tw = (
            f"{cab}\n\n"
            f"{torneo['emoji']} {torneo['nombre'].upper()}\n"
            f"📍 {torneo['ciudad']} {torneo['bandera']}\n\n"
            f"📋 {titulo}\n\n"
            f"{HASHTAGS}\n"
            f"{LINK_WEB}"
        )[:280]

        if publicar_tweet(tw):
            guardar_publicado(url)
            time.sleep(3)

# ─────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────

def ciclo():
    print(f"\n{'='*50}")
    print(f"🤖 BOT X — PADEL ARGENTINA INICIADO")
    print(f"📅 {hora_arg().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*50}\n")

    contador = 0
    while True:
        print(f"\n🔍 [{hora_arg().strftime('%H:%M:%S')}] Ciclo {contador+1}")

        tarea_cuadros()
        tarea_orden_dia()
        monitorear_premier()
        monitorear_fip()

        print(f"✅ Próximo chequeo en {INTERVALO_MINUTOS} min")
        contador += 1
        time.sleep(INTERVALO_MINUTOS * 60)

if __name__ == "__main__":
    ciclo()
