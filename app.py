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

SEDES = [
    "Callao",
    "Villa el Salvador",
    "Punta Negra",
    "Ferrosal"
]

ESTADOS = [
    "Pendiente",
    "Pago parcial",
    "Pagado"
]

conn = sqlite3.connect(DB, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS creditos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concepto TEXT,
    fecha TEXT,
    sede TEXT,
    total REAL,
    estado TEXT,
    dias_credito INTEGER,
    vencimiento TEXT,
    imagen TEXT,
    adicional TEXT
)
""")

conn.commit()

try:
    cursor.execute("""
    ALTER TABLE creditos
    ADD COLUMN adicional TEXT DEFAULT 'No'
    """)
    conn.commit()
except sqlite3.OperationalError:
    pass


def cargar_creditos():
    return pd.read_sql_query(
        "SELECT * FROM creditos ORDER BY fecha DESC",
        conn
    )


def estado_real(row):
    hoy = date.today()

    try:
        vencimiento = pd.to_datetime(
            row["vencimiento"]
        ).date()
    except Exception:
        return row["estado"]

    if (
        row["estado"] != "Pagado"
        and vencimiento < hoy
    ):
        return "Vencido"

    return row["estado"]


def guardar_imagen(imagen):
    if imagen is None:
        return ""

    extension = imagen.name.split(".")[-1]

    nombre_archivo = f"{uuid.uuid4()}.{extension}"

    ruta_imagen = str(
        UPLOAD_DIR / nombre_archivo
    )

    with open(ruta_imagen, "wb") as f:
        f.write(imagen.getbuffer())

    return ruta_imagen


st.title("💰 Sistema de Control de Créditos")

menu = st.sidebar.radio(
    "Menú",
    [
        "Registrar crédito",
        "Ver créditos",
        "Modificar crédito",
        "Eliminar crédito"
    ]
)

# =========================
# REGISTRAR
# =========================

if menu == "Registrar crédito":

    st.subheader("Registrar crédito")

    with st.form("form_credito"):

        col1, col2, col3 = st.columns(3)

        with col1:

            concepto = st.text_input(
                "N° Orden de compra",
                placeholder="00035"
            )

            fecha = st.date_input(
                "Fecha",
                value=date.today()
            )

        with col2:

            sede = st.selectbox(
                "Sede",
                SEDES
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
                ESTADOS
            )

            adicional = st.checkbox(
                "¿Pedido adicional?"
            )

            imagen = st.file_uploader(
                "Orden de compra",
                type=["png", "jpg", "jpeg"]
            )

        guardar = st.form_submit_button(
            "Guardar crédito"
        )

        if guardar:

            if concepto.strip() == "":
                st.error(
                    "Debes ingresar el número de OC."
                )

            elif total <= 0:
                st.error(
                    "El total debe ser mayor a 0."
                )

            else:

                ruta_imagen = guardar_imagen(
                    imagen
                )

                vencimiento = (
                    fecha +
                    timedelta(
                        days=int(dias_credito)
                    )
                )

                cursor.execute("""
                INSERT INTO creditos (
                    concepto,
                    fecha,
                    sede,
                    total,
                    estado,
                    dias_credito,
                    vencimiento,
                    imagen,
                    adicional
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    concepto,
                    str(fecha),
                    sede,
                    float(total),
                    estado,
                    int(dias_credito),
                    str(vencimiento),
                    ruta_imagen,
                    "Sí" if adicional else "No"
                ))

                conn.commit()

                st.success(
                    "Crédito registrado correctamente."
                )

                st.rerun()

# =========================
# VER CREDITOS
# =========================

