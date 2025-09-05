import streamlit as st
import requests
import os
from docx import Document

# Configuración Hugging Face con token desde Streamlit Secrets
API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"
headers = {"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"}

def generar_plan(prompt):
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
    if response.status_code == 200:
        return response.json()[0]["generated_text"]
    else:
        return "⚠️ Error al generar el plan."

# Interfaz
st.set_page_config(page_title="XAVIERQUIN PLANES DE CLASE", page_icon="📚", layout="wide")
st.title("📚 XAVIERQUIN PLANES DE CLASE")
st.caption("Aplicación de planificación educativa con metodologías activas y DUA")

# Datos iniciales
st.header("1️⃣ Datos básicos")
asignatura = st.text_input("Asignatura")
grado = st.text_input("Grado")
edad = st.number_input("Edad de los estudiantes", min_value=3, max_value=25)

# Agregar destrezas
st.header("2️⃣ Destreza e indicador")
if "destrezas" not in st.session_state:
    st.session_state.destrezas = []

destreza = st.text_input("Destreza con criterio de desempeño")
indicador = st.text_input("Indicador de logro")
tema = st.text_input("Tema de estudio (opcional)")

if st.button("➕ Agregar destreza"):
    if destreza and indicador:
        st.session_state.destrezas.append({"destreza": destreza, "indicador": indicador, "tema": tema})
    else:
        st.warning("Por favor ingresa al menos Destreza e Indicador.")

# Mostrar lista
if st.session_state.destrezas:
    st.write("### ✅ Destreza(s) añadida(s):")
    for i, d in enumerate(st.session_state.destrezas):
        st.write(f"{i+1}. {d['destreza']} → {d['indicador']} (Tema: {d['tema']})")

# Generar planificación
planes = []
if st.button("🚀 Generar planificación"):
    for d in st.session_state.destrezas:
        prompt = f"""
Eres un agente experto en planificación de clases educativas. 
Genera un plan de clase estructurado con metodologías activas y DUA.

Datos:
- Asignatura: {asignatura}
- Grado: {grado}
- Edad: {edad} años
- Destreza: {d['destreza']}
- Indicador: {d['indicador']}
- Tema: {d['tema']}

Formato de salida: tabla de 5 columnas  
[Destreza con criterio de desempeño | Indicador de logro | Orientaciones metodológicas | Recursos | Orientaciones para la evaluación]

Reglas:
- Orientaciones metodológicas → dividir en Anticipación, Construcción y Consolidación.  
- Verbos en infinitivo.  
- Incluir recursos digitales reales y accesibles (nombre + enlace).  
- Recursos físicos solo en la columna Recursos.  
- Estrategias DUA para inclusión.  
- Evaluación en acciones sustantivadas alineadas al indicador.
        """
        plan = generar_plan(prompt)
        planes.append({"destreza": d["destreza"], "indicador": d["indicador"], "plan": plan})

    st.header("3️⃣ 📑 Planificación generada")
    for p in planes:
        st.markdown(f"**Destreza:** {p['destreza']}  \n**Indicador:** {p['indicador']}  \n\n{p['plan']}")

    # Exportar a Word
    def exportar_word(planes):
        doc = Document()
        doc.add_heading("XAVIERQUIN PLANES DE CLASE", 0)
        table = doc.add_table(rows=1, cols=5)
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Destreza"
        hdr_cells[1].text = "Indicador"
        hdr_cells[2].text = "Orientaciones metodológicas"
        hdr_cells[3].text = "Recursos"
        hdr_cells[4].text = "Orientaciones para la evaluación"

        for p in planes:
            row_cells = table.add_row().cells
            row_cells[0].text = p["destreza"]
            row_cells[1].text = p["indicador"]
            row_cells[2].text = p["plan"]  # aquí el modelo devuelve la tabla como texto

        doc.save("planificacion.docx")
        return "planificacion.docx"

    if st.button("💾 Exportar a Word"):
        archivo = exportar_word(planes)
        with open(archivo, "rb") as f:
            st.download_button("⬇️ Descargar Word", f, file_name="planificacion.docx")
