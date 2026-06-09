import os
import time
import json
import random
import requests
import tweepy
from bs4 import BeautifulSoup
from datetime import datetime

# ─────────────────────────────────────────────
# CREDENCIALES (se cargan desde Railway)
# ─────────────────────────────────────────────
API_KEY             = os.environ.get("API_KEY")
API_SECRET          = os.environ.get("API_SECRET")
ACCESS_TOKEN        = os.environ.get("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")

# ─────────────────────────────────────────────
# CONFIGURACIÓN GENERAL
# ─────────────────────────────────────────────
INTERVALO_PREMIER   = 2    # minutos entre chequeos de Premier Padel
INTERVALO_FIP       = 5    # minutos entre chequeos de torneos FIP
ARCHIVO_PUBLICADOS  = "publicados.json"

HASHTAGS_BASE       = "#Padel #PremierPadel #FIP #PadelArgentino"
LINK_WEB            = "Enterate de todo lo que pase en Argentina y el mundo en nuestra web: www.padelargentina.com.ar"

# ─────────────────────────────────────────────
# JUGADORES ARGENTINOS (detección)
# ─────────────────────────────────────────────
ARGENTINOS = {
    # Hombres
    "Agustin Tapia":           "Agustín Tapia",
    "Federico Chingotto":      "Federico Chingotto",
    "Franco Stupaczuk":        "Franco Stupaczuk",
    "Leandro Augsburger":      "Leandro Augsburger",
    "Martin Di Nenno":         "Martín Di Nenno",
    "Gonzalo Alfonso":         "Gonzalo Alfonso",
    "Leonel Aguirre":          "Leonel Aguirre",
    "Juan Tello":              "Juan Tello",
    "Maximiliano Arce":        "Maxi Arce",
    "Luciano Capra":           "Luciano Capra",
    "Ignacio Piotto":          "Ignacio Piotto",
    "Juan Cruz Belluati":      "Juan Cruz Belluati",
    "Juan Ignacio Rubini":     "Juan I. Rubini",
    "Federico Mourino":        "Federico Mouriño",
    "Valentino Libaak":        "Valentino Libaak",
    "Alex Chozas":             "Alex Chozas",
    "Carlos Gutierrez":        "Carlos Gutiérrez",
    "Maximiliano Sanchez Blasco": "Maxi Sánchez Blasco",
    "Agustin Torre":           "Agustín Torre",
    "Juan Cruz Forastello":    "Juan Cruz Forastello",
    "Juan Ignacio De Pascual": "Juan I. De Pascual",
    "Maximiliano Sanchez Aguero": "Maxi Sánchez Agüero",
    # Mujeres
    "Delfina Brea":            "Delfina Brea",
    "Ariana Sanchez":          "Ariana Sánchez",
    "Sofia Araujo":            "Sofía Araújo",
}

# Top 3 del ranking para detectar upset
TOP3 = ["coello", "tapia", "chingotto", "galan", "lebron", "stupaczuk"]

# ─────────────────────────────────────────────
# TORNEOS ACTIVOS (actualizar cada semana)
# ─────────────────────────────────────────────
TORNEOS_PREMIER = [
    {
        "nombre": "Premier Padel P1 Valencia",
        "url":    "https://www.padelfip.com/es/events/valencia-p1-2026/",
        "emoji":  "🏟️",
        "ciudad": "Valencia, España",
    },
]

TORNEOS_FIP = [
    {
        "nombre": "FIP Bronze Eslovenia",
        "url":    "https://www.padelfip.com/es/events/fip-bronze-slovenia-2026/",
        "emoji":  "🎾",
        "ciudad": "Ljubljana, Eslovenia",
    },
]

# ─────────────────────────────────────────────
# FRASES DINÁMICAS POR CONTEXTO
# ─────────────────────────────────────────────

FRASES_VICTORIA_ARG = [
    "¡VICTORIA ARGENTINA! 🇦🇷🔥",
    "¡LOS PIBES LO HICIERON! 🇦🇷💪",
    "¡ARRIBA ARGENTINA! 🇦🇷⚡",
    "¡VICTORIA ALBICELESTE! 🇦🇷🎾",
]

# FIP: cabecera fija para victorias (formato: 🎾🇦🇷 VICTORIA ARGENTINA:)
def cabecera_victoria_fip(torneo_nombre):
    return f"🎾🇦🇷 VICTORIA ARGENTINA:"

