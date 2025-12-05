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

    # % Área
    
