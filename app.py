import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import geopandas as gpd
from datetime import datetime

# -----------------------
# FUNCIONS AUXILIARS
# -----------------------
def calcular_mitjana_mobil(df, columna, finestra):
    return df[panta_to_sensor_id[columna]].rolling(window=finestra, min_periods=1).mean()

def calcular_index_global(df, capacitats):
    df_ponderat = df.copy()
    for emb in capacitats:
        sensor_id = panta_to_sensor_id[emb]
        df_ponderat[sensor_id] = df_ponderat[sensor_id] * capacitats[emb]
    total_capacitat = sum(capacitats.values())
    df_ponderat['mitjana_ponderada'] = df_ponderat[list(panta_to_sensor_id.values())].sum(axis=1) / total_capacitat
    return df_ponderat[['timestamp', 'mitjana_ponderada']]

# -----------------------
# DADES DE MOSTRA (Substitueix-ho amb les teves dades reals)
# -----------------------
# Carreguem les metadades
df_pantans = pd.read_csv('data/enriched/metadata/reservoir_sensors_metadata.csv')  # Carrega les dades reals dels embassaments
sensor_id = df_pantans['sensor_id']
pantans = df_pantans['componentDesc']
sensor_id_to_panta = dict(zip(sensor_id, pantans))
panta_to_sensor_id = dict(zip(pantans, sensor_id))

# Carreguem les dades dels nivells dels embassaments
df = pd.read_csv('data/aggregated/date/reservoir_sensors_reads.csv')  # Carrega les dades reals dels nivells dels embassaments
df["timestamp"] = df["timestamp"].astype("datetime64[ns]")
dates = df["timestamp"].dt.date.to_list()
capacitats = dict(zip(pantans, df_pantans['info_reservoir_max_capacity_(hm3)']))

localitzacions = pd.DataFrame({
    'pantà': pantans,
    'lat': df_pantans['latitude'],
    'lon': df_pantans['longitude'],
    'nivell_actual': [df[panta_to_sensor_id[p]][len(df)-1] for p in pantans],
    'capacitat': df_pantans['info_reservoir_max_capacity_(hm3)']
})

# -----------------------
# STREAMLIT APP
# -----------------------
st.set_page_config(page_title="Monitoratge d'Embassaments de Catalunya", layout="wide")
st.title("💧 Monitoratge dels Embassaments de Catalunya")
st.markdown("""
Aquesta aplicació interactiva mostra diferents visualitzacions sobre l'estat i evolució del nivell dels embassaments catalans. Pots explorar les dades per respondre preguntes clau sobre la disponibilitat hídrica.
""")

# 1. EVOLUCIÓ TEMPORAL
st.header("1. Evolució temporal del nivell dels embassaments")
st.markdown("""
Com ha evolucionat el nivell dels pantans en un període determinat? El nivell augmenta o disminueix?
""")
col1, col2, col3 = st.columns(3)
with col1:
    sensors_seleccionats = st.multiselect("Selecciona embassaments", pantans, default=pantans)
with col2:
    data_inici = st.date_input("Data d'inici", value=dates[0], min_value=dates[0], max_value=dates[-1])
with col3:
    finestra_mobil = st.slider("Finestra mitjana mòbil (dies)", min_value=1, max_value=30, value=7)

df_filtrat = df[df['timestamp'] >= pd.to_datetime(data_inici)]
fig1 = go.Figure()
for sensor in sensors_seleccionats:
    val_suavitzats = calcular_mitjana_mobil(df_filtrat, sensor, finestra_mobil)
    fig1.add_trace(go.Scatter(x=df_filtrat['timestamp'], y=val_suavitzats, mode='lines', name=sensor))
fig1.update_layout(title="Evolució temporal amb mitjanes mòbils", xaxis_title="Data", yaxis_title="Nivell (%)")
st.plotly_chart(fig1, use_container_width=True)

