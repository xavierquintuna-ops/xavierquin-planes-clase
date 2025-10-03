# -*- coding: utf-8 -*-
"""
app.py - Generador de Plan de Clase (Gemini, exportación Word + Excel)
"""

import streamlit as st
from io import BytesIO
from docx import Document
import time, unicodedata
from typing import List, Dict, Any
import pandas as pd

# -------------------------
# Configuración fija de la API Gemini
# -------------------------
from google import genai
from google.genai.errors import APIError

# 馃憞 Pega aqu铆 tu API Key real
GEMINI_API_KEY = "AIzaSyC0FOYvSIwW2WEePc4ks_dB6WdHyVBvmy0"

# Modelo por defecto
MODEL_NAME = "gemini-2.5-flash"
MAX_TOKENS = 2800
TEMPERATURE = 0.3

# -------------------------
# Configuraci贸n de la p谩gina
# -------------------------
st.set_page_config(page_title="XAVIERQUIN PLANIFICACI脫N DE CLASES EDUCATIVAS",
                   page_icon="馃摌",
                   layout="wide")

st.markdown("## 馃摌 XAVIERQUIN PLANIFICACI脫N DE CLASES EDUCATIVAS")
st.markdown("Aplicaci贸n para generar planificaciones por destreza.")

# -------------------------
# Inicializaci贸n de session_state
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

def create_excel_from_plan(destrezas: List[Dict[str,str]], plan_text: str) -> BytesIO:
    # Genera un Excel con columnas b谩sicas
    rows = []
    for d in destrezas:
        rows.append({
            "DESTREZA": d["destreza"],
            "INDICADOR": d["indicador"],
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
    if not GEMINI_API_KEY:
        raise RuntimeError("La clave API de Gemini no est谩 configurada en el c贸digo.")
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
# Prompt para el plan de clase (condici贸n Ingl茅s)
# -------------------------
def build_prompt(asignatura: str, grado: str, edad: Any, tema_insercion: str, destrezas_list: List[Dict[str,str]]) -> str:
    is_english = asignatura.strip().lower() in ["ingles", "ingl茅s", "english"]

    if is_english:
        instructions = (
            "You are an expert in curriculum design and lesson planning. Generate a LESSON PLAN in U.S. ENGLISH "
            "with clear, structured, and detailed text. \n\n"
            f"Subject: {asignatura}\n"
            f"Grade: {grado}\n"
            f"Age: {edad}\n"
            f"Transversal Topic: {tema_insercion}\n\n"
            "### SKILLS AND INDICATORS\n"
        )
        for d in destrezas_list:
            instructions += f"- Skill: {d['destreza']} | Indicator: {d['indicador']}\n"

        instructions += (
            "\n### ANTICIPATION\n"
            "- Activities that activate prior knowledge (all must start with verbs in infinitive form).\n\n"
            "### CONSTRUCTION\n"
            "- At least 6 sequenced activities (all starting with verbs in infinitive form).\n"
            "- Include UDL (Universal Design for Learning) activities.\n\n"
            "### CONSOLIDATION\n"
            "- Activities to apply and reinforce knowledge.\n\n"
            "### RESOURCES\n"
            "- List physical and technological resources (board, notebook, projector, etc.)\n\n"
            "### EVALUATION GUIDELINES\n"
            "- Evaluation activities aligned with the indicator.\n"
            "- Include UDL strategies for evaluation.\n\n"
        )
    else:
        instructions = (
            "Eres un experto en dise帽o curricular y planificaci贸n educativa. Genera un PLAN DE CLASE en ESPA脩OL "
            "en formato TEXTO estructurado y detallado. \n\n"
            f"Asignatura: {asignatura}\n"
            f"Grado: {grado}\n"
            f"Edad: {edad}\n"
            f"Tema de Inserci贸n: {tema_insercion}\n\n"
            "### DESTREZAS E INDICADORES\n"
        )
        for d in destrezas_list:
            instructions += f"- Destreza: {d['destreza']} | Indicador: {d['indicador']}\n"

        instructions += (
            "\n### ANTICIPACI脫N\n"
            "- Actividades que activen conocimientos previos (todas empiezan con verbos en infinitivo).\n\n"
            "### CONSTRUCCI脫N\n"
            "- Al menos 6 actividades en secuencia pedag贸gica (todas con verbos en infinitivo).\n"
            "- Incluir actividades DUA (Dise帽o Universal de Aprendizaje).\n\n"
            "### CONSOLIDACI脫N\n"
            "- Actividades para aplicar lo aprendido y reforzar conocimientos.\n\n"
            "### RECURSOS\n"
            "- Listar recursos f铆sicos y tecnol贸gicos (pizarra, cuaderno, proyector, etc.)\n\n"
            "### ORIENTACIONES PARA LA EVALUACI脫N\n"
            "- Actividades de evaluaci贸n en relaci贸n con el indicador.\n"
            "- Incluir orientaciones DUA para la evaluaci贸n.\n\n"
        )

    return instructions

# -------------------------
# Interfaz - Datos b谩sicos
# -------------------------
st.subheader("Datos b谩sicos")
c1, c2 = st.columns(2)
with c1:
    st.text_input("Asignatura", key="asignatura", value=st.session_state["asignatura"])
    st.text_input("Grado", key="grado", value=st.session_state["grado"])
with c2:
    st.number_input("Edad de los estudiantes", min_value=3, max_value=99, key="edad", value=st.session_state["edad"])
    st.text_input("Tema de Inserci贸n (actividad transversal)", key="tema_insercion", value=st.session_state["tema_insercion"])

st.markdown("---")
st.subheader("Agregar destreza e indicador")

with st.form(key="form_add_destreza"):
    d = st.text_area("Destreza", key="form_destreza")
    i = st.text_area("Indicador de logro", key="form_indicador")
    t = st.text_input("Tema de estudio (opcional)", key="form_tema_estudio")
    submitted = st.form_submit_button("鉃?Agregar destreza")
    if submitted:
        dd, ii, tt = normalize_text(d), normalize_text(i), normalize_text(t)
        if not dd or not ii:
            st.warning("Completa la destreza y el indicador antes de agregar.")
        else:
            st.session_state["destrezas"].append({"destreza": dd, "indicador": ii, "tema_estudio": tt})
            st.success("Destreza agregada 鉁?)
            st.rerun()

if st.session_state["destrezas"]:
    st.subheader("Destrezas a帽adidas")
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
        st.session_state["excel_bytes"] = create_excel_from_plan(dests, resp).getvalue()
        st.success("鉁?Plan generado con 茅xito.")
    except Exception as e:
        st.session_state["last_error"] = str(e)

st.button("馃摑 Generar Plan de Clase", on_click=generar_plan_callback)

if st.session_state.get("last_error"):
    st.error(st.session_state["last_error"])

# -------------------------
# Vista previa del Plan generado
# -------------------------
if st.session_state.get("plan_text"):
    st.markdown("---")
    st.subheader("馃摉 Vista previa del Plan")
    st.markdown(st.session_state["plan_text"])

# -------------------------
# Exportar a Word y Excel
# -------------------------
if st.session_state.get("doc_bytes"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "馃捑 Exportar a Word",
        data=st.session_state["doc_bytes"],
        file_name=f"plan_{ts}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

if st.session_state.get("excel_bytes"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "馃搳 Exportar a Excel",
        data=st.session_state["excel_bytes"],
        file_name=f"plan_{ts}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# -------------------------
# Reiniciar
# -------------------------
def reset_app():
    for k, v in defaults.items():
        st.session_state[k] = v
    st.rerun()

if st.button("馃攧 Nuevo"):
    reset_app()
