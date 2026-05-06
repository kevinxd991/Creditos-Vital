import streamlit as st
import pandas as pd
from datetime import date, timedelta
from supabase import create_client

# ======================================
# CONFIG
# ======================================

st.set_page_config(
    page_title="VITAL CREDIT",
    page_icon="💰",
    layout="wide"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

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

# ======================================
# FUNCIONES
# ======================================

def cargar_creditos():

    response = supabase.table(
        "creditos"
    ).select("*").order(
        "id",
        desc=True
    ).execute()

    data = response.data

    if data:
        return pd.DataFrame(data)

    return pd.DataFrame()


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

# ======================================
# TITULO
# ======================================

st.title("💰 VITAL CREDIT")

menu = st.sidebar.radio(
    "Menú",
    [
        "Registrar crédito",
        "Ver créditos",
        "Modificar crédito",
        "Eliminar crédito"
    ]
)

# ======================================
# REGISTRAR
# ======================================

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

        guardar = st.form_submit_button(
            "Guardar crédito"
        )

        if guardar:

            if concepto.strip() == "":
                st.error(
                    "Debes ingresar la OC."
                )

            elif total <= 0:
                st.error(
                    "El total debe ser mayor a 0."
                )

            else:

                vencimiento = (
                    fecha +
                    timedelta(
                        days=int(dias_credito)
                    )
                )

                supabase.table(
                    "creditos"
                ).insert({

                    "concepto": concepto,
                    "fecha": str(fecha),
                    "sede": sede,
                    "total": float(total),
                    "estado": estado,
                    "dias_credito": int(
                        dias_credito
                    ),
                    "vencimiento": str(
                        vencimiento
                    ),
                    "adicional":
                    "Sí" if adicional else "No"

                }).execute()

                st.success(
                    "Crédito registrado correctamente."
                )

                st.rerun()

# ======================================
# VER CREDITOS
# ======================================

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

        total_general = df[
            "total"
        ].sum()

        total_pendiente = df[
            df["estado_real"]
            != "Pagado"
        ]["total"].sum()

        total_pagado = df[
            df["estado_real"]
            == "Pagado"
        ]["total"].sum()

        total_vencido = df[
            df["estado_real"]
            == "Vencido"
        ]["total"].sum()

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Total",
            f"S/ {total_general:,.2f}"
        )

        c2.metric(
            "Pendiente",
            f"S/ {total_pendiente:,.2f}"
        )

        c3.metric(
            "Pagado",
            f"S/ {total_pagado:,.2f}"
        )

        c4.metric(
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
                df_filtrado["sede"]
                == filtro_sede
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
                    "vencimiento",
                    "adicional"
                ]
            ],
            use_container_width=True
        )

# ======================================
# MODIFICAR
# ======================================

if menu == "Modificar crédito":

    st.subheader("Modificar crédito")

    df = cargar_creditos()

    if not df.empty:

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

        with st.form("editar_credito"):

            col1, col2 = st.columns(2)

            with col1:

                nuevo_estado = st.selectbox(
                    "Estado",
                    ESTADOS,
                    index=ESTADOS.index(
                        credito["estado"]
                    )
                )

                nueva_sede = st.selectbox(
                    "Sede",
                    SEDES,
                    index=SEDES.index(
                        credito["sede"]
                    )
                )

            with col2:

                nuevo_total = st.number_input(
                    "Total",
                    min_value=0.0,
                    value=float(
                        credito["total"]
                    ),
                    step=0.10
                )

                nuevo_adicional = st.checkbox(
                    "¿Pedido adicional?",
                    value=(
                        credito["adicional"]
                        == "Sí"
                    )
                )

            guardar = st.form_submit_button(
                "Guardar cambios"
            )

            if guardar:

                supabase.table(
                    "creditos"
                ).update({

                    "estado":
                    nuevo_estado,

                    "sede":
                    nueva_sede,

                    "total":
                    float(nuevo_total),

                    "adicional":
                    "Sí" if nuevo_adicional
                    else "No"

                }).eq(
                    "id",
                    int(credito_id)
                ).execute()

                st.success(
                    "Crédito actualizado."
                )

                st.rerun()

# ======================================
# ELIMINAR
# ======================================

if menu == "Eliminar crédito":

    st.subheader("Eliminar crédito")

    df = cargar_creditos()

    if not df.empty:

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
            f"Total: S/ {credito['total']:,.2f}"
        )

        confirmar = st.checkbox(
            "Confirmar eliminación"
        )

        if st.button(
            "Eliminar crédito"
        ):

            if confirmar:

                supabase.table(
                    "creditos"
                ).delete().eq(
                    "id",
                    int(credito_id)
                ).execute()

                st.success(
                    "Crédito eliminado."
                )

                st.rerun()

            else:

                st.error(
                    "Debes confirmar."
                )
