import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN VISUAL (TODO EN BLANCO) ---
st.set_page_config(page_title="Bazar Master Pro", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stAppDeployButton {visibility: hidden;}
    [data-testid="stHeader"] {display:none !important;}
    .stApp { background-color: #0E1117; }
    html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, h4, span, label {
        color: #FFFFFF !important;
    }
    input, .stSelectbox div[data-baseweb="select"], .stSelectbox div[data-baseweb="select"] > div {
        background-color: #262730 !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        border: 1px solid #4a4a4a !important;
        border-radius: 5px !important;
    }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"], .stTable td, .stTable th {
        color: #FFFFFF !important;
    }
    svg[title="open"] { fill: #FFFFFF !important; width: 22px !important; }
    hr { border-color: #4a4a4a !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS (NUEVA VERSIÓN LIMPIA) ---
DB_NAME = "bazar_final_v1.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT UNIQUE, categoria TEXT, 
        stock_inicial INTEGER, precio_costo REAL, precio_venta REAL, ventas_acumuladas INTEGER DEFAULT 0)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_producto TEXT, categoria TEXT,
        cantidad INTEGER, fecha TEXT, ganancia_vta REAL, total_vta REAL)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS historial_tienda (
        id INTEGER PRIMARY KEY AUTOINCREMENT, evento TEXT, hora TEXT)""")
    cursor.execute("CREATE TABLE IF NOT EXISTS estado_tienda (id INTEGER PRIMARY KEY, abierto INTEGER)")
    cursor.execute("INSERT OR IGNORE INTO estado_tienda (id, abierto) VALUES (1, 0)")
    conn.commit()
    conn.close()

init_db()

def get_data():
    conn = sqlite3.connect(DB_NAME)
    inv = pd.read_sql_query("SELECT * FROM inventario", conn)
    vts = pd.read_sql_query("SELECT * FROM ventas", conn)
    hst = pd.read_sql_query("SELECT * FROM historial_tienda", conn)
    res_est = conn.execute("SELECT abierto FROM estado_tienda WHERE id = 1").fetchone()
    conn.close()
    return inv, vts, hst, (res_est[0] if res_est else 0)

df_inv, df_vts, df_hst, estado_abierto = get_data()
abierto = True if estado_abierto == 1 else False
ahora = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")

# --- 3. CABECERA ---
st.title("🏪 Bazar Master Pro")
col1, col2 = st.columns([1, 2])
with col1:
    if abierto:
        if st.button("🔒 CERRAR TIENDA", use_container_width=True, type="primary"):
            conn = sqlite3.connect(DB_NAME); conn.execute("UPDATE estado_tienda SET abierto = 0 WHERE id = 1")
            conn.execute("INSERT INTO historial_tienda (evento, hora) VALUES (?,?)", ("CERRADO 🔒", ahora))
            conn.commit(); conn.close(); st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            conn = sqlite3.connect(DB_NAME); conn.execute("UPDATE estado_tienda SET abierto = 1 WHERE id = 1")
            conn.execute("INSERT INTO historial_tienda (evento, hora) VALUES (?,?)", ("ABIERTO 🔓", ahora))
            conn.commit(); conn.close(); st.rerun()
with col2:
    st.subheader("🟢 Activo" if abierto else "⚠️ Cerrado")

st.divider()

# --- 4. REGISTRO (USANDO FORMULARIO PARA EVITAR REPETICIÓN) ---
with st.sidebar:
    st.header("📦 Registro")
    with st.form("form_registro", clear_on_submit=True):
        reg_nom = st.text_input("Nombre del Producto")
        reg_cat = st.selectbox("Sección", ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"])
        reg_stk = st.number_input("Stock Inicial", min_value=0, value=10)
        reg_cst = st.number_input("Costo (Bs)", min_value=0.0, value=1.0)
        reg_vta = st.number_input("Venta (Bs)", min_value=0.0, value=1.5)
        btn_guardar = st.form_submit_button("💾 GUARDAR", use_container_width=True)
        
        if btn_guardar:
            if reg_nom:
                nombre_limpio = reg_nom.strip().upper()
                try:
                    conn = sqlite3.connect(DB_NAME)
                    conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", 
                                 (nombre_limpio, reg_cat, reg_stk, reg_cst, reg_vta))
                    conn.commit(); conn.close()
                    st.success("Guardado!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Ese producto ya existe en la lista.")

# --- 5. MOSTRADOR ---
col_izq, col_der = st.columns([2.2, 1.2])

with col_izq:
    st.subheader("🛒 Panel de Ventas")
    if not df_inv.empty:
        categorias_existentes = sorted(df_inv['categoria'].unique())
        tabs = st.tabs(categorias_existentes)
        for i, cat in enumerate(categorias_existentes):
            with tabs[i]:
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
                                         (row['producto'], row['categoria'], ahora, row['precio_venta']-row['precio_costo'], row['precio_venta']))
                            conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (row['id'],))
                            conn.commit(); conn.close(); st.rerun()
                    else: st.error("Agotado")
                
                st.markdown("---")
                df_vts_cat = df_vts[df_vts['categoria'] == cat]
                if not df_vts_cat.empty:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Ventas", f"{int(df_vts_cat['cantidad'].sum())}")
                    m2.metric("Ganancia", f"{df_vts_cat['ganancia_vta'].sum():.2f} Bs")
                    m3.metric("Caja", f"{df_vts_cat['total_vta'].sum():.2f} Bs")

with col_der:
    st.subheader("💰 Resumen Total")
    total_caja = df_vts['total_vta'].sum() if not df_vts.empty else 0.0
    st.metric("Caja General Hoy", f"{total_caja:.2f} Bs")
    st.write("---")
    st.subheader("📜 Actividad General")
    
    vts_log = df_vts[['fecha', 'nombre_producto', 'total_vta']].copy() if not df_vts.empty else pd.DataFrame(columns=['fecha', 'nombre_producto', 'total_vta'])
    vts_log.columns = ['Hora', 'Detalle', 'Monto']
    hst_log = df_hst[['hora', 'evento']].copy() if not df_hst.empty else pd.DataFrame(columns=['hora', 'evento'])
    hst_log['Monto'] = 0.0
    hst_log.columns = ['Hora', 'Detalle', 'Monto']
    
    log_completo = pd.concat([vts_log, hst_log]).sort_index(ascending=False)
    if not log_completo.empty: st.table(log_completo.head(15))
