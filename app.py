# -*- coding: utf-8 -*-
"""
app.py - Generador de Plan de Clase (Versión final)
Incluye:
 - Corrección de errores de codificación UTF-8
 - Generación en inglés si la asignatura es "Inglés / English"
 - Contador estimado de tokens por planificación + historial y gráfica
 - Estilo visual personalizado (CSS)
 - Banner superior animado con frases motivadoras aleatorias
 - Descarga a Word y Excel
 - Interfaz organizada con expanders y mensajes claros
"""

import streamlit as st
from io import BytesIO
from docx import Document
import time
import unicodedata
import datetime
import random
from typing import List, Dict, Any
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------
# Dependencia para Gemini (Google Generative AI)
# -------------------------
from google import genai
from google.genai.errors import APIError

# -------------------------
# CONFIGURACIÓN GENERAL
# -------------------------
GEMINI_API_KEY = "TU_API_KEY_AQUI"  # ⚠️ Reemplaza con tu API key real antes de desplegar
MODEL_NAME = "gemini-2.5-flash"
MAX_TOKENS = 2800
TEMPERATURE = 0.3

# -------------------------
# Página y estilo general
# -------------------------
st.set_page_config(page_title="Planificador Educativo", page_icon="📘", layout="wide")

# Frases motivadoras aleatorias
frases_docentes = [
    "Educar es sembrar esperanza 🌱",
    "El mejor maestro enseña con el corazón ❤️",
    "Compartir conocimiento es dejar huella ✨",
    "Cada clase es una oportunidad para transformar vidas 🌍",
    "La educación es el arma más poderosa para cambiar el mundo 🌟",
    "Un docente inspira más allá de las palabras 💡",
    "La enseñanza que deja huella va de corazón a corazón 💖"
]
frase_motivadora = random.choice(frases_docentes)

