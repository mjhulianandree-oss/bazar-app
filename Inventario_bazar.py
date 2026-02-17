import streamlit as st
import pandas as pd

# Título de la aplicación
st.title('Sistema de Inventario - Bazar Familia')

# Inicializar el inventario en la sesión si no existe
if 'inventario' not in st.session_state:
    st.session_state.inventario = pd.DataFrame(columns=['Producto', 'Cantidad', 'Precio'])

# Formulario para añadir productos
with st.form("nuevo_producto"):
    # CAMBIO AQUÍ: Antes era un ID (número), ahora es el Nombre (texto)
    nombre = st.text_input("Nombre del Producto")
    cantidad = st.number_input("Cantidad", min_value=0, step=1)
    precio = st.number_input("Precio unitario (Bs)", min_value=0.0, format="%.2f")
    
    submit_button = st.form_submit_button("Agregar al Inventario")

if submit_button:
    if nombre:
        nuevo_item = pd.DataFrame({'Producto': [nombre], 'Cantidad': [cantidad], 'Precio': [precio]})
        st.session_state.inventario = pd.concat([st.session_state.inventario, nuevo_item], ignore_index=True)
        st.success(f"¡{nombre} agregado con éxito!")
    else:
        st.warning("Por favor, escribe el nombre del producto.")

# Mostrar el inventario
st.subheader("Inventario Actual")
st.dataframe(st.session_state.inventario)
