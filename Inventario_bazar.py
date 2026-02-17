import streamlit as st
import pandas as pd
import sqlite3
import shutil
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bazar Master Pro", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stAppDeployButton {visibility: hidden;}
    [data-testid="stHeader"] {display:none !important;}
    input, .stSelectbox div[data-baseweb="select"], .stSelectbox div[data-baseweb="select"] > div {
        background-color: #262730 !important; color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important; font-weight: 700 !important;
    }
    svg[title="open"] { fill: #FF4B4B !important; width: 22px !important; }
    label p { color: #000000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS CON AUTO-REPARACIÓN ---
DB_NAME = "bazar_v30_final.db" # Cambiamos nombre para asegurar éxito total

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT UNIQUE, categoria TEXT, 
        stock_inicial INTEGER, precio_costo REAL, precio_venta REAL, ventas_acumuladas INTEGER DEFAULT 0)""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_producto TEXT, 
        cantidad INTEGER, fecha TEXT, ganancia_vta REAL, total_vta REAL)""")
    
    # --- EL TRUCO: Si no existe la columna categoria en ventas, la creamos a la fuerza ---
    try:
        cursor.execute("ALTER TABLE ventas ADD COLUMN categoria TEXT DEFAULT 'General'")
    except sqlite3.OperationalError:
        pass # Si ya existe, no hace nada y sigue adelante
    
    cursor.execute("CREATE TABLE IF NOT EXISTS estado_tienda (id INTEGER PRIMARY KEY, abierto INTEGER)")
    cursor.execute("INSERT OR IGNORE INTO estado_tienda (id, abierto) VALUES (1, 0)")
    conn.commit()
    conn.close()

init_db()

def get_data():
    conn = sqlite3.connect(DB_NAME)
    inv = pd.read_sql_query("SELECT * FROM inventario", conn)
    vts = pd.read_sql_query("SELECT * FROM ventas", conn)
    res_est = conn.execute("SELECT abierto FROM estado_tienda WHERE id = 1").fetchone()
    conn.close()
    return inv, vts, (res_est[0] if res_est else 0)

df_inv, df_vts, estado_abierto = get_data()
abierto = True if estado_abierto == 1 else False

# --- 3. CABECERA ---
st.title("🏪 Bazar Master Pro")
c1, c2 = st.columns([1, 2])
with c1:
    if abierto:
        if st.button("🔒 CERRAR Y RESPALDAR", use_container_width=True, type="primary"):
            conn = sqlite3.connect(DB_NAME); conn.execute("UPDATE estado_tienda SET abierto = 0 WHERE id = 1"); conn.commit(); conn.close()
            st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            conn = sqlite3.connect(DB_NAME); conn.execute("UPDATE estado_tienda SET abierto = 1 WHERE id = 1"); conn.commit(); conn.close(); st.rerun()
with c2: st.subheader("🟢 Activo" if abierto else "⚠️ Cerrado")

# --- 4. REGISTRO ---
with st.sidebar:
    st.header("📦 Registro")
    reg_nom = st.text_input("Nombre", key="n")
    reg_cat = st.selectbox("Sección", ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"])
    reg_stk = st.number_input("Stock", min_value=0, value=10)
    reg_cst = st.number_input("Costo", min_value=0.0, value=1.0)
    reg_vta = st.number_input("Venta", min_value=0.0, value=1.5)
    
    if st.button("💾 GUARDAR"):
        if reg_nom:
            try:
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", 
                             (reg_nom.upper(), reg_cat, reg_stk, reg_cst, reg_vta))
                conn.commit(); conn.close(); st.rerun()
            except: st.error("Error al guardar")

# --- 5. MOSTRADOR ---
col_izq, col_der = st.columns([2.2, 1.2])
with col_izq:
    if not df_inv.empty:
        tabs = st.tabs(sorted(df_inv['categoria'].unique()))
        for i, cat in enumerate(sorted(df_inv['categoria'].unique())):
            with tabs[i]:
                for _, row in df_inv[df_inv['categoria'] == cat].iterrows():
                    disp = row['stock_inicial'] - row['ventas_acumuladas']
                    c_a, c_b, c_c = st.columns([3, 1.5, 2])
                    c_a.write(f"**{row['producto']}**")
                    c_b.write(f"Disp: {int(disp)}")
                    if disp > 0:
                        if c_c.button(f"Venta {row['precio_venta']} Bs", key=f"v_{row['id']}", disabled=not abierto):
                            conn = sqlite3.connect(DB_NAME)
                            f = (datetime.now() - timedelta(hours=4)).strftime("%H:%M")
                            # ESTA LINEA ES LA QUE DABA ERROR EN TUS FOTOS: Ahora está protegida.
                            conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, 1, ?, ?, ?)", 
                                         (row['producto'], row['categoria'], f, row['precio_venta']-row['precio_costo'], row['precio_venta']))
                            conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (row['id'],))
                            conn.commit(); conn.close(); st.rerun()

with col_der:
    st.subheader("💰 Resumen")
    st.metric("Caja", f"{df_vts['total_vta'].sum() if not df_vts.empty else 0:.2f} Bs")
    if not df_vts.empty: st.table(df_vts.tail(5)[['fecha', 'nombre_producto', 'total_vta']])
