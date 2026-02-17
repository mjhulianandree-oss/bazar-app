import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Bazar Familiar Llallagua", layout="wide")

# Inicializar los datos en la sesión (Simulando una base de datos)
if 'inventario' not in st.session_state:
    data = {
        'Producto': ['Arroz', 'Azúcar', 'Aceite', 'Fideo'],
        'Precio (Bs)': [5.50, 6.00, 12.00, 4.50],
        'Stock': [50, 40, 20, 30]
    }
    st.session_state.inventario = pd.DataFrame(data)

if 'ventas' not in st.session_state:
    st.session_state.ventas = pd.DataFrame(columns=['Producto', 'Cantidad', 'Total (Bs)'])

st.title("🏪 Sistema de Inventario - Bazar")

# --- SECCIÓN 1: REGISTRAR VENTA ---
st.header("🛒 Registrar Venta")
col1, col2 = st.columns(2)

with col1:
    # Ahora elegimos por Nombre de Producto
    producto_seleccionado = st.selectbox(
        "Seleccione el Producto", 
        st.session_state.inventario['Producto'].tolist()
    )
    
with col2:
    cantidad = st.number_input("Cantidad", min_value=1, step=1)

if st.button("Registrar Venta"):
    # Obtener info del producto seleccionado
    idx = st.session_state.inventario[st.session_state.inventario['Producto'] == producto_seleccionado].index[0]
    precio = st.session_state.inventario.at[idx, 'Precio (Bs)']
    stock_actual = st.session_state.inventario.at[idx, 'Stock']

    if stock_actual >= cantidad:
        total = precio * cantidad
        # Restar del inventario
        st.session_state.inventario.at[idx, 'Stock'] = stock_actual - cantidad
        # Guardar venta
        nueva_venta = pd.DataFrame({'Producto': [producto_seleccionado], 'Cantidad': [cantidad], 'Total (Bs)': [total]})
        st.session_state.ventas = pd.concat([st.session_state.ventas, nueva_venta], ignore_index=True)
        st.success(f"✅ Venta registrada: {producto_seleccionado} x{cantidad} - Total: {total} Bs")
    else:
        st.error("❌ Stock insuficiente")

# --- SECCIÓN 2: MOSTRAR TABLAS ---
st.divider()
c1, c2 = st.columns(2)

with c1:
    st.subheader("📦 Inventario Actual")
    st.table(st.session_state.inventario)

with c2:
    st.subheader("📈 Ventas del Día")
    st.table(st.session_state.ventas)
