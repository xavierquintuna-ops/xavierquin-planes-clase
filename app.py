# -*- coding: utf-8 -*-
"""
app.py - Generador de Plan de Clase (reescrito para evitar pérdida de inputs)
Guardar este archivo en UTF-8 (sin BOM).
"""

import streamlit as st
from io import BytesIO
from docx import Document
import json
import os
import time
import unicodedata
from typing import List, Dict, Any

# -------------------------
# Configuración de la página
# -------------------------
st.set_page_config(page_title="Generador de Plan de Clase", page_icon="📘", layout="wide")
st.title("📘 Generador Automático de Planes de Clase")

# -------------------------
# Sidebar: API / modelo
# -------------------------
st.sidebar.header("Configuración API / Modelo")
api_key_input = st.sidebar.text_input("OpenAI API Key (opcional, sólo si no usas Gemini)", type="password")
model_name = st.sidebar.text_input("Modelo OpenAI (ej: gpt-4o-mini) - fallback", value="gpt-4o-mini")
max_tokens = st.sidebar.number_input("Max tokens", value=1500, step=100)
temperature = st.sidebar.slider("Temperatura", 0.0, 1.0, 0.2)
debug_mode = st.sidebar.checkbox("Mostrar debug (valores guardados)", value=False)

def get_api_key():
    if api_key_input:
        return api_key_input
    env_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_APIKEY")
    if env_key:
        return env_key
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return None

OPENAI_API_KEY = get_api_key()

# -------------------------
# Intentar cargar gemini_client (no modificar su implementación)
# -------------------------
gemini_client = None
_has_gemini = False
try:
    import gemini_client  # si tienes este archivo en tu repo, será usado
    gemini_client = gemini_client
    _has_gemini = True
except Exception:
    _has_gemini = False

# -------------------------
# Inicializar session_state (campos con keys para persistencia)
# -------------------------
if "asignatura" not in st.session_state:
    st.session_state["asignatura"] = ""
if "grado" not in st.session_state:
    st.session_state["grado"] = ""
if "edad" not in st.session_state:
    st.session_state["edad"] = 12
if "tema_insercion" not in st.session_state:
    st.session_state["tema_insercion"] = ""
# inputs temporales para agregar destrezas
if "destreza_input" not in st.session_state:
    st.session_state["destreza_input"] = ""
if "indicador_input" not in st.session_state:
    st.session_state["indicador_input"] = ""
if "tema_estudio_input" not in st.session_state:
    st.session_state["tema_estudio_input"] = ""
# lista de destrezas
if "destrezas" not in st.session_state:
    st.session_state["destrezas"] = []
# outputs
if "plan_raw" not in st.session_state:
    st.session_state["plan_raw"] = None
if "plan_parsed" not in st.session_state:
    st.session_state["plan_parsed"] = None
if "doc_bytes" not in st.session_state:
    st.session_state["doc_bytes"] = None

# -------------------------
# Utilidades
# -------------------------
def normalize_text(s: str) -> str:
    if s is None:
        return ""
    return unicodedata.normalize("NFKC", str(s)).strip()

def extract_first_json(text: str) -> str:
    """Extrae el primer JSON (lista u objeto) del texto."""
    if not isinstance(text, str):
        raise ValueError("Texto no es cadena.")
    start = None
    for i, ch in enumerate(text):
        if ch in ('{', '['):
            start = i
            break
    if start is None:
        raise ValueError("No se encontró JSON en el texto.")
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
            if ch in ('{', '['):
                stack.append(ch)
            elif ch in ('}', ']'):
                if not stack:
                    raise ValueError("JSON mal formado.")
                stack.pop()
                if not stack:
                    return text[start:i+1]
    raise ValueError("No se pudo extraer JSON completo.")

