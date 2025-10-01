# -*- coding: utf-8 -*-
"""
app.py - Generador de Plan de Clase (versión Gemini con recursos)
"""

import streamlit as st
from io import BytesIO
from docx import Document
import os, time, unicodedata, re
from typing import List, Dict, Any

# Bibliotecas para la IA de Google Gemini
from google import genai
from google.genai.errors import APIError

# Bibliotecas para la búsqueda de recursos online
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode

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

st.markdown("Aplicación para generar planificaciones por destreza.")

# -------------------------
# Configuración fija de la API
# -------------------------
# 👇 Pega aquí tu API Key de Gemini
GEMINI_API_KEY = "AIzaSyB63V1035g-gaZ_KNKAajyjezxnNcJTZW0"

# Modelo por defecto
model_name = "gemini-2.5-flash"
max_tokens = 2800
temperature = 0.3

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
    "last_error": ""
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
# Integración con Perplexity AI (para buscar recursos online)
# -------------------------
def buscar_recursos_perplexity(query: str, sitio_preferido: str = None) -> List[Dict[str, str]]:
    base_url = "https://www.perplexity.ai/search?"
    
    if sitio_preferido and sitio_preferido != "general":
        query_completa = f"{query} site:{sitio_preferido}"
    else:
        query_completa = query
        
    params = {'q': query_completa, 'copilot': 'false'}

    try:
        headers = {'User-Agent': 'Mozilla/5.0'} 
        response = requests.get(base_url + urlencode(params), headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        recursos_encontrados = []
        for link_tag in soup.find_all('a', href=True):
            href = link_tag['href']
            if href.startswith('http') and 'perplexity.ai' not in href:
                titulo = link_tag.text.strip() or "Recurso"
                if not any(r['enlace'] == href for r in recursos_encontrados):
                    recursos_encontrados.append({'titulo': titulo, 'enlace': href})
                    if len(recursos_encontrados) >= 3:
                        break

        if not recursos_encontrados and sitio_preferido:
             return buscar_recursos_perplexity(query)

        return recursos_encontrados

    except requests.exceptions.RequestException as e:
        st.info(f"Advertencia: Error al buscar recursos online. Se continuará con la generación del plan. Error: {e}")
        return []

# -------------------------
# Llamada al modelo Gemini
# -------------------------
def call_model(prompt_text: str, max_tokens: int, temperature: float) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("La clave API de Gemini no está configurada en el código.")
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        config = genai.types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=[{"role": "user", "parts": [{"text": prompt_text}]}],
            config=config,
        )
        return response.text
    
    except APIError as e:
        st.error(f"Ocurrió un error con la API de Gemini: {e}. Revisa la clave API y el nombre del modelo ({model_name}).")
        raise
    except Exception as e:
        st.error(f"Error inesperado: {e}")
        raise

# -------------------------
# Prompt adaptado para texto
# -------------------------
def build_prompt(asignatura: str, grado: str, edad: Any, tema_insercion: str, destrezas_list: List[Dict[str,str]]) -> str:
    instructions = (
        "Eres un experto en diseño curricular y planificación educativa. Genera un PLAN DE CLASE en ESPAÑOL en formato TEXTO estructurado y detallado. \n\n"
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
        "- Actividades que activen conocimientos previos (todas empiezan con verbos en infinitivo).\n\n"
        "### CONSTRUCCIÓN\n"
        "- Al menos 6 actividades en secuencia pedagógica (todas con verbos en infinitivo).\n"
        "- Incluir actividades DUA (Diseño Universal de Aprendizaje).\n\n"
        "### CONSOLIDACIÓN\n"
        "- Actividades para aplicar lo aprendido y reforzar conocimientos.\n\n"
        "### RECURSOS\n"
        "- Listar recursos físicos y tecnológicos (pizarra, cuaderno, proyector, etc.)\n\n"
        "### ORIENTACIONES PARA LA EVALUACIÓN\n"
        "- Actividades de evaluación en relación con el indicador.\n"
        "- Incluir orientaciones DUA para la evaluación.\n\n"
    )
    return instructions

# -------------------------
# Interfaz - Datos básicos
# -------------------------
st.subheader("Datos básicos")
c1, c2 = st.columns(2)
with c1:
    st.text_input("Asignatura", key="asignatura", value=st.session_state["asignatura"])
    st.text_input("Grado", key="grado", value=st.session_state["grado"])
with c2:
    st.number_input("Edad de los estudiantes", min_value=3, max_value=99, key="edad", value=st.session_state["edad"])
    st.text_input("Tema de Inserción (actividad transversal)", key="tema_insercion", value=st.session_state["tema_insercion"])

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
    if not asig or not grad or not dests:
        st.session_state["last_error"] = "Faltan campos obligatorios."
        return
    try:
        with st.spinner("Generando estructura del plan con Gemini..."):
            prompt = build_prompt(asig, grad, edad_val, tema, dests)
            resp = call_model(prompt, max_tokens=max_tokens, temperature=temperature)
        
        st.session_state["plan_text"] = resp
        st.session_state["doc_bytes"] = create_docx_from_text(resp).getvalue()
        st.success("✅ Plan generado con éxito.")
    except Exception as e:
        st.session_state["last_error"] = str(e)

st.button("📝 Generar Plan de Clase", on_click=generar_plan_callback)

if st.session_state.get("last_error"):
    st.error(st.session_state["last_error"])

# -------------------------
#
