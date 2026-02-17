import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bazar Familiar - Control de Ventas", layout="wide")

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect("bazar_datos.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            stock_inicial INTEGER,
            precio_costo REAL,
            precio_venta REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            cantidad INTEGER,
            fecha TEXT,
            ganancia_vta REAL
        )
    """)
    conn.commit()
    conn.close()

# Función para borrar solo un producto del inventario
def borrar_producto(id_prod):
    conn = sqlite3.connect("bazar_datos.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventario WHERE id = ?", (id_prod,))
    conn.commit()
    conn.close()

init_db()

# --- FUNCIONES DE AYUDA ---
def registrar_venta(id_prod, p_venta, p_costo):
    conn = sqlite3.connect("bazar_datos.db")
    cursor = conn.cursor()
    ganancia = p_venta - p_costo
    # Ajuste de hora para Bolivia (UTC-4)
    hora_actual = datetime.now() - timedelta(hours=4) 
    fecha_formateada = hora_actual.strftime("%Y-%m-%d %H:%M")
    
    cursor.execute("INSERT INTO ventas (producto_id, cantidad, fecha, ganancia_vta) VALUES (?, ?, ?, ?)",
                   (id_prod, 1, fecha_formateada, ganancia))
    conn.commit()
    conn.close()

# --- INTERFAZ SIDEBAR ---
with st.sidebar:
    st.header("📦 Gestión de Inventario")
    nuevo_nombre = st.text_input("Nombre del Producto")
    n_stock = st.number_input("Stock Inicial", min_value=1, value=50)
    n_costo = st.number_input("Precio Costo (Bs)", min_value=0.1, value=1.0)
    n_venta = st.number_input("Precio Venta (Bs)", min_value=0.1, value=1.5)
    
    if st.button("Guardar Producto"):
        if nuevo_nombre:
            conn = sqlite3.connect("bazar_datos.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO inventario (producto, stock_inicial, precio_costo, precio_venta) VALUES (?,?,?,?)",
                           (nuevo_nombre, n_stock, n_costo, n_venta))
            conn.commit()
            conn.close()
            st.success(f"¡{nuevo_nombre} añadido!")
            st.rerun()

# --- OBTENCIÓN DE DATOS ---
conn = sqlite3.connect("bazar_datos.db")
df_inv = pd.read_sql_query("SELECT * FROM inventario", conn)
# Traemos las ventas unidas con el nombre del producto para el historial
query_ventas = """
    SELECT v.id, i.producto, v.cantidad, v.fecha, v.ganancia_vta 
    FROM ventas v 
    LEFT JOIN inventario i ON v.producto_id = i.id
"""
df_vts = pd.read_sql_query(query_ventas, conn)
conn.close()

# --- CUERPO PRINCIPAL ---
st.title("🛒 Control del Bazar")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📦 Inventario y Ventas Rápidas")
    if df_inv.empty:
        st.info("El inventario está vacío. Agrega productos en la barra lateral.")
    else:
        for index, row in df_inv.iterrows():
            # Calcular stock actual filtrando por el ID del producto
            # Nota: usamos el nombre guardado en la tabla de ventas para evitar errores si el ID cambia
            v_hechas = df_vts[df_vts['producto'] == row['producto']]['cantidad'].sum()
            stock_actual = row['stock_inicial'] - v_hechas
            
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            
            if stock_actual <= 0:
                c1.markdown(f"🔴 ~~{row['producto']}~~")
                c2.write("⚠️ Sin Stock")
                # Botón para borrar el producto del inventario si ya no hay stock
                if c4.button("🗑️", key=f"del_{row['id']}", help="Eliminar del inventario"):
                    borrar_producto(row['id'])
                    st.rerun()
            else:
                c1.write(f"**{row['producto']}**")
                c2.write(f"Stock: {int(stock_actual)}")
                c3.write(f"{row['precio_venta']} Bs")
                if c3.button(f"Vender 1", key=f"vta_{row['id']}"):
                    registrar_venta(row['id'], row['precio_venta'], row['precio_costo'])
                    st.rerun()
                # También permitimos borrar aunque tenga stock por si hubo error al crearlo
                if c4.button("🗑️", key=f"del_{row['id']}", help="Eliminar producto"):
                    borrar_producto(row['id'])
                    st.rerun()

with col2:
    st.subheader("💰 Resumen Financiero")
    ganancia_total = df_vts['ganancia_vta'].sum()
    st.metric("Ganancia Total", f"{ganancia_total:.2f} Bs")
    st.write(f"Ventas totales: {len(df_vts)}")

    if st.checkbox("Ver historial detallado"):
        # Mostramos el historial. Si borraste el producto del inventario, 
        # el nombre seguirá apareciendo gracias al LEFT JOIN y la lógica previa.
        st.dataframe(df_vts, use_container_width=True)
