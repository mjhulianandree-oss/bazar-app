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
    .stInstructions { display: none !important; }
    input, .stSelectbox div[data-baseweb="select"], .stSelectbox select { 
        background-color: #262730 !important; color: #FFFFFF !important; border-color: #4a4a4a !important;
    }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #FFFFFF !important; }
    hr { border-color: #4a4a4a !important; }
    [data-testid="stTable"] { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS Y GESTIÓN DE CATEGORÍAS ---
DB_NAME = "bazar_final_PROD.db"

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
    # Tabla para categorías dinámicas
    cursor.execute("CREATE TABLE IF NOT EXISTS categorias (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE)")
    conn.commit()
    
    # Categorías iniciales si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM categorias")
    if cursor.fetchone()[0] == 0:
        cats = ["🍭 Dulces y Snacks", "🥤 Bebidas/Líquidos", "🥛 Lácteos", "📝 Escolar/Académico", "🏠 Otros"]
        cursor.executemany("INSERT INTO categorias (nombre) VALUES (?)", [(c,) for c in cats])
    
    cursor.execute("INSERT OR IGNORE INTO estado_tienda (id, abierto) VALUES (1, 0)")
    conn.commit()
    conn.close()

init_db()

def get_data():
    conn = sqlite3.connect(DB_NAME)
    inv = pd.read_sql_query("SELECT * FROM inventario", conn)
    vts = pd.read_sql_query("SELECT * FROM ventas", conn)
    act = pd.read_sql_query("SELECT hora as 'Fecha y Hora', detalle as 'Actividad' FROM log_actividad ORDER BY id DESC LIMIT 20", conn)
    cats = [r[0] for r in conn.execute("SELECT nombre FROM categorias").fetchall()]
    res_est = conn.execute("SELECT abierto FROM estado_tienda WHERE id = 1").fetchone()
    conn.close()
    return inv, vts, act, cats, (res_est[0] if res_est else 0)

df_inv, df_vts, df_act, CATEGORIAS, estado_abierto = get_data()
abierto = True if estado_abierto == 1 else False
ahora_full = (datetime.now() - timedelta(hours=4)).strftime("%d/%m %H:%M")

# --- 3. CABECERA ---
st.title("🏪 Bazar Master Pro")
col_e1, col_e2 = st.columns([1, 2])
with col_e1:
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
with col_e2:
    st.subheader("🟢 Activo" if abierto else "⚠️ Cerrado")

# --- 4. REGISTRO FRONTAL ---
with st.expander("➕ REGISTRAR NUEVO PRODUCTO", expanded=False):
    with st.form("registro_frontal", clear_on_submit=True):
        f1, f2, f3, f4, f5 = st.columns([2, 1.5, 1, 1, 1])
        reg_nom = f1.text_input("Nombre")
        reg_cat = f2.selectbox("Sección", CATEGORIAS)
        reg_stk = f3.number_input("Stock", min_value=0, value=0)
        reg_cst = f4.number_input("Costo Bs", min_value=0.0, value=0.0)
        reg_vta = f5.number_input("Venta Bs", min_value=0.0, value=0.0)
        if st.form_submit_button("💾 GUARDAR PRODUCTO", use_container_width=True):
            if reg_nom:
                nombre_up = reg_nom.strip().upper()
                conn = sqlite3.connect(DB_NAME)
                # PARCHE 2: EVITAR DUPLICADOS
                if not conn.execute("SELECT 1 FROM inventario WHERE producto = ?", (nombre_up,)).fetchone():
                    conn.execute("INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?,?)", 
                                 (nombre_up, reg_cat, reg_stk, reg_cst, reg_vta))
                    conn.execute("INSERT INTO log_actividad (hora, detalle) VALUES (?,?)", (ahora_full, f"NUEVO: {nombre_up}"))
                    conn.commit(); conn.close(); st.rerun()
                else: conn.close(); st.warning("Ya existe.")

st.divider()

# --- 5. MOSTRADOR ---
col_izq, col_der = st.columns([2.5, 1])

with col_izq:
    tabs = st.tabs(CATEGORIAS + ["📋 INVENTARIO NETO", "⚙️ AJUSTES"])
    
    # --- VENTAS POR CATEGORÍA ---
    for i, cat in enumerate(CATEGORIAS):
        with tabs[i]:
            df_cat = df_inv[df_inv['categoria'] == cat]
            for _, row in df_cat.iterrows():
                disp = row['stock_inicial'] - row['ventas_acumuladas']
                c_a, c_b, c_vta = st.columns([2, 1, 1.5])
                c_a.write(f"**{row['producto']}**")
                c_b.write(f"Tienda: {int(disp)}")
                if disp > 0:
                    if c_vta.button(f"Venta {row['precio_venta']} Bs", key=f"v_{row['id']}", disabled=not abierto, use_container_width=True):
                        conn = sqlite3.connect(DB_NAME)
                        conn.execute("INSERT INTO ventas (nombre_producto, categoria, cantidad, fecha, ganancia_vta, total_vta) VALUES (?, ?, 1, ?, ?, ?)", 
                                     (row['producto'], row['categoria'], ahora_full, row['precio_venta']-row['precio_costo'], row['precio_venta']))
                        conn.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (row['id'],))
                        conn.execute("INSERT INTO log_actividad (hora, detalle) VALUES (?,?)", (ahora_full, f"VENTA: {row['producto']}"))
                        conn.commit(); conn.close(); st.rerun()
                else: c_vta.error("Agotado")

    # --- INVENTARIO NETO (POR SECCIONES) ---
    with tabs[-2]:
        st.subheader("📊 Control Maestro")
        for cat in CATEGORIAS:
            with st.expander(f"📁 {cat}", expanded=True):
                df_c = df_inv[df_inv['categoria'] == cat]
                for _, row in df_c.iterrows():
                    tienda = row['stock_inicial'] - row['ventas_acumuladas']
                    c1, c2, c3, c4, c5 = st.columns([2, 0.8, 0.8, 0.5, 0.3])
                    c1.write(f"**{row['producto']}**")
                    c2.write(f"Stock: {int(tienda)}")
                    n_stk = c3.number_input("Sumar", min_value=1, value=1, key=f"inv_n_{row['id']}", label_visibility="collapsed")
                    if c4.button("➕", key=f"bi_{row['id']}"):
                        conn = sqlite3.connect(DB_NAME); conn.execute("UPDATE inventario SET stock_inicial = stock_inicial + ? WHERE id = ?", (n_stk, row['id']))
                        conn.commit(); conn.close(); st.rerun()
                    if c5.button("✏️", key=f"ed_btn_{row['id']}"): st.session_state[f"edit_all_{row['id']}"] = True
                    
                    if st.session_state.get(f"edit_all_{row['id']}", False):
                        with st.form(f"f_ed_{row['id']}"):
                            new_name = st.text_input("Nombre", value=row['producto'])
                            new_cat = st.selectbox("Categoría", CATEGORIAS, index=CATEGORIAS.index(row['categoria']))
                            new_vta = st.number_input("Precio Venta", value=row['precio_venta'])
                            new_cst = st.number_input("Precio Costo", value=row['precio_costo'])
                            if st.form_submit_button("Actualizar"):
                                conn = sqlite3.connect(DB_NAME)
                                conn.execute("UPDATE inventario SET producto=?, categoria=?, precio_venta=?, precio_costo=? WHERE id=?", 
                                             (new_name.upper(), new_cat, new_vta, new_cst, row['id']))
                                conn.commit(); conn.close()
                                st.session_state[f"edit_all_{row['id']}"] = False
                                st.rerun()

    # --- AJUSTES DE SECCIONES ---
    with tabs[-1]:
        st.subheader("🛠️ Gestionar Secciones")
        # Crear Nueva
        with st.form("nueva_cat"):
            n_c = st.text_input("Nombre de nueva sección (Ej: 🍞 Panadería)")
            if st.form_submit_button("➕ Crear Sección"):
                if n_c:
                    conn = sqlite3.connect(DB_NAME); conn.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES (?)", (n_c.strip(),))
                    conn.commit(); conn.close(); st.rerun()
        
        # Cambiar nombre / Quitar (Solo si no tienen productos)
        st.write("---")
        for c in CATEGORIAS:
            col_c1, col_c2 = st.columns([3, 1])
            col_c1.write(f"Sección actual: **{c}**")
            if col_c2.button("🗑️ Borrar", key=f"del_{c}"):
                if not df_inv[df_inv['categoria'] == c].empty:
                    st.error("No puedes borrar una sección que tiene productos.")
                else:
                    conn = sqlite3.connect(DB_NAME); conn.execute("DELETE FROM categorias WHERE nombre = ?", (c,))
                    conn.commit(); conn.close(); st.rerun()

with col_der:
    st.subheader("💰 Balance")
    total_caja = df_vts['total_vta'].sum() if not df_vts.empty else 0.0
    mc1, mc2 = st.columns(2)
    mc1.metric("Caja", f"{total_caja:.2f} Bs")
    mc2.metric("Ganancia", f"{df_vts['ganancia_vta'].sum():.2f} Bs")
    st.write("---")
    st.subheader("📜 Actividad")
    if not df_act.empty:
        # PARCHE 1: SIN ÍNDICE
        st.dataframe(df_act, use_container_width=True, hide_index=True)
