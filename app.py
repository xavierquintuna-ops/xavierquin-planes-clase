def build_prompt(asignatura, grado, edad, tema_insercion, destrezas_list):
    """
    Construye un prompt que solicita a la IA producir un JSON con la planificaci車n
    estructurada (una entrada por destreza).
    """
    instructions = (
        "Genera un array JSON donde cada elemento corresponde a una destreza a?adida. "
        "Cada elemento debe tener estas claves obligatorias: "
        "'destreza', 'indicador', 'orientaciones', 'recursos', 'evaluacion'. "
        "La clave 'orientaciones' debe ser un objeto con: "
        "'anticipacion', 'construccion', 'construccion_transversal', 'consolidacion'. "
        "En 'construccion_transversal' incluye una actividad transversal basada en el Tema de Inserci車n proporcionado. "
        "Todas las actividades deben iniciar con verbos en infinitivo. "
        "Los recursos online deben estar dentro de 'construccion' o 'anticipacion'/'consolidacion', "
        "con formato: Nombre del recurso + enlace (ej: Video 'T赤tulo' - https://...). "
        "Los recursos f赤sicos deben ir 迆nicamente en 'recursos' como lista de strings. "
        "La clave 'evaluacion' debe contener acciones sustantivadas alineadas con el indicador. "
        "Responde 迆nicamente con JSON v芍lido. No incluyas explicaciones ni texto adicional."
    )

    header = {
        "asignatura": asignatura,
        "grado": grado,
        "edad": edad,
        "tema_insercion": tema_insercion
    }

    payload = {
        "header": header,
        "destrezas": destrezas_list,
        "instructions": instructions
    }

    # Prompt reforzado con ejemplo de salida
    example_output = [
        {
            "destreza": "Identificar ideas principales en un texto narrativo",
            "indicador": "Resume un texto narrativo identificando la idea principal",
            "orientaciones": {
                "anticipacion": "Activar conocimientos previos preguntando sobre historias conocidas.",
                "construccion": "Analizar un cuento breve aplicando t谷cnicas de subrayado.",
                "construccion_transversal": "Relacionar el texto con el tema de inserci車n: Medio ambiente (ej: identificar mensajes ecol車gicos).",
                "consolidacion": "Elaborar un resumen escrito con la idea principal del cuento."
            },
            "recursos": ["pizarra", "cuaderno", "marcadores"],
            "evaluacion": "Elaboraci車n de un resumen que identifique la idea principal"
        }
    ]

    prompt = (
        "Debes devolver SOLO JSON v芍lido siguiendo esta estructura. "
        "Aqu赤 tienes los datos de entrada:\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n\nEjemplo de salida JSON (usa esta forma, pero con los datos del usuario):\n"
        + json.dumps(example_output, ensure_ascii=False, indent=2)
    )
    return prompt
