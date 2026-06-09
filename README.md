# 🎾 Bot Padel Argentina — @padelargentinaok

Bot que monitorea y publica resultados automáticos en X.

---

## 📋 LÓGICA EDITORIAL

### PREMIER PADEL — Todos los partidos
Publica TODOS los resultados apenas terminan.
Si gana un argentino → encabeza con 🇦🇷 VICTORIA ARGENTINA
Si es un upset (equipo bajo ranking vence a Top 3) → encabeza con ¡SORPRESÓN!

Formato:
─────────────────────────────
🇦🇷 ¡VICTORIA ARGENTINA! 🔥

🏟️ PREMIER PADEL P1 VALENCIA | 2DA RONDA
📍 Valencia, España

✅ 🇦🇷 Agustín Tapia / Arturo Coello
❌ Javier García / Jose Jiménez
🎯 6-4 / 7-6 / 6-3
⏱️ 1h 42min

➡️ Avanzan a Cuartos de Final
🆚 Próximos rivales: Yanguas / Stupaczuk

#Padel #PremierPadel #FIP #PadelArgentino
Enterate de todo en: www.padelargentina.com.ar
─────────────────────────────

### FIP TORNEOS — Solo argentinos
Publica cuando gana O pierde un argentino.

Formato victoria:
─────────────────────────────
🇦🇷 ¡LOS PIBES LO HICIERON! 💪

🎾 FIP BRONZE ESLOVENIA | 2DA RONDA
📍 Ljubljana, Eslovenia

✅ 🇦🇷 Valentino Libaak / 🇦🇷 Alex Chozas
❌ Kovac / Novak
🎯 6-3 / 6-4

➡️ Avanzan a Cuartos de Final

#Padel #PremierPadel #FIP #PadelArgentino
Enterate de todo en: www.padelargentina.com.ar
─────────────────────────────

Formato derrota:
─────────────────────────────
Se terminó el sueño. 😔🇦🇷

🎾 FIP BRONZE ESLOVENIA | CUARTOS DE FINAL
📍 Ljubljana, Eslovenia

✅ Kovac / Novak
❌ 🇦🇷 Valentino Libaak / 🇦🇷 Alex Chozas
🎯 6-4 / 6-2

#Padel #PremierPadel #FIP #PadelArgentino
Enterate de todo en: www.padelargentina.com.ar
─────────────────────────────

### CAMPEONES — Premier Padel y FIP
─────────────────────────────
👑🇦🇷 ¡¡CAMPEONES ARGENTINOS!! ¡¡LOS PIBES SE LLEVARON EL TÍTULO!!

🏆 PREMIER PADEL P1 VALENCIA — FINAL
📍 Valencia, España

🥇 🇦🇷 Agustín Tapia / Arturo Coello
🥈 🇦🇷 Federico Chingotto / Alejandro Galán
🎯 6-4 / 3-6 / 6-3

#Padel #PremierPadel #FIP #PadelArgentino
Enterate de todo en: www.padelargentina.com.ar
─────────────────────────────

---

## 🚀 CÓMO DEPLOYAR EN RAILWAY

### Paso 1 — GitHub
1. Ir a https://github.com → crear cuenta gratuita
2. New repository → nombre: padelargentina-bot → Private
3. Subir los archivos: bot.py / requirements.txt / railway.toml

### Paso 2 — Railway
1. Ir a https://railway.app → Sign in with GitHub
2. New Project → Deploy from GitHub repo → padelargentina-bot
3. Antes de deployar, ir a Settings → Variables → agregar:

   API_KEY             = (tu clave)
   API_SECRET          = (tu clave)
   ACCESS_TOKEN        = (tu clave)
   ACCESS_TOKEN_SECRET = (tu clave)

4. Deploy → el bot corre 24/7 sin tener la PC encendida ✅

---

## 🔄 ACTUALIZAR TORNEOS ACTIVOS

Cada semana nueva, editar bot.py sección TORNEOS_PREMIER y TORNEOS_FIP
con las URLs de los torneos que están en juego.

Ejemplo:
TORNEOS_FIP = [
    {
        "nombre": "FIP Gold Portugal",
        "url":    "https://www.padelfip.com/es/events/fip-gold-portugal-2026/",
        "emoji":  "🎾",
        "ciudad": "Lisboa, Portugal",
    },
]

---

## ⏱️ FRECUENCIA DE CHEQUEO
- Premier Padel: cada 2 minutos
- FIP: cada 5 minutos
