# app.py
import streamlit as st
from io import BytesIO
from docx import Document
import json, os, time

# Intento cliente moderno de OpenAI, con fallback al cliente cl芍sico
try:
    from openai import OpenAI as OpenAIClientModern
    modern_openai_available = True
except Exception:
    modern_openai_available = False
    try:
        import openai as openai_classic
    except Exception:
        openai_classic = None

st.set_page_config(page_title="Generador de Plan de Clase", page_icon="??", layout="wide")
st.title("?? Generador Autom芍tico de Planes de Clase")

# --- Sidebar: OpenAI setup ---
st.sidebar.header("OpenAI / Configuraci車n")
api_key_input = st.sidebar.text_input("OpenAI API Key (pegar aqu赤, opcional)", type="password")
model_name = st.sidebar.text_input("Modelo (ej: gpt-4o-mini)", value="gpt-4o-mini")
max_tokens = st.sidebar.number_input("Max tokens (OpenAI)", value=1500, step=100)
temperature = st.sidebar.slider("Temperatura", 0.0, 1.0, 0.2)

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

if not OPENAI_API_KEY:
    st.sidebar.warning("No se detect車 OpenAI API Key. P谷gala arriba o configura STREAMLIT secrets / variable de entorno.")

# --- Session state init ---
if "destrezas" not in st.session_state:
    st.session_state["destrezas"] = []
if "plan_raw" not in st.session_state:
    st.session_state["plan_raw"] = None
if "plan_parsed" not in st.session_state:
    st.session_state["plan_parsed"] = None
if "doc_bytes" not in st.session_state:
    st.session_state["doc_bytes"] = None

# --- Datos b芍sicos ---
st.subheader("Datos B芍sicos")
col1, col2 = st.columns(2)
with col1:
    asignatura = st.text_input("Asignatura")
    grado = st.text_input("Grado")
with col2:
    edad = st.number_input("Edad de los estudiantes", min_value=3, max_value=99, value=12)
    tema_insercion = st.text_input("Tema de Inserci車n (actividad transversal)")

# --- Datos pedag車gicos ---
st.subheader("Agregar Destreza e Indicador")
d_col1, d_col2 = st.columns([2,2])
with d_col1:
    destreza_input = st.text_area("Destreza con criterio de desempe?o", height=120)
with d_col2:
    indicador_input = st.text_area("Indicador de logro", height=120)
    tema_estudio_input = st.text_input("Tema de estudio (opcional)")

if st.button("? Agregar destreza"):
    if destreza_input.strip() and indicador_input.strip():
        st.session_state["destrezas"].append({
            "destreza": destreza_input.strip(),
            "indicador": indicador_input.strip(),
            "tema_estudio": tema_estudio_input.strip()
        })
        st.success("Destreza agregada ?")
        st.experimental_rerun()
    else:
        st.warning("Por favor completa la destreza y el indicador antes de agregar.")

if st.session_state["destrezas"]:
    st.subheader("Destrezas a?adidas")
    st.write(st.session_state["destrezas"])

# --- Funciones de ayuda ---
def extract_first_json(text: str):
    start = None
    for i, ch in enumerate(text):
        if ch in ['{', '[']:
            start = i
            break
    if start is None:
        raise ValueError("No se encontr車 JSON en el texto.")
    stack, in_string, escape = [], False, False
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '"' and not escape:
            in_string = not in_string
        if ch == '\\' and not escape:
            escape = True
        else:
            escape = False
        if not in_string:
            if ch in ['{', '[']:
                stack.append(ch)
            elif ch in ['}', ']']:
                opening = stack.pop()
                if not stack:
                    return text[start:i+1]
    raise ValueError("No se pudo extraer JSON.")

def call_openai_chat(prompt_text: str):
    if not OPENAI_API_KEY:
        raise RuntimeError("API Key no configurada.")
    messages = [
        {"role": "system", "content": "Eres un agente experto en planificaci車n de clases educativas. Responde SOLO con JSON v芍lido."},
        {"role": "user", "content": prompt_text}
    ]
    if modern_openai_available:
        try:
            client = OpenAIClientModern(api_key=OPENAI_API_KEY)
            resp = client.chat.completions.create(model=model_name, messages=messages, max_tokens=int(max_tokens), temperature=float(temperature))
            return resp.choices[0].message["content"]
        except Exception:
            pass
    openai_classic.api_key = OPENAI_API_KEY
    resp = openai_classic.ChatCompletion.create(model=model_name, messages=messages, max_tokens=int(max_tokens), temperature=float(temperature))
    return resp["choices"][0]["message"]["content"]