def create_docx_from_parsed(parsed_list: List[Dict[str, Any]], asignatura: str, grado: str, edad: Any, tema_insercion: str) -> BytesIO:
    doc = Document()
    doc.add_heading("Plan de Clase", level=1)
    doc.add_paragraph(f"Asignatura: {asignatura} | Grado: {grado} | Edad: {edad} | Tema de Inserción: {tema_insercion}")
    table = doc.add_table(rows=1, cols=5)
    hdr = table.rows[0].cells
    hdr[0].text = "Destreza"
    hdr[1].text = "Indicador"
    hdr[2].text = "Orientaciones"
    hdr[3].text = "Recursos (físicos)"
    hdr[4].text = "Evaluación"
    for item in parsed_list:
        row = table.add_row().cells
        row[0].text = str(item.get("destreza", ""))
        row[1].text = str(item.get("indicador", ""))
        orient = item.get("orientaciones", {}) or {}
        parts = []
        if isinstance(orient, dict):
            if orient.get("anticipacion"):
                parts.append("Anticipación: " + str(orient.get("anticipacion")))
            if orient.get("construccion"):
                parts.append("Construcción: " + str(orient.get("construccion")))
            if orient.get("construccion_transversal"):
                parts.append("Actividad transversal: " + str(orient.get("construccion_transversal")))
            if orient.get("consolidacion"):
                parts.append("Consolidación: " + str(orient.get("consolidacion")))
        row[2].text = "\n".join(parts)
        recursos = item.get("recursos", [])
        if isinstance(recursos, list):
            row[3].text = ", ".join(map(str, recursos))
        else:
            row[3].text = str(recursos)
        row[4].text = str(item.get("evaluacion", ""))
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# -------------------------
# Llamada al modelo (Gemini -> NO modificar la lógica interna del gemini_client)
# -------------------------
def call_model(prompt_text: str, max_tokens: int = 1500, temperature: float = 0.2) -> str:
    if _has_gemini and gemini_client:
        # Llamamos funciones comunes si existen (sin alterar gemini_client)
        for fn_name in ("call_gemini", "generate_with_gemini", "request_gemini", "generate", "call", "main", "run"):
            if hasattr(gemini_client, fn_name):
                fn = getattr(gemini_client, fn_name)
                try:
                    return fn(prompt_text, max_tokens=max_tokens, temperature=temperature)
                except TypeError:
                    # si la firma es diferente, llamamos sólo con prompt
                    return fn(prompt_text)
        raise RuntimeError("Se detectó gemini_client pero no contiene función invocable conocida.")
    # Fallback OpenAI
    if OPENAI_API_KEY:
        try:
            import openai
            openai.api_key = OPENAI_API_KEY
            resp = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "Eres un experto en planificación de clases. Responde SOLO con JSON válido."},
                    {"role": "user", "content": prompt_text}
                ],
                max_tokens=int(max_tokens),
                temperature=float(temperature)
            )
            return resp["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Error fallback OpenAI: {e}")
    raise RuntimeError("No hay integración disponible. Añade gemini_client.py o configura OPENAI_API_KEY.")

