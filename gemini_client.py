import streamlit as st
import google.generativeai as genai

# Configura la clave API de Gemini
api_key = st.secrets["gemini"]["api_key"]
genai.configure(api_key=api_key)

# Inicializa el modelo de Gemini
def get_gemini_model():
    """Inicializa y devuelve el modelo de Gemini."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    return model

def generate_response(prompt):
    """Genera una respuesta de Gemini para el prompt dado."""
    model = get_gemini_model()
    try:
        response = model.generate_content(prompt)
        # Accede a la respuesta del modelo, si existe
        if response.text:
            return response.text
        else:
            return "No se pudo generar una respuesta. Intenta de nuevo."
    except Exception as e:
        # Maneja cualquier error que ocurra durante la llamada a la API
        return f"Ocurrió un error: {e}"