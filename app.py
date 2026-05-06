import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
import uuid

st.set_page_config(
    page_title="Créditos Vital",
    page_icon="💰",
    layout="wide"
)

DB = "creditos.db"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

conn = sqlite3.connect(DB, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS creditos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mes TEXT,
    concepto TEXT,
    fecha TEXT,
    sede TEXT,
    total REAL,
    estado TEXT,
    dias_credito INTEGER,
    vencimiento TEXT,
    imagen TEXT
)
""")
conn.commit()


def cargar_creditos():
    return pd.read_sql_query(
        "SELECT * FROM creditos ORDER BY fecha DESC",
        conn
    )


st.title("💰 Sistema de Control de Créditos")
st.caption("Registro de créditos, órdenes de compra y control de vencimientos")

menu = st.sidebar.radio(
    "Menú",
    ["Registrar crédito", "Ver créditos"]
)

if menu == "Registrar crédito":
    st.subheader("Registrar nuevo crédito")

    with st.form("form_credito"):
        col1, col2, col3 = st.columns(3)

        with col1:
            mes = st.selectbox(
                "Mes",
                [
                    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                ]
            )

            concepto = st.text_input(
                "Concepto / N° Orden de Compra",
                placeholder="00035"
            )

            fecha = st.date_input(
                "Fecha de emisión",
                value=date.today()
            )

        with col2:
            sede = st.text_input(
                "Sede",
                placeholder="Ferrosal"
            )

            total = st.number_input(
                "Total S/",
                min_value=0.0,
                step=0.10,
                format="%.2f"
            )

            dias_credito = st.number_input(
                "Días de crédito",
                min_value=1,
                max_value=60,
                value=15
            )

        with col3:
            estado = st.selectbox(
                "Estado",
                ["Pendiente", "Pagado", "Pago parcial"]
            )

            imagen = st.file_uploader(
                "Subir orden de compra",
                type=["png", "jpg", "jpeg"]
            )

        guardar = st.form_submit_button("Guardar crédito")

        if guardar:
            if concepto.strip() == "":
                st.error("Debes ingresar el número de orden de compra.")
            elif sede.strip() == "":
                st.error("Debes ingresar la sede.")
            elif total <= 0:
                st.error("El total debe ser mayor a 0.")
            else:
                ruta_imagen = ""

                if imagen is not None:
                    extension = imagen.name.split(".")[-1]
                    nombre_archivo = f"{uuid.uuid4()}.{extension}"
                    ruta_imagen = str(UPLOAD_DIR / nombre_archivo)

                    with open(ruta_imagen, "wb") as f:
                        f.write(imagen.getbuffer())

                vencimiento = fecha + timedelta(days=int(dias_credito))

                cursor.execute("""
                    INSERT INTO creditos (
                        mes,
                        concepto,
                        fecha,
                        sede,
                        total,
                        estado,
                        dias_credito,
                        vencimiento,
                        imagen
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    mes,
                    concepto,
                    str(fecha),
                    sede,
                    float(total),
                    estado,
                    int(dias_credito),
                    str(vencimiento),
                    ruta_imagen
                ))

                conn.commit()
                st.success("Crédito registrado correctamente.")

if menu == "Ver créditos":
    st.subheader("Créditos registrados")

    df = cargar_creditos()

    if df.empty:
        st.info("Todavía no tienes créditos registrados.")
    else:
        hoy = date.today()

        df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
        df["vencimiento"] = pd.to_datetime(df["vencimiento"]).dt.date

        df["estado_real"] = df.apply(
            lambda row: "Vencido"
            if row["estado"] != "Pagado" and row["vencimiento"] < hoy
            else row["estado"],
            axis=1
        )

        total_general = df["total"].sum()
        total_pendiente = df[df["estado_real"] != "Pagado"]["total"].sum()
        total_pagado = df[df["estado_real"] == "Pagado"]["total"].sum()
        total_vencido = df[df["estado_real"] == "Vencido"]["total"].sum()

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total general", f"S/ {total_general:,.2f}")
        col2.metric("Pendiente", f"S/ {total_pendiente:,.2f}")
        col3.metric("Pagado", f"S/ {total_pagado:,.2f}")
        col4.metric("Vencido", f"S/ {total_vencido:,.2f}")

        st.divider()

        colf1, colf2 = st.columns(2)

        with colf1:
            filtro_sede = st.selectbox(
                "Filtrar por sede",
                ["Todas"] + sorted(df["sede"].dropna().unique().tolist())
            )

        with colf2:
            filtro_estado = st.selectbox(
                "Filtrar por estado",
                ["Todos", "Pendiente", "Pago parcial", "Pagado", "Vencido"]
            )

        df_filtrado = df.copy()

        if filtro_sede != "Todas":
            df_filtrado = df_filtrado[df_filtrado["sede"] == filtro_sede]

        if filtro_estado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["estado_real"] == filtro_estado]

        st.dataframe(
            df_filtrado[
                [
                    "id",
                    "mes",
                    "concepto",
                    "fecha",
                    "sede",
                    "total",
                    "estado_real",
                    "dias_credito",
                    "vencimiento"
                ]
            ],
            use_container_width=True
        )

        st.divider()

        st.subheader("Ver orden de compra")

        credito_id = st.selectbox(
            "Selecciona un crédito",
            df_filtrado["id"].tolist(),
            format_func=lambda x: f"OC {df[df['id'] == x]['concepto'].values[0]} - {df[df['id'] == x]['sede'].values[0]}"
        )

        credito = df[df["id"] == credito_id].iloc[0]

        col_a, col_b = st.columns([1, 2])

        with col_a:
            st.write(f"**OC:** {credito['concepto']}")
            st.write(f"**Mes:** {credito['mes']}")
            st.write(f"**Fecha:** {credito['fecha']}")
            st.write(f"**Sede:** {credito['sede']}")
            st.write(f"**Total:** S/ {credito['total']:,.2f}")
            st.write(f"**Estado:** {credito['estado_real']}")
            st.write(f"**Vencimiento:** {credito['vencimiento']}")

        with col_b:
            if credito["imagen"]:
                st.image(
                    credito["imagen"],
                    caption="Orden de compra",
                    use_container_width=True
                )
            else:
                st.warning("Este crédito no tiene imagen de orden de compra.")
