import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Bazar Master Pro v33", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stAppDeployButton {visibility: hidden;}
    [data-testid="stHeader"] {display:none !important;}
    input, .stSelectbox div[data-baseweb="select"], .stSelectbox div[data-baseweb="select"] > div {
        background-color: #262730 !important; color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important; font-weight: 700 !important;
        font-size: 16px !important;
    }
    svg[title="open"] { fill: #FF4B4B !important; width: 22px !important; }
    label p { color: #000000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS ---
DB_NAME = "bazar_pro_v33.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT UNIQUE, categoria TEXT, 
        stock_inicial INTEGER, precio_costo REAL, precio_venta REAL, ventas_acumuladas INTEGER DEFAULT 0)""")
    # Tabla unificada de actividad (Ventas + Tienda)
    cursor.execute("""CREATE TABLE IF NOT EXISTS actividad (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        fecha_hora TEXT, 
        detalle TEXT, 
        monto REAL DEFAULT 0.0)""")
    cursor.execute("CREATE TABLE IF NOT EXISTS estado_tienda (id INTEGER PRIMARY KEY, abierto INTEGER)")
    cursor.execute("INSERT OR IGNORE INTO estado_tienda (id, abierto) VALUES (1, 0)")
    conn.commit()
    conn.close()

init_db()

def get_data():
    conn = sqlite3.connect(DB_NAME)
    inv = pd.read_sql_query("SELECT * FROM inventario", conn)
    act = pd.read_sql_query("SELECT * FROM actividad ORDER BY id DESC LIMIT 15", conn)
    # Calcular caja del día (solo sumando ventas, no eventos de apertura)
    caja = conn.execute("SELECT SUM(monto) FROM actividad WHERE detalle NOT LIKE '%TIENDA%'").fetchone()[0]
    res_est = conn.execute("SELECT abierto FROM estado_tienda WHERE id = 1").fetchone()
    conn.close()
    return inv, act, (caja if caja else 0.0), (res_est[0] if res_est else 0)

df_inv, df_act, caja_total, estado_abierto = get_data()
abierto = True if estado_abierto == 1 else False
ahora = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")

# --- 3. CABECERA Y CONTROL DE TIENDA ---
st.title("🏪 Bazar Master Pro")
col_t1, col_t2 = st.columns([1, 2])

with col_t1:
    if abierto:
        if st.button("🔒 CERRAR TIENDA", use_container_width=True, type="primary"):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("UPDATE estado_tienda SET abierto = 0 WHERE id = 1")
            conn.execute("INSERT INTO actividad (fecha_hora, detalle, monto) VALUES (?,?,?)", (ahora, "❌ TIENDA CERRADA", 0.0))
            conn.commit(); conn.close(); st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("UPDATE estado_tienda SET abierto = 1 WHERE id = 1")
            conn.execute("INSERT INTO actividad (fecha_hora, detalle, monto) VALUES (?,?,?)", (ahora, "✅ TIENDA ABIERTA", 0.0))
            conn.commit(); conn.close(); st.rerun()

with col_t2:
    st.subheader("🟢 EN LÍNEA" if abierto else "⚠️ CERRADO")

st.divider()

# --- 4. CUERPO PRINCIPAL (Registro y Resumen arriba) ---
col_reg, col_res = st.columns([1.5, 2])

with col_reg:
    with st.expander("📦 Registrar Nuevo Producto", expanded=True):
        reg_nom = st.text_input("Nombre", key="n", placeholder="Ej: PAPA FRITA")
        reg_cat = st.selectbox("Sección", ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"])
        c_r1, c_r2, c_r3 = st.columns(3)
        reg_stk = c_r1.number_input("Stock", min_value=0, value=10)
        reg_cst = c_r2.number_input("Costo", min_value=0.0, value=1.0)
        reg_vta = c_r3.number_input("Venta", min_value=0.0, value=1.5)
        
        if st.button("💾 GUARDAR", use_container_width=True):
            if reg_nom:
                nombre_up = reg_nom.strip().upper()
                try:
                    conn = sqlite3.connect(DB_NAME)
                    conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", 
                                 (nombre_up, reg_cat, reg_stk, reg_cst, reg_vta))
                    conn.commit(); conn.close(); st.rerun()
                except: st.error("Ya existe.")

with col_res:
    st.metric("💰 CAJA DEL DÍA", f"{caja_total:.2f} Bs")
    st.subheader("📜 Historial de Actividad")
    if not df_act.empty:
        # Mostramos el historial unificado (Fecha, Detalle, Monto)
        st.table(df_act[['fecha_hora', 'detalle', 'monto']].rename(columns={'fecha_hora':'Fecha/Hora', 'detalle':'Movimiento', 'monto':'Bs'}))

st.divider()

# --- 5. MOSTRADOR (Secciones divididas en la parte inferior) ---
st.subheader("🛒 MOSTRADOR POR SECCIONES")
if not df_inv.empty:
    categorias = sorted(df_inv['categoria'].unique())
    tabs = st.tabs(categorias)
    
    for i, cat in enumerate(categorias):
        with tabs[i]:
            df_cat = df_inv[df_inv['categoria'] == cat]
            # Crear filas para los productos de esta categoría
            for _, row in df_cat.iterrows():
                disp = row['stock_inicial'] - row['ventas_acumuladas']
                c1, c2, c3, c4 = st.columns([3, 1, 2, 1])
                c1.write(f"**{row['producto']}**")
                c2.write(f"Stock: {int(disp)}")
                
                if disp > 0:
                    if c3.button(f"Vender {row['precio_venta']} Bs", key=f"v_{row['id']}", disabled=not abierto, use_container_width=True):
                        conn = sqlite3.connect(DB_NAME)
                        conn.execute("INSERT INTO actividad (fecha_hora, detalle, monto) VALUES (?,?,?)", 
                                     (ahora, row['producto'], row['precio_venta']))
                        conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (row['id'],))
                        conn.commit(); conn.close(); st.rerun()
                else:
                    c3.error("Agotado")
                
                with c4.popover("➕"):
                    if st.button("Surtir +10", key=f"s_{row['id']}"):
                        conn = sqlite3.connect(DB_NAME)
                        conn.execute("UPDATE inventario SET stock_inicial = stock_inicial + 10 WHERE id = ?", (row['id'],))
                        conn.commit(); conn.close(); st.rerun()
else:
    st.info("No hay productos registrados aún.")
