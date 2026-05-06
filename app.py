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

# =========================
# SUPABASE
# =========================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# LOGIN
# =========================

if "logueado" not in st.session_state:
    st.session_state["logueado"] = False

if not st.session_state["logueado"]:

    st.title("🔐 LOGIN VITAL CREDIT")

    usuario_input = st.text_input("Usuario")
    contraseña_input = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):

        response = supabase.table("usuarios").select("*").eq(
            "usuario",
            usuario_input
        ).eq(
            "contraseña",
            contraseña_input
        ).execute()

        if response.data:
            st.session_state["logueado"] = True
            st.session_state["usuario"] = usuario_input
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")

    st.stop()

# =========================
# VARIABLES
# =========================

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

MESES = {
    "Todos": 0,
    "Enero": 1,
    "Febrero": 2,
    "Marzo": 3,
    "Abril": 4,
    "Mayo": 5,
    "Junio": 6,
    "Julio": 7,
    "Agosto": 8,
    "Septiembre": 9,
    "Octubre": 10,
    "Noviembre": 11,
    "Diciembre": 12,
}

# =========================
# FUNCIONES
# =========================

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
        vencimiento = pd.to_datetime(
            row["vencimiento"]
        ).date()

    except:
        return row["estado"]

    if row["estado"] != "Pagado" and vencimiento < hoy:
        return "Vencido"

    return row["estado"]


def subir_archivo(archivo, bucket):

    if archivo is None:
        return None

    try:

        extension = archivo.name.split(".")[-1]

        nombre = f"{uuid.uuid4()}.{extension}"

        contenido = archivo.getvalue()

        supabase.storage.from_(bucket).upload(
            nombre,
            contenido,
            {"content-type": archivo.type}
        )

        return supabase.storage.from_(bucket).get_public_url(nombre)

    except Exception as e:

        st.error("No se pudo subir el archivo.")
        st.error(str(e))

        return None


def url_valida(valor):

    return (
        valor is not None
        and str(valor).strip() != ""
        and str(valor).lower() != "none"
        and str(valor).lower() != "null"
        and str(valor) != "nan"
    )

# =========================
# TITULO
# =========================

st.title("💰 VITAL CREDIT")

st.sidebar.success(
    f"Usuario: {st.session_state['usuario']}"
)

if st.sidebar.button("Cerrar sesión"):
    st.session_state["logueado"] = False
    st.rerun()

# =========================
# MENU
# =========================

menu = st.sidebar.radio(
    "Menú",
    [
        "Registrar crédito",
        "Ver créditos",
        "Registrar pago múltiple",
        "Modificar crédito",
        "Eliminar crédito"
    ]
)

# =========================
# REGISTRAR CREDITO
# =========================

