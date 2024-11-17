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

# Título de la aplicación
st.title("Sectorizador - Zonas comunes")

# Subir archivo CSV
uploaded_file = st.file_uploader("Subir archivo CSV", type="csv")

if uploaded_file is not None:
    # Leer el archivo CSV
    celdas = pd.read_csv(uploaded_file)
    st.subheader("Datos de Celdas")
    st.write(celdas)

    # Mostrar las columnas del DataFrame
    #st.write("Columnas del DataFrame:", celdas.columns.tolist())

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
        poligono = Polygon(puntos)
        poligonos.append((poligono, row['Abonado'], color))

        # Añadir el polígono al mapa
        folium.vector_layers.Polygon(locations=puntos, tooltip=row['Abonado'], color=color, fill=True, fill_color=color, fill_opacity=0.4).add_to(mapa)

    # Mostrar el mapa en Streamlit
    st.subheader("Mapa de Celdas")
    st_data = st_folium(mapa, width=700, height=500)

    # Convertir la columna 'fecha' a tipo datetime
    if 'fecha' in celdas.columns:
        celdas['fecha'] = pd.to_datetime(celdas['fecha'], errors='coerce')
    else:
        st.error("La columna 'fecha' no se encuentra en el DataFrame. Por favor, verifica el archivo CSV.")
        st.stop()

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
