# -*- coding: utf-8 -*-
"""
app.py - Versi車n robusta para asegurar que las destrezas se guarden correctamente.
Guardar en UTF-8 (sin BOM).
"""

import streamlit as st
from io import BytesIO
from docx import Document
import json, os, time, unicodedata
from typing import List, Dict, Any

# --- P芍gina ---
st.set_page_config(page_title="Generador de Plan de Clase", page_icon="??", layout="wide")
st.title("?? Generador Autom芍tico de Planes de Clase 〞 (versi車n robusta)")

# --- Sidebar / configuraci車n ---
st.sidebar.header("Configuraci車n API / Modelo")
api_key_input = st.sidebar.text_input("OpenAI API Key (opcional, si no usas Gemini)", type="password")
model_name = st.sidebar.text_input("Modelo OpenAI (ej: gpt-4o-mini) - fallback", value="gpt-4o-mini")
max_tokens = st.sidebar.number_input("Max tokens", value=1500, step=100)
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

# --- Intento de carga gemini_client (no modificar su l車gica) ---
gemini_client = None
_has_gemini = False
try:
    import gemini_client
    gemini_client = gemini_client
    _has_gemini = True
except Exception:
    _has_gemini = False

# --- Inicializar session_state de forma segura ---
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
    "generating": False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Utilidades ---
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
        raise ValueError("No se encontr車 JSON en el texto.")
    stack = []
    in_string = False
    escape = False
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

def create_docx_from_parsed(parsed_list: List[Dict[str,Any]], asignatura: str, grado: str, edad: Any, tema_insercion: str) -> BytesIO:
    doc = Document()
    doc.add_heading("Plan de Clase", level=1)
    doc.add_paragraph(f"Asignatura: {asignatura} | Grado: {grado} | Edad: {edad} | Tema de Inserci車n: {tema_insercion}")
    table = doc.add_table(rows=1, cols=5)
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text, hdr[4].text = (
        "Destreza", "Indicador", "Orientaciones", "Recursos (f赤sicos)", "Evaluaci車n"
    )
    for item in parsed_list:
        row = table.add_row().cells
        row[0].text = str(item.get("destreza",""))
        row[1].text = str(item.get("indicador",""))
        orient = item.get("orientaciones",{}) or {}
        parts = []
        if isinstance(orient, dict):
            if orient.get("anticipacion"): parts.append("Anticipaci車n: " + str(orient["anticipacion"]))
            if orient.get("construccion"): parts.append("Construcci車n: " + str(orient["construccion"]))
            if orient.get("construccion_transversal"): parts.append("Actividad transversal: " + str(orient["construccion_transversal"]))
            if orient.get("consolidacion"): parts.append("Consolidaci車n: " + str(orient["consolidacion"]))
        row[2].text = "\n".join(parts)
        recursos = item.get("recursos",[])
        row[3].text = ", ".join(map(str, recursos)) if isinstance(recursos, list) else str(recursos)
        row[4].text = str(item.get("evaluacion",""))
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- Llamar modelo: usa gemini_client si existe (sin modificar su c車digo), si no OpenAI ---
def call_model(prompt_text: str, max_tokens: int = 1500, temperature: float = 0.2) -> str:
    if _has_gemini and gemini_client:
        for name in ("call_gemini","generate_with_gemini","request_gemini","generate","call","main","run"):
            if hasattr(gemini_client, name):
                fn = getattr(gemini_client, name)
                try:
                    return fn(prompt_text, max_tokens=max_tokens, temperature=temperature)
                except TypeError:
                    return fn(prompt_text)
        raise RuntimeError("gemini_client presente pero sin funci車n invocable conocida.")
    if OPENAI_API_KEY:
        try:
            import openai
            openai.api_key = OPENAI_API_KEY
            resp = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {"role":"system","content":"Eres un experto en planificaci車n de clases. Responde SOLO con JSON v芍lido."},
                    {"role":"user","content":prompt_text}
                ],
                max_tokens=int(max_tokens),
                temperature=float(temperature)
            )
            return resp["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Fallback OpenAI fall車: {e}")
    raise RuntimeError("No hay integraci車n de modelo: a?ade gemini_client.py o configura OPENAI_API_KEY.")

# --- Prompt reforzado para forzar JSON limpio ---
def build_prompt(asignatura: str, grado: str, edad: Any, tema_insercion: str, destrezas_list: List[Dict[str,str]]) -> str:
    instructions = (
        "RESPONDE 迆NICAMENTE CON UN ARRAY JSON. Cada elemento es una destreza con las claves EXACTAS: "
        "'destreza','indicador','orientaciones','recursos','evaluacion'. "
        "La subclave 'orientaciones' debe contener: 'anticipacion','construccion','construccion_transversal','consolidacion'. "
        f"En 'construccion_transversal' incluye UNA actividad relacionada con el Tema de Inserci車n: {tema_insercion}. "
        "NO uses tablas ni HTML ni texto adicional. SOLO JSON v芍lido."
    )
    payload = {"header":{"asignatura":asignatura,"grado":grado,"edad":edad,"tema_insercion":tema_insercion},
               "destrezas":destrezas_list,"instructions":instructions}
    return json.dumps(payload, ensure_ascii=False, indent=2)