if menu == "Ver créditos":

    st.subheader("Créditos registrados")

    df = cargar_creditos()

    if df.empty:

        st.info(
            "No hay créditos registrados."
        )

    else:

        df["estado_real"] = df.apply(
            estado_real,
            axis=1
        )

        total_general = df["total"].sum()

        total_pendiente = df[
            df["estado_real"] != "Pagado"
        ]["total"].sum()

        total_pagado = df[
            df["estado_real"] == "Pagado"
        ]["total"].sum()

        total_vencido = df[
            df["estado_real"] == "Vencido"
        ]["total"].sum()

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Total general",
            f"S/ {total_general:,.2f}"
        )

        col2.metric(
            "Pendiente",
            f"S/ {total_pendiente:,.2f}"
        )

        col3.metric(
            "Pagado",
            f"S/ {total_pagado:,.2f}"
        )

        col4.metric(
            "Vencido",
            f"S/ {total_vencido:,.2f}"
        )

        st.divider()

        colf1, colf2 = st.columns(2)

        with colf1:

            filtro_sede = st.selectbox(
                "Filtrar sede",
                ["Todas"] + SEDES
            )

        with colf2:

            filtro_estado = st.selectbox(
                "Filtrar estado",
                [
                    "Todos",
                    "Pendiente",
                    "Pago parcial",
                    "Pagado",
                    "Vencido"
                ]
            )

        df_filtrado = df.copy()

        if filtro_sede != "Todas":
            df_filtrado = df_filtrado[
                df_filtrado["sede"] == filtro_sede
            ]

        if filtro_estado != "Todos":
            df_filtrado = df_filtrado[
                df_filtrado["estado_real"]
                == filtro_estado
            ]

        st.dataframe(
            df_filtrado[
                [
                    "id",
                    "concepto",
                    "fecha",
                    "sede",
                    "total",
                    "estado_real",
                    "dias_credito",
                    "vencimiento",
                    "adicional"
                ]
            ],
            use_container_width=True
        )

        st.divider()

        if not df_filtrado.empty:

            credito_id = st.selectbox(
                "Selecciona un crédito",
                df_filtrado["id"].tolist(),
                format_func=lambda x:
                (
                    f"OC "
                    f"{df[df['id']==x]['concepto'].values[0]}"
                    f" - "
                    f"{df[df['id']==x]['sede'].values[0]}"
                )
            )

            credito = df[
                df["id"] == credito_id
            ].iloc[0]

            col_a, col_b = st.columns([1, 1])

            with col_a:

                st.write(
                    f"**OC:** "
                    f"{credito['concepto']}"
                )

                st.write(
                    f"**Fecha:** "
                    f"{credito['fecha']}"
                )

                st.write(
                    f"**Sede:** "
                    f"{credito['sede']}"
                )

                st.write(
                    f"**Total:** "
                    f"S/ {credito['total']:,.2f}"
                )

                st.write(
                    f"**Estado:** "
                    f"{credito['estado_real']}"
                )

                st.write(
                    f"**Vencimiento:** "
                    f"{credito['vencimiento']}"
                )

                st.write(
                    f"**Adicional:** "
                    f"{credito['adicional']}"
                )

            with col_b:

                if credito["imagen"]:

                    with open(
                        credito["imagen"],
                        "rb"
                    ) as archivo:

                        st.download_button(
                            label="Descargar orden de compra",
                            data=archivo,
                            file_name=(
                                f"OC_"
                                f"{credito['concepto']}_"
                                f"{credito['sede']}.jpg"
                            ),
                            mime="image/jpeg"
                        )

                else:

                    st.warning(
                        "No tiene orden de compra."
                    )

# =========================
# MODIFICAR
# =========================

