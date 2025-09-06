# app.py
import streamlit as st
from io import BytesIO
from docx import Document
import json, os, time, unicodedata

# --- Configuración página ---
st.set_page_config(page_title="Generador de Plan de Clase", page_icon="📘", layout="wide")
st.title("📘 Generador Automático de Planes de Clase")

# --- Sidebar: OpenAI setup ---
st.sidebar.header("OpenAI / Configuración")
api_key_input = st.sidebar.text_input("OpenAI API Key (pegar aquí, opcional)", type="password")
model_name = st.sidebar.text_input("Modelo (ej: gpt-4o-mini)", value="gpt-4o-mini")
max_tokens = st.sidebar.number_input("Max tokens (OpenAI)", value=1500, step=100)
temperature = st.sidebar.slider("Temperatura", 0.0, 1.0, 0.2)

# --- API Key helper ---
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
    st.sidebar.warning("No se detectó API Key. Pégala arriba o configúrala en secrets / variable de entorno.")

# --- Session state ---
for key in ["destrezas", "plan_raw", "plan_parsed", "doc_bytes"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "destrezas" else None

# --- Datos básicos ---
st.subheader("Datos Básicos")
col1, col2 = st.columns(2)
with col1:
    asignatura = st.text_input("Asignatura")
    grado = st.text_input("Grado")
with col2:
    edad = st.number_input("Edad de los estudiantes", min_value=3, max_value=99, value=12)
    tema_insercion = st.text_input("Tema de Inserción (actividad transversal)")

# --- Destreza e indicador ---
st.subheader("Agregar Destreza e Indicador")
d_col1, d_col2 = st.columns([2, 2])
with d_col1:
    destreza_input = st.text_area("Destreza con criterio de desempeño", height=120)
with d_col2:
    indicador_input = st.text_area("Indicador de logro", height=120)
    tema_estudio_input = st.text_input("Tema de estudio (opcional)")

if st.button("➕ Agregar destreza"):
    if destreza_input.strip() and indicador_input.strip():
        st.session_state["destrezas"].append({
            "destreza": destreza_input.strip(),
            "indicador": indicador_input.strip(),
            "tema_estudio": tema_estudio_input.strip()
        })
        st.success("Destreza agregada ✅")
        st.experimental_rerun()
    else:
        st.warning("Completa la destreza y el indicador antes de agregar.")

if st.session_state["destrezas"]:
    st.subheader("Destrezas añadidas")
    st.write(st.session_state["destrezas"])

# --- Funciones auxiliares ---
def extract_first_json(text: str):
    start = None
    for i, ch in enumerate(text):
        if ch in ['{', '[']:
            start = i
            break
    if start is None:
        raise ValueError("No se encontró JSON.")
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
                stack.pop()
                if not stack:
                    return text[start:i+1]
    raise ValueError("No se pudo extraer JSON.")

def call_openai_chat(prompt_text: str):
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

def build_prompt(asignatura, grado, edad, tema_insercion, destrezas_list):
    instructions = (
        "Genera un array JSON. Cada elemento = una destreza. "
        "Claves: 'destreza','indicador','orientaciones','recursos','evaluacion'. "
        "orientaciones = {'anticipacion','construccion','construccion_transversal','consolidacion'}. "
        f"En 'construccion_transversal' incluye una actividad relacionada con el Tema de Inserción: {tema_insercion}. "
        "Usa verbos en infinitivo. Recursos online en orientaciones, físicos en 'recursos'. "
        "Respuesta SOLO JSON válido."
    )
    payload = {"asignatura": asignatura, "grado": grado, "edad": edad, "tema_insercion": tema_insercion, "destrezas": destrezas_list}
    return json.dumps({"instrucciones": instructions, "payload": payload}, ensure_ascii=False, indent=2)

def create_docx_from_parsed(parsed_list, asignatura, grado, edad, tema_insercion):
    doc = Document()
    doc.add_heading("Plan de Clase", level=1)
    doc.add_paragraph(f"Asignatura: {asignatura} | Grado: {grado} | Edad: {edad} | Tema de Inserción: {tema_insercion}")
    table = doc.add_table(rows=1, cols=5)
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text, hdr[4].text = (
        "Destreza", "Indicador", "Orientaciones", "Recursos (físicos)", "Evaluación"
    )
    for item in parsed_list:
        row = table.add_row().cells
        row[0].text = str(item.get("destreza", ""))
        row[1].text = str(item.get("indicador", ""))
        orient = item.get("orientaciones", {})
        parts = []
        if isinstance(orient, dict):
            if orient.get("anticipacion"): parts.append("Anticipación: " + str(orient["anticipacion"]))
            if orient.get("construccion"): parts.append("Construcción: " + str(orient["construccion"]))
            if orient.get("construccion_transversal"): parts.append("Actividad transversal: " + str(orient["construccion_transversal"]))
            if orient.get("consolidacion"): parts.append("Consolidación: " + str(orient["consolidacion"]))
        row[2].text = "\n".join(parts)
        row[3].text = ", ".join(item.get("recursos", [])) if isinstance(item.get("recursos"), list) else str(item.get("recursos", ""))
        row[4].text = str(item.get("evaluacion", ""))
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- Generar plan ---
if st.button("📑 Generar Plan de Clase"):
    if not (asignatura and grado and edad and tema_insercion and st.session_state["destrezas"]):
        st.warning("Completa todos los campos y agrega al menos una destreza.")
    else:
        with st.spinner("Generando plan..."):
            try:
                prompt = build_prompt(asignatura, grado, edad, tema_insercion, st.session_state["destrezas"])
                response_text = call_openai_chat(prompt)
                response_text = response_text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
                st.session_state["plan_raw"] = response_text
                try:
                    parsed = json.loads(extract_first_json(response_text))
                except:
                    parsed = None
                if parsed and isinstance(parsed, list):
                    st.session_state["plan_parsed"] = parsed
                    st.session_state["doc_bytes"] = create_docx_from_parsed(parsed, asignatura, grado, edad, tema_insercion).getvalue()
                    st.success("✅ Plan generado con éxito")
                else:
                    st.warning("No se pudo interpretar JSON. Exportando texto bruto.")
                    doc = Document(); doc.add_paragraph(response_text)
                    buf = BytesIO(); doc.save(buf); buf.seek(0)
                    st.session_state["doc_bytes"] = buf.getvalue()
            except Exception as e:
                st.error(f"Error: {e}")

# --- Mostrar preview tabla y descarga ---
if st.session_state.get("plan_parsed"):
    st.subheader("📋 Vista previa del Plan")
    st.table(st.session_state["plan_parsed"])

if st.session_state.get("doc_bytes"):
    ts = time.strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="💾 Exportar a Word",
        data=st.session_state["doc_bytes"],
        file_name=f"plan_de_clase_{ts}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

if st.button("🔄 Nuevo"):
    st.session_state.clear()
    st.experimental_rerun()
