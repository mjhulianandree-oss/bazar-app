import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bazar Familiar - Control de Ventas", layout="wide")

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect("bazar_final.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
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
    conn = sqlite3.connect("bazar_final.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventario WHERE id = ?", (id_prod,))
    conn.commit()
    conn.close()

init_db()

# --- FUNCIONES DE AYUDA ---
def registrar_venta(id_prod, nombre_prod, p_venta, p_costo):
    conn = sqlite3.connect("bazar_final.db")
    cursor = conn.cursor()
    ganancia = p_venta - p_costo
    # Hora de Bolivia
    hora_actual = datetime.now() - timedelta(hours=4) 
    fecha_formateada = hora_actual.strftime("%d/%m %H:%M")
    
    cursor.execute("""
        INSERT INTO ventas (nombre_producto, cantidad, fecha, ganancia_vta, total_vta) 
        VALUES (?, ?, ?, ?, ?)
    """, (nombre_prod, 1, fecha_formateada, ganancia, p_venta))
    
    cursor.execute("UPDATE inventario SET ventas_acumuladas = ventas_acumuladas + 1 WHERE id = ?", (id_prod,))
    conn.commit()
    conn.close()

# --- INTERFAZ SIDEBAR ---
with st.sidebar:
    st.header("📦 Nuevo Producto")
    nuevo_nombre = st.text_input("Nombre del Producto")
    n_stock = st.number_input("Stock Inicial", min_value=1, value=50)
    n_costo = st.number_input("Precio Costo (Bs)", min_value=0.1, value=1.0)
    n_venta = st.number_input("Precio Venta (Bs)", min_value=0.1, value=1.5)
    
    if st.button("Guardar en Inventario"):
        if nuevo_nombre:
            conn = sqlite3.connect("bazar_final.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventario (producto, stock_inicial, precio_costo, precio_venta, ventas_acumuladas) 
                VALUES (?,?,?,?,0)
            """, (nuevo_nombre, n_stock, n_costo, n_venta))
            conn.commit()
            conn.close()
            st.success(f"¡{nuevo_nombre} añadido!")
            st.rerun()

# --- OBTENCIÓN DE DATOS ---
conn = sqlite3.connect("bazar_final.db")
df_inv = pd.read_sql_query("SELECT * FROM inventario", conn)
df_vts = pd.read_sql_query("SELECT nombre_producto, cantidad, fecha, ganancia_vta, total_vta FROM ventas", conn)
conn.close()

# --- CUERPO PRINCIPAL ---
st.title("🛒 Control del Bazar")

col1, col2 = st.columns([2, 1.2])

with col1:
    st.subheader("📦 Stock y Ventas")
    if df_inv.empty:
        st.info("Agrega productos para comenzar.")
    else:
        for index, row in df_inv.iterrows():
            stock_actual = row['stock_inicial'] - row['ventas_acumuladas']
            
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            
            if stock_actual <= 0:
                c1.markdown(f"🔴 ~~{row['producto']}~~")
                c2.write("⚠️ Agotado")
                # El botón de borrar SOLO aparece aquí cuando el stock es 0 o menor
                if c4.button("🗑️", key=f"del_{row['id']}", help="Eliminar producto agotado"):
                    borrar_producto(row['id'])
                    st.rerun()
            else:
                c1.write(f"**{row['producto']}**")
                c2.write(f"Disp: {int(stock_actual)}")
                if c3.button(f"Vender {row['precio_venta']} Bs", key=f"vta_{row['id']}"):
                    registrar_venta(row['id'], row['producto'], row['precio_venta'], row['precio_costo'])
                    st.rerun()
                # Aquí NO ponemos el botón de borrar (c4 queda vacío) para proteger el stock activo

with col2:
    st.subheader("💰 Resumen")
    ganancia_total = df_vts['ganancia_vta'].sum()
    st.metric("Ganancia Total", f"{ganancia_total:.2f} Bs")
    
    with st.expander("📝 Historial (Numerado desde 1)", expanded=True):
        if not df_vts.empty:
            df_mostrar = df_vts[['fecha', 'nombre_producto', 'total_vta', 'ganancia_vta']].copy()
            df_mostrar.index = range(1, len(df_mostrar) + 1)
            st.table(df_mostrar.rename(
                columns={'nombre_producto': 'Producto', 'total_vta': 'Venta', 'ganancia_vta': 'Ganancia'}
            ))
        else:
            st.write("No hay ventas registradas.")
