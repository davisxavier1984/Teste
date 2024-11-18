import streamlit as st
import matplotlib.pyplot as plt

# Função para atualizar o gráfico de pizza
def update_pie(total_value, val):
    val = int(val)
    sizes[2] = val
    sizes[0] = (100 - val) / 2
    sizes[1] = sizes[0]

    # Atualiza os valores em R$
    real_sizes[2] = total_value * (sizes[2] / 100)
    real_sizes[0] = total_value * (sizes[0] / 100)
    real_sizes[1] = real_sizes[0]

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=[f'Fatia 1: R$ {real_sizes[0]:.2f}', f'Fatia 2: R$ {real_sizes[1]:.2f}', f'Fatia 3: R$ {real_sizes[2]:.2f}'], autopct='%1.1f%%')
    return fig

# Solicitação de valor em reais
total_value = st.number_input("Insira o valor total em R$:", min_value=0.0, format="%.2f")

# Valores iniciais das fatias
sizes = [33.5, 33.5, 33]
real_sizes = [total_value * (size / 100) for size in sizes]

# Controle deslizante para ajustar a terceira fatia
slider_value = st.slider("Ajuste a terceira fatia (%):", min_value=0, max_value=100, value=50, step=1)

# Atualiza o gráfico de pizza
fig = update_pie(total_value, slider_value)
st.pyplot(fig)
