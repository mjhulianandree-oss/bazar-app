import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bazar Pro - Control Total", layout="wide")

# --- 2. BLINDAJE VISUAL ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stAppDeployButton {display:none !important;}
    [data-testid="stHeader"] {display:none !important;}
    .block-container {padding-top: 1rem !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. BASE DE DATOS (v5 con Estado de Tienda) ---
def init_db():
    conn = sqlite3.connect("bazar_final_pro.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS inventario (id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT, categoria TEXT, stock_inicial INTEGER, precio_costo REAL, precio_venta REAL, ventas_acumuladas INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_producto TEXT, cantidad INTEGER, fecha TEXT, ganancia_vta REAL, total_vta REAL)")
    # Tabla para el estado de la tienda
    cursor.execute("CREATE TABLE IF NOT EXISTS estado_tienda (id INTEGER PRIMARY KEY, abierto INTEGER, ultima_actividad TEXT)")
    # Inicializar estado si no existe
    cursor.execute("INSERT OR IGNORE INTO estado_tienda (id, abierto, ultima_actividad) VALUES (1, 0, 'No registrado')")
    conn.commit()
    conn.close()

def cambiar_estado_tienda(nuevo_estado):
    conn = sqlite3.connect("bazar_final_pro.db")
    cursor = conn.cursor()
    hora = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")
    cursor.execute("UPDATE estado_tienda SET abierto = ?, ultima_actividad = ? WHERE id = 1", (nuevo_estado, hora))
    conn.commit()
    conn.close()

def registrar_venta(id_prod, nombre_prod, p_venta, p_costo):
    conn = sqlite3.connect("bazar_final_pro.db")
    cursor = conn.cursor()
    ganancia = p_venta - p_costo
    fecha = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")
    cursor.execute("INSERT INTO ventas (nombre_producto, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, ?, ?, ?)", (nombre_prod, 1, fecha, ganancia, p_venta))
    cursor.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (id_prod,))
    conn.commit()
    conn.close()

init_db()

# --- 4. CARGA DE DATOS ---
conn = sqlite3.connect("bazar_final_pro.db")
df_inv = pd.read_sql_query("SELECT * FROM inventario", conn)
df_vts = pd.read_sql_query("SELECT * FROM ventas", conn)
estado = conn.execute("SELECT abierto, ultima_actividad FROM estado_tienda WHERE id = 1").fetchone()
conn.close()

tienda_abierta = True if estado[0] == 1 else False

# --- 5. INTERFAZ SUPERIOR (CONTROL DE TIENDA) ---
st.title("🏪 Control del Bazar")

col_e1, col_e2 = st.columns([1, 2])
with col_e1:
    if tienda_abierta:
        if st.button("🔒 CERRAR TIENDA", use_container_width=True, type="primary"):
            cambiar_estado_tienda(0)
            st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            cambiar_estado_tienda(1)
            st.rerun()

with col_e2:
    texto_estado = "🟢 ABIERTO" if tienda_abierta else "🔴 CERRADO"
    st.subheader(f"Estado: {texto_estado} (Desde: {estado[1]})")

st.divider()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.header("📦 Nuevo Producto")
    nuevo_nombre = st.text_input("Nombre")
    categoria = st.selectbox("Sección", ["🍭 Dulces", "🥤 Bebidas", "🥛 Lácteos", "📝 Útiles", "🏠 Otros"])
    n_stock = st.number_input("Stock", min_value=1, value=10)
    n_costo = st.number_input("Costo (Bs)", min_value=0.1, value=1.0)
    n_venta = st.number_input("Venta (Bs)", min_value=0.1, value=1.5)
    if st.button("Guardar"):
        if nuevo_nombre:
            conn = sqlite3.connect("bazar_final_pro.db")
            conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", (nuevo_nombre, categoria, n_stock, n_costo, n_venta))
            conn.commit()
            conn.close()
            st.rerun()

# --- 7. CUERPO PRINCIPAL ---
c_inv, c_res = st.columns([2, 1.3])

with c_inv:
    st.subheader("📦 Inventario")
    if not df_inv.empty:
        cats = df_inv['categoria'].unique().tolist()
        tabs = st.tabs(cats)
        for i, cat in enumerate(cats):
            with tabs[i]:
                df_cat = df_inv[df_inv['categoria'] == cat]
                for _, row in df_cat.iterrows():
                    stock = row['stock_inicial'] - row['ventas_acumuladas']
                    col_a, col_b, col_c = st.columns([3, 2, 2])
                    col_a.write(f"**{row['producto']}**")
                    col_b.write(f"Disp: {int(stock)}")
                    
                    # El botón de venta se bloquea si la tienda está cerrada o no hay stock
                    if stock > 0:
                        btn_label = f"Vender {row['precio_venta']} Bs"
                        if col_c.button(btn_label, key=f"v_{row['id']}", disabled=not tienda_abierta):
                            registrar_venta(row['id'], row['producto'], row['precio_venta'], row['precio_costo'])
                            st.rerun()
                    else:
                        col_c.error("Agotado")
    else:
        st.info("Agrega productos en el menú lateral.")

with c_res:
    st.subheader("💰 Ganancias")
    st.metric("Total", f"{df_vts['ganancia_vta'].sum():.2f} Bs")
    with st.expander("📝 Historial de Ventas", expanded=True):
        if not df_vts.empty:
            df_h = df_vts[['fecha', 'nombre_producto', 'total_vta']].copy()
            df_h.index = range(1, len(df_h) + 1)
            st.table(df_h.rename(columns={'nombre_producto': 'Producto', 'total_vta': 'Bs'}))

if not tienda_abierta:
    st.warning("⚠️ La tienda está cerrada. No se pueden realizar ventas hasta que se abra.")
