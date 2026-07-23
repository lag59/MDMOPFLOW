from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st


st.set_page_config(
    page_title="MDM OpsFlow Studio",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
<style>
    :root {
        --bg: #f3efe7;
        --panel: rgba(255, 255, 255, 0.82);
        --panel-strong: rgba(255, 255, 255, 0.95);
        --text: #1d221f;
        --muted: #5a635e;
        --accent: #0f766e;
        --accent-2: #c2410c;
        --border: rgba(29, 34, 31, 0.10);
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(15, 118, 110, 0.14), transparent 32%),
            radial-gradient(circle at top right, rgba(194, 65, 12, 0.12), transparent 28%),
            linear-gradient(180deg, #fcfaf6 0%, #f3efe7 52%, #ece7dd 100%);
        color: var(--text);
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        border: 1px solid var(--border);
        border-radius: 28px;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(244, 242, 236, 0.72));
        box-shadow: 0 20px 55px rgba(0, 0, 0, 0.07);
        padding: 2rem 2.2rem;
        margin-bottom: 1.2rem;
    }

    .eyebrow {
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-size: 0.76rem;
        color: var(--accent);
        font-weight: 700;
        margin-bottom: 0.7rem;
    }

    .hero h1 {
        font-size: clamp(2.4rem, 5vw, 4.8rem);
        line-height: 0.95;
        letter-spacing: -0.05em;
        margin: 0;
        color: var(--text);
    }

    .hero p {
        max-width: 58rem;
        font-size: 1.05rem;
        line-height: 1.65;
        color: var(--muted);
        margin-top: 1rem;
    }

    .panel {
        border: 1px solid var(--border);
        border-radius: 22px;
        background: var(--panel);
        backdrop-filter: blur(18px);
        padding: 1.15rem 1.2rem;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.04);
    }

    .panel strong {
        display: block;
        font-size: 1rem;
        margin-bottom: 0.35rem;
        color: var(--text);
    }

    .panel p {
        margin: 0;
        color: var(--muted);
        line-height: 1.55;
    }

    .card {
        border: 1px solid var(--border);
        border-radius: 22px;
        background: var(--panel-strong);
        padding: 1.2rem 1.2rem 1rem;
        height: 100%;
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.04);
    }

    .card h3 {
        margin: 0 0 0.5rem 0;
        font-size: 1.08rem;
        color: var(--text);
    }

    .card p {
        margin: 0;
        color: var(--muted);
        line-height: 1.6;
    }

    .badge {
        display: inline-block;
        padding: 0.33rem 0.7rem;
        border-radius: 999px;
        background: rgba(15, 118, 110, 0.12);
        color: var(--accent);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        margin-bottom: 0.75rem;
    }

    .section-title {
        font-size: 1.2rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: var(--text);
        margin: 0 0 0.2rem;
    }

    .section-copy {
        color: var(--muted);
        margin: 0 0 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def fetch_text(endpoint: str) -> tuple[bool, str]:
    request = Request(endpoint, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=3) as response:
            payload = response.read().decode("utf-8")
            return True, payload
    except HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.reason}"
    except URLError as exc:
        return False, str(exc.reason)
    except TimeoutError:
        return False, "Timed out"


api_base = st.sidebar.text_input("Backend API URL", value="http://localhost:8080")
language = st.sidebar.selectbox("View language", ["English", "Español"], index=0)

titles = {
    "English": {
        "eyebrow": "Operations cockpit",
        "headline": "MDM OpsFlow Studio",
        "body": (
            "A lightweight Streamlit front end for the phase 2 starter. It gives the team a fast "
            "operational view over the API, plus a clear launchpad for intake, projects, and admin workflows."
        ),
        "status_label": "Backend status",
        "status_body": "Live health check against the FastAPI service.",
        "run_label": "How to run",
        "run_body": "Use the local Python 3.11 environment and start Streamlit directly.",
        "intake_title": "Intake signal",
        "intake_body": "Surface scanned documents, OCR results, and triage queues.",
        "projects_title": "Project map",
        "projects_body": "Track tenant-scoped project work without leaving the operations layer.",
        "admin_title": "Admin controls",
        "admin_body": "Reserve this surface for super-admin views and rollout health.",
    },
    "Español": {
        "eyebrow": "Panel operativo",
        "headline": "MDM OpsFlow Studio",
        "body": (
            "Una interfaz ligera en Streamlit para el starter de la fase 2. Da al equipo una vista operativa rápida "
            "sobre la API y un punto de partida claro para intake, proyectos y administración."
        ),
        "status_label": "Estado del backend",
        "status_body": "Verificación de salud en vivo del servicio FastAPI.",
        "run_label": "Cómo ejecutarlo",
        "run_body": "Usa el entorno local de Python 3.11 y arranca Streamlit directamente.",
        "intake_title": "Señal de intake",
        "intake_body": "Muestra documentos escaneados, resultados OCR y colas de revisión.",
        "projects_title": "Mapa de proyectos",
        "projects_body": "Sigue el trabajo por tenant sin salir de la capa operativa.",
        "admin_title": "Controles admin",
        "admin_body": "Reserva esta vista para super-admin y salud del despliegue.",
    },
}

copy = titles[language]

root_ok, root_payload = fetch_text(f"{api_base.rstrip('/')}/")
health_ok, health_payload = fetch_text(f"{api_base.rstrip('/')}/health")

st.sidebar.markdown(f"<div class='badge'>{copy['run_label']}</div>", unsafe_allow_html=True)
st.sidebar.code(
    "& .\\.venv311\\Scripts\\python.exe -m streamlit run streamlit_app.py",
    language="powershell",
)
st.sidebar.caption(copy["run_body"])

st.markdown(
    f"""
<div class="hero">
  <div class="eyebrow">{copy['eyebrow']}</div>
  <h1>{copy['headline']}</h1>
  <p>{copy['body']}</p>
</div>
""",
    unsafe_allow_html=True,
)

top_left, top_right = st.columns([1.15, 0.85], gap="large")

with top_left:
    st.markdown(
        f"""
        <div class="panel">
            <strong>{copy['status_label']}</strong>
            <p>{copy['status_body']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    metric_cols = st.columns(3)
    metric_cols[0].metric("API root", "Reachable" if root_ok else "Offline")
    metric_cols[1].metric("Health endpoint", "Healthy" if health_ok else "Unavailable")
    metric_cols[2].metric("Locale", language)

with top_right:
    st.markdown(
        f"""
        <div class="panel">
            <strong>API snapshot</strong>
            <p><code>{api_base.rstrip('/')}/</code></p>
            <p style="margin-top:0.75rem;color:#5a635e;">{root_payload}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

st.markdown("<div class='section-title'>Operational lanes</div>", unsafe_allow_html=True)
st.markdown(
    "<p class='section-copy'>Three entry points for the Streamlit layer: intake, project tracking, and administrative oversight.</p>",
    unsafe_allow_html=True,
)

lane_cols = st.columns(3, gap="large")
lane_cards = [
    (copy["intake_title"], copy["intake_body"]),
    (copy["projects_title"], copy["projects_body"]),
    (copy["admin_title"], copy["admin_body"]),
]

for column, (title, body) in zip(lane_cols, lane_cards, strict=True):
    with column:
        st.markdown(
            f"""
            <div class="card">
                <div class="badge">Streamlit</div>
                <h3>{title}</h3>
                <p>{body}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:0.9rem'></div>", unsafe_allow_html=True)

with st.expander("Backend details", expanded=False):
    st.write("Root response:")
    st.code(root_payload)
    st.write("Health response:")
    st.code(health_payload)
