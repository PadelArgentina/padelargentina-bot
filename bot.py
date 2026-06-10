import os
import time
import json
import random
import requests
import tweepy
import pytz
from datetime import datetime, timedelta

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

DIAS_EN = {
    0:"MONDAY",1:"TUESDAY",2:"WEDNESDAY",
    3:"THURSDAY",4:"FRIDAY",5:"SATURDAY",6:"SUNDAY"
}
MESES_EN = {
    1:"JANUARY",2:"FEBRUARY",3:"MARCH",4:"APRIL",
    5:"MAY",6:"JUNE",7:"JULY",8:"AUGUST",
    9:"SEPTEMBER",10:"OCTOBER",11:"NOVEMBER",12:"DECEMBER"
}

TORNEOS_PREMIER = [
    {
        "nombre":      "Premier Padel P1 Valencia",
        "ciudad":      "Valencia",
        "bandera":     "🇪🇸",
        "tz_local":    "Europe/Madrid",
        "emoji":       "🏟️",
        "categoria":   "P1",
        "ss_id_men":   35317,
        "ss_id_women": 35318,
    },
]

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
TOP3 = ["coello","tapia","chingotto","galan","lebron","stupaczuk"]

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
    return nombre.strip().split()[-1] if nombre.strip() else nombre

def es_upset(gan, per):
    return any(t in " ".join(per).lower() for t in TOP3) and \
           not any(t in " ".join(gan).lower() for t in TOP3)

def cargar_json(archivo):
    if os.path.exists(archivo):
        with open(archivo) as f:
            return json.load(f)
    return {}

