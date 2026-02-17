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

# --- 3. BASE DE DATOS (NUEVA VERSIÓN LIMPIA) ---
def init_db():
    conn = sqlite3.connect("bazar_final_pro.db")
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

def cambiar_estado(abrir):
    conn = sqlite3.connect("bazar_final_pro.db")
    conn.execute("UPDATE estado_tienda SET abierto = ? WHERE id = 1", (1 if abrir else 0,))
    conn.commit()
    conn.close()
    # Registro de evento de apertura/cierre
    hora = (datetime.now() - timedelta(hours=4)).strftime("%H:%M")
    conn = sqlite3.connect("bazar_final_pro.db")
    conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, 'SISTEMA', 0, ?, 0, 0)", 
                 ("🟢 ABIERTO" if abrir else "🔴 CERRADO", hora))
    conn.commit()
    conn.close()

init_db()

# --- 4. CARGA DE DATOS ---
conn = sqlite3.connect("bazar_final_pro.db")
df_inv = pd.read_sql_query("SELECT * FROM inventario", conn)
df_vts = pd.read_sql_query("SELECT * FROM ventas ORDER BY id ASC", conn)
estado_actual = conn.execute("SELECT abierto FROM estado_tienda WHERE id = 1").fetchone()[0]
conn.close()

abierto = True if estado_actual == 1 else False

# --- 5. CABECERA ---
st.title("🏪 Bazar Master Pro")
c_btn, c_info = st.columns([1, 2])
with c_btn:
    if abierto:
        if st.button("🔒 CERRAR TIENDA", use_container_width=True, type="primary"):
            cambiar_estado(False); st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            cambiar_estado(True); st.rerun()
with c_info:
    st.subheader("✅ Sistema Activo" if abierto else "⚠️ Sistema Cerrado")

st.divider()

# --- 6. SIDEBAR (REGISTRO RÁPIDO) ---
with st.sidebar:
    st.header("📦 Nuevo Producto")
    with st.form("form_registro", clear_on_submit=True):
        n_nom = st.text_input("Nombre")
        n_cat = st.selectbox("Sección", ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"])
        n_stk = st.number_input("Stock", min_value=1, value=10)
        n_cst = st.number_input("Costo unitario (Bs)", min_value=0.0, step=0.1)
        n_vta = st.number_input("Venta unitario (Bs)", min_value=0.0, step=0.1)
        
        if st.form_submit_button("Guardar Producto"):
            if n_nom:
                try:
                    conn = sqlite3.connect("bazar_final_pro.db")
                    conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", 
                                 (n_nom.strip(), n_cat, n_stk, n_cst, n_vta))
                    conn.commit(); conn.close()
                    st.session_state.focus_cat = n_cat
                    st.rerun()
                except:
                    st.error("Ya existe este producto.")

# --- 7. MOSTRADOR ---
c_inv, c_res = st.columns([2, 1.3])

with c_inv:
    st.subheader("📦 Mostrador")
    if not df_inv.empty:
        categorias = df_inv['categoria'].unique().tolist()
        # Salto automático a la pestaña guardada
        idx_tab = categorias.index(st.session_state.focus_cat) if 'focus_cat' in st.session_state and st.session_state.focus_cat in categorias else 0
        tabs = st.tabs(categorias)
        
        for i, cat in enumerate(categorias):
            with tabs[i]:
                df_cat = df_inv[df_inv['categoria'] == cat]
                for _, row in df_cat.iterrows():
                    disp = row['stock_inicial'] - row['ventas_acumuladas']
                    col1, col2, col3, col4 = st.columns([3, 1.5, 2, 1])
                    col1.write(f"**{row['producto']}**")
                    col2.write(f"Disp: {int(disp)}")
                    
                    if disp > 0:
                        if col3.button(f"{row['precio_venta']} Bs", key=f"v_{row['id']}", disabled=not abierto):
                            conn = sqlite3.connect("bazar_final_pro.db")
                            fecha = (datetime.now() - timedelta(hours=4)).strftime("%H:%M")
                            conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, 1, ?, ?, ?)", 
                                         (row['producto'], row['categoria'], fecha, row['precio_venta']-row['precio_costo'], row['precio_venta']))
                            conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (row['id'],))
                            conn.commit(); conn.close(); st.rerun()
                    else: col3.error("Agotado")
                    
                    with col4.popover("➕"):
                        if st.button("Surtir +10", key=f"s_{row['id']}"):
                            conn = sqlite3.connect("bazar_final_pro.db")
                            conn.execute("UPDATE inventario SET stock_inicial = stock_inicial + 10 WHERE id = ?", (row['id'],))
                            conn.commit(); conn.close(); st.rerun()

with c_res:
    st.subheader("💰 Caja y Ganancia")
    m1, m2 = st.columns(2)
    m1.metric("En Caja", f"{df_vts['total_vta'].sum():.2f} Bs")
    m2.metric("Ganancia", f"{df_vts['ganancia_vta'].sum():.2f} Bs")
    
    with st.expander("📝 Actividad Reciente", expanded=True):
        if not df_vts.empty:
            hist = []
            cont = 0
            for _, v in df_vts.iterrows():
                if v['categoria'] != 'SISTEMA':
                    cont += 1
                    n = str(cont)
                else: n = "-"
                hist.append({"N°": n, "Hora": v['fecha'], "Producto": v['nombre_producto'], "Venta": f"{v['total_vta']:.2f}", "Ganancia": f"{v['ganancia_vta']:.2f}"})
            
            # ELIMINACIÓN DEFINITIVA DEL ÍNDICE EXTRA
            df_historial = pd.DataFrame(hist).set_index("N°")
            st.table(df_historial)

# --- 8. RESUMEN INFERIOR ---
st.divider()
v_reales = df_vts[df_vts['categoria'] != 'SISTEMA']
if not v_reales.empty:
    resumen = v_reales.groupby('categoria').agg({'total_vta': 'sum', 'ganancia_vta': 'sum'}).reset_index()
    cols = st.columns(len(resumen))
    for i, r in resumen.iterrows():
        with cols[i]:
            st.info(f"**{r['categoria']}**\n\nCaja: {r['total_vta']:.2f}\n\nGana: {r['ganancia_vta']:.2f}")