if menu == "Registrar crédito":

    st.subheader("Registrar crédito")

    if "registro_exitoso" in st.session_state:
        st.success(
            st.session_state["registro_exitoso"]
        )
        del st.session_state["registro_exitoso"]

    with st.form(
        "form_registro",
        clear_on_submit=True
    ):

        col1, col2, col3 = st.columns(3)

        with col1:

            concepto = st.text_input(
                "N° Orden de compra"
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
                type=["png", "jpg", "jpeg", "pdf"]
            )

        guardar = st.form_submit_button(
            "Guardar crédito"
        )

        if guardar:

            if concepto.strip() == "":
                st.error("Debes ingresar OC.")

            elif total <= 0:
                st.error("El total debe ser mayor a 0.")

            else:

                vencimiento = fecha + timedelta(
                    days=int(dias_credito)
                )

                imagen_url = subir_archivo(
                    imagen,
                    "ordenes"
                )

                supabase.table(
                    "creditos"
                ).insert({

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

                st.session_state[
                    "registro_exitoso"
                ] = "Crédito registrado correctamente."

                st.rerun()

# =========================
# VER CREDITOS
# =========================

if menu == "Ver créditos":

    st.subheader("Créditos registrados")

    df = cargar_creditos()

    if df.empty:

        st.info("No hay créditos.")

    else:

        df["estado_real"] = df.apply(
            estado_real,
            axis=1
        )

        df["fecha_dt"] = pd.to_datetime(
            df["fecha"]
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            filtro_sede = st.selectbox(
                "Sede",
                ["Todas"] + SEDES
            )

        with col2:

            filtro_estado = st.selectbox(
                "Estado",
                [
                    "Todos",
                    "Pendiente",
                    "Pago parcial",
                    "Pagado",
                    "Vencido"
                ]
            )

        with col3:

            filtro_adicional = st.selectbox(
                "Adicional",
                ["Todos", "Sí", "No"]
            )

        with col4:

            filtro_mes = st.selectbox(
                "Mes",
                list(MESES.keys())
            )

        df_filtrado = df.copy()

        if filtro_sede != "Todas":
            df_filtrado = df_filtrado[
                df_filtrado["sede"] == filtro_sede
            ]

        if filtro_estado != "Todos":
            df_filtrado = df_filtrado[
                df_filtrado["estado_real"] == filtro_estado
            ]

        if filtro_adicional != "Todos":
            df_filtrado = df_filtrado[
                df_filtrado["adicional"] == filtro_adicional
            ]

        if filtro_mes != "Todos":
            df_filtrado = df_filtrado[
                df_filtrado["fecha_dt"].dt.month
                == MESES[filtro_mes]
            ]

        total_general = df_filtrado["total"].sum()

        total_pendiente = df_filtrado[
            df_filtrado["estado_real"] != "Pagado"
        ]["total"].sum()

        total_pagado = df_filtrado[
            df_filtrado["estado_real"] == "Pagado"
        ]["total"].sum()

        total_vencido = df_filtrado[
            df_filtrado["estado_real"] == "Vencido"
        ]["total"].sum()

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Total general",
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

        tabla = df_filtrado[
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
        ]

        st.dataframe(
            tabla,
            use_container_width=True,
            hide_index=True
        )

# =========================
# REGISTRAR PAGO MULTIPLE
# =========================

if menu == "Registrar pago múltiple":

    st.subheader("Registrar pago múltiple")

    df = cargar_creditos()

    if df.empty:

        st.info("No hay créditos.")

    else:

        df["estado_real"] = df.apply(
            estado_real,
            axis=1
        )

        pendientes = df[
            df["estado"] != "Pagado"
        ].copy()

        if pendientes.empty:

            st.info("No hay pendientes.")

        else:

            tabla = pendientes[
                [
                    "id",
                    "concepto",
                    "fecha",
                    "sede",
                    "total",
                    "vencimiento"
                ]
            ]

            tabla.insert(0, "Pagar", False)

            tabla_editada = st.data_editor(
                tabla,
                use_container_width=True,
                hide_index=True,
                disabled=[
                    "id",
                    "concepto",
                    "fecha",
                    "sede",
                    "total",
                    "vencimiento"
                ]
            )

            seleccionados = tabla_editada[
                tabla_editada["Pagar"] == True
            ]

            monto = seleccionados["total"].sum()

            st.metric(
                "Monto seleccionado",
                f"S/ {monto:,.2f}"
            )

            with st.form("form_pago"):

                fecha_pago = st.date_input(
                    "Fecha de pago",
                    value=date.today()
                )

                voucher = st.file_uploader(
                    "Voucher",
                    type=["png", "jpg", "jpeg", "pdf"]
                )

                observacion = st.text_area(
                    "Observación"
                )

                registrar = st.form_submit_button(
                    "Registrar pago"
                )

                if registrar:

                    if seleccionados.empty:
                        st.error(
                            "Selecciona créditos."
                        )

                    elif voucher is None:
                        st.error(
                            "Sube voucher."
                        )

                    else:

                        voucher_url = subir_archivo(
                            voucher,
                            "vouchers"
                        )

                        pago = supabase.table(
                            "pagos"
                        ).insert({

                            "fecha_pago": str(fecha_pago),
                            "monto_total": float(monto),
                            "voucher": voucher_url,
                            "observacion": observacion

                        }).execute()

                        pago_id = pago.data[0]["id"]

                        ids = seleccionados[
                            "id"
                        ].astype(int).tolist()

                        for credito_id in ids:

                            supabase.table(
                                "creditos"
                            ).update({

                                "estado": "Pagado",
                                "pago_id": pago_id

                            }).eq(
                                "id",
                                credito_id
                            ).execute()

                        st.success(
                            "Pago registrado correctamente."
                        )

                        st.rerun()

# =========================
# MODIFICAR
# =========================

if menu == "Modificar crédito":

    st.subheader("Modificar crédito")

    df = cargar_creditos()

    if df.empty:

        st.info("No hay créditos.")

    else:

        credito_id = st.selectbox(
            "Selecciona crédito",
            df["id"].tolist()
        )

        credito = df[
            df["id"] == credito_id
        ].iloc[0]

        with st.form("form_modificar"):

            nuevo_estado = st.selectbox(
                "Estado",
                ESTADOS,
                index=ESTADOS.index(
                    credito["estado"]
                )
            )

            guardar = st.form_submit_button(
                "Guardar cambios"
            )

            if guardar:

                supabase.table(
                    "creditos"
                ).update({

                    "estado": nuevo_estado

                }).eq(
                    "id",
                    credito_id
                ).execute()

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

        st.info("No hay créditos.")

    else:

        credito_id = st.selectbox(
            "Selecciona crédito",
            df["id"].tolist()
        )

        confirmar = st.checkbox(
            "Confirmar eliminación"
        )

        if st.button("Eliminar crédito"):

            if confirmar:

                supabase.table(
                    "creditos"
                ).delete().eq(
                    "id",
                    credito_id
                ).execute()

                st.success(
                    "Crédito eliminado."
                )

                st.rerun()

            else:

                st.error(
                    "Debes confirmar."
                )