# 2. MAPA DE PANTANS
st.header("2. Estat actual dels embassaments en el territori")
st.markdown("""
Quin és l’estat actual dels embassaments de Catalunya? Amb un cop d’ull es pot veure on estan localitzats.
""")
fig2 = px.scatter_mapbox(localitzacions, lat="lat", lon="lon", hover_name="pantà", hover_data=["nivell_actual"],
                         color="nivell_actual", color_continuous_scale=[(0, "red"), (0.5, "orange"), (1, "green")], size="capacitat", size_max=40, zoom=7)
fig2.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig2, use_container_width=True)

# 3. CORRELACIÓ ENTRE DOS EMBASSAMENTS
st.header("3. Correlació entre dos embassaments")
st.markdown("""
El nivell de l’embassament 1 ha seguit una evolució similar a la de l’embassament 2?
""")
col1, col2 = st.columns(2)
with col1:
    emb1 = st.selectbox("Embassament 1", pantans, index=0)
with col2:
    emb2 = st.selectbox("Embassament 2", pantans, index=1)
fig3 = px.scatter(df, x=panta_to_sensor_id[emb1], y=panta_to_sensor_id[emb2], trendline="ols", title=f"Correlació entre {emb1} i {emb2}")
fig3.update_layout(xaxis_title=emb1, yaxis_title=emb2)
# Buscar la línia de tendència i canviar-li el color
fig3.for_each_trace(
    lambda trace: trace.update(line=dict(color="red", width=3)) if trace.mode == "lines" else None
)
st.plotly_chart(fig3, use_container_width=True)

# 4. ÍNDEX GLOBAL
if True:
    st.header("4. Índex de disponibilitat hídrica global")
    st.markdown("""
    Quin és l’estat global actual dels embassaments?
    """)
    # Dades precomputades
    df_months = pd.read_csv('data/aggregated/year_month/reservoir_sensors_reads.csv') # Carreggem les dades mensuals
    df_index = calcular_index_global(df_months, capacitats)
    df_index['timestamp'] = pd.to_datetime(df_index['timestamp'])

    # Últim valor per inicialitzar
    valor_actual = df_index['mitjana_ponderada'].iloc[-1]

    # Layout de dues columnes
    col1, col2 = st.columns(2)

    with col1:
        with col1:
            st.subheader("Evolució temporal de l’índex")

            # Diagrama de barres de l'evolució temporal de l'índex
            fig_line = px.bar(
                df_index,
                x="timestamp",
                y="mitjana_ponderada",
                labels={"timestamp": "Data", "mitjana_ponderada": "Índex global hídrica (%)"},
                title="Evolució temporal de l'índex global hídrica"
            )
            fig_line.update_layout(xaxis_title="Data", yaxis_title="Índex global hídrica (%)")
            st.plotly_chart(fig_line, use_container_width=True)

    with col2:
        st.subheader("Índex actual")
        
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=valor_actual,
            title={'text': "Índex global hídrica (%)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "blue"},
                'steps': [
                    {'range': [0, 33], 'color': "red"},
                    {'range': [33, 66], 'color': "orange"},
                    {'range': [66, 100], 'color': "green"}
                ]
            }
        ))

        st.plotly_chart(fig_gauge, use_container_width=True)
else:
    st.header("4. Índex de disponibilitat hídrica global")
    st.markdown("""
    Quin és l’estat global actual dels embassaments?
    """)
    df_index = calcular_index_global(df, capacitats)
    valor_actual = df_index['mitjana_ponderada'].iloc[-1]
    fig4 = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor_actual,
        title={'text': "Índex global hídrica (%)"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "blue"},
            'steps': [
                {'range': [0, 30], 'color': "red"},
                {'range': [30, 60], 'color': "orange"},
                {'range': [60, 100], 'color': "lightblue"}
            ],
        }
    ))
    st.plotly_chart(fig4, use_container_width=True)

st.markdown("""
---
App creada amb ❤️ i Streamlit per a la visualització interactiva de dades ambientals.
""")
