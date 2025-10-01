# -*- coding: utf-8 -*-
"""
app.py - Generador de Plan de Clase (versión fija con API en código y exportación a Word)
"""

import streamlit as st
from io import BytesIO
from docx import Document
import time, unicodedata
from typing import List, Dict, Any

# -------------------------
# Configuración fija de la API Gemini
# -------------------------
from google import genai
from google.genai.errors import APIError

# 👇 Pega aquí tu API Key real
GEMINI_API_KEY = "TU_API_KEY_AQUI"

# Modelo por defecto
MODEL_NAME = "gemini-2.5-flash"
MAX_TOKENS = 2800
TEMPERATURE = 0.3

# -------------------------
# Configuración de la página
# -------------------------
st.set_page_config(page_title="XAVIERQUIN PLANIFICACIÓN DE CLASES EDUCATIVAS",
                   page_icon="📘",
                   layout="wide")

st.markdown("## 📘 XAVIERQUIN PLANIFICACIÓN DE CLASES EDUCATIVAS")
st.markdown("Aplicación para generar planificaciones por destreza.")

# -------------------------
# Inicialización de session_state
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
# Llamada al modelo Gemini
# -------------------------
def call_model(prompt_text: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("La clave API de Gemini no está configurada en el código.")
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
# Prompt para el plan de clase
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
        with st.spinner("Generando plan con Gemini..."):
            prompt = build_prompt(asig, grad, edad_val, tema, dests)
            resp = call_model(prompt)
        
        st.session_state["plan_text"] = resp
        st.session_state["doc_bytes"] = create_docx_from_text(resp).getvalue()
        st.success("✅ Plan generado con éxito.")
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

# -------------------------
# Reiniciar
# -------------------------
def reset_app():
    for k, v in defaults.items():
        st.session_state[k] = v
    st.rerun()

if st.button("🔄 Nuevo"):
    reset_app()
