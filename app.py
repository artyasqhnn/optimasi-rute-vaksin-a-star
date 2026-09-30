import heapq
import math

import folium
import requests
import streamlit as st
from branca.element import Element
from streamlit_folium import st_folium

# ---------------------------------------------------------------
# 1. KONFIGURASI
# ---------------------------------------------------------------
st.set_page_config(page_title="Rute Vaksin Sleman", page_icon="💉",
                   layout="wide", initial_sidebar_state="expanded")

WAKTU_LOADING = 30

# Suhu target selama rute darat GFK -> Puskesmas. Semua vaksin (termasuk OPV)
# diangkut di 2-8 C pada etape ini -- suhu beku -15/-25 C untuk OPV cuma
# berlaku di gudang pusat, bukan di pengantaran kabupaten->puskesmas.
SUHU_RUTE = "2°C – 8°C"

# Kelompok sensitivitas vaksin (Kemenkes): Freeze Sensitive rusak instan (0
# menit toleransi) kalau kena beku, jadi ice pack WAJIB cair, bukan beku
# total. Heat Sensitive justru toleran suhu beku (disimpan -15/-25 C di
# tingkat pusat), tapi tetap ikut batas atas 8 C selama di jalan.
VAKSIN_INFO = {
    "Hepatitis B (PID)": {"kategori": "Freeze Sensitive", "catatan": "0 menit toleransi beku — rusak instan kalau sampai beku."},
    "DPT-HB-Hib": {"kategori": "Freeze Sensitive", "catatan": "0 menit toleransi beku — rusak instan kalau sampai beku."},
    "IPV (Polio Suntik)": {"kategori": "Freeze Sensitive", "catatan": "0 menit toleransi beku — rusak instan kalau sampai beku."},
    "DT": {"kategori": "Freeze Sensitive", "catatan": "0 menit toleransi beku — rusak instan kalau sampai beku."},
    "Td": {"kategori": "Freeze Sensitive", "catatan": "0 menit toleransi beku — rusak instan kalau sampai beku."},
    "BCG": {"kategori": "Heat Sensitive", "catatan": "Toleran suhu beku (disimpan -15°C s.d. -25°C di tingkat pusat)."},
    "Campak / MR": {"kategori": "Heat Sensitive", "catatan": "Toleran suhu beku (disimpan -15°C s.d. -25°C di tingkat pusat)."},
    "OPV (Polio Tetes)": {"kategori": "Heat Sensitive", "catatan": "Toleran suhu beku (disimpan -15°C s.d. -25°C di tingkat pusat)."},
}

# Batas waktu total perjalanan (T_maks) berdasarkan ketahanan wadah angkut
# (Kemenkes) -- ini yang jadi hard constraint buat A*: kalau T_route > T_maks,
# rute dianggap infeasible / cold chain breached. Dipakai angka batas bawah
# yang konservatif dari tiap rentang standar.
WADAH_ANGKUT = {
    "Vaccine Carrier (rutin)": {"batas_menit": 12 * 60, "rentang": "12–24 jam"},
    "Cold Box (skala besar)": {"batas_menit": 48 * 60, "rentang": "48–72 jam"},
}

# Kondisi cuaca ngaliin faktor pengali ke waktu tempuh tiap ruas (medan
# menanjak/lereng Merapi & hujan bikin kendaraan distribusi lebih lambat).
WEATHER_FACTOR = {"Cerah": 1.0, "Hujan (+20%)": 1.2}
WEATHER_ICON = {"Cerah": "sun", "Hujan (+20%)": "cloud-rain"}

