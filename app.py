# -*- coding: utf-8 -*-
"""
app.py - Generador de Plan de Clase (integración Califica.ai, imágenes y links reales via búsquedas)
Reemplaza completamente tu app.py con este archivo.
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
            start = i
            break
    if start is None:
        raise ValueError("No se encontró JSON en el texto.")
    stack, in_string, escape = [], False, False
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '"' and not escape:
            in_string = not in_string
        if ch == "\\" and not escape:
            escape = True
        else:
            escape = False
        if not in_string:
            if ch in ("{", "["):
                stack.append(ch)
            elif ch in ("}", "]"):
                if not stack:
                    raise ValueError("JSON mal formado.")
                stack.pop()
                if not stack:
                    return text[start:i+1]
    raise ValueError("No se pudo extraer JSON completo.")

# --- FUNCIÓN para generar enlaces de búsqueda ---
def generate_search_links(keywords: List[str]) -> Dict[str, str]:
    safe_terms = []
    for k in keywords:
        k_norm = normalize_text(k)
        if k_norm:
            safe_terms.append(k_norm.replace(" ", "+"))
    keywords_str = "+".join(safe_terms)
    links = {}
    if keywords_str:
        links["Califica"] = f"https://califica.ai/?s={keywords_str}"
        links["Wordwall"] = f"https://wordwall.net/es-ar/community/{keywords_str}"
        links["Educaplay"] = f"https://es.educaplay.com/recursos-educativos/?q={keywords_str}"
        links["Liveworksheets"] = f"https://es.liveworksheets.com/worksheets/search/{keywords_str}"
        links["YouTube"] = f"https://www.youtube.com/results?search_query={keywords_str}"
    return links

def create_docx_from_parsed(parsed_list: List[Dict[str,Any]], asignatura: str, grado: str, edad: Any, tema_insercion: str) -> BytesIO:
    doc = Document()
    doc.add_heading("Plan de Clase", level=1)
    doc.add_paragraph(f"Asignatura: {asignatura} | Grado: {grado} | Edad: {edad} | Tema de Inserción: {tema_insercion}")
    table = doc.add_table(rows=1, cols=5)
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text, hdr[4].text = (
        "Destreza", "Indicador", "Orientaciones (3 momentos)", "Recursos (físicos)", "Evaluación"
    )
    for item in parsed_list:
        row = table.add_row().cells
        row[0].text = str(item.get("destreza",""))
        row[1].text = str(item.get("indicador",""))
        orient = item.get("orientaciones",{}) or {}
        parts = []
        if orient.get("anticipacion"):
            parts.append("ANTICIPACIÓN:")
            for a in orient.get("anticipacion", []):
                parts.append(f"- {a}")
            if orient.get("anticipacion_keywords"):
                links = generate_search_links(orient.get("anticipacion_keywords", []))
                for k,v in links.items():
                    parts.append(f"{k}: {v}")
        if orient.get("construccion"):
            parts.append("CONSTRUCCIÓN:")
            c = orient["construccion"]
            for a in c.get("actividades", []):
                parts.append(f"- {a}")
            if c.get("dua"):
                parts.append("Actividades DUA:")
                for d in c.get("dua", []):
                    parts.append(f"- {d}")
            if c.get("palabras_clave"):
                links = generate_search_links(c.get("palabras_clave", []))
                for k,v in links.items():
                    parts.append(f"{k}: {v}")
        if orient.get("consolidacion"):
            parts.append("CONSOLIDACIÓN:")
            for a in orient.get("consolidacion", []):
                parts.append(f"- {a}")
            if orient.get("consolidacion_keywords"):
                links = generate_search_links(orient.get("consolidacion_keywords", []))
                for k,v in links.items():
                    parts.append(f"{k}: {v}")
        row[2].text = "\n".join(parts)
        recursos = item.get("recursos",[])
        row[3].text = ", ".join(map(str, recursos)) if isinstance(recursos, list) else str(recursos)
        evals = item.get("evaluacion",[])
        if isinstance(evals, list):
            row[4].text = "\n".join(evals)
        else:
            row[4].text = str(evals)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# -------------------------
# Llamada al modelo
# -------------------------
def call_model(prompt_text: str, max_tokens: int = 2000, temperature: float = 0.2) -> str:
    if _has_gemini:
        return gemini_client.call_gemini(prompt_text, max_tokens=max_tokens, temperature=temperature)
    if OPENAI_API_KEY:
        import openai
        openai.api_key = OPENAI_API_KEY
        resp = openai.ChatCompletion.create(
            model=model_name,
            messages=[
                {"role":"system","content":"Eres un experto en planificación de clases. Responde SOLO con JSON válido."},
                {"role":"user","content":prompt_text}
            ],
            max_tokens=int(max_tokens),
            temperature=float(temperature)
        )
        return resp["choices"][0]["message"]["content"]
    raise RuntimeError("No hay integración: añade gemini_client.py o configura OPENAI_API_KEY.")

# -------------------------
# Prompt
# -------------------------
def build_prompt(asignatura: str, grado: str, edad: Any, tema_insercion: str, destrezas_list: List[Dict[str,str]]) -> str:
    instructions = (
        "Eres un experto en diseño curricular y planificación educativa.\n\n"
        "Genera un plan de clase completo en formato JSON válido. Responde únicamente con un array JSON sin texto adicional.\n\n"
        "Cada objeto debe contener:\n"
        "- destreza\n"
        "- indicador\n"
        "- orientaciones (anticipacion, anticipacion_keywords, construccion con actividades y dua y palabras_clave, consolidacion, consolidacion_keywords)\n"
        "- recursos (lista)\n"
        "- evaluacion (lista)\n\n"
        "Reglas:\n"
        "- Las actividades deben empezar con verbos en infinitivo.\n"
        "- Cada momento (anticipacion, construccion, consolidacion) debe tener al menos 1 palabra clave para recursos online gratuitos (preferir Califica).\n"
        "- NO inventar links, solo palabras clave. La app construirá los enlaces.\n\n"
        f"Asignatura: {asignatura}\nGrado: {grado}\nEdad: {edad}\nTema de Inserción: {tema_insercion}\nDestrezas: {json.dumps(destrezas_list, ensure_ascii=False)}"
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
            st.rerun()   # ✅ corregido

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
        resp = str(resp).encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
        st.session_state["plan_raw"] = resp
        try:
            json_text = extract_first_json(resp)
            parsed = json.loads(json_text)
        except Exception as e:
            st.session_state["last_error"] = f"No se pudo parsear JSON: {e}"
            return
        if isinstance(parsed, list):
            st.session_state["plan_parsed"] = parsed
            st.session_state["doc_bytes"] = create_docx_from_parsed(parsed, asig, grad, edad_val, tema).getvalue()
            st.success("✅ Plan generado.")
        else:
            st.session_state["last_error"] = "El modelo no devolvió una lista JSON válida."
    except Exception as e:
        st.session_state["last_error"] = str(e)

st.button("📝 Generar Plan de Clase", on_click=generar_plan_callback)

if st.session_state.get("last_error"):
    st.error(st.session_state["last_error"])

if st.session_state.get("plan_raw"):
    with st.expander("Ver salida bruta (JSON crudo)"):
        st.code(st.session_state["plan_raw"], language="json")

if st.session_state.get("doc_bytes"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "💾 Exportar a Word",
        data=st.session_state["doc_bytes"],
        file_name=f"plan_{ts}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

if st.button("🔄 Nuevo"):
    for k, v in defaults.items():
        st.session_state[k] = v
    st.rerun()   # ✅ corregido

if debug_mode:
    st.sidebar.subheader("DEBUG session_state")
    import pprint
    st.sidebar.text(pprint.pformat(dict(st.session_state)))
