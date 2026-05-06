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

SEDES = ["Callao", "Villa el Salvador", "Punta Negra", "Ferrosal"]
ESTADOS = ["Pendiente", "Pago parcial", "Pagado"]
MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

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


def estado_real(row):
    hoy = date.today()

    try:
        vencimiento = pd.to_datetime(row["vencimiento"]).date()
    except Exception:
        return row["estado"]

    if row["estado"] != "Pagado" and vencimiento < hoy:
        return "Vencido"

    return row["estado"]


def guardar_imagen(imagen):
    if imagen is None:
        return ""

    extension = imagen.name.split(".")[-1]
    nombre_archivo = f"{uuid.uuid4()}.{extension}"
    ruta_imagen = str(UPLOAD_DIR / nombre_archivo)

    with open(ruta_imagen, "wb") as f:
        f.write(imagen.getbuffer())

    return ruta_imagen


st.title("💰 Sistema de Control de Créditos")
st.caption("Registro de créditos, órdenes de compra y control de vencimientos")

menu = st.sidebar.radio(
    "Menú",
    [
        "Registrar crédito",
        "Ver créditos",
        "Modificar crédito",
        "Eliminar crédito"
    ]
)

if menu == "Registrar crédito":
    st.subheader("Registrar nuevo crédito")

    with st.form("form_credito"):
        col1, col2, col3 = st.columns(3)

        with col1:
            mes = st.selectbox("Mes", MESES)

            concepto = st.text_input(
                "Concepto / N° Orden de Compra",
                placeholder="00035"
            )

            fecha = st.date_input(
                "Fecha de emisión",
                value=date.today()
            )

        with col2:
            sede = st.selectbox("Sede", SEDES)

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
            estado = st.selectbox("Estado", ESTADOS)

            imagen = st.file_uploader(
                "Subir orden de compra",
                type=["png", "jpg", "jpeg"]
            )

        guardar = st.form_submit_button("Guardar crédito")

        if guardar:
            if concepto.strip() == "":
                st.error("Debes ingresar el número de orden de compra.")
            elif total <= 0:
                st.error("El total debe ser mayor a 0.")
            else:
                ruta_imagen = guardar_imagen(imagen)
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
                st.rerun()