def guardar_json(archivo, data):
    with open(archivo, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def cargar_publicados():
    return set(cargar_json(ARCHIVO_PUBLICADOS).get("ids", []))

def guardar_publicado(pid):
    d = cargar_json(ARCHIVO_PUBLICADOS)
    ids = set(d.get("ids", []))
    ids.add(pid)
    guardar_json(ARCHIVO_PUBLICADOS, {"ids": list(ids)})

def ya_hecho_hoy(tarea):
    return cargar_json(ARCHIVO_ESTADO).get(tarea) == hora_arg().strftime("%Y-%m-%d")

def marcar_hecho_hoy(tarea):
    estado = cargar_json(ARCHIVO_ESTADO)
    estado[tarea] = hora_arg().strftime("%Y-%m-%d")
    guardar_json(ARCHIVO_ESTADO, estado)

def url_pdf(fecha):
    dia  = DIAS_EN[fecha.weekday()]
    mes  = MESES_EN[fecha.month]
    dd   = fecha.day
    anio = fecha.year
    v2 = f"https://www.padelfip.com/wp-content/uploads/2025/12/ORDER-OF-PLAY-{dia}-{dd}-{mes}-{anio}-2.pdf"
    return v2

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
        print(f"❌ Tweet error: {e}")
        return False

SS_H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def ss_get(path):
    try:
        r = requests.get(f"https://api.sofascore.com/api/v1{path}",
                         headers=SS_H, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[SS] {e}")
    return None

def partidos_finalizados_hoy(ss_id):
    data = ss_get(f"/unique-tournament/{ss_id}/events/last/0")
    if not data:
        return []
    hoy = hora_arg().date()
    return [p for p in data.get("events", [])
            if p.get("status", {}).get("type") == "finished"
            and datetime.fromtimestamp(p.get("startTimestamp", 0),
                                        tz=ARGENTINA_TZ).date() == hoy]

def partidos_proximos_hoy(ss_id):
    data = ss_get(f"/unique-tournament/{ss_id}/events/next/0")
    if not data:
        return []
    hoy = hora_arg().date()
    return [p for p in data.get("events", [])
            if datetime.fromtimestamp(p.get("startTimestamp", 0),
                                       tz=ARGENTINA_TZ).date() == hoy]

def parsear(p):
    home = p.get("homeTeam", {})
    away = p.get("awayTeam", {})
    hs   = p.get("homeScore", {})
    as_  = p.get("awayScore", {})
    j1, j2 = home.get("name", ""), home.get("subTeamName", "") or ""
    j3, j4 = away.get("name", ""), away.get("subTeamName", "") or ""
    sets = []
    for i in range(1, 6):
        sh, sa = hs.get(f"period{i}"), as_.get(f"period{i}")
        if sh is not None and sa is not None:
            sets.append(f"{sh}-{sa}")
    marcador = " / ".join(sets) if sets else "—"
    winner = p.get("winnerCode", 0)
    gan, per = ([j1, j2], [j3, j4]) if winner == 1 else ([j3, j4], [j1, j2])
    tm = p.get("time", {}).get("played")
    return {
        "id": str(p.get("id", "")),
        "ganadores": gan,
        "perdedores": per,
        "marcador": marcador,
        "ronda": p.get("roundInfo", {}).get("name", ""),
        "tiempo": f"{tm//60}h {tm%60}min" if tm else None,
    }

def tweet_premier(torneo, gan, per, marcador, tiempo, ronda):
    arg_gana = any(es_argentino(j) for j in gan)
    upset    = es_upset(gan, per)
    lineas   = []
    if upset:
        lineas.append(random.choice(["¡¡SORPRESÓN!! 😱🎾","¡¡CACHETAZO AL CIRCUITO!! 😱🔥","¡¡NADIE LO ESPERABA!! 😱⚡"]))
    if arg_gana:
        lineas.append(random.choice(["🇦🇷🔥 ¡VICTORIA ARGENTINA!","🇦🇷💪 ¡LOS PIBES LO HICIERON!","🇦🇷⚡ ¡ARRIBA ARGENTINA!"]))
    lineas += [
        f"{torneo['emoji']} {torneo['nombre'].upper()} | {ronda.upper()}",
        f"📍 {torneo['ciudad']} {torneo['bandera']}", "",
        f"✅ {nombre_display(gan[0])} / {nombre_display(gan[1])}",
        f"❌ {nombre_display(per[0])} / {nombre_display(per[1])}",
        f"🎯 {marcador}",
    ]
    if tiempo:
        lineas.append(f"⏱️ {tiempo}")
    lineas += ["", HASHTAGS, LINK_WEB]
    return "\n".join(lineas)[:280]

def tweet_orden_dia(torneo, manana, pdf_url):
    fecha_str = manana.strftime("%d/%m/%Y")
    dia_en    = DIAS_EN[manana.weekday()].capitalize()
    return "\n".join([
        f"🗓️ MAÑANA EN {torneo['nombre'].upper()}",
        f"📅 {dia_en} {fecha_str} | {torneo['ciudad']} {torneo['bandera']}",
        "",
        f"📋 Orden de juego completo:",
        pdf_url,
        "",
        HASHTAGS,
        LINK_WEB,
    ])[:280]

def tarea_orden_dia():
    for torneo in TORNEOS_PREMIER:
        tid = f"orden_dia_{torneo['nombre']}"
        if ya_hecho_hoy(tid):
            continue
        if partidos_proximos_hoy(torneo["ss_id_men"]):
            continue
        manana = (hora_arg() + timedelta(days=1)).date()
        pdf_link = url_pdf(manana)
        tw = tweet_orden_dia(torneo, manana, pdf_link)
        if publicar_tweet(tw):
            marcar_hecho_hoy(tid)
            time.sleep(3)

def monitorear_premier():
    publicados = cargar_publicados()
    for torneo in TORNEOS_PREMIER:
        for ss_id in [torneo["ss_id_men"], torneo["ss_id_women"]]:
            for p in partidos_finalizados_hoy(ss_id):
                d   = parsear(p)
                pid = f"premier_{d['id']}"
                if pid in publicados:
                    continue
                tw = tweet_premier(
                    torneo, d["ganadores"], d["perdedores"],
                    d["marcador"], d["tiempo"], d["ronda"]
                )
                if publicar_tweet(tw):
                    guardar_publicado(pid)
                    time.sleep(5)

def ciclo():
    print(f"\n{'='*50}")
    print(f"🤖 BOT X PADEL ARGENTINA — {hora_arg().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*50}\n")
    contador = 0
    while True:
        print(f"\n🔍 [{hora_arg().strftime('%H:%M:%S')}] Ciclo {contador+1}")
        tarea_orden_dia()
        monitorear_premier()
        print(f"✅ Próximo en {INTERVALO_MINUTOS} min")
        contador += 1
        time.sleep(INTERVALO_MINUTOS * 60)

if __name__ == "__main__":
    ciclo()