# ---------------------------------------------------------------
# 1b. IKON (SVG garis minimalis, pengganti emoji)
# ---------------------------------------------------------------
ICONS = {
    "syringe": '<path d="m18 2 4 4"/><path d="m17 7 3-3"/>'
               '<path d="M19 9 8.7 19.3a2.4 2.4 0 0 1-3.4 0l-.6-.6a2.4 2.4 0 0 1 0-3.4L15 5"/>'
               '<path d="m9 11 4 4"/><path d="m5 19-3 3"/><path d="m14 4 6 6"/>',
    "hospital": '<path d="M12 6v4"/><path d="M10 8h4"/>'
                '<path d="M18 22V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v18"/>'
                '<path d="M18 12h2a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2h2"/>'
                '<path d="M10 15h4"/><path d="M10 18h4"/>',
    "home": '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/>'
            '<path d="M3 10a2 2 0 0 1 .7-1.6l7-5.8a2 2 0 0 1 2.6 0l7 5.8A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "map-pin": '<path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "check": '<path d="M21.7 10A10 10 0 1 1 17 3.3"/><path d="m9 11 3 3L22 4"/>',
    "alert": '<path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z"/>'
             '<path d="M12 9v4"/><path d="M12 17h.01"/>',
    "truck": '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9"/>'
             '<path d="M19 18h2a1 1 0 0 0 1-1v-3.6a1 1 0 0 0-.2-.6l-3.5-4.4a1 1 0 0 0-.8-.4H14"/>'
             '<circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>',
    "package": '<path d="M11 21.7a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7Z"/>'
               '<path d="M12 22V12"/><path d="M3.3 7 12 12l8.7-5"/><path d="m7.5 4.3 9 5.2"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "snowflake": '<path d="M12 2v20"/><path d="m4.9 4.9 14.2 14.2"/><path d="m19.1 4.9-14.2 14.2"/>',
    "flag": '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1Z"/><path d="M4 22v-7"/>',
    "route": '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
    "thermometer": '<path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/><path d="M9 8h4"/><path d="M9 11h4"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/>'
           '<path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/>'
           '<path d="M2 12h2"/><path d="M20 12h2"/>'
           '<path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
    "cloud-rain": '<path d="M4 14.9A5 5 0 0 1 8 6a5.5 5.5 0 0 1 10.4 2.1A4.5 4.5 0 0 1 17.5 17H6"/>'
                  '<path d="M8 19v2"/><path d="M12 19v2"/><path d="M16 19v2"/>',
}


def icon(name, size=18, color="currentColor", stroke=2):
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-linejoin="round" style="display:inline-block;vertical-align:middle">'
        f'{ICONS[name]}</svg>'
    )

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');

:root {
    --blue: #2f6bff;
    --blue-dark: #1f4fd1;
    --navy: #0f2350;
    --sky: #e6f0ff;
    --bg: #f3f7ff;
    --card: #ffffff;
    --line: #dde8fb;
    --muted: #6b7fa3;
    --ok: #12a05c;   --ok-bg: #dff7ea;
    --bad: #e5484d;  --bad-bg: #ffe5e6;
}
html, body, [class*="css"], .stApp { font-family: 'Nunito', sans-serif; color: var(--navy); }
.stApp { background: var(--bg); }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1320px; }

/* Sidebar */
section[data-testid="stSidebar"] { background: var(--card); border-right: 1px solid var(--line); }
.brand { display: flex; align-items: center; gap: 12px; }
.brand-mark {
    width: 46px; height: 46px; border-radius: 16px; background: var(--blue);
    display: grid; place-items: center; font-size: 24px;
    box-shadow: 0 6px 14px rgba(47,107,255,.35);
}
.brand-name { font-weight: 900; font-size: 1.15rem; line-height: 1.1; }
.brand-sub { font-size: .8rem; color: var(--muted); font-weight: 600; }
.side-label { font-weight: 800; font-size: .88rem; margin: 22px 0 8px; }
.origin {
    background: var(--sky); border-radius: 14px; padding: 12px 14px;
    font-weight: 800; color: var(--blue-dark);
}
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
    background: var(--sky); color: var(--blue-dark); font-weight: 700;
    font-size: .82rem; padding: 7px 12px; border-radius: 999px;
}

