import streamlit as st
import pandas as pd
from datetime import date, timedelta
from supabase import create_client
import uuid

st.set_page_config(
    page_title="VITAL CREDIT",
    page_icon="💰",
    layout="wide"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

SEDES = ["Callao", "Villa el Salvador", "Punta Negra", "Ferrosal"]
ESTADOS = ["Pendiente", "Pago parcial", "Pagado"]


def cargar_creditos():
    response = (
        supabase.table("creditos")
        .select("*")
        .order("fecha", desc=False)
        .execute()
    )

    if response.data:
        return pd.DataFrame(response.data)

    return pd.DataFrame()


def estado_real(row):
    hoy = date.today()

    try:
        vencimiento = pd.to_datetime(row["vencimiento"]).date()
    except Exception:
        return row["estado"]

    if row["estado"] != "Pagado" and vencimiento < hoy:
        return "Vencido"

    return row["estado"]


def subir_imagen(imagen):
    if imagen is None:
        return None

    extension = imagen.name.split(".")[-1]
    nombre = f"{uuid.uuid4()}.{extension}"
    contenido = imagen.getvalue()

    supabase.storage.from_("ordenes").upload(
        nombre,
        contenido,
        {"content-type": imagen.type}
    )

    return supabase.storage.from_("ordenes").get_public_url(nombre)


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


# =========================
# REGISTRAR CRÉDITO
# =========================

if menu == "Registrar crédito":
    st.subheader("Registrar crédito")

    with st.form("form_registro"):
        col1, col2, col3 = st.columns(3)

        with col1:
            concepto = st.text_input("N° Orden de compra", placeholder="00035")
            fecha = st.date_input("Fecha", value=date.today())

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
            adicional = st.checkbox("¿Pedido adicional?")
            imagen = st.file_uploader(
                "Orden de compra",
                type=["png", "jpg", "jpeg"]
            )

        guardar = st.form_submit_button("Guardar crédito")

        if guardar:
            if concepto.strip() == "":
                st.error("Debes ingresar el número de OC.")
            elif total <= 0:
                st.error("El total debe ser mayor a 0.")
            else:
                vencimiento = fecha + timedelta(days=int(dias_credito))
                imagen_url = subir_imagen(imagen)

                supabase.table("creditos").insert({
                    "concepto": concepto,
                    "fecha": str(fecha),
                    "sede": sede,
                    "total": float(total),
                    "estado": estado,
                    "dias_credito": int(dias_credito),
                    "vencimiento": str(vencimiento),
                    "imagen": imagen_url,
                    "adicional": "Sí" if adicional else "No"
                }).execute()

                st.success("Crédito registrado correctamente.")
                st.rerun()


# =========================
# VER CRÉDITOS
# =========================

if menu == "Ver créditos":
    st.subheader("Créditos registrados")

    df = cargar_creditos()

    if df.empty:
        st.info("No hay créditos registrados.")
    else:
        df["estado_real"] = df.apply(estado_real, axis=1)

        total_general = df["total"].sum()
        total_pendiente = df[df["estado_real"] != "Pagado"]["total"].sum()
        total_pagado = df[df["estado_real"] == "Pagado"]["total"].sum()
        total_vencido = df[df["estado_real"] == "Vencido"]["total"].sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total general", f"S/ {total_general:,.2f}")
        c2.metric("Pendiente", f"S/ {total_pendiente:,.2f}")
        c3.metric("Pagado", f"S/ {total_pagado:,.2f}")
        c4.metric("Vencido", f"S/ {total_vencido:,.2f}")

        st.divider()

        col1, col2, col3 = st.columns(3)

        with col1:
            filtro_sede = st.selectbox("Sede", ["Todas"] + SEDES)

        with col2:
            filtro_estado = st.selectbox(
                "Estado",
                ["Todos", "Pendiente", "Pago parcial", "Pagado", "Vencido"]
            )

        with col3:
            filtro_adicional = st.selectbox(
                "Adicional",
                ["Todos", "Sí", "No"]
            )

        df_filtrado = df.copy()

        if filtro_sede != "Todas":
            df_filtrado = df_filtrado[df_filtrado["sede"] == filtro_sede]

        if filtro_estado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["estado_real"] == filtro_estado]

        if filtro_adicional != "Todos":
            df_filtrado = df_filtrado[df_filtrado["adicional"] == filtro_adicional]

        df_mostrar = df_filtrado[
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
        ].rename(columns={
            "id": "ID",
            "concepto": "OC",
            "fecha": "Fecha",
            "sede": "Sede",
            "total": "Total S/",
            "estado_real": "Estado",
            "dias_credito": "Días crédito",
            "vencimiento": "Vencimiento",
            "adicional": "Adicional"
        })

        st.dataframe(
            df_mostrar,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        if not df_filtrado.empty:
            st.subheader("Detalle del crédito")

            credito_id = st.selectbox(
                "Selecciona un crédito",
                df_filtrado["id"].tolist(),
                format_func=lambda x: (
                    f"OC {df[df['id'] == x]['concepto'].values[0]} - "
                    f"{df[df['id'] == x]['sede'].values[0]}"
                )
            )

            credito = df[df["id"] == credito_id].iloc[0]

            col_a, col_b = st.columns(2)

            with col_a:
                st.write(f"**OC:** {credito['concepto']}")
                st.write(f"**Fecha:** {credito['fecha']}")
                st.write(f"**Sede:** {credito['sede']}")
                st.write(f"**Total:** S/ {credito['total']:,.2f}")
                st.write(f"**Estado:** {credito['estado_real']}")
                st.write(f"**Vencimiento:** {credito['vencimiento']}")
                st.write(f"**Adicional:** {credito['adicional']}")

            with col_b:
                if credito.get("imagen"):
                    st.link_button(
                        "Descargar orden de compra",
                        credito["imagen"]
                    )
                else:
                    st.info("Este crédito no tiene orden de compra registrada.")


# =========================
# MODIFICAR CRÉDITO
# =========================

if menu == "Modificar crédito":
    st.subheader("Modificar crédito")

    df = cargar_creditos()

    if df.empty:
        st.info("No hay créditos registrados.")
    else:
        credito_id = st.selectbox(
            "Selecciona crédito",
            df["id"].tolist(),
            format_func=lambda x: (
                f"OC {df[df['id'] == x]['concepto'].values[0]} - "
                f"{df[df['id'] == x]['sede'].values[0]}"
            )
        )

        credito = df[df["id"] == credito_id].iloc[0]

        with st.form("form_modificar"):
            col1, col2, col3 = st.columns(3)

            with col1:
                nuevo_concepto = st.text_input(
                    "N° Orden de compra",
                    value=credito["concepto"]
                )

                nueva_fecha = st.date_input(
                    "Fecha",
                    value=pd.to_datetime(credito["fecha"]).date()
                )

            with col2:
                nueva_sede = st.selectbox(
                    "Sede",
                    SEDES,
                    index=SEDES.index(credito["sede"])
                )

                nuevo_total = st.number_input(
                    "Total S/",
                    min_value=0.0,
                    value=float(credito["total"]),
                    step=0.10,
                    format="%.2f"
                )

                nuevos_dias = st.number_input(
                    "Días de crédito",
                    min_value=1,
                    max_value=60,
                    value=int(credito["dias_credito"])
                )

            with col3:
                nuevo_estado = st.selectbox(
                    "Estado",
                    ESTADOS,
                    index=ESTADOS.index(credito["estado"])
                )

                nuevo_adicional = st.checkbox(
                    "¿Pedido adicional?",
                    value=credito["adicional"] == "Sí"
                )

                nueva_imagen = st.file_uploader(
                    "Cambiar orden de compra",
                    type=["png", "jpg", "jpeg"]
                )

            guardar = st.form_submit_button("Guardar cambios")

            if guardar:
                if nuevo_concepto.strip() == "":
                    st.error("La OC no puede estar vacía.")
                elif nuevo_total <= 0:
                    st.error("El total debe ser mayor a 0.")
                else:
                    nueva_imagen_url = credito.get("imagen")

                    if nueva_imagen is not None:
                        nueva_imagen_url = subir_imagen(nueva_imagen)

                    nuevo_vencimiento = nueva_fecha + timedelta(days=int(nuevos_dias))

                    supabase.table("creditos").update({
                        "concepto": nuevo_concepto,
                        "fecha": str(nueva_fecha),
                        "sede": nueva_sede,
                        "total": float(nuevo_total),
                        "estado": nuevo_estado,
                        "dias_credito": int(nuevos_dias),
                        "vencimiento": str(nuevo_vencimiento),
                        "imagen": nueva_imagen_url,
                        "adicional": "Sí" if nuevo_adicional else "No"
                    }).eq("id", int(credito_id)).execute()

                    st.success("Crédito actualizado correctamente.")
                    st.rerun()


# =========================
# ELIMINAR CRÉDITO
# =========================

if menu == "Eliminar crédito":
    st.subheader("Eliminar crédito")

    df = cargar_creditos()

    if df.empty:
        st.info("No hay créditos registrados.")
    else:
        credito_id = st.selectbox(
            "Selecciona crédito",
            df["id"].tolist(),
            format_func=lambda x: (
                f"OC {df[df['id'] == x]['concepto'].values[0]} - "
                f"{df[df['id'] == x]['sede'].values[0]}"
            )
        )

        credito = df[df["id"] == credito_id].iloc[0]

        st.warning("Esta acción eliminará el crédito definitivamente.")

        st.write(f"**OC:** {credito['concepto']}")
        st.write(f"**Fecha:** {credito['fecha']}")
        st.write(f"**Sede:** {credito['sede']}")
        st.write(f"**Total:** S/ {credito['total']:,.2f}")
        st.write(f"**Estado:** {credito['estado']}")

        confirmar = st.checkbox("Confirmo que quiero eliminar este crédito")

        if st.button("Eliminar crédito"):
            if confirmar:
                supabase.table("creditos").delete().eq(
                    "id",
                    int(credito_id)
                ).execute()

                st.success("Crédito eliminado correctamente.")
                st.rerun()
            else:
                st.error("Debes confirmar antes de eliminar.")
