
# app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import pydeck as pdk


# Configuración inicial
st.set_page_config(layout="wide", page_title="Comparación entre países - Airbnb")

# Carga de datos
@st.cache_data
def load_data():
    return {
        "Rio de Janeiro": pd.read_csv("Rio de Janeiro sin atipicos.csv"),
        "Naples": pd.read_csv("Datos_limpios_Naples.csv"),
        "Berlin": pd.read_csv("Datos_limpios_Berlin.csv"),
        "Mexico": pd.read_csv("México sin atipicos.csv")
    }
    

data = load_data()
colores = {
    "Rio de Janeiro": "green",
    "Naples": "gold",
    "Berlin": "black",
    "Mexico": "red"
}

# Conversión de moneda a pesos mexicanos (MXN)
conversion_monedas = {
    "Rio de Janeiro": 3.5,   # BRL a MXN
    "Naples": 18.0,          # EUR a MXN
    "Berlin": 18.0,          # EUR a MXN
    "Mexico": 1.0            # Ya está en MXN
}

# Convertir columna 'price' en cada DataFrame
for ciudad, df in data.items():
    df['price_mxn'] = pd.to_numeric(df['price'], errors='coerce') * conversion_monedas[ciudad]
    df['price_mxn'] = df['price_mxn'].round(2)


# Variables clasificadas
variables_numericas = ['accommodates', 'bathrooms', 'bedrooms', 'beds']
variables_categoricas = ['host_response_time', 'host_verifications', 'room_type', 'property_type', 'host_acceptance_rate']
variables_scores = ['review_scores_rating', 'review_scores_accuracy', 'review_scores_cleanliness',
                    'review_scores_checkin', 'review_scores_communication', 'review_scores_location',
                    'review_scores_value']
variables_binarias = ['instant_bookable', 'has_availability', 'host_is_superhost', 'host_has_profile_pic',
                      'host_identity_verified']
variable_precio=['price_mxn']
todas_las_variables = variables_numericas + variables_categoricas + variables_scores + variables_binarias + variable_precio

# Sidebar
st.sidebar.title("Panel de control")

# Variable a visualizar
selected_var = st.sidebar.selectbox("Selecciona una variable:", todas_las_variables)
show_table = st.sidebar.checkbox("Mostrar tabla")


# Tamaño de gráfico
st.sidebar.subheader("Tamaño del gráfico")
width = st.sidebar.slider("Ancho", 4, 20, 10)
height = st.sidebar.slider("Alto", 1, 15, 6)

# Título principal
st.title("Dashboard Comparativo de Alojamiento en 4 Ciudades")


# Visualización según el tipo de variable
st.header(f"Visualización para: {selected_var}")

# Variables numéricas: diagrama de puntos
if selected_var in variables_numericas:
    fig, ax = plt.subplots(figsize=(width, height))
    for ciudad, df in data.items():
        sns.stripplot(x=[ciudad]*len(df), y=df[selected_var], color=colores[ciudad], alpha=0.5, ax=ax)
    ax.set_title(f"Distribución de {selected_var}")
    st.pyplot(fig)


# Variables categóricas: barras por país en cuadrícula 2x2
elif selected_var in variables_categoricas:
    
    ciudades = list(data.keys())
    
    for i in range(0, len(ciudades), 2):
        cols = st.columns(2)
        for j, ciudad in enumerate(ciudades[i:i+2]):
            with cols[j]:
                df = data[ciudad]

                # Preprocesamiento específico para 'host_acceptance_rate'
                if selected_var == "host_acceptance_rate":
                    df = df.dropna(subset=[selected_var])
                    df['category'] = pd.qcut(df[selected_var], 5, duplicates='drop')
                    counts = df['category'].value_counts().sort_index()
                else:
                    counts = df[selected_var].value_counts().nlargest(5)

                fig, ax = plt.subplots(figsize=(5, 4))
                ax.bar(counts.index.astype(str), counts.values, color=colores[ciudad])
                ax.set_title(ciudad)
                ax.set_xlabel(selected_var)
                ax.set_ylabel("Frecuencia")
                plt.xticks(rotation=45)
                st.pyplot(fig)


