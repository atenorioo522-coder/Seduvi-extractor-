# Seduvi-extractor- 
import io
import re

import pdfplumber
import pandas as pd
import streamlit as st


# ------------ UTILIDADES BÁSICAS ------------

def extraer_texto_pdf(file_bytes: bytes) -> str:
    """Devuelve todo el texto del PDF como un string."""
    paginas = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            texto = page.extract_text() or ""
            paginas.append(texto)
    return "\n".join(paginas)


def buscar_regex(patron: str, texto: str, flags=re.IGNORECASE):
    """Devuelve el primer grupo capturado por regex o '' si no encuentra."""
    m = re.search(patron, texto, flags)
    return m.group(1).strip() if m else ""


# ------------ PARSEO ESPECÍFICO FICHA SEDUVI ------------

def parsear_ficha_seduvi(texto: str) -> dict:
    """
    Extrae información de una ficha SEDUVI con formato como el ejemplo que mandaste.
    Si algún dato no aparece claro en el texto, se deja vacío.
    """

    # --------- DATOS GENERALES ---------
    cuenta_catastral = buscar_regex(r"Cuenta Catastral\s+([\d_]+)", texto)

    # Calle y número: viene en dos renglones
    # 'Calle y Número: STA MARIA DE LA RIBERA\n91 93'
    m_calle = re.search(
        r"Calle y Número:\s*(.+)\n([^\n]+)",
        texto,
        re.IGNORECASE
    )
    if m_calle:
        calle_y_num = (m_calle.group(1) + " " + m_calle.group(2)).strip()
    else:
        calle_y_num = buscar_regex(r"Calle y Número:\s*(.+)", texto)

    colonia = buscar_regex(r"Colonia:\s*(.+)", texto)
    cp = buscar_regex(r"Código Postal:\s*([0-9]+)", texto)

    # Superficie del Predio: tiene salto de línea entre "Superficie del" y "Predio"
    superficie_predio = buscar_regex(
        r"Superficie del\s*[\r\n ]*Predio:\s*([\d\.,]+)\s*m2",
        texto,
        flags=re.IGNORECASE
    )

    # --------- ZONIFICACIÓN / LIMITACIONES ---------

    # Uso del Suelo: primera vez que aparece "Uso del Suelo 1:" o "Uso del Suelo:"
    uso_suelo = buscar_regex(
        r"Uso del Suelo 1:.*?\n([^\n]+)",
        texto,
        flags=re.IGNORECASE | re.DOTALL
    )
    if not uso_suelo:
        uso_suelo = buscar_regex(
            r"Uso del Suelo:\s*([^\n]+)",
            texto,
            flags=re.IGNORECASE
        )
    # Limpiamos por si viene acompañado de "Ver Tabla de Uso"
    if uso_suelo:
        uso_suelo = uso_suelo.replace("Ver Tabla de Uso", "").strip()

    # Niveles y Altura (primeros que aparezcan)
    niveles = buscar_regex(r"Niveles:\s*([0-9]+)", texto)
    altura = buscar_regex(r"Altura:\s*([0-9]+)", texto)

    # % Área Libre (en la segunda tabla viene como "% Area Libre 25")
    porcentaje_area_libre = buscar_regex(
        r"%\s*Area\s*Libre\s*([0-9]+)",
        texto,
        flags=re.IGNORECASE
    )

    # Superficie Máxima de Construcción (buscamos el número antes de "No. de Viviendas")
    superficie_max_construccion = buscar_regex(
        r"Superficie Máx\.[\s\S]*?Construcción[\s\S]*?\n[\s\S]*?([0-9]+)\s+No\. de Viviendas",
        texto,
        flags=re.IGNORECASE
    )

    # Número de Viviendas Permitidas
    num_viviendas = buscar_regex(
        r"No\. de Viviendas\s*Permitidas\s*([0-9]+)",
        texto,
        flags=re.IGNORECASE
    )
    if not num_viviendas:
        num_viviendas = buscar_regex(
            r"Número de\s*Viviendas\s*Permitidas\s*([0-9]+)",
            texto,
            flags=re.IGNORECASE
        )

    # M2 mínimo de vivienda (solo si aparece explícito tipo "M2 min. Vivienda: 50")
    m2_min_vivienda = buscar_regex(
        r"M2\s*min\.\s*Vivienda[: ]\s*([0-9]+)",
        texto,
        flags=re.IGNORECASE
    )

    # Densidad (solo si viene con número directo como "Densidad 100")
    densidad = buscar_regex(
        r"Densidad[: ]\s*([0-9]+)",
        texto,
        flags=re.IGNORECASE
    )

    # --------- VIALIDADES / FRENTES A CALLE ---------
    # Buscamos una línea con "de: ... a ..." después de la sección "Vialidades"
    vialidad = ""
    m_v = re.search(
        r"Vialidades[\s\S]*?\n([^\n]*de:\s*.*\sa\s.*)",
        texto,
        re.IGNORECASE
    )
    if m_v:
        vialidad = m_v.group(1).strip()

    return {
        "Cuenta Catastral": cuenta_catastral,
        "Calle y Número": calle_y_num,
        "Colonia": colonia,
        "Código Postal": cp,
        "Superficie Predio (m2)": superficie_predio,
        "Uso de Suelo": uso_suelo,
        "Niveles": niveles,
        "Altura (m)": altura,
        "% Área Libre": porcentaje_area_libre,
        "Superficie Máx. Construcción (m2)": superficie_max_construccion,
        "No. Viviendas Permitidas": num_viviendas,
        "M2 mín. Vivienda": m2_min_vivienda,
        "Densidad": densidad,
        "Frente / Vialidad": vialidad,
    }


# ------------ APP STREAMLIT ------------

st.title("Extractor de Fichas SEDUVI (Uso de Suelo y Vialidades)")

uploaded_files = st.file_uploader(
    "Sube una o varias fichas SEDUVI en PDF",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded_files:
    resultados = []
    for f in uploaded_files:
        contenido = f.read()
        texto = extraer_texto_pdf(contenido)
        info = parsear_ficha_seduvi(texto)
        info["Archivo"] = f.name
        resultados.append(info)

    df = pd.DataFrame(resultados).set_index("Archivo")

    st.subheader("Resultados")
    st.dataframe(df, use_container_width=True)

    st.download_button(
        label="Descargar resultados (CSV)",
        data=df.to_csv().encode("utf-8-sig"),
        file_name="fichas_seduvi.csv",
        mime="text/csv",
    )
else:
    st.info("Sube al menos un PDF para procesarlo.")