if menu == "Ver créditos":
    st.subheader("Créditos registrados")

    df = cargar_creditos()

    if df.empty:
        st.info("Todavía no tienes créditos registrados.")
    else:
        df["estado_real"] = df.apply(estado_real, axis=1)

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

        colf1, colf2, colf3 = st.columns(3)

        with colf1:
            filtro_sede = st.selectbox("Filtrar por sede", ["Todas"] + SEDES)

        with colf2:
            filtro_estado = st.selectbox(
                "Filtrar por estado",
                ["Todos", "Pendiente", "Pago parcial", "Pagado", "Vencido"]
            )

        with colf3:
            filtro_mes = st.selectbox("Filtrar por mes", ["Todos"] + MESES)

        df_filtrado = df.copy()

        if filtro_sede != "Todas":
            df_filtrado = df_filtrado[df_filtrado["sede"] == filtro_sede]

        if filtro_estado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["estado_real"] == filtro_estado]

        if filtro_mes != "Todos":
            df_filtrado = df_filtrado[df_filtrado["mes"] == filtro_mes]

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

        if not df_filtrado.empty:
            st.subheader("Ver orden de compra")

            credito_id = st.selectbox(
                "Selecciona un crédito",
                df_filtrado["id"].tolist(),
                format_func=lambda x: (
                    f"OC {df[df['id'] == x]['concepto'].values[0]} - "
                    f"{df[df['id'] == x]['sede'].values[0]}"
                )
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
        else:
            st.warning("No hay créditos con esos filtros.")


if menu == "Modificar crédito":
    st.subheader("Modificar crédito")

    df = cargar_creditos()

    if df.empty:
        st.info("No hay créditos registrados.")
    else:
        df["estado_real"] = df.apply(estado_real, axis=1)

        credito_id = st.selectbox(
            "Selecciona el crédito a modificar",
            df["id"].tolist(),
            format_func=lambda x: (
                f"OC {df[df['id'] == x]['concepto'].values[0]} - "
                f"{df[df['id'] == x]['sede'].values[0]}"
            )
        )

        credito = df[df["id"] == credito_id].iloc[0]

        st.info(
            f"Editando OC {credito['concepto']} | "
            f"Sede: {credito['sede']} | "
            f"Total: S/ {credito['total']:,.2f} | "
            f"Estado actual: {credito['estado_real']}"
        )

        with st.form("form_modificar"):
            col1, col2, col3 = st.columns(3)

            with col1:
                nuevo_mes = st.selectbox(
                    "Mes",
                    MESES,
                    index=MESES.index(credito["mes"]) if credito["mes"] in MESES else 0
                )

                nuevo_concepto = st.text_input(
                    "Concepto / N° OC",
                    value=str(credito["concepto"])
                )

                nueva_fecha = st.date_input(
                    "Fecha de emisión",
                    value=pd.to_datetime(credito["fecha"]).date()
                )

            with col2:
                nueva_sede = st.selectbox(
                    "Sede",
                    SEDES,
                    index=SEDES.index(credito["sede"]) if credito["sede"] in SEDES else 0
                )

                nuevo_total = st.number_input(
                    "Total S/",
                    min_value=0.0,
                    value=float(credito["total"]),
                    step=0.10,
                    format="%.2f"
                )

                nuevos_dias_credito = st.number_input(
                    "Días de crédito",
                    min_value=1,
                    max_value=60,
                    value=int(credito["dias_credito"])
                )

            with col3:
                nuevo_estado = st.selectbox(
                    "Estado",
                    ESTADOS,
                    index=ESTADOS.index(credito["estado"]) if credito["estado"] in ESTADOS else 0
                )

                nueva_imagen = st.file_uploader(
                    "Cambiar imagen de OC",
                    type=["png", "jpg", "jpeg"]
                )

                mantener_imagen = st.checkbox(
                    "Mantener imagen actual",
                    value=True
                )

            guardar_cambios = st.form_submit_button("Guardar cambios")

            if guardar_cambios:
                if nuevo_concepto.strip() == "":
                    st.error("El número de OC no puede estar vacío.")
                elif nuevo_total <= 0:
                    st.error("El total debe ser mayor a 0.")
                else:
                    ruta_imagen = credito["imagen"]

                    if nueva_imagen is not None:
                        ruta_imagen = guardar_imagen(nueva_imagen)

                    if not mantener_imagen and nueva_imagen is None:
                        ruta_imagen = ""

                    nuevo_vencimiento = nueva_fecha + timedelta(
                        days=int(nuevos_dias_credito)
                    )

                    cursor.execute("""
                        UPDATE creditos
                        SET
                            mes = ?,
                            concepto = ?,
                            fecha = ?,
                            sede = ?,
                            total = ?,
                            estado = ?,
                            dias_credito = ?,
                            vencimiento = ?,
                            imagen = ?
                        WHERE id = ?
                    """, (
                        nuevo_mes,
                        nuevo_concepto,
                        str(nueva_fecha),
                        nueva_sede,
                        float(nuevo_total),
                        nuevo_estado,
                        int(nuevos_dias_credito),
                        str(nuevo_vencimiento),
                        ruta_imagen,
                        int(credito_id)
                    ))

                    conn.commit()
                    st.success("Crédito actualizado correctamente.")
                    st.rerun()

        st.divider()

        st.subheader("Vista actual de la orden")

        col_a, col_b = st.columns([1, 2])

        with col_a:
            st.write(f"**OC:** {credito['concepto']}")
            st.write(f"**Sede:** {credito['sede']}")
            st.write(f"**Total:** S/ {credito['total']:,.2f}")
            st.write(f"**Estado:** {credito['estado_real']}")
            st.write(f"**Vencimiento:** {credito['vencimiento']}")

        with col_b:
            if credito["imagen"]:
                st.image(
                    credito["imagen"],
                    caption="Orden de compra actual",
                    use_container_width=True
                )
            else:
                st.warning("Este crédito no tiene imagen registrada.")


if menu == "Eliminar crédito":
    st.subheader("Eliminar crédito")

    df = cargar_creditos()

    if df.empty:
        st.info("No hay créditos registrados.")
    else:
        df["estado_real"] = df.apply(estado_real, axis=1)

        credito_id = st.selectbox(
            "Selecciona el crédito a eliminar",
            df["id"].tolist(),
            format_func=lambda x: (
                f"OC {df[df['id'] == x]['concepto'].values[0]} - "
                f"{df[df['id'] == x]['sede'].values[0]}"
            )
        )

        credito = df[df["id"] == credito_id].iloc[0]

        st.warning("Esta acción eliminará el crédito definitivamente.")

        col1, col2 = st.columns([1, 2])

        with col1:
            st.write(f"**OC:** {credito['concepto']}")
            st.write(f"**Mes:** {credito['mes']}")
            st.write(f"**Fecha:** {credito['fecha']}")
            st.write(f"**Sede:** {credito['sede']}")
            st.write(f"**Total:** S/ {credito['total']:,.2f}")
            st.write(f"**Estado:** {credito['estado_real']}")
            st.write(f"**Vencimiento:** {credito['vencimiento']}")

        with col2:
            if credito["imagen"]:
                st.image(
                    credito["imagen"],
                    caption="Orden de compra",
                    use_container_width=True
                )
            else:
                st.info("Este crédito no tiene imagen registrada.")

        confirmar = st.checkbox(
            "Confirmo que quiero eliminar este crédito"
        )

        if st.button("Eliminar crédito"):
            if confirmar:
                cursor.execute(
                    "DELETE FROM creditos WHERE id = ?",
                    (int(credito_id),)
                )
                conn.commit()
                st.success("Crédito eliminado correctamente.")
                st.rerun()
            else:
                st.error("Primero debes marcar la confirmación.")
