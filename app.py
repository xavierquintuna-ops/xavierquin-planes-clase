# -*- coding: utf-8 -*-
"""
app.py - Generador de Plan de Clase (versión texto, con exportación a Word)
"""

import streamlit as st
from io import BytesIO
from docx import Document
import os, time, unicodedata
from typing import List, Dict, Any

# -------------------------
# Intento de cargar gemini_client
# -------------------------
gemini_client = None
_has_gemini = False
try:
    import gemini_client
    _has_gemini = True
except Exception:
    _has_gemini = False

# -------------------------
# Configuración de la página
# -------------------------
st.set_page_config(page_title="XAVIERQUIN PLANIFICACIÓN DE CLASES EDUCATIVAS",
                   page_icon="📘",
                   layout="wide")

# Title with image (left) and text (right)
title_col1, title_col2 = st.columns([1, 6])
with title_col1:
    st.image("https://img.icons8.com/fluency/96/000000/lesson-planner.png", width=72)
with title_col2:
    st.markdown("## **XAVIERQUIN PLANIFICACIÓN DE CLASES EDUCATIVAS**")

st.markdown("Aplicación para generar planificaciones por destreza. Usa Califica.ai como referencia para recursos online reales.")

# -------------------------
# Sidebar
# -------------------------
st.sidebar.header("Configuración API / Modelo")
api_key_input = st.sidebar.text_input("OpenAI API Key (opcional, si no usas Gemini)", type="password")
model_name = st.sidebar.text_input("Modelo OpenAI (ej: gpt-4o-mini)", value="gpt-4o-mini")
max_tokens = st.sidebar.number_input("Max tokens", value=1800, step=100)
temperature = st.sidebar.slider("Temperatura", 0.0, 1.0, 0.3)
debug_mode = st.sidebar.checkbox("Mostrar debug (session_state)", value=False)

def get_api_key():
    if api_key_input:
        return api_key_input
    env = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_APIKEY")
    if env:
        return env
    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        return None

OPENAI_API_KEY = get_api_key()

