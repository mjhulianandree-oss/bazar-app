import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración inicial
st.set_page_config(page_title="Bazar Familia - Ventas y Ganancias", layout="wide")
st.title("🏪 Sistema de Ventas y Ganancias")

# 1. INICIALIZAR DATOS (Si no existen en la sesión)
if 'inventario' not in st.session_state:
    # Ejemplo con columnas de costo para calcular ganancia
    st.session_state.inventario = pd.DataFrame([
        {'Producto': 'Aceite', 'Stock': 20, 'Costo (Bs)': 10.0, 'Precio Venta (Bs)': 12.0},
        {'Producto': 'Arroz 1kg', 'Stock': 50, 'Costo (Bs)': 4.5, 'Precio Venta (Bs)': 6.0}
    ])

if 'ventas' not in st.session_state:
    st.session_state.ventas = pd.DataFrame(columns=['Fecha', 'Producto', 'Cantidad', 'Ganancia (Bs)', 'Total (Bs)'])

# --- SECCIÓN A: REGISTRAR VENTA ---
st.header("🛒 Registrar Nueva Venta")
with st.container():
    col1, col2 = st.columns(2)
    
    with col1:
        # CAMBIO CLAVE: Selección por NOMBRE en lugar de ID
        opciones_productos = st.session_state.inventario['Producto'].tolist()
        prod_seleccionado = st.selectbox("Seleccione el Producto", opciones_productos)
        
    with col2:
        cant_vender = st.number_input("Cantidad a vender", min_value=1, step=1)

    if st.button("Confirmar Venta"):
        # Buscar los datos del producto elegido
        idx = st.session_state.inventario[st.session_state.inventario['Producto'] == prod_seleccionado].index[0]
        fila = st.session_state.inventario.iloc[idx]
        
        if fila['Stock'] >= cant_vender:
            # Cálculos de dinero
            total_venta = cant_vender * fila['Precio Venta (Bs)']
            costo_total = cant_vender * fila['Costo (Bs)']
            ganancia = total_venta - costo_total
            fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")

            # 1. Restar del stock
            st.session_state.inventario.at[idx, 'Stock'] -= cant_vender
            
            # 2. Registrar la venta
            nueva_v = pd.DataFrame([{
                'Fecha': fecha_hoy,
                'Producto': prod_seleccionado,
                'Cantidad': cant_vender,
                'Ganancia (Bs)': ganancia,
                'Total (Bs)': total_venta
            }])
            st.session_state.ventas = pd.concat([st.session_state.ventas, nueva_v], ignore_index=True)
            
            st.success(f"✅ ¡Venta registrada! Ganancia: {ganancia} Bs")
        else:
            st.error("❌ No hay suficiente stock disponible.")

st.divider()

# --- SECCIÓN B: VISUALIZACIÓN ---
col_inv, col_ven = st.columns([1, 1.2])

with col_inv:
    st.subheader("📦 Stock Actual")
    st.dataframe(st.session_state.inventario, use_container_width=True)

with col_ven:
    st.subheader("📈 Historial de Ventas")
    st.dataframe(st.session_state.ventas, use_container_width=True)
    
    # Resumen total
    if not st.session_state.ventas.empty:
        total_ganado = st.session_state.ventas['Ganancia (Bs)'].sum()
        st.metric("Ganancia Total Acumulada", f"{total_ganado} Bs")
