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

st.markdown("Aplicación para generar planificaciones por destreza. Ahora con recursos online reales, actualizados y verificados.")

# -------------------------
# Función para obtener la clave API de Gemini
# -------------------------
def get_api_key(api_key_input):
    if api_key_input:
        return api_key_input
    env = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env:
        return env
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return None

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
    "last_error": "",
    "api_key_input": "" # Se añade para inicializar el input de la barra lateral
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -------------------------
# Sidebar - Configuración API / Modelo
# -------------------------
st.sidebar.header("Configuración API / Modelo")
api_key_input = st.sidebar.text_input("Gemini API Key (o usa st.secrets)", 
                                      type="password", 
                                      key="api_key_input_sidebar")
model_name = st.sidebar.text_input("Modelo Gemini (ej: gemini-2.5-flash)", value="gemini-2.5-flash") 
max_tokens = st.sidebar.number_input("Max tokens", value=2800, step=100)
temperature = st.sidebar.slider("Temperatura", 0.0, 1.0, 0.3)
debug_mode = st.sidebar.checkbox("Mostrar debug (session_state)", value=False)

GEMINI_API_KEY = get_api_key(st.session_state["api_key_input_sidebar"])

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
# Integración con Perplexity AI (Se mantiene la lógica para buscar recursos)
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
                titulo = link_tag.text.strip() or f"Recurso en {link_tag.find_parent('div').find_parent('div').text.split('...')[0].strip()[:50]}"
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
        raise RuntimeError("La clave API de Gemini no está configurada. Por favor, ingrésala en la barra lateral.")
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        config = genai.types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=[
                {"role": "user", "parts": [{"text": prompt_text}]}
            ],
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
        "📘 **PLAN DE CLASE**\n\n"
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
        "- Actividades que activen conocimientos previos (todas empiezan con verbos en infinitivo).\n"
        "- Sugiere una idea de recurso online que podría usarse en la anticipación. Escribe su descripción entre el marcador **[RECURSO SUGERIDO: ...].**\n\n"
        "### CONSTRUCCIÓN\n"
        "- Al menos 6 actividades en secuencia pedagógica (todas con verbos en infinitivo).\n"
        "- Incluir actividades DUA (Diseño Universal de Aprendizaje).\n"
        "- Sugiere dos ideas de recursos online, cada una con el marcador **[RECURSO SUGERIDO: ...]**.\n\n"
        "### CONSOLIDACIÓN\n"
        "- Actividades para aplicar lo aprendido y reforzar conocimientos.\n"
        "- Sugiere una idea de recurso online, con el marcador **[RECURSO SUGERIDO: ...]**.\n\n"
        "### RECURSOS\n"
        "- Listar recursos físicos y tecnológicos (pizarra, cuaderno, proyector, etc.)\n"
        "- **NO LISTES AQUÍ LOS RECURSOS ONLINE. SOLO LOS FÍSICOS.**\n\n"
        "### ORIENTACIONES PARA LA EVALUACIÓN\n"
        "- Actividades de evaluación en relación con el indicador.\n"
        "- Incluir orientaciones DUA para la evaluación.\n\n"
        "IMPORTANTE:\n"
        "- Usa títulos en mayúsculas para los momentos (ANTICIPACIÓN, CONSTRUCCIÓN, CONSOLIDACIÓN).\n"
        "- Devuelve solo TEXTO bien estructurado, no JSON ni código.\n"
    )
    return instructions

# -------------------------
# Interfaz - Datos básicos (Aseguramos su visibilidad)
# -------------------------
st.subheader("Datos básicos")
c1, c2 = st.columns(2)
with c1:
    # Aseguramos que los valores iniciales provengan de session_state
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
# Lógica de Generación del plan
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
        # PASO 1: Generar el plan con la IA
        with st.spinner("Generando estructura del plan con Gemini..."):
            prompt = build_prompt(asig, grad, edad_val, tema, dests)
            resp = call_model(prompt, max_tokens=max_tokens, temperature=temperature)
        
        # PASO 2: Extraer las sugerencias de recursos
        sugerencias = re.findall(r'\[RECURSO SUGERIDO: (.*?)\]', resp)
        
        # PASO 3: Buscar enlaces para cada sugerencia y reemplazar en el texto
        with st.spinner("Buscando recursos online reales (Perplexity AI)..."):
            for sugerencia in sugerencias:
                tema_recurso = sugerencia.strip()
                
                sugerencia_lower = tema_recurso.lower()
                sitios = {
                    'video': 'youtube.com',
                    'actividad de wordwall': 'wordwall.net',
                    'quiz': 'educaplay.com',
                    'interactiva': 'liveworksheets.com',
                    'genially': 'genial.ly'
                }
                sitio_preferido = None
                for tipo, dominio in sitios.items():
                    if tipo in sugerencia_lower:
                        sitio_preferido = dominio
                        break
                
                recursos_encontrados = buscar_recursos_perplexity(tema_recurso, sitio_preferido)
                
                if recursos_encontrados:
                    enlace_real = recursos_encontrados[0]['enlace']
                    titulo_recurso = recursos_encontrados[0]['titulo']
                    
                    resp = resp.replace(f"[RECURSO SUGERIDO: {sugerencia}]", f"[{titulo_recurso}]({enlace_real})", 1)
                else:
                    resp = resp.replace(f"[RECURSO SUGERIDO: {sugerencia}]", f"**[RECURSO NO ENCONTRADO: {sugerencia}]**", 1)

        st.session_state["plan_text"] = resp
        st.session_state["doc_bytes"] = create_docx_from_text(st.session_state["plan_text"]).getvalue()
        st.success("✅ Plan generado con recursos reales.")
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

# Nuevo / reiniciar
def reset_app():
    for k, v in defaults.items():
        st.session_state[k] = v
    # Preservar la clave API si fue ingresada manualmente
    if "api_key_input_sidebar" in st.session_state:
        st.session_state["api_key_input"] = st.session_state["api_key_input_sidebar"]
    st.rerun()

if st.button("🔄 Nuevo"):
    reset_app()

if debug_mode:
    st.sidebar.subheader("DEBUG session_state")
    import pprint
    st.sidebar.text(pprint.pformat(dict(st.session_state)))