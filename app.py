# -*- coding: utf-8 -*-
"""
app.py - Planificador Educativo Profesional
Autor: Mgs. Xavier Quintuña C.
"""

import streamlit as st
from io import BytesIO
from docx import Document
import time
import unicodedata
import random
from typing import List, Dict, Any
import pandas as pd
import matplotlib.pyplot as plt
from google import genai
from google.genai.errors import APIError

# -------------------------
# CONFIGURACIÓN PRINCIPAL
# -------------------------
GEMINI_API_KEY = "AIzaSyC0FOYvSIwW2WEePc4ks_dB6WdHyVBvmy0"  # ⚠️ Reemplaza con tu clave real antes de desplegar
MODEL_NAME = "gemini-2.5-flash"
MAX_TOKENS = 2800
TEMPERATURE = 0.3

# -------------------------
# Configuración de página
# -------------------------
st.set_page_config(page_title="Planificador Educativo", page_icon="📘", layout="wide")

# Frases motivadoras
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

# -------------------------
# CSS personalizado
# -------------------------
custom_css = f"""
<style>
/* Fondo y fuente general */
.stApp {{
    background: linear-gradient(135deg, #eef4ff, #ffffff);
    color: #000000;
    font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    padding-top: 10px;
}}

/* Banner principal */
.banner {{
    position: relative;
    height: 230px;
    background: linear-gradient(135deg, #1a73e8, #4285f4);
    overflow: hidden;
    border-radius: 14px;
    margin-bottom: 25px;
    box-shadow: 0 6px 25px rgba(0,0,0,0.18);
    text-align: center;
    padding-top: 35px;
}}
.banner h1 {{
    color: #ffffff;
    font-size: 34px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
}}
.banner h2 {{
    color: #e3e3e3;
    font-size: 17px;
    font-weight: 400;
    margin-top: 10px;
    font-style: italic;
}}

/* Ondas animadas */
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
}}
.wave1 {{
    background-image: radial-gradient(circle at 50% 40%, rgba(255,255,255,0.35) 15%, transparent 60%);
}}
.wave2 {{
    background-image: radial-gradient(circle at 50% 50%, rgba(255,255,255,0.2) 12%, transparent 60%);
    height: 120%;
    animation-duration: 18s;
}}
@keyframes move {{
    0% {{ transform: translateX(0); }}
    100% {{ transform: translateX(-25%); }}
}}

/* Etiquetas de campos */
.stTextInput label, .stTextArea label, .stNumberInput label {{
    color: #000000 !important;
    font-weight: 600 !important;
    font-size: 15px !important;
}}

/* Campos de texto */
.stTextInput > div > div > input,
.stTextArea textarea {{
    border: 1px solid #1a73e8 !important;
    border-radius: 8px !important;
    background-color: #fbfeff !important;
    color: #000000 !important;
    padding: 8px !important;
}}

/* Subtítulos */
h3, .stSubheader {{
    color: #1a73e8 !important;
    font-weight: 700 !important;
    text-shadow: 0.5px 0.5px 1px rgba(0,0,0,0.1);
}}

/* Botones */
button, .stButton>button {{
    background: linear-gradient(135deg, #1a73e8, #3a86ff) !important;
    color: white !important;
    border-radius: 10px !important;
    padding: 8px 14px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    transition: 0.2s ease-in-out;
}}
button:hover, .stButton>button:hover {{
    background: linear-gradient(135deg, #1557b0, #2c6de2) !important;
    transform: scale(1.02);
}}

/* Alertas y mensajes */
.stAlert {{
    border-radius: 10px !important;
}}

/* Firma inferior */
.footer {{
    margin-top: 40px;
    text-align: center;
    color: #444;
    font-weight: 600;
    font-size: 15px;
    opacity: 0.85;
    animation: fadeIn 2s ease-in-out;
}}
.footer span {{
    color: #1a73e8;
    font-weight: 700;
}}
@keyframes fadeIn {{
    from {{ opacity: 0; }}
    to {{ opacity: 1; }}
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
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -------------------------
# Funciones
# -------------------------
def normalize_text(s): return unicodedata.normalize("NFKC", str(s or "")).strip()

def create_docx_from_text(plan_text):
    doc = Document()
    doc.add_heading("Plan de Clase", level=1)
    for line in plan_text.split("\n"):
        if line.strip():
            doc.add_paragraph(line)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def call_model(prompt_text: str) -> str:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "TU_API_KEY_AQUI":
        raise RuntimeError("⚠️ La clave API de Gemini no está configurada.")
    client = genai.Client(api_key=GEMINI_API_KEY)
    config = genai.types.GenerateContentConfig(temperature=TEMPERATURE, max_output_tokens=MAX_TOKENS)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[{"role": "user", "parts": [{"text": prompt_text}]}],
        config=config,
    )
    return response.text

def build_prompt(asignatura, grado, edad, tema_insercion, destrezas_list):
    text = (
        f"Eres experto en planificación educativa. Genera un PLAN DE CLASE estructurado y práctico en español.\n"
        f"Asignatura: {asignatura}\nGrado: {grado}\nEdad: {edad}\nTema de Inserción: {tema_insercion}\n\n"
    )
    for d in destrezas_list:
        text += f"- Destreza: {d.get('destreza','')} | Indicador: {d.get('indicador','')}\n"
    return text

# -------------------------
# Interfaz
# -------------------------
with st.expander("📋 Ingresar datos básicos", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Asignatura", key="asignatura")
        st.text_input("Grado", key="grado")
    with c2:
        st.number_input("Edad de los estudiantes", 3, 99, key="edad")
        st.text_input("Tema de Inserción (actividad transversal)", key="tema_insercion")

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

# -------------------------
# Generar plan
# -------------------------
def generar_plan():
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
        st.success("✔️ Plan generado con éxito.")
    except Exception as e:
        st.error(str(e))

st.button("📄 Generar Plan de Clase", on_click=generar_plan)

# -------------------------
# Vista previa
# -------------------------
if st.session_state.get("plan_text"):
    st.markdown("---")
    st.subheader("👀 Vista previa del Plan")
    st.markdown(st.session_state["plan_text"])

# -------------------------
# Créditos con efecto visual
# -------------------------
st.markdown("<div class='footer'>✨ Creado por <span>Mgs. Xavier Quintuña C.</span> ✨</div>", unsafe_allow_html=True)
