# app.py

# Librerías
import streamlit as st
import pandas as pd
import numpy as np
import folium
import geopy

from folium.features import DivIcon
from folium.plugins import MarkerCluster

from geopy.distance import geodesic
from geopy.distance import distance
from geopy.geocoders import Nominatim

from math import sin, cos, radians

from datetime import datetime, timedelta

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

import geopandas as gpd

from streamlit_folium import st_folium

# Configurar la página para un diseño más ancho
st.set_page_config(layout="wide")

# Título de la aplicación
st.title("Sectorizador - Zonas comunes")

# Subir archivo CSV
uploaded_file = st.file_uploader("Subir archivo CSV", type="csv")

if uploaded_file is not None:
    # Leer el archivo CSV
    celdas = pd.read_csv(uploaded_file)
    st.subheader("Datos de Celdas")
    st.write(celdas)

    # Verificar si hay valores nulos en las columnas clave
    columnas_necesarias = ['Latitud', 'Longitud', 'Radio_de_cobertura', 'Azimuth', 'Angulo', 'Abonado', 'fecha']
    for columna in columnas_necesarias:
        if columna not in celdas.columns:
            st.error(f"La columna '{columna}' no se encuentra en el DataFrame. Por favor, verifica el archivo CSV.")
            st.stop()

    if celdas[['Latitud', 'Longitud', 'Radio_de_cobertura', 'Azimuth', 'Angulo']].isnull().any().any():
        st.error("Hay valores nulos en las columnas necesarias. Por favor, verifica los datos.")
        st.stop()

    # Crear un mapa centrado en los puntos del dataframe
    mapa = folium.Map(location=[celdas['Latitud'].mean(), celdas['Longitud'].mean()], zoom_start=13)

    # Crear una lista de polígonos para cada punto del dataframe
    poligonos = []
    colores = ['red', 'blue', 'green', 'orange', 'purple', 'gray']  # Lista de colores
    for index, row in celdas.iterrows():
        # Obtener el radio y la posición del centro del círculo
        radio = row['Radio_de_cobertura']
        centro = (row['Latitud'], row['Longitud'])
        azimuth = row['Azimuth']
        angle = row['Angulo']
        start_angle = radians(azimuth - angle / 2)  # Ángulo inicial
        end_angle = radians(azimuth + angle / 2)    # Ángulo final

        # Crear los puntos que forman el sector circular
        puntos = []
        for ang in np.linspace(start_angle, end_angle, num=30):
            lat = centro[0] + (radio / 111.32) * sin(ang)
            lon = centro[1] + (radio / (111.32 * cos(radians(lat)))) * cos(ang)
            puntos.append([lat, lon])
        puntos.append(centro)

        # Asignar un color según el índice de la fila
        color = colores[index % len(colores)]

        # Crear el polígono que representa el sector circular y añadirlo a la lista de polígonos
        try:
            poligono = Polygon(puntos)
            poligonos.append((poligono, row['Abonado'], color))

            # Añadir el polígono al mapa
            folium.vector_layers.Polygon(locations=puntos, tooltip=row['Abonado'], color=color, fill=True, fill_color=color, fill_opacity=0.4).add_to(mapa)
        except ValueError as e:
            st.warning(f"No se pudo crear el polígono para la fila {index} debido a: {e}")

    # Mostrar el mapa en Streamlit con dimensiones ajustadas
    st.subheader("Mapa de Celdas")
    st_data = st_folium(mapa, width=800, height=400)  # Ajusta 'width' y 'height' para reducir el espacio vacío

    # Reducir el espacio entre el mapa y el análisis de zonas comunes
    st.markdown("""
        <style>
        .stDataFrame {margin-top: -30px;}
        </style>
        """, unsafe_allow_html=True)

    # Convertir la columna 'fecha' a tipo datetime
    celdas['fecha'] = pd.to_datetime(celdas['fecha'], errors='coerce')

    # Análisis de zonas comunes
    st.subheader("Análisis de Zonas Comunes")

    for i, poligono_i in enumerate(poligonos):
        for j, poligono_j in enumerate(poligonos):
            if i < j:
                hora_i = celdas.iloc[i]['fecha']
                hora_j = celdas.iloc[j]['fecha']
                abonado_i = celdas.iloc[i]['Abonado']
                abonado_j = celdas.iloc[j]['Abonado']

                # Verificar que las horas no sean NaT (Not a Time)
                if pd.notnull(hora_i) and pd.notnull(hora_j):
                    if (poligono_i[0].intersects(poligono_j[0])) and (abs(hora_i - hora_j) < timedelta(minutes=15)) and (abonado_i != abonado_j):
                        st.write(f"Los abonados **{abonado_i}** y **{abonado_j}** activaron celdas con zonas de cobertura que presentan una intersección. Dicho solapamiento se establece en el periodo comprendido entre {hora_i.strftime('%d-%m-%Y %H:%M:%S')} - {hora_j.strftime('%d-%m-%Y %H:%M:%S')}.")
                else:
                    st.warning(f"Fechas no válidas para los abonados {abonado_i} y {abonado_j}.")

