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
    /* Estilo para que los campos resalten al estar seleccionados */
    input:focus {
        border-color: #ff4b4b !important;
        box-shadow: 0 0 5px #ff4b4b !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS (V13) ---
def init_db():
    conn = sqlite3.connect("bazar_v13_final.db")
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

# --- 3. CARGA DE DATOS ---
conn = sqlite3.connect("bazar_v13_final.db")
df_inv = pd.read_sql_query("SELECT * FROM inventario", conn)
df_vts = pd.read_sql_query("SELECT * FROM ventas ORDER BY id ASC", conn)
estado_data = conn.execute("SELECT abierto FROM estado_tienda WHERE id = 1").fetchone()
conn.close()

abierto = True if estado_data and estado_data[0] == 1 else False

# --- 4. INTERFAZ SUPERIOR ---
st.title("🏪 Bazar Master Pro")
c1, c2 = st.columns([1, 2])
with c1:
    if abierto:
        if st.button("🔒 CERRAR TIENDA", use_container_width=True, type="primary"):
            conn = sqlite3.connect("bazar_v13_final.db")
            conn.execute("UPDATE estado_tienda SET abierto = 0 WHERE id = 1")
            conn.commit(); conn.close(); st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            conn = sqlite3.connect("bazar_v13_final.db")
            conn.execute("UPDATE estado_tienda SET abierto = 1 WHERE id = 1")
            conn.commit(); conn.close(); st.rerun()
with c2:
    st.subheader("🟢 Activo" if abierto else "⚠️ Cerrado")

st.divider()

# --- 5. REGISTRO FLUIDO (Sidebar) ---
with st.sidebar:
    st.header("📦 Registro Rápido")
    st.write("💡 *Usa **Tab** o **Enter** para saltar entre campos*")
    
    # El uso de st.form es clave para que el Enter procese el formulario
    with st.form("registro_fluido", clear_on_submit=True):
        n_nom = st.text_input("1. Nombre del Producto", key="f_nom")
        n_cat = st.selectbox("2. Sección", ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"], key="f_cat")
        
        # Al poner 'value' por defecto, el sistema permite sobreescribir rápido
        n_stk = st.number_input("3. Stock Inicial", min_value=0, value=10, key="f_stk")
        n_cst = st.number_input("4. Costo Unitario (Bs)", min_value=0.0, value=0.0, step=0.1, key="f_cst")
        n_vta = st.number_input("5. Venta Unitario (Bs)", min_value=0.0, value=0.0, step=0.1, key="f_vta")
        
        submit = st.form_submit_button("✅ GUARDAR (Enter)", use_container_width=True)
        
        if submit:
            if n_nom and n_vta > 0:
                try:
                    conn = sqlite3.connect("bazar_v13_final.db")
                    conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", 
                                 (n_nom.strip().upper(), n_cat, n_stk, n_cst, n_vta))
                    conn.commit(); conn.close()
                    st.session_state.ultima_cat = n_cat
                    st.success("¡Guardado!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Ese producto ya existe.")
            else:
                st.warning("Falta nombre o precio.")

# --- 6. MOSTRADOR ---
col_izq, col_der = st.columns([2, 1.3])

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
                    c_a, c_b, c_c, c_d = st.columns([3, 1.5, 2, 1])
                    c_a.write(f"**{row['producto']}**")
                    c_b.write(f"Disp: {int(disp)}")
                    if disp > 0:
                        if c_c.button(f"Venta {row['precio_venta']} Bs", key=f"v_{row['id']}", disabled=not abierto):
                            conn = sqlite3.connect("bazar_v13_final.db")
                            fecha = (datetime.now() - timedelta(hours=4)).strftime("%H:%M")
                            conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, 1, ?, ?, ?)", 
                                         (row['producto'], row['categoria'], 1, fecha, row['precio_venta']-row['precio_costo'], row['precio_venta']))
                            conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (row['id'],))
                            conn.commit(); conn.close(); st.rerun()
                    else: c_c.error("Agotado")
                    with c_d.popover("➕"):
                        if st.button("Surtir +10", key=f"s_{row['id']}"):
                            conn = sqlite3.connect("bazar_v13_final.db")
                            conn.execute("UPDATE inventario SET stock_inicial = stock_inicial + 10 WHERE id = ?", (row['id'],))
                            conn.commit(); conn.close(); st.rerun()

with col_der:
    st.subheader("💰 Resumen Diario")
    m1, m2 = st.columns(2)
    m1.metric("En Caja", f"{df_vts['total_vta'].sum():.2f}")
    m2.metric("Ganancia", f"{df_vts['ganancia_vta'].sum():.2f}")
    
    with st.expander("📝 Actividad", expanded=True):
        if not df_vts.empty:
            hist = []
            cont = 0
            for i, v in df_vts.iterrows():
                cont += 1
                hist.append({"N°": cont, "Hora": v['fecha'], "Producto": v['nombre_producto'], "Bs": f"{v['total_vta']:.2f}"})
            st.table(pd.DataFrame(hist).set_index("N°"))

# --- 7. RESUMEN ABAJO ---
st.divider()
if not df_vts.empty:
    res = df_vts[df_vts['total_vta'] > 0].groupby('categoria').agg({'total_vta': 'sum', 'ganancia_vta': 'sum'}).reset_index()
    cols = st.columns(len(res))
    for i, r in res.iterrows():
        with cols[i]:
            st.info(f"**{r['categoria']}**\n\nCaja: {r['total_vta']:.2f}\n\nGana: {r['ganancia_vta']:.2f}")