if menu == "Modificar crédito":

    st.subheader("Modificar crédito")

    df = cargar_creditos()

    if df.empty:

        st.info(
            "No hay créditos registrados."
        )

    else:

        credito_id = st.selectbox(
            "Selecciona crédito",
            df["id"].tolist(),
            format_func=lambda x:
            (
                f"OC "
                f"{df[df['id']==x]['concepto'].values[0]}"
                f" - "
                f"{df[df['id']==x]['sede'].values[0]}"
            )
        )

        credito = df[
            df["id"] == credito_id
        ].iloc[0]

        with st.form("modificar"):

            col1, col2, col3 = st.columns(3)

            with col1:

                nuevo_concepto = st.text_input(
                    "OC",
                    value=credito["concepto"]
                )

                nueva_fecha = st.date_input(
                    "Fecha",
                    value=pd.to_datetime(
                        credito["fecha"]
                    ).date()
                )

            with col2:

                nueva_sede = st.selectbox(
                    "Sede",
                    SEDES,
                    index=SEDES.index(
                        credito["sede"]
                    )
                )

                nuevo_total = st.number_input(
                    "Total",
                    min_value=0.0,
                    value=float(
                        credito["total"]
                    ),
                    step=0.10
                )

                nuevos_dias = st.number_input(
                    "Días crédito",
                    min_value=1,
                    max_value=60,
                    value=int(
                        credito["dias_credito"]
                    )
                )

            with col3:

                nuevo_estado = st.selectbox(
                    "Estado",
                    ESTADOS,
                    index=ESTADOS.index(
                        credito["estado"]
                    )
                )

                nuevo_adicional = st.checkbox(
                    "¿Pedido adicional?",
                    value=(
                        credito["adicional"]
                        == "Sí"
                    )
                )

                nueva_imagen = st.file_uploader(
                    "Nueva imagen",
                    type=["png", "jpg", "jpeg"]
                )

            guardar = st.form_submit_button(
                "Guardar cambios"
            )

            if guardar:

                ruta_imagen = credito["imagen"]

                if nueva_imagen is not None:
                    ruta_imagen = guardar_imagen(
                        nueva_imagen
                    )

                nuevo_vencimiento = (
                    nueva_fecha +
                    timedelta(
                        days=int(nuevos_dias)
                    )
                )

                cursor.execute("""
                UPDATE creditos
                SET
                    concepto = ?,
                    fecha = ?,
                    sede = ?,
                    total = ?,
                    estado = ?,
                    dias_credito = ?,
                    vencimiento = ?,
                    imagen = ?,
                    adicional = ?
                WHERE id = ?
                """, (
                    nuevo_concepto,
                    str(nueva_fecha),
                    nueva_sede,
                    float(nuevo_total),
                    nuevo_estado,
                    int(nuevos_dias),
                    str(nuevo_vencimiento),
                    ruta_imagen,
                    "Sí" if nuevo_adicional else "No",
                    int(credito_id)
                ))

                conn.commit()

                st.success(
                    "Crédito actualizado."
                )

                st.rerun()

# =========================
# ELIMINAR
# =========================

if menu == "Eliminar crédito":

    st.subheader("Eliminar crédito")

    df = cargar_creditos()

    if df.empty:

        st.info(
            "No hay créditos registrados."
        )

    else:

        credito_id = st.selectbox(
            "Selecciona crédito",
            df["id"].tolist(),
            format_func=lambda x:
            (
                f"OC "
                f"{df[df['id']==x]['concepto'].values[0]}"
                f" - "
                f"{df[df['id']==x]['sede'].values[0]}"
            )
        )

        credito = df[
            df["id"] == credito_id
        ].iloc[0]

        st.warning(
            "Esta acción eliminará el crédito."
        )

        st.write(
            f"OC: {credito['concepto']}"
        )

        st.write(
            f"Sede: {credito['sede']}"
        )

        st.write(
            f"Total: "
            f"S/ {credito['total']:,.2f}"
        )

        confirmar = st.checkbox(
            "Confirmar eliminación"
        )

        if st.button("Eliminar crédito"):

            if confirmar:

                cursor.execute(
                    """
                    DELETE FROM creditos
                    WHERE id = ?
                    """,
                    (int(credito_id),)
                )

                conn.commit()

                st.success(
                    "Crédito eliminado."
                )

                st.rerun()

            else:

                st.error(
                    "Debes confirmar."
                )