/* Tombol */
.stButton > button {
    width: 100%; height: 50px; border: none; border-radius: 16px;
    background: var(--blue); color: #fff; font-family: inherit;
    font-weight: 800; font-size: 1rem;
    box-shadow: 0 8px 18px rgba(47,107,255,.35);
    transition: transform .12s ease, background .2s ease;
}
.stButton > button:hover { background: var(--blue-dark); color: #fff; transform: translateY(-1px); }
.stButton > button:active { transform: scale(.98); }
.stButton > button:focus-visible { outline: 3px solid #9dbbff; outline-offset: 2px; }

/* Hero */
.hero {
    position: relative; overflow: hidden;
    background: var(--blue); color: #fff; border-radius: 28px;
    padding: 30px 36px; margin-bottom: 24px;
}
.hero h1 { color: #fff !important; font-weight: 900; font-size: 2.1rem; margin: 0 0 6px; padding: 0; letter-spacing: -0.01em; }
.hero p { color: #dbe7ff; margin: 0; font-size: 1.02rem; font-weight: 600; max-width: 52ch; }
.hero .deco { position: absolute; right: 30px; top: 50%; transform: translateY(-50%); display: flex; align-items: center; gap: 14px; }
.hero .bubble { position: absolute; border-radius: 50%; background: rgba(255,255,255,.10); }
.b1 { width: 160px; height: 160px; right: 180px; top: -60px; }
.b2 { width: 90px; height: 90px; right: 60px; bottom: -35px; }

/* Kartu */
.card {
    background: var(--card); border: 1px solid var(--line);
    border-radius: 24px; padding: 20px 22px; margin-bottom: 16px;
}
.card-title { font-weight: 900; font-size: 1.02rem; margin: 0 0 14px; }

/* Status */
.status { display: flex; gap: 14px; align-items: center; border-radius: 24px; padding: 18px 20px; margin-bottom: 16px; }
.status.ok { background: var(--ok-bg); color: #0b6b3c; }
.status.bad { background: var(--bad-bg); color: #a3262b; }
.status-emoji { font-size: 2.3rem; line-height: 1; }
.status-title { font-weight: 900; font-size: 1.1rem; }
.status-text { font-size: .9rem; font-weight: 600; opacity: .9; }

/* Stat */
.stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.stat { background: var(--card); border: 1px solid var(--line); border-radius: 20px; padding: 14px 16px; }
.stat-top { font-size: .78rem; color: var(--muted); font-weight: 700; }
.stat-val { font-size: 1.8rem; font-weight: 900; line-height: 1.15; }
.stat-val small { font-size: .8rem; color: var(--muted); font-weight: 700; margin-left: 3px; }
.stat.hl { background: var(--blue); border-color: var(--blue); }
.stat.hl .stat-top, .stat.hl .stat-val, .stat.hl small { color: #fff; }
.stat.hl small { opacity: .8; }

/* Gauge */
.gauge { position: relative; margin: 34px 0 8px; }
.g-track { display: flex; height: 26px; border-radius: 13px; background: var(--sky); overflow: hidden; }
.g-load { background: #a9c6ff; }
.g-travel { background: var(--blue); }
.g-travel.over { background: var(--bad); }
.g-limit { position: absolute; top: -6px; bottom: -6px; width: 3px; background: var(--navy); border-radius: 2px; }
.g-flag {
    position: absolute; top: -34px; transform: translateX(-50%);
    background: var(--navy); color: #fff; font-size: .72rem; font-weight: 800;
    padding: 3px 10px; border-radius: 999px; white-space: nowrap;
}
.legend { display: flex; gap: 16px; font-size: .8rem; color: var(--muted); font-weight: 700; margin-top: 12px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }

/* Timeline */
.tl { list-style: none; margin: 0; padding: 0; }
.tl li { position: relative; padding: 0 0 20px 54px; min-height: 40px; }
.tl li:last-child { padding-bottom: 0; }
.tl li::before { content: ""; position: absolute; left: 19px; top: 40px; bottom: 0; width: 3px; background: var(--line); border-radius: 2px; }
.tl li:last-child::before { display: none; }
.tl-ico {
    position: absolute; left: 0; top: 0; width: 40px; height: 40px; border-radius: 14px;
    display: grid; place-items: center; font-size: 1.2rem; background: var(--c);
}
.tl-name {
    font-weight: 800; display: flex; align-items: center; flex-wrap: wrap; gap: 4px 8px;
}
.tl-meta { font-size: .82rem; color: var(--muted); font-weight: 600; }
.tl-leg {
    background: var(--sky); color: var(--blue-dark); font-size: .75rem; font-weight: 800;
    padding: 2px 10px; border-radius: 999px; white-space: nowrap; flex-shrink: 0;
}

/* Kosong */
.empty { background: var(--card); border: 2px dashed #bcd0fa; border-radius: 24px; padding: 22px 24px; margin-bottom: 16px; display: flex; gap: 16px; align-items: center; }
.empty .em { font-size: 2.4rem; }
.empty b { display: block; font-size: 1.05rem; }
.empty span { color: var(--muted); font-weight: 600; font-size: .92rem; }

.chip svg, .stat-top svg, .g-flag svg, .tl-name svg { margin-right: 5px; position: relative; top: -1px; }
.map-legend { display: flex; gap: 18px; font-size: .8rem; color: var(--muted); font-weight: 700; margin-top: 10px; }
.map-legend i { display: inline-block; width: 18px; height: 5px; border-radius: 3px; margin-right: 6px; vertical-align: middle; }
.gmaps-btn {
    display: flex; align-items: center; justify-content: center; gap: 8px;
    width: 100%; height: 46px; border-radius: 16px; margin-top: 12px;
    background: #fff; border: 2px solid var(--blue); color: var(--blue-dark);
    font-family: inherit; font-weight: 800; font-size: .92rem; text-decoration: none;
    transition: background .15s ease, color .15s ease;
}
.gmaps-btn:hover { background: var(--blue); color: #fff; }

/* Radio (mis. Kondisi perjalanan) -- pastikan teks selalu gelap di atas kartu putih */
div[data-testid="stRadio"] label,
div[data-testid="stRadio"] label p,
div[data-testid="stRadio"] label span,
div[data-testid="stRadio"] div { color: var(--navy) !important; }
iframe { border-radius: 26px; }

@media (max-width: 800px) {
    .stat-grid { grid-template-columns: 1fr; }
    .hero { padding: 24px; }
    .hero h1 { font-size: 1.5rem; }
    .hero .deco, .hero .bubble { display: none; }
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------
# 2. DATA
# ---------------------------------------------------------------
COORDINATES = {
    "Depot_Dinkes": (-7.7186048, 110.3565364),
    "PKM_Mlati1": (-7.7544835, 110.3630202),
    "PKM_DepokI": (-7.7749757, 110.4313852),
    "PKM_Gamping1": (-7.8007199, 110.3202600),
    "PKM_Kalasan": (-7.7584674, 110.4495131),
    "PKM_Prambanan": (-7.7801516, 110.4824135),
    "PKM_Turi": (-7.6539719, 110.3797434),
    "PKM_Cangkringan": (-7.6648524, 110.4564840),
}

LABELS = {
    "Depot_Dinkes": "Depo Dinkes Sleman",
    "PKM_Mlati1": "Puskesmas Mlati I",
    "PKM_DepokI": "Puskesmas Depok I",
    "PKM_Gamping1": "Puskesmas Gamping I",
    "PKM_Kalasan": "Puskesmas Kalasan",
    "PKM_Prambanan": "Puskesmas Prambanan",
    "PKM_Turi": "Puskesmas Turi",
    "PKM_Cangkringan": "Puskesmas Cangkringan",
}

GRAPH = {
    "Depot_Dinkes": {"PKM_Mlati1": 9, "PKM_Turi": 18, "PKM_Gamping1": 21, "PKM_DepokI": 22},
    "PKM_Mlati1": {"Depot_Dinkes": 9, "PKM_DepokI": 18, "PKM_Gamping1": 16},
    "PKM_Gamping1": {"Depot_Dinkes": 21, "PKM_Mlati1": 16},
    "PKM_DepokI": {"Depot_Dinkes": 22, "PKM_Mlati1": 18, "PKM_Kalasan": 10},
    "PKM_Kalasan": {"PKM_DepokI": 10, "PKM_Prambanan": 10, "PKM_Cangkringan": 24},
    "PKM_Prambanan": {"PKM_Kalasan": 10, "PKM_Cangkringan": 30},
    "PKM_Turi": {"Depot_Dinkes": 18, "PKM_Cangkringan": 20},
    "PKM_Cangkringan": {"PKM_Turi": 20, "PKM_Kalasan": 24, "PKM_Prambanan": 30},
}


# ---------------------------------------------------------------
# 3. A* SEARCH
# ---------------------------------------------------------------
def haversine(c1, c2):
    r = 6371.0
    lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
    lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def heuristic(node, goal, faktor_cuaca=1.0):
    return (haversine(COORDINATES[node], COORDINATES[goal]) / 40.0) * 60.0 * faktor_cuaca


def a_star_search(start, goal, faktor_cuaca=1.0):
    open_set = [(heuristic(start, goal, faktor_cuaca), start)]
    came_from = {}
    g_score = {node: float("inf") for node in GRAPH}
    g_score[start] = 0
    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            return path[::-1], g_score[goal]
        for neighbor, weight in GRAPH.get(current, {}).items():
            tentative_g = g_score[current] + weight * faktor_cuaca
            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                heapq.heappush(open_set, (tentative_g + heuristic(neighbor, goal, faktor_cuaca), neighbor))
    return None, float("inf")


# ---------------------------------------------------------------
# 4. KOMPONEN UI
# ---------------------------------------------------------------
def render_hero():
    st.markdown(
        f"""
<div class="hero">
    <div class="bubble b1"></div><div class="bubble b2"></div>
    <h1>Antar vaksin, tetap dingin {icon("snowflake", 28, "#dbe7ff")}</h1>
    <p>Cari rute tercepat dari Depo Dinkes ke puskesmas tujuan, dan pastikan vaksin
    sampai sebelum batas cold chain.</p>
    <div class="deco">{icon("truck", 60, "rgba(255,255,255,.55)", 1.6)}{icon("syringe", 44, "rgba(255,255,255,.55)", 1.6)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_status(total, batas):
    batas_jam = batas / 60
    selisih_jam = abs(batas - total) / 60
    if total <= batas:
        cls, title = "ok", "Aman, cold chain terjaga"
        emoji = icon("check", 30, "#12a05c")
        text = f"Total {total:g} menit. Masih {selisih_jam:g} jam di bawah batas wadah angkut ({batas_jam:g} jam)."
    else:
        cls, title = "bad", "Infeasible — cold chain breached"
        emoji = icon("alert", 30, "#e5484d")
        text = f"Total {total:g} menit. Lewat {selisih_jam:g} jam dari batas wadah angkut ({batas_jam:g} jam)."
    st.markdown(
        f'<div class="status {cls}"><div class="status-emoji">{emoji}</div>'
        f'<div><div class="status-title">{title}</div><div class="status-text">{text}</div></div></div>',
        unsafe_allow_html=True,
    )


def render_stats(travel, total):
    ic_muted = "#6b7fa3"
    st.markdown(
        f"""
<div class="stat-grid">
    <div class="stat"><div class="stat-top">{icon("truck", 14, ic_muted)} Perjalanan</div>
        <div class="stat-val">{travel:g}<small>menit</small></div></div>
    <div class="stat"><div class="stat-top">{icon("package", 14, ic_muted)} Loading</div>
        <div class="stat-val">{WAKTU_LOADING}<small>menit</small></div></div>
    <div class="stat hl"><div class="stat-top">{icon("clock", 14, "#fff")} Total</div>
        <div class="stat-val">{total:g}<small>menit</small></div></div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_gauge(travel, total, batas):
    skala = max(total, batas) * 1.12
    p_load = WAKTU_LOADING / skala * 100
    p_travel = travel / skala * 100
    p_limit = batas / skala * 100
    over = "over" if total > batas else ""
    dot = "#e5484d" if over else "#2f6bff"
    batas_label = f"{batas / 60:g} jam" if batas >= 60 else f"{batas} mnt"
    st.markdown(
        f"""
<div class="card">
    <div class="card-title">Waktu terpakai vs batas</div>
    <div class="gauge">
        <div class="g-flag" style="left:{p_limit}%">{icon("snowflake", 12, "#fff")} Batas {batas_label}</div>
        <div class="g-track">
            <div class="g-load" style="width:{p_load}%"></div>
            <div class="g-travel {over}" style="width:{p_travel}%"></div>
        </div>
        <div class="g-limit" style="left:{p_limit}%"></div>
    </div>
    <div class="legend">
        <span><i style="background:#a9c6ff"></i>Loading</span>
        <span><i style="background:{dot}"></i>Perjalanan</span>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_timeline(path, faktor_cuaca=1.0):
    items = []
    for i, node in enumerate(path):
        if i == 0:
            role, color, emoji, leg = "Berangkat dari sini", "#dbe7ff", icon("hospital", 18, "#1f4fd1"), ""
        else:
            menit_ruas = GRAPH[path[i - 1]][node] * faktor_cuaca
            leg = f'<span class="tl-leg">+{menit_ruas:g} mnt</span>'
            if i == len(path) - 1:
                role, color, emoji = "Tujuan akhir", "#ffdada", icon("flag", 18, "#e5484d")
            else:
                role, color, emoji = "Singgah dulu", "#e3f6ea", icon("map-pin", 18, "#12a05c")
        items.append(
            f'<li><div class="tl-ico" style="--c:{color}">{emoji}</div>'
            f'<div class="tl-name"><span>{LABELS[node]}</span>{leg}</div>'
            f'<div class="tl-meta">{role}</div></li>'
        )
    st.markdown(
        f'<div class="card"><div class="card-title">Jalur yang dilalui</div>'
        f'<ul class="tl">{"".join(items)}</ul></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------
# 5. PETA GAYA APPLE MAPS
# ---------------------------------------------------------------
MAP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&display=swap');
.leaflet-container { font-family: 'Nunito', sans-serif; }
.leaflet-top.leaflet-left { top: auto; bottom: 22px; left: auto; right: 14px; }
.leaflet-bar { border: none !important; border-radius: 14px; overflow: hidden; box-shadow: 0 4px 16px rgba(15,35,80,.25); }
.leaflet-bar a { width: 38px; height: 38px; line-height: 38px; color: #0f2350; font-weight: 800; }
.pin { display:grid; place-items:center; border-radius:50%; border:3px solid #fff;
       box-shadow: 0 3px 10px rgba(15,35,80,.35); font-size:14px; }
.tag { position:absolute; left:50%; top:100%; transform:translate(-50%,6px); white-space:nowrap;
       background:#fff; color:#0f2350; font:800 12px 'Nunito',sans-serif;
       padding:4px 10px; border-radius:999px; box-shadow:0 2px 8px rgba(15,35,80,.25); }
.leg { background:#fff; color:#1f4fd1; font:900 12px 'Nunito',sans-serif; padding:3px 9px;
       border-radius:999px; box-shadow:0 2px 8px rgba(15,35,80,.3); white-space:nowrap; width:max-content; }
.route-card { position:absolute; z-index:9999; top:16px; left:16px; max-width:280px;
       background:rgba(255,255,255,.94); backdrop-filter: blur(10px);
       border-radius:18px; padding:12px 16px; box-shadow:0 6px 24px rgba(15,35,80,.25);
       font-family:'Nunito',sans-serif; color:#0f2350; }
.route-card .t { font-weight:900; font-size:15px; }
.route-card .s { font-weight:700; font-size:12px; color:#6b7fa3; margin-top:2px; }
.route-card .big { font-weight:900; font-size:22px; color:#2f6bff; }
</style>
"""


OSRM_URL = "https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def get_road_routes(coord_a, coord_b):
    """Ambil geometri jalan asli antara 2 titik dari OSRM (router publik), sekalian
    rute alternatifnya (kalau ada, misal ada jalan pintas lain). Rute pertama yang
    dibalik = yang paling cepat. Balik list kosong kalau gagal/timeout/offline
    -> caller pakai garis lurus."""
    lat1, lon1 = coord_a
    lat2, lon2 = coord_b
    url = OSRM_URL.format(lon1=lon1, lat1=lat1, lon2=lon2, lat2=lat2)
    try:
        r = requests.get(
            url,
            params={"overview": "full", "geometries": "geojson", "alternatives": "true"},
            timeout=6,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return []
        routes = sorted(data["routes"], key=lambda rt: rt["duration"])
        return [[(lat, lon) for lon, lat in rt["geometry"]["coordinates"]] for rt in routes]
    except Exception:
        return []


def pin(color, icon_html, size, label=None):
    tag = f'<div class="tag">{label}</div>' if label else ""
    html = (f'<div style="position:relative;width:{size}px;height:{size}px">'
            f'<div class="pin" style="width:{size}px;height:{size}px;background:{color}">{icon_html}</div>{tag}</div>')
    return folium.DivIcon(html=html, icon_size=(size, size), icon_anchor=(size // 2, size // 2))


def gmaps_url(path):
    """Bikin link Google Maps Directions dari titik-titik path yang sama
    persis dipakai di peta kita (asal, singgah sbg waypoint, tujuan akhir)."""
    coords = [COORDINATES[n] for n in path]
    origin = f"{coords[0][0]},{coords[0][1]}"
    destination = f"{coords[-1][0]},{coords[-1][1]}"
    url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode=driving"
    if len(coords) > 2:
        waypoints = "|".join(f"{lat},{lon}" for lat, lon in coords[1:-1])
        url += f"&waypoints={waypoints}"
    return url


def build_route_line(path):
    """Sambung geometri jalan tiap ruas jadi satu rute utuh, simpan titik tengah
    tiap ruas (buat naruh label '+x mnt'), dan kumpulin rute alternatif
    (jalan lain yang lebih lambat) buat digambar samar di belakang rute utama."""
    full_route, leg_mid, alt_lines = [], {}, []
    for a, b in zip(path, path[1:]):
        routes = get_road_routes(COORDINATES[a], COORDINATES[b])
        if routes:
            seg = routes[0]
            alt_lines.extend(routes[1:3])  # maks 2 alternatif per ruas, biar peta ga penuh
        else:
            seg = [COORDINATES[a], COORDINATES[b]]  # fallback garis lurus
        if full_route and seg[0] == full_route[-1]:
            seg = seg[1:]
        leg_mid[(a, b)] = seg[len(seg) // 2]
        full_route.extend(seg)
    return full_route, leg_mid, alt_lines


def build_map(path=None, total=None, faktor_cuaca=1.0):
    route_line, leg_mid, alt_lines = (None, None, [])
    if path:
        route_line, leg_mid, alt_lines = build_route_line(path)
        lats = [p[0] for p in route_line]
        lons = [p[1] for p in route_line]
        center = [(min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2]
        span = max(max(lons) - min(lons), (max(lats) - min(lats)) * 1.3, 0.02)
        zoom = max(9, min(14, int(math.log2(430 / span))))
    else:
        center, zoom = [-7.74, 110.41], 11

    m = folium.Map(location=center, zoom_start=zoom, tiles=None, zoom_control=True)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri", max_zoom=19, name="Peta",
    ).add_to(m)
    m.get_root().html.add_child(Element(MAP_CSS))

    if path:
        # jalan alternatif (lebih lambat) digambar dulu di bawah, warna lebih muda/samar
        for alt in alt_lines:
            folium.PolyLine(alt, color="#aebedb", weight=5, opacity=0.65, line_cap="round", line_join="round").add_to(m)
        # garis rute ala Apple Maps: outline gelap + garis biru terang, ngikutin jalan asli
        folium.PolyLine(route_line, color="#1d4ed8", weight=11, opacity=1, line_cap="round", line_join="round").add_to(m)
        folium.PolyLine(route_line, color="#4c8dff", weight=7, opacity=1, line_cap="round", line_join="round").add_to(m)
        # gelembung waktu tiap ruas, ditaruh di tengah jalan (bukan tengah garis lurus)
        for a, b in zip(path, path[1:]):
            menit_ruas = GRAPH[a][b] * faktor_cuaca
            folium.Marker(
                list(leg_mid[(a, b)]),
                icon=folium.DivIcon(html=f'<div class="leg">{menit_ruas:g} mnt</div>', icon_size=(0, 0), icon_anchor=(24, 10)),
            ).add_to(m)

    for name, (lat, lon) in COORDINATES.items():
        if name == "Depot_Dinkes":
            marker_icon, z = pin("#2f6bff", icon("hospital", 18, "#fff"), 34, "Depo Dinkes"), 1000
        elif path and name == path[-1]:
            marker_icon, z = pin("#ff453a", icon("syringe", 18, "#fff"), 34, LABELS[name]), 900
        elif path and name in path:
            marker_icon, z = pin("#ffffff", icon("map-pin", 14, "#2f6bff"), 26, LABELS[name]), 800
        else:
            size = 26 if not path else 22
            marker_icon, z = pin("#ffffff", icon("home", 13, "#8497bd"), size), 0
        folium.Marker([lat, lon], icon=marker_icon, tooltip=LABELS[name], z_index_offset=z).add_to(m)

    if path:
        card = (f'<div class="route-card"><div class="s">Estimasi total</div>'
                f'<div class="big">{total:g} menit</div>'
                f'<div class="t">{LABELS[path[0]]} → {LABELS[path[-1]]}</div>'
                f'<div class="s">{len(path) - 1} ruas · termasuk loading {WAKTU_LOADING} mnt</div></div>')
        m.get_root().html.add_child(Element(card))
    return m


# ---------------------------------------------------------------
# 6. SIDEBAR
# ---------------------------------------------------------------
start_node = "Depot_Dinkes"

with st.sidebar:
    st.markdown(
        f'<div class="brand"><div class="brand-mark">{icon("syringe", 22, "#fff")}</div><div>'
        '<div class="brand-name">Rute Vaksin</div>'
        '<div class="brand-sub">Dinkes Kab. Sleman</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-label">Berangkat dari</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="origin">{icon("hospital", 16, "#1f4fd1")} {LABELS[start_node]}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="side-label">Mau dikirim ke mana?</div>', unsafe_allow_html=True)
    targets = [n for n in COORDINATES if n != start_node]
    goal_node = st.selectbox("Puskesmas tujuan", targets, format_func=lambda n: LABELS[n],
                             label_visibility="collapsed")

    st.markdown('<div class="side-label">Jenis vaksin</div>', unsafe_allow_html=True)
    vaksin = st.selectbox("Jenis vaksin", list(VAKSIN_INFO), label_visibility="collapsed")
    kategori = VAKSIN_INFO[vaksin]["kategori"]
    catatan_vaksin = VAKSIN_INFO[vaksin]["catatan"]

    st.markdown('<div class="side-label">Wadah angkut</div>', unsafe_allow_html=True)
    wadah = st.selectbox("Wadah angkut", list(WADAH_ANGKUT), label_visibility="collapsed")
    batas_menit = WADAH_ANGKUT[wadah]["batas_menit"]
    batas_jam = batas_menit / 60

    st.markdown('<div class="side-label">Kondisi perjalanan</div>', unsafe_allow_html=True)
    cuaca = st.radio("Kondisi perjalanan", list(WEATHER_FACTOR), horizontal=True, label_visibility="collapsed")
    faktor_cuaca = WEATHER_FACTOR[cuaca]

    st.markdown('<div class="side-label">Aturan cold chain</div>', unsafe_allow_html=True)
    kategori_icon = "alert" if kategori == "Freeze Sensitive" else "snowflake"
    st.markdown(
        f'<div class="chips">'
        f'<span class="chip">{icon("syringe", 13, "#1f4fd1")} {vaksin}</span>'
        f'<span class="chip">{icon("thermometer", 13, "#1f4fd1")} {SUHU_RUTE}</span>'
        f'<span class="chip">{icon(kategori_icon, 13, "#1f4fd1")} {kategori}</span>'
        f'<span class="chip">{icon("truck", 13, "#1f4fd1")} Maks {batas_jam:g} jam ({wadah.split(" (")[0]})</span>'
        f'<span class="chip">{icon(WEATHER_ICON[cuaca], 13, "#1f4fd1")} {cuaca}</span>'
        f'<span class="chip">{icon("package", 13, "#1f4fd1")} Loading {WAKTU_LOADING} menit</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.caption(catatan_vaksin)
    st.write("")
    st.write("")
    btn_cari = st.button("Cari rute terbaik  →")


# ---------------------------------------------------------------
# 7. AREA UTAMA
# ---------------------------------------------------------------
render_hero()

if btn_cari:
    path, time_cost = a_star_search(start_node, goal_node, faktor_cuaca)
    total_waktu = time_cost + WAKTU_LOADING

    col_left, col_right = st.columns([1, 1.35], gap="large")
    with col_left:
        render_status(total_waktu, batas_menit)
        render_stats(time_cost, total_waktu)
        render_gauge(time_cost, total_waktu, batas_menit)
        render_timeline(path, faktor_cuaca)
    with col_right:
        st_folium(build_map(path, total_waktu, faktor_cuaca), use_container_width=True, height=680, returned_objects=[])
        st.markdown(
            '<div class="map-legend">'
            '<span><i style="background:#4c8dff"></i>Rute tercepat</span>'
            '<span><i style="background:#aebedb"></i>Jalan alternatif</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<a class="gmaps-btn" href="{gmaps_url(path)}" target="_blank" rel="noopener">'
            f'{icon("route", 16, "currentColor")} Buka rute ini di Google Maps</a>',
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        f'<div class="empty"><div class="em">{icon("route", 38, "#8fa8dd", 1.6)}</div><div><b>Belum ada rute nih</b>'
        '<span>Pilih puskesmas tujuan di menu kiri, lalu klik Cari rute terbaik.</span></div></div>',
        unsafe_allow_html=True,
    )
    st_folium(build_map(), use_container_width=True, height=560, returned_objects=[])
