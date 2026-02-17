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
    conn = sqlite3.connect("bazar_master_v8.db")
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
    conn = sqlite3.connect("bazar_master_v8.db")
    conn.execute("UPDATE estado_tienda SET abierto = ? WHERE id = 1", (1 if abrir else 0,))
    conn.commit()
    conn.close()
    # Registro de evento
    hora = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")
    conn = sqlite3.connect("bazar_master_v8.db")
    conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, 'SISTEMA', 0, ?, 0, 0)", 
                 ("🟢 TIENDA ABIERTA" if abrir else "🔴 TIENDA CERRADA", hora))
    conn.commit()
    conn.close()

init_db()

# --- 4. CARGA DE DATOS ---
conn = sqlite3.connect("bazar_master_v8.db")
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

# --- 6. SIDEBAR (REGISTRO CON SALTOS) ---
with st.sidebar:
    st.header("📦 Registro Rápido")
    with st.form("form_registro", clear_on_submit=True):
        n_nom = st.text_input("Nombre del Producto")
        n_cat = st.selectbox("Sección", ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"])
        n_stk = st.number_input("Stock Inicial", min_value=1, value=10)
        n_cst = st.number_input("Costo unitario (Bs)", min_value=0.1, step=0.1)
        n_vta = st.number_input("Venta unitario (Bs)", min_value=0.1, step=0.1)
        
        enviar = st.form_submit_button("Guardar Producto")
        
        if enviar:
            if n_nom:
                try:
                    conn = sqlite3.connect("bazar_master_v8.db")
                    conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", 
                                 (n_nom, n_cat, n_stk, n_cst, n_vta))
                    conn.commit()
                    conn.close()
                    st.session_state.pestaña_activa = n_cat # Guardamos la categoría para saltar a ella
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("⚠️ Este producto ya existe. ¡Usa el botón '+' para surtirlo!")

# --- 7. MOSTRADOR ---
c_inv, c_res = st.columns([2, 1.3])

with c_inv:
    st.subheader("📦 Mostrador")
    if not df_inv.empty:
        lista_categorias = df_inv['categoria'].unique().tolist()
        
        # Lógica para saltar a la pestaña del producto recién guardado
        indice_pestaña = 0
        if 'pestaña_activa' in st.session_state and st.session_state.pestaña_activa in lista_categorias:
            indice_pestaña = lista_categorias.index(st.session_state.pestaña_activa)
        
        tabs = st.tabs(lista_categorias)
        
        for i, cat in enumerate(lista_categorias):
            with tabs[i]:
                df_cat = df_inv[df_inv['categoria'] == cat]
                for _, row in df_cat.iterrows():
                    stk = row['stock_inicial'] - row['ventas_acumuladas']
                    col1, col2, col3, col4 = st.columns([3, 1.5, 2, 1])
                    col1.write(f"**{row['producto']}**")
                    col2.write(f"Disp: {int(stk)}")
                    
                    if stk > 0:
                        if col3.button(f"Venta {row['precio_venta']} Bs", key=f"v_{row['id']}", disabled=not abierto):
                            # Registrar Venta
                            conn = sqlite3.connect("bazar_master_v8.db")
                            fecha = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")
                            conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, 1, ?, ?, ?)", 
                                         (row['producto'], row['categoria'], fecha, row['precio_venta']-row['precio_costo'], row['precio_venta']))
                            conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (row['id'],))
                            conn.commit(); conn.close(); st.rerun()
                    else: col3.error("Agotado")
                    
                    with col4.popover("➕"):
                        cant = st.number_input("Surtir", min_value=1, value=10, key=f"s_{row['id']}")
                        if st.button("Ok", key=f"bs_{row['id']}"):
                            conn = sqlite3.connect("bazar_master_v8.db")
                            conn.execute("UPDATE inventario SET stock_inicial = stock_inicial + ? WHERE id = ?", (cant, row['id']))
                            conn.commit(); conn.close(); st.rerun()

with c_res:
    st.subheader("💰 Resumen de Caja")
    m1, m2 = st.columns(2)
    m1.metric("En Caja", f"{df_vts['total_vta'].sum():.2f} Bs")
    m2.metric("Ganancia", f"{df_vts['ganancia_vta'].sum():.2f} Bs")
    
    with st.expander("📝 Diario de Actividad", expanded=True):
        if not df_vts.empty:
            historial_visual = []
            contador_productos = 0
            for _, vta in df_vts.iterrows():
                if vta['categoria'] != 'SISTEMA':
                    contador_productos += 1
                    num_str = f"{contador_productos}"
                else: num_str = "-"
                historial_visual.append({
                    "N°": num_str,
                    "Fecha": vta['fecha'],
                    "Descripción": vta['nombre_producto'],
                    "Bs": f"{vta['total_vta']:.2f}" if vta['total_vta'] > 0 else ""
                })
            st.table(pd.DataFrame(historial_visual).set_index("N°"))

# --- 8. RESUMEN POR SECCIONES (ABAJO) ---
st.divider()
st.subheader("📊 Control por Clasificación")
v_prods = df_vts[df_vts['categoria'] != 'SISTEMA']
if not v_prods.empty:
    resumen_secciones = v_prods.groupby('categoria').agg({'cantidad': 'sum', 'total_vta': 'sum', 'ganancia_vta': 'sum'}).reset_index()
    columnas_cat = st.columns(len(resumen_secciones))
    for i, row_cat in resumen_secciones.iterrows():
        with columnas_cat[i]:
            st.info(f"**{row_cat['categoria']}**")
            st.write(f"Venta: {row_cat['total_vta']:.2f} Bs")
            st.write(f"Ganancia: {row_cat['ganancia_vta']:.2f} Bs")