# -------------------------
# Prompt reforzado para forzar JSON
# -------------------------
def build_prompt(asignatura: str, grado: str, edad: Any, tema_insercion: str, destrezas_list: List[Dict[str,str]]) -> str:
    instructions = (
        "RESPONDE ÚNICAMENTE CON UN ARRAY JSON. Cada elemento es una destreza con las claves: "
        "'destreza','indicador','orientaciones','recursos','evaluacion'. "
        "La clave 'orientaciones' debe tener subclaves: 'anticipacion','construccion','construccion_transversal','consolidacion'. "
        f"EN 'construccion_transversal' incluye UNA actividad relacionada con el Tema de Inserción: {tema_insercion}. "
        "NO uses tablas, NO uses HTML, NO agregues texto explicativo. SOLO JSON válido."
    )
    payload = {
        "header": {"asignatura": asignatura, "grado": grado, "edad": edad, "tema_insercion": tema_insercion},
        "destrezas": destrezas_list,
        "instructions": instructions
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

# -------------------------
# Interfaz: Inputs (persistentes mediante 'key')
# -------------------------
st.subheader("Datos Básicos")
# Usamos keys para que Streamlit mantenga los valores entre reruns
asignatura = st.text_input("Asignatura", key="asignatura")
grado = st.text_input("Grado", key="grado")
edad = st.number_input("Edad de los estudiantes", min_value=3, max_value=99, value=st.session_state.get("edad",12), key="edad")
tema_insercion = st.text_input("Tema de Inserción (actividad transversal)", key="tema_insercion")

st.markdown("---")
st.subheader("Agregar Destreza e Indicador (añadir una por vez)")
dest_col1, dest_col2 = st.columns([2,1])
with dest_col1:
    st.text_area("Destreza (con criterio de desempeño)", key="destreza_input", height=120)
with dest_col2:
    st.text_area("Indicador de logro", key="indicador_input", height=120)
    st.text_input("Tema de estudio (opcional)", key="tema_estudio_input")

# Botón para agregar destreza
if st.button("➕ Agregar destreza"):
    d = normalize_text(st.session_state.get("destreza_input",""))
    i = normalize_text(st.session_state.get("indicador_input",""))
    t = normalize_text(st.session_state.get("tema_estudio_input",""))
    if not d or not i:
        st.warning("Por favor completa la destreza y el indicador antes de agregar.")
    else:
        st.session_state["destrezas"].append({"destreza": d, "indicador": i, "tema_estudio": t})
        # limpiar los campos de entrada para nueva destreza
        st.session_state["destreza_input"] = ""
        st.session_state["indicador_input"] = ""
        st.session_state["tema_estudio_input"] = ""
        st.success("Destreza agregada ✅")

# Mostrar destrezas añadidas
if st.session_state["destrezas"]:
    st.subheader("Destrezas añadidas")
    st.table(st.session_state["destrezas"])

# -------------------------
# Botón: Generar Plan
# -------------------------
def validar_campos(asig, grad, edad_val, tema, dests):
    faltantes = []
    if not asig or not str(asig).strip():
        faltantes.append("Asignatura")
    if not grad or not str(grad).strip():
        faltantes.append("Grado")
    if not tema or not str(tema).strip():
        faltantes.append("Tema de Inserción")
    if not dests or len(dests) == 0:
        faltantes.append("Al menos una destreza")
    return faltantes

if st.button("📑 Generar Plan de Clase"):
    # leemos SIEMPRE desde session_state (valores persistentes)
    asig = normalize_text(st.session_state.get("asignatura",""))
    grad = normalize_text(st.session_state.get("grado",""))
    edad_val = st.session_state.get("edad",12)
    tema = normalize_text(st.session_state.get("tema_insercion",""))
    dests = st.session_state.get("destrezas", [])
    faltantes = validar_campos(asig, grad, edad_val, tema, dests)
    if faltantes:
        st.error("Faltan campos obligatorios: " + ", ".join(faltantes))
    else:
        with st.spinner("Generando plan..."):
            try:
                prompt = build_prompt(asig, grad, edad_val, tema, dests)
                resp_text = call_model(prompt, max_tokens=max_tokens, temperature=temperature)
                # asegurar cadena utf-8
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
                    st.error(f"No se pudo parsear JSON: {e}")
                if parsed and isinstance(parsed, list):
                    st.session_state["plan_parsed"] = parsed
                    st.session_state["doc_bytes"] = create_docx_from_parsed(parsed, asig, grad, edad_val, tema).getvalue()
                    st.success("✅ Plan generado con éxito")
                else:
                    st.error("El modelo no devolvió un JSON válido.")
            except Exception as e:
                st.error(f"Error al generar plan: {e}")

# -------------------------
# Mostrar resultados y descarga
# -------------------------
if st.session_state.get("plan_parsed"):
    st.subheader("📋 Vista previa del Plan")
    st.table(st.session_state["plan_parsed"])

if st.session_state.get("plan_raw"):
    with st.expander("Ver JSON / salida bruta"):
        st.code(st.session_state["plan_raw"], language="json")

if st.session_state.get("doc_bytes"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="💾 Exportar a Word",
        data=st.session_state["doc_bytes"],
        file_name=f"plan_de_clase_{ts}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# Botón limpiar
if st.button("🔄 Nuevo (limpiar todo)"):
    # conservamos API key y debug, limpiamos lo demás
    keep_api = api_key_input
    keep_debug = debug_mode
    st.session_state.clear()
    # restaurar las claves necesarias en session_state para evitar KeyError
    st.session_state["asignatura"] = ""
    st.session_state["grado"] = ""
    st.session_state["edad"] = 12
    st.session_state["tema_insercion"] = ""
    st.session_state["destreza_input"] = ""
    st.session_state["indicador_input"] = ""
    st.session_state["tema_estudio_input"] = ""
    st.session_state["destrezas"] = []
    st.session_state["plan_raw"] = None
    st.session_state["plan_parsed"] = None
    st.session_state["doc_bytes"] = None
    # recargar la app
    st.experimental_rerun()

# -------------------------
# Debug (opcional)
# -------------------------
if debug_mode:
    st.sidebar.subheader("DEBUG: session_state")
    import pprint
    st.sidebar.text(pprint.pformat(dict(st.session_state)))