# CSS personalizado + banner animado
custom_css = f"""
<style>
.stApp {{
    background: linear-gradient(135deg, #eaf3ff, #ffffff);
    color: #222;
    font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    padding-top: 10px;
}}

.banner {{
    position: relative;
    height: 220px;
    background: linear-gradient(135deg, #1a73e8, #4285f4);
    overflow: hidden;
    border-radius: 12px;
    margin-bottom: 20px;
    box-shadow: 0 6px 22px rgba(0,0,0,0.15);
    text-align: center;
    padding-top: 30px;
}}

.banner h1 {{
    color: white;
    font-size: 30px;
    font-weight: 700;
    margin: 0;
    z-index: 2;
    position: relative;
    letter-spacing: 0.2px;
}}
.banner h2 {{
    color: #f1f1f1;
    font-size: 16px;
    font-weight: 400;
    margin-top: 8px;
    z-index: 2;
    position: relative;
    font-style: italic;
}}

.wave {{
    position: absolute;
    bottom: 0;
    left: 0;
    width: 200%;
    height: 100%;
    background-repeat: repeat-x;
    background-size: 50% 100%;
    opacity: 0.55;
    animation: move 12s linear infinite;
    z-index: 1;
}}
.wave1 {{
    background-image: radial-gradient(circle at 50% 40%, rgba(255,255,255,0.35) 15%, transparent 60%);
    height: 100%;
}}
.wave2 {{
    background-image: radial-gradient(circle at 50% 50%, rgba(255,255,255,0.18) 12%, transparent 60%);
    height: 120%;
    animation-duration: 18s;
}}

@keyframes move {{
    0% {{ transform: translateX(0); }}
    100% {{ transform: translateX(-25%); }}
}}

.stTextInput > div > div > input, .stTextArea textarea {{
    border: 1px solid #1a73e8 !important;
    border-radius: 8px !important;
    background-color: #fbfeff !important;
    padding: 8px !important;
}}
button, .stButton>button {{
    background-color: #1a73e8 !important;
    color: white !important;
    border-radius: 10px !important;
    padding: 6px 12px !important;
    font-size: 14px !important;
}}
button:hover, .stButton>button:hover {{
    background-color: #1557b0 !important;
}}

.stAlert {{
    border-radius: 8px !important;
}}
</style>

<div class="banner">
    <h1>📘 XAVIERQUIN - Planificación de Clases</h1>
    <h2>{frase_motivadora}</h2>
    <div class="wave wave1"></div>
    <div class="wave wave2"></div>
</div>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# -------------------------
# Inicialización
# -------------------------
defaults = {
    "asignatura": "",
    "grado": "",
    "edad": 12,
    "tema_insercion": "",
    "destrezas": [],
    "plan_text": None,
    "doc_bytes": None,
    "excel_bytes": None,
    "last_error": "",
    "tokens_usados": 0,
    "historial_tokens": [],
    "planes_generados": 0
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -------------------------
# Funciones utilitarias
# -------------------------
def normalize_text(s: str) -> str:
    if s is None:
        return ""
    return unicodedata.normalize("NFKC", str(s)).strip()

def contar_tokens_estimado(texto: str) -> int:
    if not texto:
        return 0
    return max(1, len(texto) // 4)

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

def create_excel_from_plan(destrezas: List[Dict[str,str]], plan_text: str) -> BytesIO:
    rows = []
    for d in destrezas:
        rows.append({
            "DESTREZA": d.get("destreza", ""),
            "INDICADOR": d.get("indicador", ""),
            "TEMA": d.get("tema_estudio", ""),
            "PLAN DE CLASE": plan_text
        })
    df = pd.DataFrame(rows)
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Planificacion")
    buf.seek(0)
    return buf

# -------------------------
# Llamada al modelo Gemini
# -------------------------
def call_model(prompt_text: str) -> str:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "AIzaSyC0FOYvSIwW2WEePc4ks_dB6WdHyVBvmy0":
        raise RuntimeError("⚠️ La clave API de Gemini no está configurada.")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        config = genai.types.GenerateContentConfig(
            temperature=TEMPERATURE,
            max_output_tokens=MAX_TOKENS,
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[{"role": "user", "parts": [{"text": prompt_text}]}],
            config=config,
        )
        return response.text
    except APIError as e:
        st.error(f"Error con la API de Gemini: {e}")
        raise
    except Exception as e:
        st.error(f"Error inesperado: {e}")
        raise

# -------------------------
# Construcción del prompt
# -------------------------
def build_prompt(asignatura, grado, edad, tema_insercion, destrezas_list):
    is_english = asignatura.strip().lower() in ["ingles", "inglés", "english"]

    if is_english:
        text = (
            "You are an expert in lesson planning. Generate a detailed LESSON PLAN in English.\n"
            f"Subject: {asignatura}\nGrade: {grado}\nAge: {edad}\nTransversal Topic: {tema_insercion}\n\n"
        )
        for d in destrezas_list:
            text += f"- Skill: {d.get('destreza','')} | Indicator: {d.get('indicador','')}\n"
    else:
        text = (
            "Eres experto en planificación educativa. Genera un PLAN DE CLASE completo en español.\n"
            f"Asignatura: {asignatura}\nGrado: {grado}\nEdad: {edad}\nTema de Inserción: {tema_insercion}\n\n"
        )
        for d in destrezas_list:
            text += f"- Destreza: {d.get('destreza','')} | Indicador: {d.get('indicador','')}\n"

    return text

# -------------------------
# Interfaz principal
# -------------------------
with st.expander("📋 Ingresar datos básicos", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Asignatura", key="asignatura")
        st.text_input("Grado", key="grado")
    with c2:
        st.number_input("Edad de los estudiantes", 3, 99, key="edad")
        st.text_input("Tema de Inserción", key="tema_insercion")

st.markdown("---")
st.subheader("➕ Agregar destrezas e indicadores")

with st.form(key="form_add_destreza"):
    d = st.text_area("Destreza")
    i = st.text_area("Indicador de logro")
    t = st.text_input("Tema de estudio (opcional)")
    submitted = st.form_submit_button("Agregar destreza")
    if submitted:
        dd, ii, tt = normalize_text(d), normalize_text(i), normalize_text(t)
        if not dd or not ii:
            st.warning("⚠️ Completa la destreza y el indicador.")
        else:
            st.session_state["destrezas"].append({"destreza": dd, "indicador": ii, "tema_estudio": tt})
            st.success("✔️ Destreza agregada.")
            st.rerun()

if st.session_state["destrezas"]:
    st.table(st.session_state["destrezas"])

def generar_plan():
    st.session_state["last_error"] = ""
    try:
        prompt = build_prompt(
            st.session_state["asignatura"],
            st.session_state["grado"],
            st.session_state["edad"],
            st.session_state["tema_insercion"],
            st.session_state["destrezas"],
        )
        with st.spinner("⏳ Generando plan..."):
            respuesta = call_model(prompt)
        st.session_state["plan_text"] = respuesta
        st.session_state["doc_bytes"] = create_docx_from_text(respuesta).getvalue()
        st.session_state["excel_bytes"] = create_excel_from_plan(st.session_state["destrezas"], respuesta).getvalue()
        st.success("✔️ Plan generado con éxito.")
    except Exception as e:
        st.error(str(e))

st.button("📄 Generar Plan de Clase", on_click=generar_plan)

if st.session_state.get("plan_text"):
    st.markdown("---")
    st.subheader("👀 Vista previa del Plan")
    st.markdown(st.session_state["plan_text"])

# -------------------------
# Descargas
# -------------------------
if st.session_state.get("doc_bytes"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    st.download_button("💾 Exportar a Word", data=st.session_state["doc_bytes"],
                       file_name=f"plan_{ts}.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

if st.session_state.get("excel_bytes"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    st.download_button("📊 Exportar a Excel", data=st.session_state["excel_bytes"],
                       file_name=f"plan_{ts}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# -------------------------
# Créditos
# -------------------------
st.markdown("---")
st.markdown("<center>✨ Creado por <b>Mgs. Xavier Quintuña C.</b> ✨</center>", unsafe_allow_html=True)
