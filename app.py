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
    # small planning image (hosted remote). You can replace with a local image path if you add the file.
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
    """
    Recibe lista de palabras clave y devuelve enlaces de búsqueda en plataformas:
    - Califica (califica.ai) -> usa parámetro ?s=
    - Wordwall
    - Educaplay
    - Liveworksheets
    - YouTube
    """
    # normalizar y crear string de búsqueda
    safe_terms = []
    for k in keywords:
        k_norm = normalize_text(k)
        if k_norm:
            safe_terms.append(k_norm.replace(" ", "+"))
    keywords_str = "+".join(safe_terms)
    links = {}
    if keywords_str:
        # Califica usa búsqueda con '?s=' en su web pública
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
        # ANTICIPACIÓN
        if orient.get("anticipacion"):
            parts.append("ANTICIPACIÓN:")
            # each activity text
            for a in orient.get("anticipacion", []):
                parts.append(f"- {a}")
            # if moment has recursos_online keywords -> add links
            if orient.get("anticipacion_keywords"):
                links = generate_search_links(orient.get("anticipacion_keywords", []))
                parts.append("Recursos online sugeridos (ANTICIPACIÓN):")
                for k,v in links.items():
                    parts.append(f"{k}: {v}")
        # CONSTRUCCIÓN
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
                parts.append("Recursos online sugeridos (CONSTRUCCIÓN):")
                for k,v in links.items():
                    parts.append(f"{k}: {v}")
        # CONSOLIDACIÓN
        if orient.get("consolidacion"):
            parts.append("CONSOLIDACIÓN:")
            for a in orient.get("consolidacion", []):
                parts.append(f"- {a}")
            if orient.get("consolidacion_keywords"):
                links = generate_search_links(orient.get("consolidacion_keywords", []))
                parts.append("Recursos online sugeridos (CONSOLIDACIÓN):")
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
    """
    Si existe gemini_client lo usa; sino usa OpenAI ChatCompletion (si OPENAI_API_KEY está configurada).
    """
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
# Prompt altamente específico (califica.ai como referencia)
# -------------------------
def build_prompt(asignatura: str, grado: str, edad: Any, tema_insercion: str, destrezas_list: List[Dict[str,str]]) -> str:
    """
    El prompt exige:
    - JSON válido (lista)
    - Cada destreza tiene las claves: destreza, indicador, orientaciones, recursos, evaluacion
    - En orientaciones: ANTICIPACIÓN, CONSTRUCCIÓN (>=6 actividades + DUA) y CONSOLIDACIÓN
    - Cada momento debe incluir al menos un recurso online gratuito en español; devolver SOLO palabras clave (no URLs)
    - Preferir y sugerir Califica (califica.ai) como primera plataforma de búsqueda; incluir palabras clave que permitan búsquedas en Califica.
    - Las actividades deben comenzar con verbos en infinitivo.
    """
    instructions = (
        "Eres un experto en diseño curricular y planificación educativa.\n\n"
        "Genera un plan de clase completo EN ESPAÑOL en formato JSON válido. Responde únicamente con un array JSON SIN texto adicional.\n\n"
        "Estructura para cada objeto (cada destreza):\n"
        "  - \"destreza\": texto (provisto por el usuario)\n"
        "  - \"indicador\": texto (provisto por el usuario)\n"
        "  - \"orientaciones\": objeto con las siguientes claves:\n"
        "      * \"anticipacion\": lista de actividades (cada actividad debe iniciar con un verbo en infinitivo, ej. 'Plantear', 'Activar', 'Solicitar').\n"
        "      * \"anticipacion_keywords\": lista de palabras clave (mínimo 1) para buscar un recurso online gratuito en español preferentemente en Califica (ej. 'fracciones Califica 5 grado').\n"
        "      * \"construccion\": objeto que contenga:\n"
        "          - \"actividades\": lista de AL MENOS 6 actividades (todas inician con verbos en infinitivo).\n"
        "          - \"dua\": lista de AL MENOS 2 adaptaciones/actividades DUA (Diseño Universal del Aprendizaje).\n"
        "          - \"palabras_clave\": lista de palabras clave (mínimo 1) para buscar recursos online gratuitos en español (preferir Califica).\n"
        "      * \"construccion_transversal\": (opcional) texto breve si aplica.\n"
        "      * \"consolidacion\": lista de actividades (cada una inicia con verbo en infinitivo).\n"
        "      * \"consolidacion_keywords\": lista de palabras clave (mínimo 1) para buscar un recurso online gratuito en español.\n"
        "  - \"recursos\": lista de recursos físicos y tecnológicos necesarios (ej. 'pizarra', 'marcadores', 'computador', 'proyector', 'cuaderno').\n"
        "  - \"evaluacion\": lista de enunciados de lo que el estudiante será capaz de hacer (relacionado con el indicador) y orientaciones DUA para la evaluación.\n\n"
        "Reglas IMPORTANTES:\n"
        "- Todos los títulos de momentos deben aparecer: ANTICIPACIÓN, CONSTRUCCIÓN y CONSOLIDACIÓN (la app espera estos tres momentos).\n"
        "- Cada momento debe contener al menos UNA palabra clave para recursos online gratuitos en español.\n"
        "- NO DEVOLVER URLs en el JSON. Devuelve SOLO palabras clave para que la aplicación construya enlaces de búsqueda en Califica, Wordwall, Educaplay, Liveworksheets y YouTube.\n"
        "- Todas las actividades deben comenzar con verbos en infinitivo (terminados en -ar, -er, -ir).\n"
        "- Priorizar Califica (califica.ai) como repositorio de referencia; en las palabras clave incluya la palabra 'Califica' cuando sea apropiado (ej. 'fracciones Califica 5 grado').\n"
        "- Responder en ESPAÑOL y con JSON válido.\n\n"
        f"Datos del contexto:\nAsignatura: {asignatura}\nGrado: {grado}\nEdad: {edad}\nTema de Inserción: {tema_insercion}\nDestrezas (lista): {json.dumps(destrezas_list, ensure_ascii=False)}\n"
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

# show small image next to the form submit button area
with st.form(key="form_add_destreza"):
    d = st.text_area("Destreza", key="form_destreza", help="Ej: Resolver problemas de adición y sustracción con números naturales")
    i = st.text_area("Indicador de logro", key="form_indicador", help="Ej: Resolver operaciones de suma y resta con resultados correctos en contextos prácticos")
    t = st.text_input("Tema de estudio (opcional)", key="form_tema_estudio")
    submitted = st.form_submit_button("➕ Agregar destreza")
    if submitted:
        dd, ii, tt = normalize_text(d), normalize_text(i), normalize_text(t)
        if not dd or not ii:
            st.warning("Completa la destreza y el indicador antes de agregar.")
        else:
            st.session_state["destrezas"].append({"destreza": dd, "indicador": ii, "tema_estudio": tt})
            st.success("Destreza agregada ✅")
            st.experimental_rerun()

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
            st.success("✅ Plan generado. Desplácese hacia abajo para ver el resultado.")
        else:
            st.session_state["last_error"] = "El modelo no devolvió una lista JSON válida."
    except Exception as e:
        st.session_state["last_error"] = str(e)

# Show an image above the generate button
gen_col1, gen_col2 = st.columns([1, 6])
with gen_col1:
    st.image("https://img.icons8.com/fluency/48/000000/document--v1.png", width=48)
with gen_col2:
    st.button("📝 Generar Plan de Clase", on_click=generar_plan_callback)

if st.session_state.get("last_error"):
    st.error(st.session_state["last_error"])

# -------------------------
# Vista previa del Plan generado
# -------------------------
if st.session_state.get("plan_parsed"):
    st.markdown("---")
    st.subheader("📖 Vista previa del Plan")

    for item in st.session_state["plan_parsed"]:
        st.markdown(f"#### **Destreza:** {item.get('destreza', '')}")
        st.markdown(f"**Indicador:** {item.get('indicador', '')}")
        # Recursos físicos
        recursos_fisicos = item.get("recursos", [])
        if recursos_fisicos:
            st.markdown(f"**Recursos físicos y tecnológicos:** {', '.join(recursos_fisicos)}")
        # Evaluación
        evaluacion = item.get("evaluacion", [])
        if evaluacion:
            st.markdown("**Orientaciones para la evaluación (incluye DUA):**")
            if isinstance(evaluacion, list):
                for e in evaluacion:
                    st.markdown(f"- {e}")
            else:
                st.markdown(evaluacion)
        st.markdown("---")
        st.markdown("### **ORIENTACIONES METODOLÓGICAS**")
        orientaciones = item.get("orientaciones", {})

        # ANTICIPACIÓN
        if orientaciones.get("anticipacion"):
            st.markdown("#### **ANTICIPACIÓN**")
            for a in orientaciones.get("anticipacion", []):
                st.markdown(f"- {a}")
            # enlaces sugeridos para anticipación
            ak = orientaciones.get("anticipacion_keywords", [])
            if ak:
                links = generate_search_links(ak)
                st.markdown("**Recursos online sugeridos (ANTICIPACIÓN)**")
                for name, url in links.items():
                    st.markdown(f"- 🔗 [{name}]({url})")

        # CONSTRUCCIÓN
        if orientaciones.get("construccion"):
            st.markdown("#### **CONSTRUCCIÓN**")
            construccion = orientaciones["construccion"]
            for a in construccion.get("actividades", []):
                st.markdown(f"- {a}")
            # DUA
            if construccion.get("dua"):
                st.markdown("**Actividades DUA:**")
                for d in construccion.get("dua", []):
                    st.markdown(f"- {d}")
            # enlaces sugeridos para construccion
            pk = construccion.get("palabras_clave", [])
            if pk:
                links = generate_search_links(pk)
                st.markdown("**Recursos online sugeridos (CONSTRUCCIÓN)**")
                for name, url in links.items():
                    st.markdown(f"- 🔗 [{name}]({url})")

        # CONSOLIDACIÓN
        if orientaciones.get("consolidacion"):
            st.markdown("#### **CONSOLIDACIÓN**")
            for a in orientaciones.get("consolidacion", []):
                st.markdown(f"- {a}")
            ck = orientaciones.get("consolidacion_keywords", [])
            if ck:
                links = generate_search_links(ck)
                st.markdown("**Recursos online sugeridos (CONSOLIDACIÓN)**")
                for name, url in links.items():
                    st.markdown(f"- 🔗 [{name}]({url})")

    st.markdown("---")

# -------------------------
# Depuración y exportación
# -------------------------
if st.session_state.get("plan_raw"):
    with st.expander("Ver salida bruta (solo para depuración)"):
        st.code(st.session_state["plan_raw"], language="json")

if st.session_state.get("doc_bytes"):
    # image above the download button
    dl_col1, dl_col2 = st.columns([1, 6])
    with dl_col1:
        st.image("https://img.icons8.com/fluency/48/000000/download.png", width=48)
    with dl_col2:
        ts = time.strftime("%Y%m%d_%H%M%S")
        st.download_button(
            "💾 Exportar a Word",
            data=st.session_state["doc_bytes"],
            file_name=f"plan_{ts}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

# Nuevo / reiniciar
if st.button("🔄 Nuevo"):
    for k, v in defaults.items():
        st.session_state[k] = v
    st.experimental_rerun()

if debug_mode:
    st.sidebar.subheader("DEBUG session_state")
    import pprint
    st.sidebar.text(pprint.pformat(dict(st.session_state)))
