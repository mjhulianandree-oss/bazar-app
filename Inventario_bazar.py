import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Bazar Master Pro v36", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stAppDeployButton {visibility: hidden;}
    [data-testid="stHeader"] {display:none !important;}
    input, .stSelectbox div[data-baseweb="select"], .stSelectbox div[data-baseweb="select"] > div {
        background-color: #262730 !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        border: 1px solid #4a4a4a !important;
        border-radius: 5px !important;
        font-weight: 700 !important;
        font-size: 16px !important;
    }
    svg[title="open"] { fill: #FF4B4B !important; width: 22px !important; }
    label p { color: #000000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS ---
DB_NAME = "bazar_pro_v36.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        producto TEXT UNIQUE, 
        categoria TEXT, 
        stock_inicial INTEGER, 
        precio_costo REAL, 
        precio_venta REAL, 
        ventas_acumuladas INTEGER DEFAULT 0)""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre_producto TEXT, 
        categoria TEXT,
        cantidad INTEGER, 
        fecha TEXT, 
        ganancia_vta REAL, 
        total_vta REAL)""")
    
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
hora_vta = (datetime.now() - timedelta(hours=4)).strftime("%H:%M")

# --- 3. CABECERA ---
st.title("🏪 Bazar Master Pro")
col1, col2 = st.columns([1, 2])
with col1:
    if abierto:
        if st.button("🔒 CERRAR TIENDA", use_container_width=True, type="primary"):
            conn = sqlite3.connect(DB_NAME); conn.execute("UPDATE estado_tienda SET abierto = 0 WHERE id = 1"); conn.commit(); conn.close()
            st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            conn = sqlite3.connect(DB_NAME); conn.execute("UPDATE estado_tienda SET abierto = 1 WHERE id = 1"); conn.commit(); conn.close()
            st.rerun()
with col2:
    st.subheader("🟢 Activo" if abierto else "⚠️ Cerrado")

st.divider()

# --- 4. REGISTRO (Sidebar) ---
with st.sidebar:
    st.header("📦 Registro")
    reg_nom = st.text_input("Nombre", key="n")
    reg_cat = st.selectbox("Sección", ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"])
    reg_stk = st.number_input("Stock Inicial", min_value=0, value=10)
    reg_cst = st.number_input("Costo (Bs)", min_value=0.0, value=1.0)
    reg_vta = st.number_input("Venta (Bs)", min_value=0.0, value=1.5)
    
    if st.button("💾 GUARDAR", use_container_width=True):
        if reg_nom:
            try:
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", 
                             (reg_nom.strip().upper(), reg_cat, reg_stk, reg_cst, reg_vta))
                conn.commit(); conn.close(); st.rerun()
            except: st.error("Ese producto ya existe.")

# --- 5. MOSTRADOR SUPERIOR ---
col_izq, col_der = st.columns([2.2, 1.2])

with col_izq:
    st.subheader("🛒 Panel de Ventas")
    if not df_inv.empty:
        categorias_existentes = sorted(df_inv['categoria'].unique())
        tabs = st.tabs(categorias_existentes)
        for i, cat in enumerate(categorias_existentes):
            with tabs[i]:
                # --- BOTONES DE VENTA ---
                df_cat = df_inv[df_inv['categoria'] == cat]
                for _, row in df_cat.iterrows():
                    disp = row['stock_inicial'] - row['ventas_acumuladas']
                    c_a, c_b, c_c = st.columns([3, 1.5, 2])
                    c_a.write(f"**{row['producto']}**")
                    c_b.write(f"Stock: {int(disp)}")
                    
                    if disp > 0:
                        if c_c.button(f"Venta {row['precio_venta']} Bs", key=f"v_{row['id']}", disabled=not abierto):
                            conn = sqlite3.connect(DB_NAME)
                            conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, 1, ?, ?, ?)", 
                                         (row['producto'], row['categoria'], hora_vta, row['precio_venta']-row['precio_costo'], row['precio_venta']))
                            conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (row['id'],))
                            conn.commit(); conn.close(); st.rerun()
                    else:
                        c_c.error("Agotado")
                
                # --- HISTORIAL POR SECCIÓN (EN LA PARTE INFERIOR DE CADA PESTAÑA) ---
                st.markdown("---")
                st.subheader(f"📊 Resumen de {cat}")
                
                # Filtrar ventas solo de esta categoría
                df_vts_cat = df_vts[df_vts['categoria'] == cat]
                
                if not df_vts_cat.empty:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Cant. Vendida", f"{int(df_vts_cat['cantidad'].sum())}")
                    m2.metric("Ganancia", f"{df_vts_cat['ganancia_vta'].sum():.2f} Bs")
                    m3.metric("Caja Sección", f"{df_vts_cat['total_vta'].sum():.2f} Bs")
                    
                    st.write("**Últimas ventas de esta sección:**")
                    st.table(df_vts_cat.tail(5)[['fecha', 'nombre_producto', 'total_vta']].rename(columns={'total_vta':'Bs'}))
                else:
                    st.info("Aún no hay ventas en esta sección.")

with col_der:
    st.subheader("💰 Resumen Total")
    total_caja = df_vts['total_vta'].sum() if not df_vts.empty else 0.0
    st.metric("Caja General Hoy", f"{total_caja:.2f} Bs")
    if not df_vts.empty:
        st.write("**Actividad General:**")
        st.table(df_vts.tail(8)[['fecha', 'nombre_producto', 'total_vta']])
