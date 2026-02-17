import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN VISUAL (ESTRUCTURA MANTENIDA + PARCHE SIN INSTRUCCIONES) ---
st.set_page_config(page_title="Bazar Master Pro", layout="wide")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stAppDeployButton {visibility: hidden;}
    [data-testid="stHeader"] {display:none !important;}
    .stApp { background-color: #0E1117; }
    html, body, p, h1, h2, h3, h4, span, label, .stMarkdown { color: #FFFFFF !important; }
    
    /* OCULTAR MENSAJE "PRESS ENTER TO APPLY" */
    .stInstructions { display: none !important; }
    
    /* Parche de Color para Casillas */
    input, .stSelectbox div[data-baseweb="select"], .stSelectbox select { 
        background-color: #262730 !important; 
        color: #FFFFFF !important; 
        border-color: #4a4a4a !important;
    }
    
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #FFFFFF !important; }
    hr { border-color: #4a4a4a !important; }
    [data-testid="stTable"] { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS (NUEVA PARA EMPEZAR DE 0) ---
DB_NAME = "bazar_final_PROD.db"
CATEGORIAS = ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"]

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT UNIQUE, categoria TEXT, 
        stock_inicial INTEGER, precio_costo REAL, precio_venta REAL, ventas_acumuladas INTEGER DEFAULT 0)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_producto TEXT, categoria TEXT,
        cantidad INTEGER, fecha TEXT, ganancia_vta REAL, total_vta REAL)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS log_actividad (
        id INTEGER PRIMARY KEY AUTOINCREMENT, hora TEXT, detalle TEXT)""")
    cursor.execute("CREATE TABLE IF NOT EXISTS estado_tienda (id INTEGER PRIMARY KEY, abierto INTEGER)")
    conn.commit()
    cursor.execute("INSERT OR IGNORE INTO estado_tienda (id, abierto) VALUES (1, 0)")
    conn.commit()
    conn.close()

init_db()

def get_data():
    conn = sqlite3.connect(DB_NAME)
    inv = pd.read_sql_query("SELECT * FROM inventario", conn)
    vts = pd.read_sql_query("SELECT * FROM ventas", conn)
    act = pd.read_sql_query("SELECT hora as 'Fecha y Hora', detalle as 'Actividad' FROM log_actividad ORDER BY id DESC LIMIT 20", conn)
    res_est = conn.execute("SELECT abierto FROM estado_tienda WHERE id = 1").fetchone()
    conn.close()
    return inv, vts, act, (res_est[0] if res_est else 0)

df_inv, df_vts, df_act, estado_abierto = get_data()
abierto = True if estado_abierto == 1 else False
ahora_full = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")

# --- 3. CABECERA ---
st.title("🏪 Bazar Master Pro")
col1, col2 = st.columns([1, 2])
with col1:
    if abierto:
        if st.button("🔒 CERRAR TIENDA", use_container_width=True, type="primary"):
            conn = sqlite3.connect(DB_NAME); conn.execute("UPDATE estado_tienda SET abierto = 0 WHERE id = 1")
            conn.execute("INSERT INTO log_actividad (hora, detalle) VALUES (?,?)", (ahora_full, "CERRADO 🔒"))
            conn.commit(); conn.close(); st.rerun()
    else:
        if st.button("🔓 ABRIR TIENDA", use_container_width=True):
            conn = sqlite3.connect(DB_NAME); conn.execute("UPDATE estado_tienda SET abierto = 1 WHERE id = 1")
            conn.execute("INSERT INTO log_actividad (hora, detalle) VALUES (?,?)", (ahora_full, "ABIERTO 🔓"))
            conn.commit(); conn.close(); st.rerun()
with col2:
    st.subheader("🟢 Activo" if abierto else "⚠️ Cerrado")

st.divider()

# --- 4. REGISTRO (VALORES INICIALES EN 0) ---
with st.sidebar:
    st.header("📦 Registro")
    with st.form("registro_prod", clear_on_submit=True):
        reg_nom = st.text_input("Nombre")
        reg_cat = st.selectbox("Sección", CATEGORIAS)
        reg_stk = st.number_input("Stock Inicial", min_value=0, value=0)
        reg_cst = st.number_input("Costo (Bs)", min_value=0.0, value=0.0)
        reg_vta = st.number_input("Venta (Bs)", min_value=0.0, value=0.0)
        if st.form_submit_button("💾 GUARDAR", use_container_width=True):
            if reg_nom:
                nombre_up = reg_nom.strip().upper()
                conn = sqlite3.connect(DB_NAME)
                # PARCHE 2: VERIFICAR SI EXISTE (PARA EVITAR ERRORES)
                existe = conn.execute("SELECT 1 FROM inventario WHERE producto = ?", (nombre_up,)).fetchone()
                if not existe:
                    conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", 
                                 (nombre_up, reg_cat, reg_stk, reg_cst, reg_vta))
                    conn.execute("INSERT INTO log_actividad (hora, detalle) VALUES (?,?)", (ahora_full, f"NUEVO: {nombre_up}"))
                    conn.commit(); conn.close(); st.rerun()
                else:
                    conn.close(); st.warning(f"'{nombre_up}' ya existe.")

# --- 5. MOSTRADOR ---
col_izq, col_der = st.columns([2.5, 1])

with col_izq:
    st.subheader("🛒 Panel de Ventas")
    if not df_inv.empty:
        tabs = st.tabs(CATEGORIAS)
        for i, cat in enumerate(CATEGORIAS):
            with tabs[i]:
                df_cat = df_inv[df_inv['categoria'] == cat]
                for _, row in df_cat.iterrows():
                    disp = row['stock_inicial'] - row['ventas_acumuladas']
                    vta_indiv = row['ventas_acumuladas']
                    
                    c_a, c_b, c_input, c_btn_add, c_vta, c_edit = st.columns([2, 0.8, 0.7, 0.5, 1.4, 0.4])
                    c_a.write(f"**{row['producto']}** \n*(V: {int(vta_indiv)})*")
                    c_b.write(f"Tienda: {int(disp)}")
                    
                    add_val = c_input.number_input("Cant", min_value=1, value=1, key=f"num_{row['id']}", label_visibility="collapsed")
                    
                    if c_btn_add.button("➕", key=f"add_{row['id']}"):
                        conn = sqlite3.connect(DB_NAME)
                        conn.execute("UPDATE inventario SET stock_inicial = stock_inicial + ? WHERE id = ?", (add_val, row['id']))
                        conn.execute("INSERT INTO log_actividad (hora, detalle) VALUES (?,?)", (ahora_full, f"STOCK +{add_val}: {row['producto']}"))
                        conn.commit(); conn.close(); st.rerun()
                    
                    if disp > 0:
                        if c_vta.button(f"Venta {row['precio_venta']} Bs", key=f"v_{row['id']}", disabled=not abierto, use_container_width=True):
                            conn = sqlite3.connect(DB_NAME)
                            conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, 1, ?, ?, ?)", 
                                         (row['producto'], row['categoria'], ahora_full, row['precio_venta']-row['precio_costo'], row['precio_venta']))
                            conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (row['id'],))
                            conn.execute("INSERT INTO log_actividad (hora, detalle) VALUES (?,?)", (ahora_full, f"VENTA: {row['producto']}"))
                            conn.commit(); conn.close(); st.rerun()
                    else: c_vta.error("Agotado")
                    
                    with c_edit:
                        if st.button("✏️", key=f"pencil_{row['id']}"):
                            st.session_state[f"editing_{row['id']}"] = True
                    
                    if st.session_state.get(f"editing_{row['id']}", False):
                        with st.expander(f"Editar: {row['producto']}", expanded=True):
                            e1, e2 = st.columns(2)
                            new_cat = e1.selectbox("Mover a sección:", CATEGORIAS, index=CATEGORIAS.index(cat), key=f"newcat_{row['id']}")
                            new_price = e2.number_input("Nuevo Precio Venta:", min_value=0.0, value=row['precio_venta'], key=f"newprice_{row['id']}")
                            b1, b2 = st.columns(2)
                            if b1.button("✅ Aplicar", key=f"ok_{row['id']}", use_container_width=True):
                                conn = sqlite3.connect(DB_NAME)
                                conn.execute("UPDATE inventario SET categoria = ?, precio_venta = ? WHERE id = ?", (new_cat, new_price, row['id']))
                                conn.execute("INSERT INTO log_actividad (hora, detalle) VALUES (?,?)", (ahora_full, f"EDITADO: {row['producto']}"))
                                conn.commit(); conn.close()
                                st.session_state[f"editing_{row['id']}"] = False
                                st.rerun()
                            if b2.button("❌", key=f"cancel_{row['id']}", use_container_width=True):
                                st.session_state[f"editing_{row['id']}"] = False
                                st.rerun()

                st.markdown("---")
                df_vts_cat = df_vts[df_vts['categoria'] == cat]
                if not df_vts_cat.empty:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Vendido Total", f"{int(df_vts_cat['cantidad'].sum())} u.")
                    m2.metric("Ganancia", f"{df_vts_cat['ganancia_vta'].sum():.2f} Bs")
                    m3.metric("Caja", f"{df_vts_cat['total_vta'].sum():.2f} Bs")

with col_der:
    st.subheader("💰 Balance Hoy")
    total_caja = df_vts['total_vta'].sum() if not df_vts.empty else 0.0
    total_ganancia = df_vts['ganancia_vta'].sum() if not df_vts.empty else 0.0
    mc1, mc2 = st.columns(2)
    mc1.metric("Caja General", f"{total_caja:.2f} Bs")
    mc2.metric("Ganancia Total", f"{total_ganancia:.2f} Bs")
    st.write("---")
    st.subheader("📜 Actividad")
    if not df_act.empty:
        # PARCHE 1: ACTIVIDAD LIMPIA SIN ÍNDICE
        st.dataframe(df_act, use_container_width=True, hide_index=True)
    else: st.write("Sin actividad.")
