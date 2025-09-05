import streamlit as st
from io import BytesIO
from docx import Document
import openai

# Configuraci贸n inicial de la p谩gina
st.set_page_config(page_title="Generador de Plan de Clase", page_icon="馃摌", layout="wide")

st.title("馃摌 Generador Autom谩tico de Planes de Clase")

# ------------------------------
# SECCI脫N: Entrada de datos b谩sicos
# ------------------------------
st.subheader("Datos B谩sicos")

asignatura = st.text_input("Asignatura")
grado = st.text_input("Grado")
edad = st.number_input("Edad de los estudiantes", min_value=3, max_value=25, step=1)
tema_insercion = st.text_input("Tema de Inserci贸n (actividad transversal)")

# ------------------------------
# SECCI脫N: Destrezas e indicadores
# ------------------------------
st.subheader("Datos Pedag贸gicos")

destreza = st.text_area("Destreza con criterio de desempe帽o")
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
Eres un agente experto en planificaci贸n de clases educativas. Tu funci贸n es elaborar planes de clase estructurados, aplicando metodolog铆as activas, inclusi贸n (DUA), y garantizando que los recursos online sean reales, actuales y accesibles.

Datos b谩sicos:
- Asignatura: {asignatura}
- Grado: {grado}
- Edad de los estudiantes: {edad}
- Tema de Inserci贸n: {tema_insercion}

Destreza: {destreza}
Indicador de logro: {indicador}
Tema de estudio: {tema_estudio if tema_estudio else "No especificado"}

Genera el plan en una tabla con 5 columnas:
[Destreza con criterio de desempe帽o | Indicador de logro | Orientaciones metodol贸gicas | Recursos | Orientaciones para la evaluaci贸n]

Reglas:
- Anticipaci贸n 鈫?actividades para activar conocimientos previos.
- Construcci贸n 鈫?actividades con metodolog铆as activas (ABP, Flipped Classroom, SDA, etc.) e incluir una actividad transversal relacionada con el Tema de Inserci贸n: "{tema_insercion}".
- Consolidaci贸n 鈫?actividades de refuerzo y aplicaci贸n.
- Actividades con verbos en infinitivo.
- Recursos online reales, actuales y accesibles.
- Estrategias DUA para inclusi贸n.
- Recursos: solo f铆sicos.
- Evaluaci贸n: acciones sustantivadas alineadas con el indicador.
"""

        # 馃毃 Aqu铆 debes reemplazar por tu llamada real a OpenAI o al modelo que uses
        # Ejemplo con OpenAI
        import openai
# ... otras importaciones

# Inicializa el cliente de OpenAI
client = openai.OpenAI()

# Tu código original
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}]
)

        plan = response["choices"][0]["message"]["content"]
        st.session_state.plan_generado = plan

        st.success("鉁?Plan de clase generado con 茅xito")
        st.write(plan)
    else:
        st.warning("鈿狅笍 Por favor, llena todos los campos obligatorios.")

# ------------------------------
# EXPORTAR A WORD
# ------------------------------
if st.session_state.plan_generado:
    if st.button("馃摜 Exportar a Word"):
        doc = Document()
        doc.add_heading("Plan de Clase", level=1)
        doc.add_paragraph(st.session_state.plan_generado)

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        st.download_button(
            label="猬囷笍 Descargar Plan en Word",
            data=buffer,
            file_name="plan_de_clase.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

# ------------------------------
# NUEVO PLAN
# ------------------------------
if st.button("馃啎 Nuevo"):
    st.session_state.plan_generado = None
    st.experimental_rerun()