# -------------------------
# Inicialización session_state
# -------------------------
defaults = {
    "asignatura": "",
    "grado": "",
    "edad": 12,
    "tema_insercion": "",
    "destrezas": [],
    "plan_text": None,
    "doc_bytes": None,
    "last_error": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -------------------------
# Utilidades
# -------------------------
def normalize_text(s: str) -> str:
    if s is None: return ""
    return unicodedata.normalize("NFKC", str(s)).strip()

def create_docx_from_text(plan_text: str) -> BytesIO:
    doc = Document()
    doc.add_heading("Plan de Clase", level=1)
    for line in plan_text.split("\n"):
        if line.strip():
            doc.add_paragraph(line)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# -------------------------
# Llamada al modelo
# -------------------------
def call_model(prompt_text: str, max_tokens: int = 1800, temperature: float = 0.3) -> str:
    if _has_gemini:
        return gemini_client.call_gemini(prompt_text, max_tokens=max_tokens, temperature=temperature)
    if OPENAI_API_KEY:
        import openai
        openai.api_key = OPENAI_API_KEY
        resp = openai.ChatCompletion.create(
            model=model_name,
            messages=[
                {"role":"system","content":"Eres un experto en planificación de clases."},
                {"role":"user","content":prompt_text}
            ],
            max_tokens=int(max_tokens),
            temperature=float(temperature)
        )
        return resp["choices"][0]["message"]["content"]
    raise RuntimeError("No hay integración: añade gemini_client.py o configura OPENAI_API_KEY.")

# -------------------------
# Prompt adaptado para texto
# -------------------------
def build_prompt(asignatura: str, grado: str, edad: Any, tema_insercion: str, destrezas_list: List[Dict[str,str]]) -> str:
    instructions = (
        "Eres un experto en diseño curricular y planificación educativa.\n\n"
        "Genera un PLAN DE CLASE en ESPAÑOL en formato TEXTO estructurado.\n\n"
        "📘 **PLAN DE CLASE**\n\n"
        f"Asignatura: {asignatura}\n"
        f"Grado: {grado}\n"
        f"Edad: {edad}\n"
        f"Tema de Inserción: {tema_insercion}\n\n"
        "### DESTREZAS E INDICADORES\n"
    )
    for d in destrezas_list:
        instructions += f"- Destreza: {d['destreza']} | Indicador: {d['indicador']}\n"

    instructions += (
        "\n### ANTICIPACIÓN\n"
        "- Actividades que activen conocimientos previos (todas empiezan con verbos en infinitivo).\n"
        "- Incluir al menos un recurso online gratuito y real (Califica, Wordwall, Educaplay, Liveworksheets o YouTube).\n\n"
        "### CONSTRUCCIÓN\n"
        "- Al menos 6 actividades en secuencia pedagógica (todas con verbos en infinitivo).\n"
        "- Incluir actividades DUA (Diseño Universal de Aprendizaje).\n"
        "- Incluir al menos un recurso online gratuito y real.\n\n"
        "### CONSOLIDACIÓN\n"
        "- Actividades para aplicar lo aprendido y reforzar conocimientos.\n"
        "- Incluir al menos un recurso online gratuito y real.\n\n"
        "### RECURSOS\n"
        "- Listar recursos físicos y tecnológicos (pizarra, cuaderno, proyector, etc.)\n\n"
        "### ORIENTACIONES PARA LA EVALUACIÓN\n"
        "- Actividades de evaluación en relación con el indicador.\n"
        "- Incluir orientaciones DUA para la evaluación.\n\n"
        "IMPORTANTE:\n"
        "- Usa títulos en mayúsculas para los momentos (ANTICIPACIÓN, CONSTRUCCIÓN, CONSOLIDACIÓN).\n"
        "- Devuelve solo TEXTO bien estructurado, no JSON ni código.\n"
    )
    return instructions

# -------------------------
# Interfaz
# -------------------------
st.subheader("Datos básicos")
c1, c2 = st.columns(2)
with c1:
    st.text_input("Asignatura", key="asignatura")
    st.text_input("Grado", key="grado")
with c2:
    st.number_input("Edad de los estudiantes", min_value=3, max_value=99, key="edad")
    st.text_input("Tema de Inserción (actividad transversal)", key="tema_insercion")

st.markdown("---")
st.subheader("Agregar destreza e indicador")

with st.form(key="form_add_destreza"):
    d = st.text_area("Destreza", key="form_destreza")
    i = st.text_area("Indicador de logro", key="form_indicador")
    t = st.text_input("Tema de estudio (opcional)", key="form_tema_estudio")
    submitted = st.form_submit_button("➕ Agregar destreza")
    if submitted:
        dd, ii, tt = normalize_text(d), normalize_text(i), normalize_text(t)
        if not dd or not ii:
            st.warning("Completa la destreza y el indicador antes de agregar.")
        else:
            st.session_state["destrezas"].append({"destreza": dd, "indicador": ii, "tema_estudio": tt})
            st.success("Destreza agregada ✅")
            st.rerun()

if st.session_state["destrezas"]:
    st.subheader("Destrezas añadidas")
    st.table(st.session_state["destrezas"])

# -------------------------
# Generar plan
# -------------------------
def generar_plan_callback():
    st.session_state["last_error"] = ""
    asig = normalize_text(st.session_state["asignatura"])
    grad = normalize_text(st.session_state["grado"])
    edad_val = st.session_state["edad"]
    tema = normalize_text(st.session_state["tema_insercion"])
    dests = st.session_state["destrezas"]
    faltantes = []
    if not asig: faltantes.append("Asignatura")
    if not grad: faltantes.append("Grado")
    if not dests: faltantes.append("Al menos una destreza")
    if faltantes:
        st.session_state["last_error"] = "Faltan campos: " + ", ".join(faltantes)
        return
    try:
        prompt = build_prompt(asig, grad, edad_val, tema, dests)
        with st.spinner("Generando plan de clase..."):
            resp = call_model(prompt, max_tokens=max_tokens, temperature=temperature)
        st.session_state["plan_text"] = str(resp)
        st.session_state["doc_bytes"] = create_docx_from_text(st.session_state["plan_text"]).getvalue()
        st.success("✅ Plan generado.")
    except Exception as e:
        st.session_state["last_error"] = str(e)

st.button("📝 Generar Plan de Clase", on_click=generar_plan_callback)

if st.session_state.get("last_error"):
    st.error(st.session_state["last_error"])

# -------------------------
# Vista previa del Plan generado
# -------------------------
if st.session_state.get("plan_text"):
    st.markdown("---")
    st.subheader("📖 Vista previa del Plan")
    st.markdown(st.session_state["plan_text"])

# -------------------------
# Exportar a Word
# -------------------------
if st.session_state.get("doc_bytes"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "💾 Exportar a Word",
        data=st.session_state["doc_bytes"],
        file_name=f"plan_{ts}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# Nuevo / reiniciar
if st.button("🔄 Nuevo"):
    for k, v in defaults.items():
        st.session_state[k] = v
    st.rerun()

if debug_mode:
    st.sidebar.subheader("DEBUG session_state")
    import pprint
    st.sidebar.text(pprint.pformat(dict(st.session_state)))