# -------------------------------------------------
# INTERFAZ
# -------------------------------------------------
st.subheader("Datos b芍sicos")
left, right = st.columns(2)
with left:
    st.text_input("Asignatura", key="asignatura")
    st.text_input("Grado", key="grado")
with right:
    st.number_input("Edad de los estudiantes", min_value=3, max_value=99, key="edad")
    st.text_input("Tema de Inserci車n (actividad transversal)", key="tema_insercion")

st.markdown("---")
st.subheader("Agregar una destreza (formulario)")

with st.form(key="form_add_destreza"):
    d = st.text_area("Destreza (con criterio de desempe?o)", key="form_destreza")
    i = st.text_area("Indicador de logro", key="form_indicador")
    t = st.text_input("Tema de estudio (opcional)", key="form_tema_estudio")
    submitted = st.form_submit_button("? Agregar destreza")
    if submitted:
        dd = normalize_text(st.session_state.get("form_destreza",""))
        ii = normalize_text(st.session_state.get("form_indicador",""))
        tt = normalize_text(st.session_state.get("form_tema_estudio",""))
        if not dd or not ii:
            st.warning("Completa la destreza y el indicador antes de agregar.")
        else:
            st.session_state["destrezas"].append({"destreza": dd, "indicador": ii, "tema_estudio": tt})
            # limpiar campos del form
            st.session_state["form_destreza"] = ""
            st.session_state["form_indicador"] = ""
            st.session_state["form_tema_estudio"] = ""
            st.success("Destreza agregada ?")
            # Forzar rerun para que la tabla aparezca inmediatamente
            st.experimental_rerun()

# Mostrar n迆mero de destrezas y la tabla
st.markdown(f"**Destrezas a?adidas:** {len(st.session_state['destrezas'])}")
if st.session_state["destrezas"]:
    st.table(st.session_state["destrezas"])

# Mostramos error previo si lo hay
if st.session_state.get("last_error"):
    st.error(st.session_state["last_error"])

# -------------------------------------------------
# Generar plan: usamos callback al hacer click para evitar race conditions
# -------------------------------------------------
def generar_plan_callback():
    st.session_state["last_error"] = ""
    asig = normalize_text(st.session_state.get("asignatura",""))
    grad = normalize_text(st.session_state.get("grado",""))
    edad_val = st.session_state.get("edad",12)
    tema = normalize_text(st.session_state.get("tema_insercion",""))
    dests = st.session_state.get("destrezas", [])
    faltantes = []
    if not asig: faltantes.append("Asignatura")
    if not grad: faltantes.append("Grado")
    if not tema: faltantes.append("Tema de Inserci車n")
    if not dests or len(dests)==0: faltantes.append("Al menos una destreza")
    if faltantes:
        st.session_state["last_error"] = "Faltan campos obligatorios: " + ", ".join(faltantes)
        return
    # construimos prompt y llamamos al modelo
    st.session_state["generating"] = True
    try:
        prompt = build_prompt(asig, grad, edad_val, tema, dests)
        resp_text = call_model(prompt, max_tokens=max_tokens, temperature=temperature)
        if isinstance(resp_text, bytes):
            resp_text = resp_text.decode("utf-8", errors="ignore")
        else:
            resp_text = str(resp_text)
        resp_text = resp_text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
        st.session_state["plan_raw"] = resp_text
        # extraer JSON
        try:
            json_text = extract_first_json(resp_text)
            parsed = json.loads(json_text)
        except Exception as e:
            parsed = None
            st.session_state["last_error"] = "No se pudo parsear JSON: " + str(e)
            st.session_state["generating"] = False
            return
        if parsed and isinstance(parsed, list):
            st.session_state["plan_parsed"] = parsed
            st.session_state["doc_bytes"] = create_docx_from_parsed(parsed, asig, grad, edad_val, tema).getvalue()
            st.session_state["generating"] = False
        else:
            st.session_state["last_error"] = "El modelo no devolvi車 una lista JSON v芍lida."
            st.session_state["generating"] = False
    except Exception as e:
        st.session_state["last_error"] = "Error generando plan: " + str(e)
        st.session_state["generating"] = False

st.button("?? Generar Plan de Clase", on_click=generar_plan_callback)

# Mostrar progreso / resultado
if st.session_state.get("generating"):
    st.info("Generando plan... espera unos segundos.")

if st.session_state.get("plan_parsed"):
    st.subheader("?? Vista previa del Plan")
    st.table(st.session_state["plan_parsed"])

if st.session_state.get("plan_raw"):
    with st.expander("Ver salida bruta (raw)"):
        st.code(st.session_state["plan_raw"], language="json")

if st.session_state.get("doc_bytes"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    st.download_button(label="?? Exportar a Word", data=st.session_state["doc_bytes"],
                       file_name=f"plan_de_clase_{ts}.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# Bot車n limpiar
if st.button("?? Nuevo (limpiar todo)"):
    for k in list(st.session_state.keys()):
        if k in defaults:
            st.session_state[k] = defaults[k]
    st.experimental_rerun()

# Debug
if debug_mode:
    st.sidebar.subheader("DEBUG session_state")
    import pprint
    st.sidebar.text(pprint.pformat(dict(st.session_state)))
