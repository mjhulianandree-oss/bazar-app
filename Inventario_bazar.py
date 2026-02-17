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
    conn = sqlite3.connect("bazar_master_v2.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS inventario (id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT, categoria TEXT, stock_inicial INTEGER, precio_costo REAL, precio_venta REAL, ventas_acumuladas INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_producto TEXT, cantidad INTEGER, fecha TEXT, ganancia_vta REAL, total_vta REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS estado_tienda (id INTEGER PRIMARY KEY, abierto INTEGER, ultima_actividad TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS cierres_caja (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, total_venta REAL, ganancia_total REAL)")
    cursor.execute("INSERT OR IGNORE INTO estado_tienda (id, abierto, ultima_actividad) VALUES (1, 0, 'No registrado')")
    conn.commit()
    conn.close()

def cambiar_estado_tienda(nuevo_estado, resumen=None):
    conn = sqlite3.connect("bazar_master_v2.db")
    cursor = conn.cursor()
    hora = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")
    cursor.execute("UPDATE estado_tienda SET abierto = ?, ultima_actividad = ? WHERE id = 1", (nuevo_estado, hora))
    if resumen:
        cursor.execute("INSERT INTO cierres_caja (fecha, total_venta, ganancia_total) VALUES (?, ?, ?)", (hora, resumen['total'], resumen['ganancia']))
    conn.commit()
    conn.close()

def surtir_stock(id_prod, cantidad):
    conn = sqlite3.connect("bazar_master_v2.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE inventario SET stock_inicial = stock_inicial + ? WHERE id = ?", (cantidad, id_prod))
    conn.commit()
    conn.close()

def registrar_venta(id_prod, nombre_prod, p_venta, p_costo):
    conn = sqlite3.connect("bazar_master_v2.db")
    cursor = conn.cursor()
    ganancia = p_venta - p_costo
    fecha = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")
    cursor.execute("INSERT INTO ventas (nombre_producto, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, ?, ?, ?)", (nombre_prod, 1, fecha, ganancia, p_venta))
    cursor.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (id_prod,))
    conn.commit()
    conn.close()

init_db()

# --- 4. CARGA DE DATOS ---
conn = sqlite3.connect("bazar_master_v2.db")
df_inv = pd.read_sql_query("SELECT * FROM inventario", conn)
df_vts = pd.read_sql_query("SELECT * FROM ventas", conn)
estado = conn.execute("SELECT abierto, ultima_actividad FROM estado_tienda WHERE id = 1").fetchone()
conn.close()

tienda_abierta = True if estado[0] == 1 else False

# --- 5. CABECERA Y CONTROL ---
st.title("🏪 Bazar Master Pro")

col_e1, col_e2 = st.columns([1, 2])
with col_e1:
    if tienda_abierta:
        if st.button("🔒 CERRAR TIENDA", use_container_width=True, type="primary"):
            hoy_vta = df_vts['total_vta'].sum()
            hoy_gan = df_vts['ganancia_vta'].sum()
            cambiar_estado_tienda(0, {'total': hoy_vta, 'ganancia': hoy_gan})
            st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            cambiar_estado_tienda(1)
            st.rerun()

with col_e2:
    status = "🟢 TIENDA ABIERTA" if tienda_abierta else "🔴 TIENDA CERRADA"
    st.subheader(f"{status} (Actividad: {estado[1]})")

st.divider()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.header("📦 Registro")
    n_nom = st.text_input("Nombre")
    n_cat = st.selectbox("Sección", ["🍭 Dulces", "🥤 Bebidas", "🥛 Lácteos", "📝 Útiles", "🏠 Otros"])
    n_stk = st.number_input("Stock Inicial", min_value=1, value=10)
    n_cst = st.number_input("Costo unitario", min_value=0.1, value=1.0)
    n_vta = st.number_input("Venta unitario", min_value=0.1, value=1.5)
    if st.button("Guardar"):
        if n_nom:
            conn = sqlite3.connect("bazar_master_v2.db")
            conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", (n_nom, n_cat, n_stk, n_cst, n_vta))
            conn.commit()
            conn.close()
            st.rerun()

# --- 7. CUERPO PRINCIPAL ---
c_inv, c_res = st.columns([2, 1.3])

with c_inv:
    st.subheader("📦 Mostrador")
    if not df_inv.empty:
        tabs = st.tabs(df_inv['categoria'].unique().tolist())
        for i, cat in enumerate(df_inv['categoria'].unique().tolist()):
            with tabs[i]:
                df_cat = df_inv[df_inv['categoria'] == cat]
                for _, row in df_cat.iterrows():
                    stk = row['stock_inicial'] - row['ventas_acumuladas']
                    c1, c2, c3, c4 = st.columns([3, 1.5, 2, 1])
                    c1.write(f"**{row['producto']}**")
                    c2.write(f"Disp: {int(stk)}")
                    
                    if stk > 0:
                        if c3.button(f"Venta {row['precio_venta']} Bs", key=f"v_{row['id']}", disabled=not tienda_abierta):
                            registrar_venta(row['id'], row['producto'], row['precio_venta'], row['precio_costo'])
                            st.rerun()
                    else:
                        c3.error("Agotado")
                    
                    with c4.popover("➕"):
                        mas_stk = st.number_input("Cantidad", min_value=1, value=10, key=f"add_{row['id']}")
                        if st.button("Surtir", key=f"btn_add_{row['id']}"):
                            surtir_stock(row['id'], mas_stk)
                            st.rerun()
                    
                    if stk <= 0:
                        if st.button("🗑️", key=f"del_{row['id']}"):
                            conn = sqlite3.connect("bazar_master_v2.db")
                            conn.execute("DELETE FROM inventario WHERE id=?", (row['id'],))
                            conn.commit()
                            conn.close()
                            st.rerun()

with c_res:
    st.subheader("💰 Resumen de Caja")
    
    # --- LAS DOS MÉTRICAS CLAVE ---
    total_efectivo = df_vts['total_vta'].sum()
    ganancia_neta = df_vts['ganancia_vta'].sum()
    
    m1, m2 = st.columns(2)
    m1.metric("Dinero en Caja", f"{total_efectivo:.2f} Bs")
    m2.metric("Ganancia Limpia", f"{ganancia_neta:.2f} Bs")
    
    st.divider()
    
    with st.expander("📝 Ventas del Turno", expanded=True):
        if not df_vts.empty:
            df_h = df_vts[['fecha', 'nombre_producto', 'total_vta']].copy()
            df_h.index = range(1, len(df_h)+1)
            st.table(df_h.rename(columns={'nombre_producto':'Producto','total_vta':'Precio'}))
        else:
            st.info("Caja vacía.")
    
    with st.expander("📊 Historial de Cierres"):
        conn = sqlite3.connect("bazar_master_v2.db")
        df_cierres = pd.read_sql_query("SELECT * FROM cierres_caja ORDER BY id DESC", conn)
        conn.close()
        if not df_cierres.empty:
            st.dataframe(df_cierres[['fecha', 'total_venta', 'ganancia_total']], hide_index=True)
