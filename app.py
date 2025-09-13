# -*- coding: utf-8 -*-
"""
app.py - Generador de Plan de Clase (versi車n final con prompt adaptado)
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
# Configuraci車n de la p芍gina
# -------------------------
st.set_page_config(page_title="Xavierquin Plan de Clase", page_icon="??", layout="wide")
st.title("?? Xavierquin Plan de Clase")

st.image("https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExbmZyeWRwZmRlbGR3bGw0Z2I3aGFjNGg1emJ1bWd3azNxdnU1bGF6MyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/26AHOx46iHjG6P7jO/giphy.gif")

# -------------------------
# Sidebar
# -------------------------
st.sidebar.header("Configuraci車n API / Modelo")
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
# Inicializaci車n session_state
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
        raise ValueError("No se encontr車 JSON en el texto.")
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

# --- FUNCI車N para generar enlaces de b迆squeda ---
def generate_search_links(keywords: List[str]) -> Dict[str, str]:
    keywords_str = "+".join([normalize_text(k) for k in keywords])
    links = {}
    if keywords_str:
        links["enlace_wordwall"] = f"https://wordwall.net/es-ar/community/{keywords_str}"
        links["enlace_educaplay"] = f"https://es.educaplay.com/recursos-educativos/?q={keywords_str}"
        links["enlace_liveworksheets"] = f"https://es.liveworksheets.com/worksheets/search/{keywords_str}"
        links["enlace_youtube"] = f"https://www.youtube.com/results?search_query={keywords_str}"
    return links

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
            if orient.get("anticipacion"):
                parts.append("ANTICIPACI車N:\n" + "\n".join(orient["anticipacion"]))
            if orient.get("construccion"):
                c = orient["construccion"]
                parts.append("CONSTRUCCI車N:\n" + "\n".join(c.get("actividades", [])))
                if c.get("dua"):
                    parts.append("Actividades DUA:\n" + "\n".join(c["dua"]))
                gamificacion_keywords = c.get("palabras_clave", [])
                if gamificacion_keywords:
                    links = generate_search_links(gamificacion_keywords)
                    parts.append("\nRecursos online sugeridos:")
                    for k, v in links.items():
                        parts.append(f"?? {k}: {v}")
            if orient.get("consolidacion"):
                parts.append("CONSOLIDACI車N:\n" + "\n".join(orient["consolidacion"]))
        row[2].text = "\n".join(parts)
        recursos = item.get("recursos",[])
        row[3].text = ", ".join(map(str, recursos)) if isinstance(recursos, list) else str(recursos)
        row[4].text = "\n".join(item.get("evaluacion",[])) if isinstance(item.get("evaluacion",[]), list) else str(item.get("evaluacion",""))
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
                {"role":"system","content":"Eres un experto en planificaci車n de clases. Responde SOLO con JSON v芍lido."},
                {"role":"user","content":prompt_text}
            ],
            max_tokens=int(max_tokens),
            temperature=float(temperature)
        )
        return resp["choices"][0]["message"]["content"]
    
    raise RuntimeError("No hay integraci車n: a?ade gemini_client.py o configura OPENAI_API_KEY.")

# -------------------------
# Prompt adaptado
# -------------------------
def build_prompt(asignatura: str, grado: str, edad: Any, tema_insercion: str, destrezas_list: List[Dict[str,str]]) -> str:
    instructions = (
        "Eres un experto en dise?o curricular y planificaci車n educativa.\n\n"
        "Genera un plan de clase completo en formato JSON v芍lido. Responde 迆nicamente con un array JSON, sin texto extra.\n\n"
        "### Estructura JSON:\n"
        "Cada objeto del array representa una destreza y debe contener:\n"
        "- \"destreza\": (texto de la destreza)\n"
        "- \"indicador\": (texto del indicador)\n"
        "- \"orientaciones\": objeto con:\n"
        "   * \"anticipacion\": lista de actividades (cada una inicia con verbo en infinitivo)\n"
        "   * \"construccion\": objeto con:\n"
        "       - \"actividades\": lista de al menos 6 actividades (todas inician con verbo en infinitivo)\n"
        "       - \"dua\": lista de actividades inclusivas seg迆n el Dise?o Universal de Aprendizaje\n"
        "       - \"palabras_clave\": lista de palabras clave del tema para buscar recursos online\n"
        "   * \"consolidacion\": lista de actividades (cada una inicia con verbo en infinitivo)\n"
        "- \"recursos\": lista de recursos f赤sicos y digitales necesarios (pizarra, cuaderno, computador, proyector, etc.)\n"
        "- \"evaluacion\": lista de actividades de evaluaci車n relacionadas directamente con el indicador, incluyendo orientaciones DUA\n\n"
        "### Reglas:\n"
        "- Las secciones deben llevar los t赤tulos: ANTICIPACI車N, CONSTRUCCI車N y CONSOLIDACI車N (en may迆sculas).\n"
        "- Las actividades deben iniciar con verbos en infinitivo (-ar, -er, -ir).\n"
        "- Los recursos online no deben ser inventados; devuelve solo palabras clave en \"palabras_clave\" para generar enlaces.\n"
        "- Responde exclusivamente con JSON v芍lido, sin explicaciones.\n\n"
        f"Asignatura: {asignatura}\n"
        f"Grado: {grado}\n"
        f"Edad: {edad}\n"
        f"Tema de Inserci車n: {tema_insercion}\n"
        f"Destrezas: {json.dumps(destrezas_list, ensure_ascii=False, indent=2)}\n"
    )
    return instructions

# -------------------------
# Interfaz
# -------------------------
st.subheader("Datos b芍sicos")
c1, c2 = st.columns(2)
with c1:
    st.text_input("Asignatura", key="asignatura")
    st.text_input("Grado", key="grado")
with c2:
    st.number_input("Edad de los estudiantes", min_value=3, max_value=99, key="edad")
    st.text_input("Tema de Inserci車n (actividad transversal)", key="tema_insercion")

st.markdown("---")
st.subheader("Agregar destreza e indicador")

with st.form(key="form_add_destreza"):
    d = st.text_area("Destreza", key="form_destreza")
    i = st.text_area("Indicador de logro", key="form_indicador")
    t = st.text_input("Tema de estudio (opcional)", key="form_tema_estudio")
    submitted = st.form_submit_button("? Agregar destreza")

    if submitted:
        dd, ii, tt = normalize_text(d), normalize_text(i), normalize_text(t)
        if not dd or not ii:
            st.warning("Completa la destreza y el indicador antes de agregar.")
        else:
            st.session_state["destrezas"].append({"destreza": dd, "indicador": ii, "tema_estudio": tt})
            st.success("Destreza agregada ?")
            st.rerun()

if st.session_state["destrezas"]:
    st.subheader("Destrezas a?adidas")
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
            st.success("? Plan generado. Despl芍cese hacia abajo para ver el resultado.")
        else:
            st.session_state["last_error"] = "El modelo no devolvi車 una lista JSON v芍lida."
    except Exception as e:
        st.session_state["last_error"] = str(e)

st.button("?? Generar Plan de Clase", on_click=generar_plan_callback)

if st.session_state.get("last_error"):
    st.error(st.session_state["last_error"])

if st.session_state.get("plan_parsed"):
    st.markdown("---")
    st.subheader("?? Vista previa del Plan")

    for item in st.session_state["plan_parsed"]:
        st.markdown(f"#### **Destreza:** {item.get('destreza', '')}")
        st.markdown(f"**Indicador:** {item.get('indicador', '')}")
        st.markdown(f"**Evaluaci車n:** {'; '.join(item.get('evaluacion', []))}")
        st.markdown(f"**Recursos F赤sicos:** {', '.join(item.get('recursos', []))}")
        
        st.markdown("---")
        st.markdown("### **ORIENTACIONES METODOL車GICAS**")
        
        orientaciones = item.get("orientaciones", {})
        
        if "anticipacion" in orientaciones:
            st.markdown("#### **ANTICIPACI車N**")
            st.markdown("\n".join(orientaciones["anticipacion"]))

        if "construccion" in orientaciones:
            st.markdown("#### **CONSTRUCCI車N**")
            construccion = orientaciones["construccion"]
            st.markdown("\n".join(construccion.get("actividades", [])))
            
            if construccion.get("dua"):
                st.markdown("**Actividades DUA:**")
                st.markdown("\n".join(construccion["dua"]))
            
            gamificacion_keywords = construccion.get("palabras_clave", [])
            if gamificacion_keywords:
                links = generate_search_links(gamificacion_keywords)
                st.markdown("**Recursos online (haz clic):**")
                for name, url in links.items():
                    st.markdown(f"?? [{name}]({url})")

        if "consolidacion" in orientaciones:
            st.markdown("#### **CONSOLIDACI車N**")
            st.markdown("\n".join(orientaciones["consolidacion"]))

    st.markdown("---")

if st.session_state.get("plan_raw"):
    with st.expander("Ver salida bruta (solo para depuraci車n)"):
        st.code(st.session_state["plan_raw"], language="json")

if st.session_state.get("doc_bytes"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "?? Exportar a Word",
        data=st.session_state["doc_bytes"],
        file_name=f"plan_{ts}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

if st.button("?? Nuevo"):
    for k, v in defaults.items():
        st.session_state[k] = v
    st.rerun()

if debug_mode:
    st.sidebar.subheader("DEBUG session_state")
    import pprint
    st.sidebar.text(pprint.pformat(dict(st.session_state)))
