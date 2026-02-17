import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Bazar Master Pro", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stAppDeployButton {visibility: hidden;}
    [data-testid="stHeader"] {display:none !important;}
    .stApp { background-color: #0E1117; }
    html, body, p, h1, h2, h3, h4, span, label, .stMarkdown { color: #FFFFFF !important; }
    input, .stSelectbox div[data-baseweb="select"] { background-color: #262730 !important; color: #FFFFFF !important; }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #FFFFFF !important; }
    hr { border-color: #4a4a4a !important; }
    [data-testid="stTable"] { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS (CORRECCIÓN DE ERROR OPERATIONALERROR) ---
DB_NAME = "bazar_v45_final.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Aseguramos la creación de tablas antes de cualquier operación
    cursor.execute("""CREATE TABLE IF NOT EXISTS inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT UNIQUE, categoria TEXT, 
        stock_inicial INTEGER, precio_costo REAL, precio_venta REAL, ventas_acumuladas INTEGER DEFAULT 0)""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_producto TEXT, categoria TEXT,
        cantidad INTEGER, fecha TEXT, ganancia_vta REAL, total_vta REAL)""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS log_actividad (
        id INTEGER PRIMARY KEY AUTOINCREMENT, hora TEXT, detalle TEXT)""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS estado_tienda (
        id INTEGER PRIMARY KEY, abierto INTEGER)""")
    
    # Commit inmediato de las tablas antes de insertar
    conn.commit()
    cursor.execute("INSERT OR IGNORE INTO estado_tienda (id, abierto) VALUES (1, 0)")
    conn.commit()
    conn.close()

init_db()

def get_data():
    conn = sqlite3.connect(DB_NAME)
    inv = pd.read_sql_query("SELECT * FROM inventario", conn)
    vts = pd.read_sql_query("SELECT * FROM ventas", conn)
    # Seleccionamos con alias para la tabla de actividad
    act = pd.read_sql_query("SELECT hora as 'Hora', detalle as 'Detalle' FROM log_actividad ORDER BY id DESC LIMIT 20", conn)
    res_est = conn.execute("SELECT abierto FROM estado_tienda WHERE id = 1").fetchone()
    conn.close()
    return inv, vts, act, (res_est[0] if res_est else 0)

df_inv, df_vts, df_act, estado_abierto = get_data()
abierto = True if estado_abierto == 1 else False
ahora = (datetime.now() - timedelta(hours=4)).strftime("%H:%M")

# --- 3. CABECERA ---
st.title("🏪 Bazar Master Pro")
col1, col2 = st.columns([1, 2])
with col1:
    if abierto:
        if st.button("🔒 CERRAR TIENDA", use_container_width=True, type="primary"):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("UPDATE estado_tienda SET abierto = 0 WHERE id = 1")
            conn.execute("INSERT INTO log_actividad (hora, detalle) VALUES (?,?)", (ahora, "CERRADO 🔒"))
            conn.commit(); conn.close(); st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("UPDATE estado_tienda SET abierto = 1 WHERE id = 1")
            conn.execute("INSERT INTO log_actividad (hora, detalle) VALUES (?,?)", (ahora, "ABIERTO 🔓"))
            conn.commit(); conn.close(); st.rerun()
with col2:
    st.subheader("🟢 Activo" if abierto else "⚠️ Cerrado")

st.divider()

# --- 4. REGISTRO (Sidebar con lógica de "Ya existe" corregida) ---
with st.sidebar:
    st.header("📦 Registro")
    with st.form("registro_prod", clear_on_submit=True):
        reg_nom = st.text_input("Nombre")
        reg_cat = st.selectbox("Sección", ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"])
        reg_stk = st.number_input("Stock Inicial", min_value=0, value=10)
        reg_cst = st.number_input("Costo (Bs)", min_value=0.0, value=1.0)
        reg_vta = st.number_input("Venta (Bs)", min_value=0.0, value=1.5)
        
        if st.form_submit_button("💾 GUARDAR", use_container_width=True):
            if reg_nom:
                nombre_up = reg_nom.strip().upper()
                conn = sqlite3.connect(DB_NAME)
                # Verificamos si existe antes de insertar para evitar el error duplicado
                existe = conn.execute("SELECT 1 FROM inventario WHERE producto = ?", (nombre_up,)).fetchone()
                if not existe:
                    conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", 
                                 (nombre_up, reg_cat, reg_stk, reg_cst, reg_vta))
                    conn.commit(); conn.close(); st.rerun()
                else:
                    conn.close()
                    st.warning(f"'{nombre_up}' ya existe en el inventario.")

# --- 5. MOSTRADOR ---
col_izq, col_der = st.columns([2.2, 1.2])

with col_izq:
    st.subheader("🛒 Panel de Ventas")
    if not df_inv.empty:
        tabs = st.tabs(sorted(df_inv['categoria'].unique()))
        for i, cat in enumerate(sorted(df_inv['categoria'].unique())):
            with tabs[i]:
                df_cat = df_inv[df_inv['categoria'] == cat]
                for _, row in df_cat.iterrows():
                    disp = row['stock_inicial'] - row['ventas_acumuladas']
                    c_a, c_b, c_plus, c_c = st.columns([2.5, 1, 0.5, 2])
                    
                    c_a.write(f"**{row['producto']}**")
                    c_b.write(f"Stock: {int(disp)}")
                    
                    if c_plus.button("➕", key=f"add_{row['id']}"):
                        conn = sqlite3.connect(DB_NAME)
                        conn.execute("UPDATE inventario SET stock_inicial = stock_inicial + 1 WHERE id = ?", (row['id'],))
                        conn.execute("INSERT INTO log_actividad (hora, detalle) VALUES (?,?)", (ahora, f"STOCK +1: {row['producto']}"))
                        conn.commit(); conn.close(); st.rerun()
                    
                    if disp > 0:
                        if c_c.button(f"Venta {row['precio_venta']} Bs", key=f"v_{row['id']}", disabled=not abierto):
                            conn = sqlite3.connect(DB_NAME)
                            conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, 1, ?, ?, ?)", 
                                         (row['producto'], row['categoria'], ahora, row['precio_venta']-row['precio_costo'], row['precio_venta']))
                            conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (row['id'],))
                            conn.execute("INSERT INTO log_actividad (hora, detalle) VALUES (?,?)", (ahora, f"VENTA: {row['producto']}"))
                            conn.commit(); conn.close(); st.rerun()
                    else: c_c.error("Agotado")
                
                st.markdown("---")
                df_vts_cat = df_vts[df_vts['categoria'] == cat]
                if not df_vts_cat.empty:
                    m1, m2 = st.columns(2)
                    m1.metric("Ganancia", f"{df_vts_cat['ganancia_vta'].sum():.2f} Bs")
                    m2.metric("Caja", f"{df_vts_cat['total_vta'].sum():.2f} Bs")

with col_der:
    st.subheader("💰 Total Hoy")
    total_caja = df_vts['total_vta'].sum() if not df_vts.empty else 0.0
    st.metric("Caja General", f"{total_caja:.2f} Bs")
    st.write("---")
    st.subheader("📜 Actividad")
    
    if not df_act.empty:
        # AQUÍ SE OCULTA EL ÍNDICE (LOS NÚMEROS DE LA IZQUIERDA)
        st.dataframe(df_act, use_container_width=True, hide_index=True)
    else:
        st.write("Sin actividad.")
