import streamlit as st
import pandas as pd
import sqlite3
import shutil
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bazar Master Pro", layout="wide")

# Estilo visual de alta visibilidad (Texto blanco en casillas)
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
    .stSelectbox div[role="button"] { background-color: transparent !important; }
    svg[title="open"] { fill: #FF4B4B !important; width: 22px !important; height: 22px !important; }
    label p { color: #000000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS (NUEVA VERSIÓN PARA EVITAR ERRORES) ---
# Cambiamos el nombre a v27 para forzar una base de datos limpia y sin errores
DB_NAME = "bazar_v27_estable.db"
BACKUP_DIR = "respaldos_bazar"

if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

def crear_respaldo():
    if os.path.exists(DB_NAME):
        fecha_hoy = datetime.now().strftime("%Y-%m-%d_%H-%M")
        backup_path = os.path.join(BACKUP_DIR, f"respaldo_{fecha_hoy}.db")
        shutil.copy2(DB_NAME, backup_path)
        return backup_path
    return None

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabla Inventario
    cursor.execute("""CREATE TABLE IF NOT EXISTS inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        producto TEXT UNIQUE, 
        categoria TEXT, 
        stock_inicial INTEGER, 
        precio_costo REAL, 
        precio_venta REAL, 
        ventas_acumuladas INTEGER DEFAULT 0)""")
    # Tabla Ventas - Aquí estaba el error de las fotos
    cursor.execute("""CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre_producto TEXT, 
        categoria TEXT,
        cantidad INTEGER, 
        fecha TEXT, 
        ganancia_vta REAL, 
        total_vta REAL)""")
    # Tabla Estado
    cursor.execute("CREATE TABLE IF NOT EXISTS estado_tienda (id INTEGER PRIMARY KEY, abierto INTEGER)")
    cursor.execute("INSERT OR IGNORE INTO estado_tienda (id, abierto) VALUES (1, 0)")
    conn.commit()
    conn.close()

init_db()

def get_data():
    conn = sqlite3.connect(DB_NAME)
    inv = pd.read_sql_query("SELECT * FROM inventario", conn)
    vts = pd.read_sql_query("SELECT * FROM ventas ORDER BY id ASC", conn)
    res_est = conn.execute("SELECT abierto FROM estado_tienda WHERE id = 1").fetchone()
    conn.close()
    return inv, vts, (res_est[0] if res_est else 0)

# Carga de datos
try:
    df_inv, df_vts, estado_abierto = get_data()
except:
    # Si algo falla, reiniciamos la conexión una vez
    st.warning("Actualizando base de datos...")
    init_db()
    df_inv, df_vts, estado_abierto = get_data()

abierto = True if estado_abierto == 1 else False

# --- 3. CABECERA ---
st.title("🏪 Bazar Master Pro")
c1, c2 = st.columns([1, 2])
with c1:
    if abierto:
        if st.button("🔒 CERRAR Y RESPALDAR", use_container_width=True, type="primary"):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("UPDATE estado_tienda SET abierto = 0 WHERE id = 1")
            conn.commit(); conn.close()
            crear_respaldo()
            st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("UPDATE estado_tienda SET abierto = 1 WHERE id = 1")
            conn.commit(); conn.close()
            st.rerun()
with c2:
    st.subheader("🟢 Activo" if abierto else "⚠️ Cerrado")

st.divider()

# --- 4. REGISTRO (Sidebar) ---
with st.sidebar:
    st.header("📦 Registro")
    reg_nom = st.text_input("Nombre", key="input_nom", autocomplete="off")
    reg_cat = st.selectbox("Sección", ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"])
    reg_stk = st.number_input("Stock", min_value=0, value=10)
    reg_cst = st.number_input("Costo", min_value=0.0, value=1.0, step=0.1)
    reg_vta = st.number_input("Venta", min_value=0.0, value=1.5, step=0.1)
    
    if st.button("💾 GUARDAR PRODUCTO", use_container_width=True):
        if reg_nom and reg_vta > 0:
            nombre_final = reg_nom.strip().upper()
            try:
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", 
                             (nombre_final, reg_cat, reg_stk, reg_cst, reg_vta))
                conn.commit(); conn.close()
                st.session_state.ultima_cat = reg_cat
                st.success(f"¡{nombre_final} guardado!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error(f"¡{nombre_final} ya existe!")
        else:
            st.warning("Completa los datos.")

# --- 5. MOSTRADOR ---
col_izq, col_der = st.columns([2.2, 1.2])

with col_izq:
    st.subheader("📦 Mostrador")
    if not df_inv.empty:
        cats = sorted(df_inv['categoria'].unique().tolist())
        tabs = st.tabs(cats)
        
        for i, cat in enumerate(cats):
            with tabs[i]:
                df_cat = df_inv[df_inv['categoria'] == cat]
                for _, row in df_cat.iterrows():
                    disp = row['stock_inicial'] - row['ventas_acumuladas']
                    c_a, c_b, c_c, c_d = st.columns([3, 1.5, 2, 0.8])
                    c_a.write(f"**{row['producto']}**")
                    c_b.write(f"Disp: {int(disp)}")
                    
                    if disp > 0:
                        if c_c.button(f"Venta {row['precio_venta']} Bs", key=f"v_{row['id']}", disabled=not abierto):
                            conn = sqlite3.connect(DB_NAME)
                            # Ajuste de hora (Bolivia -4h)
                            fecha_actual = (datetime.now() - timedelta(hours=4)).strftime("%H:%M")
                            conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, 1, ?, ?, ?)", 
                                         (row['producto'], row['categoria'], 1, fecha_actual, row['precio_venta']-row['precio_costo'], row['precio_venta']))
                            conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (row['id'],))
                            conn.commit(); conn.close()
                            st.rerun()
                    else:
                        c_c.error("Agotado")
                    
                    with c_d.popover("➕"):
                        if st.button("Surtir +10", key=f"s_{row['id']}"):
                            conn = sqlite3.connect(DB_NAME)
                            conn.execute("UPDATE inventario SET stock_inicial = stock_inicial + 10 WHERE id = ?", (row['id']))
                            conn.commit(); conn.close(); st.rerun()

with col_der:
    st.subheader("💰 Resumen")
    st.metric("Caja Total", f"{df_vts['total_vta'].sum() if not df_vts.empty else 0:.2f} Bs")
    
    with st.expander("📝 Actividad Reciente", expanded=True):
        if not df_vts.empty:
            # Mostramos las últimas 10 ventas filtrando por categoría válida
            v_reales = df_vts.tail(10)
            st.table(v_reales[['fecha', 'nombre_producto', 'total_vta']].rename(columns={'total_vta':'Bs'}))
    
    if st.button("📁 Crear Respaldo Ahora"):
        p = crear_respaldo()
        st.success("Copia guardada en carpeta 'respaldos_bazar'")
