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

def borrar_todo():
    conn = sqlite3.connect("bazar_datos.db")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS inventario")
    cursor.execute("DROP TABLE IF EXISTS ventas")
    conn.commit()
    conn.close()
    init_db()

init_db()

# --- FUNCIONES DE AYUDA ---
def registrar_venta(id_prod, p_venta, p_costo):
    conn = sqlite3.connect("bazar_datos.db")
    cursor = conn.cursor()
    ganancia = p_venta - p_costo
    # CORRECCIÓN DE HORA: Ajustamos a la hora de Bolivia (UTC-4) 
    # Si en el servidor sale con 4 horas de más, restamos 4.
    hora_actual = datetime.now() - timedelta(hours=4) 
    fecha_formateada = hora_actual.strftime("%Y-%m-%d %H:%M")
    
    cursor.execute("INSERT INTO ventas (producto_id, cantidad, fecha, ganancia_vta) VALUES (?, ?, ?, ?)",
                   (id_prod, 1, fecha_formateada, ganancia))
    conn.commit()
    conn.close()

# --- INTERFAZ SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # BOTÓN DE REINICIO TOTAL
    st.subheader("⚠️ Zona de Peligro")
    if st.button("REINICIAR TODO (BORRAR TODO)"):
        borrar_todo()
        st.success("¡Todo ha sido borrado! Reiniciando...")
        st.rerun()

    st.divider()
    
    st.header("📦 Agregar Nuevo Producto")
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
            st.success("¡Producto añadido!")
            st.rerun()
        else:
            st.error("Escribe un nombre")

# --- OBTENCIÓN DE DATOS ---
conn = sqlite3.connect("bazar_datos.db")
df_inv = pd.read_sql_query("SELECT * FROM inventario", conn)
query_ventas = """
    SELECT v.id, i.producto, v.cantidad, v.fecha, v.ganancia_vta 
    FROM ventas v 
    JOIN inventario i ON v.producto_id = i.id
"""
df_vts = pd.read_sql_query(query_ventas, conn)
conn.close()

# --- CUERPO PRINCIPAL ---
st.title("🛒 Control del Bazar")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📦 Inventario y Ventas Rápidas")
    if df_inv.empty:
        st.info("No hay productos. Agrega uno en el menú de la izquierda.")
    else:
        for index, row in df_inv.iterrows():
            # Calcular stock actual
            v_hechas = df_vts[df_vts['producto'] == row['producto']]['cantidad'].sum()
            stock_actual = row['stock_inicial'] - v_hechas
            
            c1, c2, c3 = st.columns([3, 2, 2])
            
            # Color del stock
            if stock_actual <= 0:
                c1.write(f"❌ **{row['producto']}**")
                c2.write("SIN STOCK")
            else:
                c1.write(f"**{row['producto']}** (Stock: {stock_actual})")
                c2.write(f"{row['precio_venta']} Bs")
                if c3.button(f"Vender 1", key=row['id']):
                    registrar_venta(row['id'], row['precio_venta'], row['precio_costo'])
                    st.rerun()

with col2:
    st.subheader("💰 Resumen Financiero")
    ganancia_total = df_vts['ganancia_vta'].sum()
    st.metric("Ganancia Total acumulada", f"{ganancia_total:.2f} Bs")
    st.write(f"Total ventas realizadas: {len(df_vts)}")

    if st.checkbox("Ver historial de ventas"):
        st.dataframe(df_vts, use_container_width=True)
