import streamlit as st
import google.generativeai as genai

# Inicializa la configuración de la API de Gemini
def configure_gemini():
    """Configura la API de Gemini con la clave secreta de Streamlit."""
    try:
        api_key = st.secrets["gemini"]["api_key"]
        genai.configure(api_key=api_key)
        st.session_state["gemini_configured"] = True
    except KeyError:
        st.session_state["gemini_configured"] = False
        st.error("Error: La clave 'gemini' no está en Streamlit Secrets. Por favor, añade [gemini] y la api_key.")
        st.stop()
    except Exception as e:
        st.session_state["gemini_configured"] = False
        st.error(f"Error al configurar la API de Gemini: {e}")
        st.stop()

# Llama al modelo de Gemini
def call_gemini(prompt_text: str, model_name: str = 'gemini-1.5-flash', max_tokens: int = 1500, temperature: float = 0.2) -> str:
    """Llama al modelo de Gemini con el prompt dado y los parámetros especificados."""
    if "gemini_configured" not in st.session_state or not st.session_state["gemini_configured"]:
        configure_gemini()
    
    if not st.session_state["gemini_configured"]:
        return "Error: API de Gemini no configurada."
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt_text,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
        )
        # Accede a la respuesta del modelo, si existe
        if response.text:
            return response.text
        else:
            return "No se pudo generar una respuesta. Intenta de nuevo."
    except Exception as e:
        # Maneja cualquier error que ocurra durante la llamada a la API
        st.session_state["last_error"] = f"Ocurrió un error: {e}"
        return f"Ocurrió un error: {e}"