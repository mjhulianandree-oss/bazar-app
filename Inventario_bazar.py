import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bazar Master Pro", layout="wide")

# Estilo para mejorar la visibilidad del foco y selección
st.markdown("""
    <style>
    #MainMenu, footer, header, .stAppDeployButton {visibility: hidden;}
    [data-testid="stHeader"] {display:none !important;}
    
    /* Resaltado del campo seleccionado para que tus papás vean dónde están */
    input:focus {
        border-color: #ff4b4b !important;
        box-shadow: 0 0 8px #ff4b4b !important;
        background-color: #fffdfd !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS (V17) ---
DB_NAME = "bazar_v17_final.db"

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
    vts = pd.read_sql_query("SELECT * FROM ventas ORDER BY id ASC", conn)
    res_est = conn.execute("SELECT abierto FROM estado_tienda WHERE id = 1").fetchone()
    conn.close()
    return inv, vts, res_est[0] if res_est else 0

df_inv, df_vts, estado_abierto = get_data()
abierto = True if estado_abierto == 1 else False

# --- 3. CABECERA ---
st.title("🏪 Bazar Master Pro")
c1, c2 = st.columns([1, 2])
with c1:
    if abierto:
        if st.button("🔒 CERRAR TIENDA", use_container_width=True, type="primary"):
            conn = sqlite3.connect(DB_NAME); conn.execute("UPDATE estado_tienda SET abierto = 0 WHERE id = 1"); conn.commit(); conn.close()
            st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            conn = sqlite3.connect(DB_NAME); conn.execute("UPDATE estado_tienda SET abierto = 1 WHERE id = 1"); conn.commit(); conn.close()
            st.rerun()
with c2:
    st.subheader("🟢 Sistema Activo" if abierto else "⚠️ Sistema Cerrado")

st.divider()

# --- 4. REGISTRO RÁPIDO (Optimizado para sobreescribir) ---
with st.sidebar:
    st.header("📦 Registro de Producto")
    st.write("💡 *Tip: Usa **TAB** para saltar y sobreescribir.*")

    # Usamos st.empty para poder limpiar el input después de guardar
    placeholder_nombre = st.empty()
    
    # El truco: Si el nombre ya existe en session_state, lo usamos; si no, vacío.
    # Al estar fuera de un form, el comportamiento de selección de texto del navegador es más agresivo (lo cual queremos)
    reg_nom = placeholder_nombre.text_input("Nombre del Producto", key="input_nom", placeholder="Escribe aquí...")
    reg_cat = st.selectbox("Sección", ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"])
    reg_stk = st.number_input("Stock Inicial", min_value=0, value=10)
    reg_cst = st.number_input("Costo unitario (Bs)", min_value=0.0, value=1.0, step=0.1)
    reg_vta = st.number_input("Venta unitario (Bs)", min_value=0.0, value=1.5, step=0.1)
    
    if st.button("💾 GUARDAR PRODUCTO", use_container_width=True):
        if reg_nom and reg_vta > 0:
            nombre_final = reg_nom.strip().upper()
            try:
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", 
                             (nombre_final, reg_cat, reg_stk, reg_cst, reg_vta))
                conn.commit(); conn.close()
                
                # Guardamos la categoría para abrir la pestaña correcta
                st.session_state.ultima_cat = reg_cat
                st.success(f"¡{nombre_final} guardado!")
                # Forzamos reinicio para limpiar campos y ver el producto nuevo
                st.rerun()
                
            except sqlite3.IntegrityError:
                st.error(f"¡Ojo! '{nombre_final}' ya existe en el inventario.")
        else:
            st.warning("Falta el nombre o el precio.")

# --- 5. MOSTRADOR ---
col_izq, col_der = st.columns([2.2, 1.2])

with col_izq:
    st.subheader("📦 Mostrador")
    if not df_inv.empty:
        cats = sorted(df_inv['categoria'].unique().tolist())
        idx_tab = cats.index(st.session_state.ultima_cat) if 'ultima_cat' in st.session_state and st.session_state.ultima_cat in cats else 0
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
                            fecha = (datetime.now() - timedelta(hours=4)).strftime("%H:%M")
                            conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, 1, ?, ?, ?)", 
                                         (row['producto'], row['categoria'], 1, fecha, row['precio_venta']-row['precio_costo'], row['precio_venta']))
                            conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (row['id'],))
                            conn.commit(); conn.close(); st.rerun()
                    else: c_c.error("Agotado")
                    
                    with c_d.popover("➕"):
                        if st.button("Surtir +10", key=f"s_{row['id']}"):
                            conn = sqlite3.connect(DB_NAME); conn.execute("UPDATE inventario SET stock_inicial = stock_inicial + 10 WHERE id = ?", (row['id'])); conn.commit(); conn.close()
                            st.rerun()

with col_der:
    st.subheader("💰 Resumen")
    m1, m2 = st.columns(2)
    m1.metric("Caja", f"{df_vts['total_vta'].sum():.2f}")
    m2.metric("Ganancia", f"{df_vts['ganancia_vta'].sum():.2f}")
    
    with st.expander("📝 Actividad", expanded=True):
        if not df_vts.empty:
            v_reales = df_vts[df_vts['cantidad'] > 0].tail(10)
            st.table(v_reales[['fecha', 'nombre_producto', 'total_vta']].rename(columns={'total_vta': 'Bs'}))

# --- 6. RESUMEN SECCIONES ---
st.divider()
if not df_vts.empty:
    res = df_vts[df_vts['cantidad'] > 0].groupby('categoria').agg({'total_vta': 'sum'}).reset_index()
    cols = st.columns(len(res) if len(res) > 0 else 1)
    for i, r in res.iterrows():
        with cols[i]:
            st.info(f"**{r['categoria']}**\n\nCaja: {r['total_vta']:.2f}")