# Scores: polígonos de frecuencia
elif selected_var in variables_scores:
    fig, ax = plt.subplots(figsize=(width, height))
    for ciudad, df in data.items():
        sns.kdeplot(df[selected_var].dropna(), label=ciudad, color=colores[ciudad], ax=ax)
    ax.set_title(f"Densidad de {selected_var}")
    ax.legend()
    st.pyplot(fig)

# Variables binarias: pastel por ciudad (en columnas)
elif selected_var in variables_binarias:

    col1, col2 = st.columns(2)
    ciudades = list(data.keys())

    for i in range(0, len(ciudades), 2):
        col_a = col1 if i % 4 == 0 else col2
        col_b = col2 if i % 4 == 0 else col1

        for col, ciudad in zip([col1, col2], ciudades[i:i+2]):
            with col:
                fig, ax = plt.subplots(figsize=(4, 4))  # Tamaño pequeño
                df = data[ciudad]
                df[selected_var] = df[selected_var].astype(str)
                df[selected_var].value_counts().plot.pie(autopct='%1.1f%%', colors=[colores[ciudad], 'lightgray'], ax=ax)
                ax.set_ylabel('')
                ax.set_title(ciudad)
                st.pyplot(fig)

#Precio
elif selected_var in variable_precio:
    fig, axs = plt.subplots(2, 2, figsize=(width, height + 2))
    fig.tight_layout(pad=10)
    ciudades = list(data.keys())

    for i, ciudad in enumerate(ciudades):
        df = data[ciudad].dropna(subset=['price_mxn'])
        df['precio_categoria'] = pd.qcut(df['price_mxn'], q=5, duplicates='drop')

        conteo = df['precio_categoria'].value_counts().sort_index()

        fila = i // 2
        col = i % 2

        axs[fila, col].bar(conteo.index.astype(str), conteo.values, color=colores[ciudad])
        axs[fila, col].set_title(f"Categorías de precio en {ciudad}")
        axs[fila, col].tick_params(axis='x', rotation=45)

    st.pyplot(fig)

    # ------------------ Mapa con control de intervalo de precios -------------------
    st.subheader("Mapa interactivo de precios (MXN)")

    ciudad_mapa = st.sidebar.selectbox("Selecciona una ciudad para el mapa", ciudades)
    df_mapa = data[ciudad_mapa].dropna(subset=['latitude', 'longitude', 'price_mxn'])

    if not df_mapa.empty:
        precio_min, precio_max = int(df_mapa['price_mxn'].min()), int(df_mapa['price_mxn'].max())

        rango = st.sidebar.slider(
            "Rango de precios a visualizar en el mapa (MXN)",
            min_value=precio_min,
            max_value=precio_max,
            value=(precio_min, precio_max)
        )

        df_filtrado = df_mapa[(df_mapa['price_mxn'] >= rango[0]) & (df_mapa['price_mxn'] <= rango[1])].copy()

        if df_filtrado.empty:
            st.warning("No hay alojamientos en ese rango de precios.")
        else:
            max_price = df_filtrado['price_mxn'].max()
            df_filtrado['color'] = df_filtrado['price_mxn'].apply(
                lambda x: [255, max(0, 255 - int((x / max_price) * 255)), 0]
            )

            st.pydeck_chart(pdk.Deck(
                initial_view_state=pdk.ViewState(
                    latitude=df_filtrado["latitude"].mean(),
                    longitude=df_filtrado["longitude"].mean(),
                    zoom=11,
                    pitch=45,
                ),
                layers=[
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=df_filtrado,
                        get_position='[longitude, latitude]',
                        get_color='color',
                        get_radius=200,
                        pickable=True
                    ),
                ],
                tooltip={"text": "Precio: {price_mxn} MXN"}
            ))
    else:
        st.warning(f"No hay datos geográficos disponibles para {ciudad_mapa}.")


# Mostrar tabla resumen solo si se activa el checkbox
if show_table:
    st.markdown("---")
    st.subheader("Tabla resumen por país")

    pais_seleccionado = st.sidebar.selectbox("Selecciona un país para ver su tabla", list(data.keys()))

    df = data[pais_seleccionado]
    resumen = df[selected_var].value_counts(dropna=False).reset_index()
    resumen.columns = [selected_var, "Frecuencia"]

    st.markdown(f"**{pais_seleccionado}**")
    st.dataframe(resumen)