def build_prompt(asignatura, grado, edad, tema_insercion, destrezas_list):
    instructions = (
        "Genera un array JSON. Cada elemento = una destreza. "
        "Claves: 'destreza','indicador','orientaciones','recursos','evaluacion'. "
        "orientaciones = {'anticipacion','construccion','construccion_transversal','consolidacion'}. "
        "Incluye actividad transversal en 'construccion_transversal'. "
        "Usa verbos en infinitivo. Recursos online en orientaciones, f赤sicos en 'recursos'. "
        "Respuesta SOLO JSON v芍lido."
    )

    header = {"asignatura": asignatura, "grado": grado, "edad": edad, "tema_insercion": tema_insercion}
    payload = {"header": header, "destrezas": destrezas_list, "instructions": instructions}

    example_output = [
        {
            "destreza": "Identificar ideas principales en un texto narrativo",
            "indicador": "Resume un texto narrativo identificando la idea principal",
            "orientaciones": {
                "anticipacion": "Activar conocimientos previos preguntando sobre historias conocidas.",
                "construccion": "Analizar un cuento breve aplicando t谷cnicas de subrayado.",
                "construccion_transversal": "Relacionar el texto con el Tema de Inserci車n: Medio ambiente.",
                "consolidacion": "Elaborar un resumen escrito con la idea principal."
            },
            "recursos": ["pizarra","cuaderno","marcadores"],
            "evaluacion": "Elaboraci車n de un resumen identificando la idea principal"
        }
    ]

    prompt = (
        "Debes devolver SOLO JSON v芍lido. Datos de entrada:\n\n"
        + json.dumps(payload, ensure_ascii=True, indent=2)
        + "\n\nEjemplo de salida:\n"
        + json.dumps(example_output, ensure_ascii=True, indent=2)
    )
    return prompt

def create_docx_from_parsed(parsed_list, asignatura, grado, edad, tema_insercion):
    doc = Document()
    doc.add_heading("Plan de Clase", level=1)
    doc.add_paragraph(f"Asignatura: {asignatura} | Grado: {grado} | Edad: {edad} | Tema de Inserci車n: {tema_insercion}")
    table = doc.add_table(rows=1, cols=5)
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text, hdr[4].text = (
        "Destreza","Indicador","Orientaciones metodol車gicas","Recursos (f赤sicos)","Evaluaci車n"
    )
    for item in parsed_list:
        row = table.add_row().cells
        row[0].text = str(item.get("destreza",""))
        row[1].text = str(item.get("indicador",""))
        orient = item.get("orientaciones",{})
        parts = []
        if isinstance(orient, dict):
            if orient.get("anticipacion"): parts.append("Anticipaci車n: "+str(orient["anticipacion"]))
            if orient.get("construccion"): parts.append("Construcci車n: "+str(orient["construccion"]))
            if orient.get("construccion_transversal"): parts.append("Actividad transversal: "+str(orient["construccion_transversal"]))
            if orient.get("consolidacion"): parts.append("Consolidaci車n: "+str(orient["consolidacion"]))
        row[2].text = "\n".join(parts)
        row[3].text = ", ".join(item.get("recursos",[])) if isinstance(item.get("recursos"), list) else str(item.get("recursos",""))
        row[4].text = str(item.get("evaluacion",""))
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- Generar plan ---
if st.button("?? Generar Plan de Clase"):
    if not (asignatura and grado and edad and tema_insercion and st.session_state["destrezas"]):
        st.warning("Completa todos los campos y agrega al menos una destreza.")
    else:
        with st.spinner("Generando plan..."):
            try:
                prompt = build_prompt(asignatura, grado, edad, tema_insercion, st.session_state["destrezas"])
                response_text = call_openai_chat(prompt)

                # ?? Normalizar a UTF-8 v芍lido
                response_text = response_text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
                st.session_state["plan_raw"] = response_text

                try:
                    json_text = extract_first_json(response_text)
                    parsed = json.loads(json_text)
                except:
                    parsed = None

                if parsed and isinstance(parsed, list):
                    st.session_state["plan_parsed"] = parsed
                    buffer = create_docx_from_parsed(parsed, asignatura, grado, edad, tema_insercion)
                    st.session_state["doc_bytes"] = buffer.getvalue()
                    st.success("? Plan generado con 谷xito")
                else:
                    st.warning("No se pudo parsear JSON, exportando texto bruto.")
                    doc = Document()
                    doc.add_paragraph("Salida del modelo (bruta):")
                    doc.add_paragraph(response_text)
                    buf = BytesIO(); doc.save(buf); buf.seek(0)
                    st.session_state["doc_bytes"] = buf.getvalue()
            except Exception as e:
                st.error(f"Error: {e}")

# --- Mostrar preview y descarga ---
if st.session_state.get("plan_raw"):
    st.subheader("Preview (raw)")
    safe_raw = st.session_state["plan_raw"]
    if isinstance(safe_raw, bytes):
        safe_raw = safe_raw.decode("utf-8", errors="ignore")
    st.code(safe_raw, language="json")

if st.session_state.get("doc_bytes"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="?? Exportar a Word",
        data=st.session_state["doc_bytes"],
        file_name=f"plan_de_clase_{ts}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# --- Nuevo ---
if st.button("?? Nuevo"):
    st.session_state.clear()
    st.experimental_rerun()
