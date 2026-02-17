import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bazar Master Pro", layout="wide")

# --- 2. BLINDAJE VISUAL ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stAppDeployButton {display:none !important;}
    [data-testid="stHeader"] {display:none !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect("bazar_master_v4.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS inventario (id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT, categoria TEXT, stock_inicial INTEGER, precio_costo REAL, precio_venta REAL, ventas_acumuladas INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_producto TEXT, cantidad INTEGER, fecha TEXT, ganancia_vta REAL, total_vta REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS estado_tienda (id INTEGER PRIMARY KEY, abierto INTEGER, última_apertura TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS cierres_caja (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, total_venta REAL, ganancia_total REAL)")
    cursor.execute("INSERT OR IGNORE INTO estado_tienda (id, abierto, última_apertura) VALUES (1, 0, 'Cerrado')")
    conn.commit()
    conn.close()

def abrir_tienda():
    conn = sqlite3.connect("bazar_master_v4.db")
    hora = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")
    conn.execute("UPDATE estado_tienda SET abierto = 1, última_apertura = ? WHERE id = 1", (hora,))
    conn.commit()
    conn.close()

def cerrar_tienda(resumen):
    conn = sqlite3.connect("bazar_master_v4.db")
    hora = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")
    conn.execute("UPDATE estado_tienda SET abierto = 0, última_apertura = 'Cerrado' WHERE id = 1")
    conn.execute("INSERT INTO cierres_caja (fecha, total_venta, ganancia_total) VALUES (?, ?, ?)", (hora, resumen['total'], resumen['ganancia']))
    conn.commit()
    conn.close()

def registrar_venta(id_prod, nombre_prod, p_venta, p_costo):
    conn = sqlite3.connect("bazar_master_v4.db")
    ganancia = p_venta - p_costo
    fecha = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")
    conn.execute("INSERT INTO ventas (nombre_producto, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, ?, ?, ?)", (nombre_prod, 1, fecha, ganancia, p_venta))
    conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (id_prod,))
    conn.commit()
    conn.close()

init_db()

# --- 4. CARGA DE DATOS ---
conn = sqlite3.connect("bazar_master_v4.db")
df_inv = pd.read_sql_query("SELECT * FROM inventario", conn)
df_vts = pd.read_sql_query("SELECT * FROM ventas", conn)
estado_tienda = conn.execute("SELECT abierto, última_apertura FROM estado_tienda WHERE id = 1").fetchone()
conn.close()

abierto = True if estado_tienda[0] == 1 else False
registro_apertura = estado_tienda[1]

# --- 5. CABECERA ---
st.title("🏪 Bazar Master Pro")

col_c1, col_c2 = st.columns([1, 2])
with col_c1:
    if abierto:
        if st.button("🔒 CERRAR TIENDA", use_container_width=True, type="primary"):
            hoy_vta = df_vts['total_vta'].sum()
            hoy_gan = df_vts['ganancia_vta'].sum()
            cerrar_tienda({'total': hoy_vta, 'ganancia': hoy_gan})
            st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            abrir_tienda()
            st.rerun()

with col_c2:
    if abierto:
        st.subheader(f"🟢 ABIERTO (Desde: {registro_apertura})")
    else:
        st.subheader("🔴 CERRADO")

st.divider()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.header("📦 Nuevo Producto")
    n_nom = st.text_input("Nombre")
    n_cat = st.selectbox("Categoría", ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"])
    n_stk = st.number_input("Stock", min_value=1, value=10)
    n_cst = st.number_input("Costo unitario", min_value=0.1, value=1.0)
    n_vta = st.number_input("Venta unitario", min_value=0.1, value=1.5)
    if st.button("Guardar en Inventario"):
        if n_nom:
            conn = sqlite3.connect("bazar_master_v4.db")
            conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", (n_nom, n_cat, n_stk, n_cst, n_vta))
            conn.commit()
            conn.close()
            st.rerun()

# --- 7. MOSTRADOR ---
c_inv, c_res = st.columns([2, 1.3])

with c_inv:
    st.subheader("📦 Mostrador")
    if not df_inv.empty:
        cats = df_inv['categoria'].unique().tolist()
        tabs = st.tabs(cats)
        for i, cat in enumerate(cats):
            with tabs[i]:
                df_cat = df_inv[df_inv['categoria'] == cat]
                for _, row in df_cat.iterrows():
                    stk = row['stock_inicial'] - row['ventas_acumuladas']
                    col1, col2, col3, col4 = st.columns([3, 1.5, 2, 1])
                    col1.write(f"**{row['producto']}**")
                    col2.write(f"Disp: {int(stk)}")
                    
                    if stk > 0:
                        if col3.button(f"Venta {row['precio_venta']} Bs", key=f"v_{row['id']}", disabled=not abierto):
                            registrar_venta(row['id'], row['producto'], row['precio_venta'], row['precio_costo'])
                            st.rerun()
                    else:
                        col3.error("Agotado")
                    
                    with col4.popover("➕"):
                        cant = st.number_input("Surtir", min_value=1, value=10, key=f"s_{row['id']}")
                        if st.button("Surtir", key=f"bs_{row['id']}"):
                            conn = sqlite3.connect("bazar_master_v4.db")
                            conn.execute("UPDATE inventario SET stock_inicial = stock_inicial + ? WHERE id = ?", (cant, row['id']))
                            conn.commit()
                            conn.close()
                            st.rerun()

with c_res:
    st.subheader("💰 Resumen")
    caja = df_vts['total_vta'].sum()
    ganancia = df_vts['ganancia_vta'].sum()
    m1, m2 = st.columns(2)
    m1.metric("Dinero en Caja", f"{caja:.2f} Bs")
    m2.metric("Ganancia Limpia", f"{ganancia:.2f} Bs")
    
    with st.expander("📝 Ventas de hoy", expanded=True):
        if not df_vts.empty:
            df_h = df_vts[['fecha', 'nombre_producto', 'total_vta']].copy()
            df_h.index = range(1, len(df_h)+1)
            st.table(df_h.rename(columns={'nombre_producto':'Producto','total_vta':'Bs'}))

    with st.expander("📊 Cierres Anteriores"):
        conn = sqlite3.connect("bazar_master_v4.db")
        df_c = pd.read_sql_query("SELECT * FROM cierres_caja ORDER BY id DESC", conn)
        conn.close()
        if not df_c.empty:
            st.dataframe(df_c[['fecha', 'total_venta', 'ganancia_total']], hide_index=True)
