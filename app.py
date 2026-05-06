import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# -------------------------------------------------
# CONFIGURACIÓN GENERAL
# -------------------------------------------------
st.set_page_config(
    page_title="Forecasting de Ventas - FRUTA",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
    <style>
    .main {
        padding-top: 1rem;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    .titulo-principal {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.3rem;
    }
    .subtitulo {
        font-size: 1rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="titulo-principal">Dashboard de Predicción de Ventas - Familia FRUTA</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitulo">Analiza estadísticas históricas, actualiza datos y genera pronósticos de ventas para los próximos 30 días.</div>',
    unsafe_allow_html=True
)

# -------------------------------------------------
# FUNCIONES
# -------------------------------------------------
def preparar_datos(df):
    df = df.copy()

    df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")
    df["ventas_totales"] = pd.to_numeric(df["ventas_totales"], errors="coerce")

    df = df.dropna(subset=["FECHA", "ventas_totales"])
    df = df.sort_values("FECHA").reset_index(drop=True)

    # Variables calendario
    df["year"] = df["FECHA"].dt.year
    df["month"] = df["FECHA"].dt.month
    df["month_name"] = df["FECHA"].dt.month_name()
    df["day_of_week"] = df["FECHA"].dt.dayofweek
    df["dia_nombre"] = df["FECHA"].dt.day_name()
    df["fin_semana"] = (df["day_of_week"] >= 5).astype(int)

    # Variables para ML
    df["lag_1"] = df["ventas_totales"].shift(1)
    df["lag_7"] = df["ventas_totales"].shift(7)
    df["lag_14"] = df["ventas_totales"].shift(14)
    df["lag_30"] = df["ventas_totales"].shift(30)

    df["media_7"] = df["ventas_totales"].rolling(7).mean()
    df["media_30"] = df["ventas_totales"].rolling(30).mean()

    return df


def entrenar_modelo(df):
    df_model = df.dropna().copy()

    features = [
        "year",
        "month",
        "day_of_week",
        "fin_semana",
        "lag_1",
        "lag_7",
        "lag_14",
        "lag_30",
        "media_7",
        "media_30"
    ]

    X = df_model[features]
    y = df_model["ventas_totales"]

    split = int(len(df_model) * 0.8)

    X_train = X.iloc[:split]
    X_test = X.iloc[split:]

    y_train = y.iloc[:split]
    y_test = y.iloc[split:]

    modelo = LinearRegression()
    modelo.fit(X_train, y_train)

    pred = modelo.predict(X_test)

    mae = mean_absolute_error(y_test, pred)
    mse = mean_squared_error(y_test, pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, pred)

    return modelo, features, split, y_train, y_test, pred, mae, mse, rmse, r2, df_model


def predecir_30_dias(df_model, modelo, features, dias=30):
    df_future = df_model.copy()
    predicciones = []

    for _ in range(dias):
        ultima_fecha = df_future["FECHA"].iloc[-1]
        nueva_fecha = ultima_fecha + pd.Timedelta(days=1)

        nueva_fila = {
            "FECHA": nueva_fecha,
            "ventas_totales": np.nan
        }

        nueva_fila["year"] = nueva_fecha.year
        nueva_fila["month"] = nueva_fecha.month
        nueva_fila["month_name"] = nueva_fecha.month_name()
        nueva_fila["day_of_week"] = nueva_fecha.dayofweek
        nueva_fila["dia_nombre"] = nueva_fecha.day_name()
        nueva_fila["fin_semana"] = 1 if nueva_fecha.dayofweek >= 5 else 0

        nueva_fila["lag_1"] = df_future["ventas_totales"].iloc[-1]
        nueva_fila["lag_7"] = df_future["ventas_totales"].iloc[-7]
        nueva_fila["lag_14"] = df_future["ventas_totales"].iloc[-14]
        nueva_fila["lag_30"] = df_future["ventas_totales"].iloc[-30]

        nueva_fila["media_7"] = df_future["ventas_totales"].tail(7).mean()
        nueva_fila["media_30"] = df_future["ventas_totales"].tail(30).mean()

        X_new = pd.DataFrame([nueva_fila])[features]
        pred = modelo.predict(X_new)[0]

        nueva_fila["ventas_totales"] = pred

        predicciones.append({
            "FECHA": nueva_fecha,
            "ventas_predichas": round(pred, 2)
        })

        df_future = pd.concat([df_future, pd.DataFrame([nueva_fila])], ignore_index=True)

    return pd.DataFrame(predicciones)


# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
st.sidebar.header("Carga de archivos")
historico = st.sidebar.file_uploader("Subir archivo histórico", type="csv")
nuevo = st.sidebar.file_uploader("Subir nuevos datos", type="csv")

# -------------------------------------------------
# CUERPO PRINCIPAL
# -------------------------------------------------
if historico is None:
    st.info("Sube primero el archivo histórico para iniciar el análisis.")
else:
    df = pd.read_csv(historico)

    if nuevo is not None:
        df_nuevo = pd.read_csv(nuevo)
        df = pd.concat([df, df_nuevo], ignore_index=True)

    df = preparar_datos(df)

    if len(df.dropna()) < 31:
        st.error("Se necesitan al menos 31 registros válidos para generar lags y entrenar el modelo.")
        st.stop()

    # -------------------------------------------------
    # KPIs
    # -------------------------------------------------
    st.subheader("Resumen general")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total vendido", f"{df['ventas_totales'].sum():,.2f}")
    k2.metric("Promedio diario", f"{df['ventas_totales'].mean():,.2f}")
    k3.metric("Máximo diario", f"{df['ventas_totales'].max():,.2f}")
    k4.metric("Mínimo diario", f"{df['ventas_totales'].min():,.2f}")
    k5.metric("Última fecha", str(df["FECHA"].max().date()))

    # -------------------------------------------------
    # ESTADÍSTICAS
    # -------------------------------------------------
    st.subheader("Estadísticas descriptivas")

    c1, c2 = st.columns(2)

    # Ventas promedio por día de semana
    orden_dias = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    ventas_dia = (
        df.groupby("dia_nombre", as_index=False)["ventas_totales"]
        .mean()
        .rename(columns={"ventas_totales": "promedio_ventas"})
    )
    ventas_dia["dia_nombre"] = pd.Categorical(ventas_dia["dia_nombre"], categories=orden_dias, ordered=True)
    ventas_dia = ventas_dia.sort_values("dia_nombre")

    with c1:
        fig1, ax1 = plt.subplots(figsize=(8, 4))
        ax1.bar(ventas_dia["dia_nombre"], ventas_dia["promedio_ventas"])
        ax1.set_title("Promedio de ventas por día de la semana")
        ax1.set_xlabel("Día")
        ax1.set_ylabel("Promedio de ventas")
        plt.xticks(rotation=45)
        st.pyplot(fig1)

    # Porcentaje de ventas por día de semana
    pct_dia = (
        df.groupby("dia_nombre", as_index=False)["ventas_totales"]
        .sum()
    )
    pct_dia["porcentaje"] = pct_dia["ventas_totales"] / pct_dia["ventas_totales"].sum() * 100
    pct_dia["dia_nombre"] = pd.Categorical(pct_dia["dia_nombre"], categories=orden_dias, ordered=True)
    pct_dia = pct_dia.sort_values("dia_nombre")

    with c2:
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        ax2.pie(pct_dia["porcentaje"], labels=pct_dia["dia_nombre"], autopct="%1.1f%%")
        ax2.set_title("Participación porcentual de ventas por día")
        st.pyplot(fig2)

    c3, c4 = st.columns(2)

    # Ventas por mes
    orden_meses = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    ventas_mes = (
        df.groupby("month_name", as_index=False)["ventas_totales"]
        .mean()
        .rename(columns={"ventas_totales": "promedio_ventas"})
    )
    ventas_mes["month_name"] = pd.Categorical(ventas_mes["month_name"], categories=orden_meses, ordered=True)
    ventas_mes = ventas_mes.sort_values("month_name")

    with c3:
        fig3, ax3 = plt.subplots(figsize=(8, 4))
        ax3.bar(ventas_mes["month_name"], ventas_mes["promedio_ventas"])
        ax3.set_title("Promedio de ventas por mes")
        ax3.set_xlabel("Mes")
        ax3.set_ylabel("Promedio de ventas")
        plt.xticks(rotation=45)
        st.pyplot(fig3)

    # Crecimiento anual
    ventas_anio = df.groupby("year", as_index=False)["ventas_totales"].sum()
    ventas_anio["crecimiento_%"] = ventas_anio["ventas_totales"].pct_change() * 100

    with c4:
        fig4, ax4 = plt.subplots(figsize=(8, 4))
        ax4.plot(ventas_anio["year"], ventas_anio["ventas_totales"], marker="o")
        ax4.set_title("Crecimiento histórico de ventas por año")
        ax4.set_xlabel("Año")
        ax4.set_ylabel("Ventas totales")
        st.pyplot(fig4)

    # Histórico completo
    st.subheader("Serie histórica de ventas")
    fig5, ax5 = plt.subplots(figsize=(14, 5))
    ax5.plot(df["FECHA"], df["ventas_totales"])
    ax5.set_title("Comportamiento histórico de ventas")
    ax5.set_xlabel("Fecha")
    ax5.set_ylabel("Ventas")
    plt.xticks(rotation=45)
    st.pyplot(fig5)

    # -------------------------------------------------
    # MODELO
    # -------------------------------------------------
    modelo, features, split, y_train, y_test, pred, mae, mse, rmse, r2, df_model = entrenar_modelo(df)

    st.subheader("Resumen del modelo predictivo")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("MAE", f"{mae:,.2f}")
    m2.metric("MSE", f"{mse:,.2f}")
    m3.metric("RMSE", f"{rmse:,.2f}")
    m4.metric("R²", f"{r2:.3f}")

    st.subheader("Comparación de ventas reales vs predicción")
    fechas_train = df_model.iloc[:split]["FECHA"]
    fechas_test = df_model.iloc[split:]["FECHA"]

    fig6, ax6 = plt.subplots(figsize=(14, 5))
    ax6.plot(fechas_train, y_train.values, label="Train real")
    ax6.plot(fechas_test, y_test.values, label="Test real")
    ax6.plot(fechas_test, pred, label="Predicción")
    ax6.set_title("Ventas reales vs predicción del modelo")
    ax6.set_xlabel("Fecha")
    ax6.set_ylabel("Ventas")
    ax6.legend()
    plt.xticks(rotation=45)
    st.pyplot(fig6)

    # -------------------------------------------------
    # FORECAST 30 DÍAS
    # -------------------------------------------------
    forecast_30 = predecir_30_dias(df_model, modelo, features, dias=30)

    st.subheader("Proyección de los próximos 30 días")
    fig7, ax7 = plt.subplots(figsize=(14, 5))
    ax7.plot(df["FECHA"].tail(90), df["ventas_totales"].tail(90), label="Histórico reciente")
    ax7.plot(forecast_30["FECHA"], forecast_30["ventas_predichas"], label="Forecast 30 días")
    ax7.set_title("Pronóstico de ventas a 30 días")
    ax7.set_xlabel("Fecha")
    ax7.set_ylabel("Ventas")
    ax7.legend()
    plt.xticks(rotation=45)
    st.pyplot(fig7)

    st.subheader("Tabla de pronóstico a 30 días")
    st.dataframe(forecast_30, use_container_width=True)

    csv = forecast_30.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Descargar forecast en CSV",
        data=csv,
        file_name="forecast_30_dias_fruta.csv",
        mime="text/csv"
    )