# FIP: cabecera fija para derrotas (formato: 🎾🇦🇷 Derrota argentina en el FIP de ...)
def cabecera_derrota_fip(torneo_nombre):
    # Extraer nombre corto del torneo (ej: "FIP Bronze Eslovenia" → "Eslovenia")
    partes = torneo_nombre.split()
    lugar = partes[-1] if partes else torneo_nombre
    return f"🎾🇦🇷 Derrota argentina en el FIP de {lugar}"

FRASES_DERROTA_ARG = [
    "Se terminó el sueño. 😔🇦🇷",
    "Eliminados. Hasta la próxima. 🇦🇷",
    "Cayeron, pero dejaron todo en la cancha. 🇦🇷",
]

FRASES_UPSET = [
    "¡¡SORPRESÓN!! 😱🎾",
    "¡¡CACHETAZO AL CIRCUITO!! 😱🔥",
    "¡¡NADIE LO ESPERABA!! 😱⚡",
]

FRASES_CAMPEON = [
    "👑 ¡¡CAMPEONES!!",
    "🏆 ¡¡SE CORONARON!!",
    "👑 ¡¡CAMPEONES DEL TORNEO!!",
]

FRASES_CAMPEON_ARG = [
    "👑🇦🇷 ¡¡CAMPEONES ARGENTINOS!! ¡¡LOS PIBES SE LLEVARON EL TÍTULO!!",
    "🏆🇦🇷 ¡¡CAMPEONES!! ¡¡ARGENTINA GRITA CAMPEÓN!!",
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def cargar_publicados():
    if os.path.exists(ARCHIVO_PUBLICADOS):
        with open(ARCHIVO_PUBLICADOS, "r") as f:
            return set(json.load(f))
    return set()

def guardar_publicado(id_partido):
    publicados = cargar_publicados()
    publicados.add(id_partido)
    with open(ARCHIVO_PUBLICADOS, "w") as f:
        json.dump(list(publicados), f)

def es_argentino(nombre):
    nombre_lower = nombre.lower()
    for clave in ARGENTINOS:
        if clave.lower() in nombre_lower:
            return True
    return False

def nombre_display(nombre):
    for clave, display in ARGENTINOS.items():
        if clave.lower() in nombre.lower():
            return f"🇦🇷 {display}"
    return nombre

def es_upset(ganadores, perdedores):
    """Detecta si un equipo bajo ranking venció a un top 3"""
    perdedores_str = " ".join(perdedores).lower()
    ganadores_str  = " ".join(ganadores).lower()
    hay_top_perdedor  = any(t in perdedores_str for t in TOP3)
    hay_top_ganador   = any(t in ganadores_str  for t in TOP3)
    return hay_top_perdedor and not hay_top_ganador

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
        print(f"✅ Tweet publicado ({len(texto)} chars): {texto[:80]}...")
        return True
    except Exception as e:
        print(f"❌ Error publicando tweet: {e}")
        return False

# ─────────────────────────────────────────────
# TEMPLATES DE TWEETS
# ─────────────────────────────────────────────

def tweet_premier_resultado(torneo, ganadores, perdedores, marcador,
                             tiempo, ronda_actual, ronda_siguiente,
                             proximos_rivales):
    """
    Tweet completo para un resultado de Premier Padel.
    Incluye victoria argentina si aplica, upset si aplica.
    """
    arg_gana  = any(es_argentino(j) for j in ganadores)
    arg_pierde = any(es_argentino(j) for j in perdedores)
    upset     = es_upset(ganadores, perdedores)

    lineas = []

    # Cabecera
    if upset:
        lineas.append(random.choice(FRASES_UPSET))
    if arg_gana:
        lineas.append(random.choice(FRASES_VICTORIA_ARG))

    # Torneo y ronda
    lineas.append(f"{torneo['emoji']} {torneo['nombre'].upper()} | {ronda_actual.upper()}")
    lineas.append(f"📍 {torneo['ciudad']}")
    lineas.append("")

    # Resultado
    g1 = nombre_display(ganadores[0])
    g2 = nombre_display(ganadores[1])
    p1 = nombre_display(perdedores[0])
    p2 = nombre_display(perdedores[1])

    lineas.append(f"✅ {g1} / {g2}")
    lineas.append(f"❌ {p1} / {p2}")
    lineas.append(f"🎯 {marcador}")
    if tiempo:
        lineas.append(f"⏱️ {tiempo}")
    lineas.append("")

    # Avance
    lineas.append(f"➡️ Avanzan a {ronda_siguiente}")
    if proximos_rivales:
        lineas.append(f"🆚 Próximos rivales: {proximos_rivales}")
    lineas.append("")

    # Footer
    lineas.append(HASHTAGS_BASE)
    lineas.append(LINK_WEB)

    return "\n".join(lineas)[:280]


def tweet_premier_campeon(torneo, campeones, finalistas, marcador, es_arg):
    lineas = []

    c1_raw = campeones[0]
    c2_raw = campeones[1]

    if es_arg:
        # Ambos argentinos → celebración especial
        lineas.append(random.choice(FRASES_CAMPEON_ARG))
    else:
        # No son argentinos → formato simple: CAMPEONES + nombre
        nombre_c1 = c1_raw.split()[-1]  # apellido
        nombre_c2 = c2_raw.split()[-1]  # apellido
        lineas.append(f"🏆 ¡CAMPEONES! {nombre_c1} y {nombre_c2}")

    lineas.append(f"🏆 {torneo['nombre'].upper()} — FINAL")
    lineas.append(f"📍 {torneo['ciudad']}")
    lineas.append("")

    c1 = nombre_display(c1_raw)
    c2 = nombre_display(c2_raw)
    f1 = nombre_display(finalistas[0])
    f2 = nombre_display(finalistas[1])

    lineas.append(f"🥇 {c1} / {c2}")
    lineas.append(f"🥈 {f1} / {f2}")
    lineas.append(f"🎯 {marcador}")
    lineas.append("")
    lineas.append(HASHTAGS_BASE)
    lineas.append(LINK_WEB)

    return "\n".join(lineas)[:280]


def tweet_fip_resultado(torneo, ganadores, perdedores, marcador,
                        ronda_actual, ronda_siguiente, arg_gana):
    """
    Tweet para torneos FIP — solo cuando hay argentinos involucrados.
    """
    lineas = []

    if arg_gana:
        lineas.append(cabecera_victoria_fip(torneo["nombre"]))
    else:
        lineas.append(cabecera_derrota_fip(torneo["nombre"]))

    lineas.append(f"{torneo['emoji']} {torneo['nombre'].upper()} | {ronda_actual.upper()}")
    lineas.append(f"📍 {torneo['ciudad']}")
    lineas.append("")

    g1 = nombre_display(ganadores[0])
    g2 = nombre_display(ganadores[1])
    p1 = nombre_display(perdedores[0])
    p2 = nombre_display(perdedores[1])

    lineas.append(f"✅ {g1} / {g2}")
    lineas.append(f"❌ {p1} / {p2}")
    lineas.append(f"🎯 {marcador}")
    lineas.append("")

    if arg_gana and ronda_siguiente:
        lineas.append(f"➡️ Avanzan a {ronda_siguiente}")
        lineas.append("")

    lineas.append(HASHTAGS_BASE)
    lineas.append(LINK_WEB)

    return "\n".join(lineas)[:280]


def tweet_fip_campeon(torneo, campeones, finalistas, marcador, es_arg):
    lineas = []
    if es_arg:
        lineas.append(random.choice(FRASES_CAMPEON_ARG))
    else:
        lineas.append(random.choice(FRASES_CAMPEON))

    lineas.append(f"🏆 {torneo['nombre'].upper()} — CAMPEONES")
    lineas.append(f"📍 {torneo['ciudad']}")
    lineas.append("")

    c1 = nombre_display(campeones[0])
    c2 = nombre_display(campeones[1])

    lineas.append(f"🥇 {c1} / {c2}")
    lineas.append(f"🎯 {marcador}")
    lineas.append("")
    lineas.append(HASHTAGS_BASE)
    lineas.append(LINK_WEB)

    return "\n".join(lineas)[:280]


# ─────────────────────────────────────────────
# SCRAPING — NOTICIAS FIP (fuente de resultados)
# ─────────────────────────────────────────────

def obtener_noticias_fip():
    url = "https://www.padelfip.com/es/noticias/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        noticias = []
        for a in soup.find_all("a", href=True):
            href  = a.get("href", "")
            texto = a.get_text(strip=True)
            if "/2026/" in href and len(texto) > 25:
                noticias.append({"titulo": texto, "url": href})
        # deduplicar por URL
        vistos = set()
        result = []
        for n in noticias:
            if n["url"] not in vistos:
                vistos.add(n["url"])
                result.append(n)
        return result
    except Exception as e:
        print(f"[ERROR] noticias FIP: {e}")
        return []


def procesar_noticia_como_tweet(noticia, torneo):
    """
    Convierte una noticia de resultado de FIP en un tweet formateado.
    Esto se usa cuando no tenemos datos estructurados del partido.
    """
    titulo = noticia["titulo"]
    tiene_arg = any(a.lower() in titulo.lower() for a in ARGENTINOS)
    es_final  = any(kw in titulo.lower() for kw in ["campeón", "campeones", "final", "título"])

    if es_final:
        cabecera = random.choice(FRASES_CAMPEON_ARG if tiene_arg else FRASES_CAMPEON)
    elif tiene_arg:
        # Detectar si ganó o perdió el argentino por palabras clave
        palabras_victoria = ["vence", "gana", "triunfa", "campeón", "avanza", "elimina"]
        arg_gana = any(kw in titulo.lower() for kw in palabras_victoria)
        cabecera = cabecera_victoria_fip(torneo["nombre"]) if arg_gana else cabecera_derrota_fip(torneo["nombre"])
    else:
        return None  # No publicar si no hay argentino y no es final

    tweet = (
        f"{cabecera}\n\n"
        f"{torneo['emoji']} {torneo['nombre'].upper()}\n"
        f"📍 {torneo['ciudad']}\n\n"
        f"📋 {titulo}\n\n"
        f"{HASHTAGS_BASE}\n"
        f"{LINK_WEB}"
    )
    return tweet[:280]


# ─────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────

def ciclo():
    print(f"\n{'='*50}")
    print(f"🤖 BOT PADEL ARGENTINA — INICIADO")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"⏱️  Premier Padel: cada {INTERVALO_PREMIER} min")
    print(f"⏱️  FIP: cada {INTERVALO_FIP} min")
    print(f"{'='*50}\n")

    contador = 0

    while True:
        ahora = datetime.now().strftime("%H:%M:%S")
        print(f"\n🔍 [{ahora}] Chequeando resultados...")

        publicados = cargar_publicados()
        noticias   = obtener_noticias_fip()

        # ── PREMIER PADEL ─────────────────────────
        # Los resultados de Premier se obtienen vía noticias FIP
        # (cada 2 min — todos los partidos)
        for noticia in noticias:
            url = noticia["url"]
            if url in publicados:
                continue
            # Premier Padel: publicar TODOS los partidos
            es_premier = any(kw in noticia["titulo"].lower() for kw in
                             ["premier", "p1", "p2", "major"])
            if es_premier:
                tiene_arg = any(a.lower() in noticia["titulo"].lower() for a in ARGENTINOS)
                cabecera = random.choice(FRASES_VICTORIA_ARG) if tiene_arg else "🎾 RESULTADO"
                tweet = (
                    f"{cabecera}\n\n"
                    f"🏟️ PREMIER PADEL\n\n"
                    f"📋 {noticia['titulo']}\n\n"
                    f"{HASHTAGS_BASE}\n"
                    f"{LINK_WEB}"
                )
                if publicar_tweet(tweet[:280]):
                    guardar_publicado(url)
                    time.sleep(3)

        # ── FIP TORNEOS ────────────────────────────
        # Solo cuando hay argentinos involucrados
        for torneo in TORNEOS_FIP:
            for noticia in noticias:
                url = noticia["url"]
                if url in publicados:
                    continue
                if torneo["nombre"].split()[1].lower() not in noticia["url"].lower():
                    continue
                tweet = procesar_noticia_como_tweet(noticia, torneo)
                if tweet:
                    if publicar_tweet(tweet):
                        guardar_publicado(url)
                        time.sleep(3)

        # Intervalo: Premier cada 2 min, FIP cada 5 min
        intervalo = INTERVALO_PREMIER if contador % 2 == 0 else INTERVALO_FIP
        print(f"✅ Ciclo {contador+1} completado — próximo en {intervalo} min")
        contador += 1
        time.sleep(intervalo * 60)


if __name__ == "__main__":
    ciclo()
