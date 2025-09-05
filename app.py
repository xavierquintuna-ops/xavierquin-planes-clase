import streamlit as st
from io import BytesIO
from docx import Document
import openai

# Configuración inicial de la página
st.set_page_config(page_title="Generador de Plan de Clase", page_icon="📘", layout="wide")

st.title("📘 Generador Automático de Planes de Clase")

# ------------------------------
# SECCIÓN: Entrada de datos básicos
# ------------------------------
st.subheader("Datos Básicos")

asignatura = st.text_input("Asignatura")
grado = st.text_input("Grado")
edad = st.number_input("Edad de los estudiantes", min_value=3, max_value=25, step=1)
tema_insercion = st.text_input("Tema de Inserción (actividad transversal)")

# ------------------------------
# SECCIÓN: Destrezas e indicadores
# ------------------------------
st.subheader("Datos Pedagógicos")

destreza = st.text_area("Destreza con criterio de desempeño")
indicador = st.text_area("Indicador de logro")
tema_estudio = st.text_input("Tema de estudio (opcional)")

# Variable de estado para almacenar el plan
if "plan_generado" not in st.session_state:
    st.session_state.plan_generado = None

# ------------------------------
# GENERAR PLAN
# ------------------------------
if st.button("Generar Plan de Clase"):
    if asignatura and grado and edad and destreza and indicador and tema_insercion:
        # Prompt adaptado
        prompt = f"""
Eres un agente experto en planificación de clases educativas. Tu función es elaborar planes de clase estructurados, aplicando metodologías activas, inclusión (DUA), y garantizando que los recursos online sean reales, actuales y accesibles.

Datos básicos:
- Asignatura: {asignatura}
- Grado: {grado}
- Edad de los estudiantes: {edad}
- Tema de Inserción: {tema_insercion}

Destreza: {destreza}
Indicador de logro: {indicador}
Tema de estudio: {tema_estudio if tema_estudio else "No especificado"}

Genera el plan en una tabla con 5 columnas:
[Destreza con criterio de desempeño | Indicador de logro | Orientaciones metodológicas | Recursos | Orientaciones para la evaluación]

Reglas:
- Anticipación → actividades para activar conocimientos previos.
- Construcción → actividades con metodologías activas (ABP, Flipped Classroom, SDA, etc.) e incluir una actividad transversal relacionada con el Tema de Inserción: "{tema_insercion}".
- Consolidación → actividades de refuerzo y aplicación.
- Actividades con verbos en infinitivo.
- Recursos online reales, actuales y accesibles.
- Estrategias DUA para inclusión.
- Recursos: solo físicos.
- Evaluación: acciones sustantivadas alineadas con el indicador.
"""

        # 🚨 Aquí debes reemplazar por tu llamada real a OpenAI o al modelo que uses
        # Ejemplo con OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        plan = response["choices"][0]["message"]["content"]
        st.session_state.plan_generado = plan

        st.success("✅ Plan de clase generado con éxito")
        st.write(plan)
    else:
        st.warning("⚠️ Por favor, llena todos los campos obligatorios.")

# ------------------------------
# EXPORTAR A WORD
# ------------------------------
if st.session_state.plan_generado:
    if st.button("📥 Exportar a Word"):
        doc = Document()
        doc.add_heading("Plan de Clase", level=1)
        doc.add_paragraph(st.session_state.plan_generado)

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        st.download_button(
            label="⬇️ Descargar Plan en Word",
            data=buffer,
            file_name="plan_de_clase.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

# ------------------------------
# NUEVO PLAN
# ------------------------------
if st.button("🆕 Nuevo"):
    st.session_state.plan_generado = None
    st.experimental_rerun()
