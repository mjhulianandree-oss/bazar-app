import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bazar Master Pro", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stAppDeployButton {visibility: hidden;}
    [data-testid="stHeader"] {display:none !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS (Versión 9 - Limpia) ---
def init_db():
    conn = sqlite3.connect("bazar_final_v9.db")
    cursor = conn.cursor()
    # Inventario con nombre único para evitar duplicados
    cursor.execute("""CREATE TABLE IF NOT EXISTS inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        producto TEXT UNIQUE, 
        categoria TEXT, 
        stock_inicial INTEGER, 
        precio_costo REAL, 
        precio_venta REAL, 
        ventas_acumuladas INTEGER DEFAULT 0)""")
    # Ventas con columna de categoría para el resumen inferior
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

def registrar_evento(mensaje):
    conn = sqlite3.connect("bazar_final_v9.db")
    hora = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")
    conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, 'SISTEMA', 0, ?, 0, 0)", (mensaje, hora))
    conn.commit()
    conn.close()

init_db()

# --- 3. CARGA DE DATOS ---
conn = sqlite3.connect("bazar_final_v9.db")
df_inv = pd.read_sql_query("SELECT * FROM inventario", conn)
df_vts = pd.read_sql_query("SELECT * FROM ventas ORDER BY id ASC", conn)
estado_actual = conn.execute("SELECT abierto FROM estado_tienda WHERE id = 1").fetchone()[0]
conn.close()

abierto = True if estado_actual == 1 else False

# --- 4. INTERFAZ SUPERIOR ---
st.title("🏪 Bazar Master Pro")
c1, c2 = st.columns([1, 2])
with c1:
    if abierto:
        if st.button("🔒 CERRAR TIENDA", use_container_width=True, type="primary"):
            conn = sqlite3.connect("bazar_final_v9.db")
            conn.execute("UPDATE estado_tienda SET abierto = 0 WHERE id = 1")
            conn.commit(); conn.close()
            registrar_evento("🔴 TIENDA CERRADA")
            st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            conn = sqlite3.connect("bazar_final_v9.db")
            conn.execute("UPDATE estado_tienda SET abierto = 1 WHERE id = 1")
            conn.commit(); conn.close()
            registrar_evento("🟢 TIENDA ABIERTA")
            st.rerun()
with c2:
    st.subheader("🟢 Activo" if abierto else "⚠️ Cerrado")

st.divider()

# --- 5. REGISTRO (A la izquierda) ---
with st.sidebar:
    st.header("📦 Registro de Productos")
    with st.form("registro_form", clear_on_submit=True):
        n_nom = st.text_input("Nombre")
        n_cat = st.selectbox("Sección", ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"])
        n_stk = st.number_input("Stock", min_value=1, value=10)
        n_cst = st.number_input("Costo (Bs)", min_value=0.0, step=0.1)
        n_vta = st.number_input("Venta (Bs)", min_value=0.0, step=0.1)
        
        if st.form_submit_button("Guardar"):
            if n_nom:
                try:
                    conn = sqlite3.connect("bazar_final_v9.db")
                    conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", 
                                 (n_nom, n_cat, n_stk, n_cst, n_vta))
                    conn.commit(); conn.close()
                    st.session_state.cat_foco = n_cat # Para saltar a la pestaña
                    st.rerun()
                except:
                    st.error("Ese producto ya existe.")

# --- 6. MOSTRADOR Y RESUMEN ---
col_izq, col_der = st.columns([2, 1.3])

with col_izq:
    st.subheader("📦 Mostrador")
    if not df_inv.empty:
        cats = df_inv['categoria'].unique().tolist()
        # Salto automático a la pestaña del producto guardado
        idx_tab = cats.index(st.session_state.cat_foco) if 'cat_foco' in st.session_state and st.session_state.cat_foco in cats else 0
        tabs = st.tabs(cats)
        
        for i, cat in enumerate(cats):
            with tabs[i]:
                df_cat = df_inv[df_inv['categoria'] == cat]
                for _, row in df_cat.iterrows():
                    disp = row['stock_inicial'] - row['ventas_acumuladas']
                    c_a, c_b, c_c, c_d = st.columns([3, 1.5, 2, 1])
                    c_a.write(f"**{row['producto']}**")
                    c_b.write(f"Disp: {int(disp)}")
                    if disp > 0:
                        if c_c.button(f"Venta {row['precio_venta']} Bs", key=f"v_{row['id']}", disabled=not abierto):
                            conn = sqlite3.connect("bazar_final_v9.db")
                            fecha = (datetime.now() - timedelta(hours=4)).strftime("%H:%M (%d/%m)")
                            conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, 1, ?, ?, ?)", 
                                         (row['producto'], row['categoria'], fecha, row['precio_venta']-row['precio_costo'], row['precio_venta']))
                            conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (row['id'],))
                            conn.commit(); conn.close(); st.rerun()
                    else: c_c.error("Agotado")
                    with c_d.popover("➕"):
                        if st.button("Surtir +10", key=f"s_{row['id']}"):
                            conn = sqlite3.connect("bazar_final_v9.db")
                            conn.execute("UPDATE inventario SET stock_inicial = stock_inicial + 10 WHERE id = ?", (row['id'],))
                            conn.commit(); conn.close(); st.rerun()

with col_der:
    st.subheader("💰 Resumen")
    m1, m2 = st.columns(2)
    m1.metric("Caja", f"{df_vts['total_vta'].sum():.2f}")
    m2.metric("Ganancia", f"{df_vts['ganancia_vta'].sum():.2f}")
    
    with st.expander("📝 Actividad", expanded=True):
        if not df_vts.empty:
            hist = []
            cont = 0
            for _, v in df_vts.iterrows():
                if v['categoria'] != 'SISTEMA':
                    cont += 1
                    n = str(cont)
                else: n = "-"
                hist.append({"N°": n, "Hora": v['fecha'], "Detalle": v['nombre_producto'], "Bs": v['total_vta']})
            
            # ELIMINACIÓN DE ÍNDICE EXTRA:
            st.table(pd.DataFrame(hist).set_index("N°"))

# --- 7. CLASIFICACIÓN (Abajo) ---
st.divider()
st.subheader("📊 Por Clasificación")
v_reales = df_vts[df_vts['categoria'] != 'SISTEMA']
if not v_reales.empty:
    res = v_reales.groupby('categoria').agg({'total_vta': 'sum', 'ganancia_vta': 'sum'}).reset_index()
    cols = st.columns(len(res))
    for i, r in res.iterrows():
        with cols[i]:
            st.info(f"**{r['categoria']}**")
            st.write(f"Caja: {r['total_vta']:.2f}")
            st.write(f"Gana: {r['ganancia_vta']:.2f}")
