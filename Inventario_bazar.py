import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bazar Pro - Gestión Total", layout="wide")

# --- 2. BLINDAJE VISUAL (Oculta "Administrar la aplicación", menús y pie de página) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stAppDeployButton {display:none;}
    [data-testid="stStatusWidget"] {display:none;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. BASE DE DATOS (Mantenemos la versión con secciones) ---
def init_db():
    conn = sqlite3.connect("bazar_secciones.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            categoria TEXT,
            stock_inicial INTEGER,
            precio_costo REAL,
            precio_venta REAL,
            ventas_acumuladas INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_producto TEXT, 
            cantidad INTEGER,
            fecha TEXT,
            ganancia_vta REAL,
            total_vta REAL
        )
    """)
    conn.commit()
    conn.close()

def borrar_producto(id_prod):
    conn = sqlite3.connect("bazar_secciones.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventario WHERE id = ?", (id_prod,))
    conn.commit()
    conn.close()

init_db()

# --- 4. FUNCIONES DE REGISTRO ---
def registrar_venta(id_prod, nombre_prod, p_venta, p_costo):
    conn = sqlite3.connect("bazar_secciones.db")
    cursor = conn.cursor()
    ganancia = p_venta - p_costo
    # Ajuste de hora Bolivia (UTC-4)
    hora_actual = datetime.now() - timedelta(hours=4) 
    fecha_formateada = hora_actual.strftime("%d/%m %H:%M")
    
    cursor.execute("""
        INSERT INTO ventas (nombre_producto, cantidad, fecha, ganancia_vta, total_vta) 
        VALUES (?, ?, ?, ?, ?)
    """, (nombre_prod, 1, fecha_formateada, ganancia, p_venta))
    
    cursor.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (id_prod,))
    conn.commit()
    conn.close()

# --- 5. INTERFAZ LATERAL (SIDEBAR) ---
with st.sidebar:
    st.header("📦 Nuevo Producto")
    nuevo_nombre = st.text_input("Nombre del Producto")
    
    # Categorías para facilitar la búsqueda
    categoria = st.selectbox("Sección", 
                            ["🍭 Dulces y Snacks", "🥤 Bebidas", "🥛 Lácteos", "📝 Útiles/Académico", "🏠 Otros"])
    
    n_stock = st.number_input("Stock Inicial", min_value=1, value=50)
    n_costo = st.number_input("Costo Unitario (Bs)", min_value=0.1, value=1.0)
    n_venta = st.number_input("Venta Unitario (Bs)", min_value=0.1, value=1.5)
    
    if st.button("Guardar en Inventario"):
        if nuevo_nombre:
            conn = sqlite3.connect("bazar_secciones.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventario (producto, categoria, stock_inicial, precio_costo, precio_venta, ventas_acumuladas) 
                VALUES (?,?,?,?,?,0)
            """, (nuevo_nombre, categoria, n_stock, n_costo, n_venta))
            conn.commit()
            conn.close()
            st.success(f"¡{nuevo_nombre} guardado!")
            st.rerun()

# --- 6. CARGA DE DATOS ---
conn = sqlite3.connect("bazar_secciones.db")
df_inv = pd.read_sql_query("SELECT * FROM inventario", conn)
df_vts = pd.read_sql_query("SELECT nombre_producto, cantidad, fecha, ganancia_vta, total_vta FROM ventas", conn)
conn.close()

# --- 7. CUERPO PRINCIPAL ---
st.title("🛒 Control del Bazar")

col1, col2 = st.columns([2, 1.3])

with col1:
    st.subheader("📦 Inventario por Sección")
    if df_inv.empty:
        st.info("El inventario está vacío.")
    else:
        # Pestañas inteligentes según las secciones creadas
        categorias_reales = df_inv['categoria'].unique().tolist()
        tabs = st.tabs(categorias_reales)
        
        for i, cat in enumerate(categorias_reales):
            with tabs[i]:
                df_cat = df_inv[df_inv['categoria'] == cat]
                for index, row in df_cat.iterrows():
                    stock_actual = row['stock_inicial'] - row['ventas_acumuladas']
                    
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    
                    if stock_actual <= 0:
                        c1.markdown(f"🔴 ~~{row['producto']}~~")
                        c2.write("⚠️ Agotado")
                        if c4.button("🗑️", key=f"del_{row['id']}"):
                            borrar_producto(row['id'])
                            st.rerun()
                    else:
                        c1.write(f"**{row['producto']}**")
                        c2.write(f"Disp: {int(stock_actual)}")
                        if c3.button(f"Venta: {row['precio_venta']} Bs", key=f"vta_{row['id']}"):
                            registrar_venta(row['id'], row['producto'], row['precio_venta'], row['precio_costo'])
                            st.rerun()

with col2:
    st.subheader("💰 Resumen de Ganancias")
    ganancia_total = df_vts['ganancia_vta'].sum()
    st.metric("Total Ganado", f"{ganancia_total:.2f} Bs")
    
    with st.expander("📝 Historial (Actualizado)", expanded=True):
        if not df_vts.empty:
            df_mostrar = df_vts[['fecha', 'nombre_producto', 'total_vta', 'ganancia_vta']].copy()
            # El contador siempre inicia en 1
            df_mostrar.index = range(1, len(df_mostrar) + 1)
            st.table(df_mostrar.rename(
                columns={'nombre_producto': 'Producto', 'total_vta': 'Venta', 'ganancia_vta': 'Ganancia'}
            ))
        else:
            st.write("Aún no hay ventas.")
