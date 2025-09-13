# -*- coding: utf-8 -*-
"""
app.py - Generador de Plan de Clase (integración Califica.ai, imágenes y links reales via búsquedas)
Versión corregida (st.rerun en lugar de st.experimental_rerun).
"""

import streamlit as st
from io import BytesIO
from docx import Document
import json, os, time, unicodedata
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
max_tokens = st.sidebar.number_input("Max tokens", value=2000, step=100)
temperature = st.sidebar.slider("Temperatura", 0.0, 1.0, 0.2)
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
    "plan_raw": None,
    "plan_parsed": None,
    "doc_bytes": None,
    "last_error": "",
    "generating": False,
    "gemini_configured": False,
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

def extract_first_json(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("Texto no es cadena.")
    start = None
    for i, ch in enumerate(text):
        if ch in ("{", "["):
            start
