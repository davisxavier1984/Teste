import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
from babel.numbers import format_currency

# Função para estilizar métricas com IDs únicos
def style_metric_card(
    element_id: str,
    background_color: str = "#FFF",
    border_size_px: int = 1,
    border_color: str = "#CCC",
    border_radius_px: int = 5,
    border_left_color: str = "red",
    box_shadow: bool = True,
) -> None:
    """
    Aplica um estilo customizado a um st.metric com ID único.

    Args:
        element_id (str): ID único para o elemento estilizado.
        background_color (str, optional): Cor de fundo. Defaults to "#FFF".
        border_size_px (int, optional): Tamanho da borda em pixels. Defaults to 1.
        border_color (str, optional): Cor da borda. Defaults to "#CCC".
        border_radius_px (int, optional): Raio da borda em pixels. Defaults to 5.
        border_left_color (str, optional): Cor da borda esquerda. Defaults to "red".
        box_shadow (bool, optional): Sombra ao redor da caixa. Defaults to True.
    """
    box_shadow_str = (
        "box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.15) !important;"
        if box_shadow
        else "box-shadow: none !important;"
    )
    st.markdown(
        f"""
        <style>
            #{element_id} {{
                background-color: {background_color};
                border: {border_size_px}px solid {border_color};
                padding: 15px;
                border-radius: {border_radius_px}px;
                border-left: 0.5rem solid {border_left_color} !important;
                {box_shadow_str}
            }}
            #{element_id} .metric-label {{
                font-weight: bold;
                font-size: 1rem;
            }}
            #{element_id} .metric-value {{
                font-size: 1.2rem;
                font-weight: bold;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# Dados simulados
dados = {
    'Ano': list(range(2010, 2025)),
    'Teto Total (R$)': [
        1995962.74, 3422104.76, 3717137.9, 3609136.8, 3500116.8,
        3520116.68, 3666022.02, 3620148.55, 5725025.51, 6090350.64,
        6163326.42, 6473076.42, 7037782.17, 6844944.34, 6844944.34
    ],
    'Sem Incentivos (R$)': [
        1995962.74, 3422104.76, 3377477.9, 3269476.8, 3160456.8,
        3160456.68, 3206362.02, 3160488.55, 3165365.51, 3530690.64,
        3603666.42, 3603666.42, 3654957.17, 3757538.67, 3757538.67
    ],
    'Incentivos (R$)': [
        0, 0, 339660, 339660, 339660,
        359660, 459660, 459660, 2559660, 2559660,
        2559660, 2869410, 3382825, 3087405.67, 3087405.67
    ]
}

df = pd.DataFrame(dados)

# Calcular valores e formatar
recurso_atual_anual = format_currency(dados['Teto Total (R$)'][-1], 'BRL', locale='pt_BR')
potencial_aumento_anual = format_currency(1026741.65, 'BRL', locale='pt_BR')
soma_total = format_currency(dados['Teto Total (R$)'][-1] + 1026741.65, 'BRL', locale='pt_BR')

# Função para converter imagem em base64
def img_to_base64(file_path):
    with open(file_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# Caminhos das imagens
logo_maisgestor = 'logo_maisgestor.png'
logo = 'logo.png'

# Converter imagens para base64
logo_maisgestor_base64 = img_to_base64(logo_maisgestor)
logo_base64 = img_to_base64(logo)

# Criar o conteúdo HTML com flexbox para ser responsivo
html_content = f"""
<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 0px;">
    <div style="flex: 1; display: flex; justify-content: flex-start; padding: 0px;">
        <img src='data:image/png;base64,{logo_maisgestor_base64}' style='height: 200px; max-width: 200%;'>
    </div>
    <div style="flex: 1; display: flex; justify-content: flex-end; padding: 0px;">
        <img src='data:image/png;base64,{logo_base64}' style='height: 100px; max-width: 100%;'>
    </div>
</div>
"""

# Renderizar o conteúdo HTML
st.markdown(html_content, unsafe_allow_html=True)

# Placas de identificação do recurso atual e potenciais aumentos no início da página
st.subheader("Recurso Atual e Potencial de Aumento (MAC)")

col1, col2, col3 = st.columns(3)

# Card 1: Recurso Atual Anual
with col1:
    metric_id = "metric-red"
    st.markdown(
        f"""
        <div id="{metric_id}">
            <div class="metric-label">Teto MAC Atual</div>
            <div class="metric-value">{recurso_atual_anual}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    style_metric_card(element_id=metric_id, border_left_color="red")

# Card 2: Potencial de Aumento Anual
with col2:
    metric_id = "metric-yellow"
    st.markdown(
        f"""
        <div id="{metric_id}">
            <div class="metric-label">Potencial de Aumento</div>
            <div class="metric-value">{potencial_aumento_anual}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    style_metric_card(element_id=metric_id, border_left_color="yellow")

# Card 3: Soma dos Dois Anteriores
with col3:
    metric_id = "metric-green"
    st.markdown(
        f"""
        <div id="{metric_id}">
            <div class="metric-label">Novo Teto MAC</div>
            <div class="metric-value">{soma_total}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    style_metric_card(element_id=metric_id, border_left_color="green")

# Gráficos
fig1 = px.line(df, x='Ano', y=['Teto Total (R$)', 'Sem Incentivos (R$)', 'Incentivos (R$)'],
               title="Evolução do Teto MAC (2010-2023)")

# Destaque para redução de 2022 para 2023
fig1.add_trace(go.Scatter(x=[2022, 2023], y=[dados['Teto Total (R$)'][-3], dados['Teto Total (R$)'][-2]],
                          mode='lines+markers+text',
                          name='Redução',
                          line=dict(color='red', width=4),
                          text=["2022", "2023"],
                          textposition="top center"))

st.plotly_chart(fig1)

st.markdown("**Comparação de Recursos**")
fig2 = px.bar(df, x='Ano', y='Teto Total (R$)', title="Comparação de Recursos Anuais")


import plotly.graph_objects as go

# Adicionar a coluna de 2025
df.loc[len(df)] = [2025, 7871685.99, 0, 1026741.65]

# Atualizar o gráfico de barras com todas as colunas em azul
fig2 = go.Figure(data=[
    go.Bar(name='Teto Total (R$)', x=df['Ano'], y=df['Teto Total (R$)'], marker_color='green')
])

# Destaque para potencial de aumento entre 2024 e 2025
fig2.add_annotation(
    x=2024.5, y=(6844944.34 + 7871685.99) / 2,
    text='Potencial de Aumento',
    showarrow=True,
    arrowhead=2,
    arrowsize=1,
    arrowcolor='blue',
    ax=0,
    ay=-50,
    bgcolor='rgba(255, 255, 0, 0.5)',
    bordercolor='blue',
    borderwidth=2
)

# Adicionar anotação específica de aumento
fig2.add_trace(go.Scatter(
    x=[2024, 2025],
    y=[6844944.34, 7871685.99],
    mode='lines+markers+text',
    text=["2024", "2025"],
    textposition="top center",
    line=dict(color='blue', dash='dash'),
    showlegend=False
))

# Remover legenda e definir títulos dos eixos
fig2.update_layout(
    title="Comparação de Recursos Anuais",
    xaxis_title="Ano",
    yaxis_title="Teto Total (R$)",
    showlegend=False
)

st.plotly_chart(fig2)



# Informação contextual
st.markdown("""
### Contexto
O município de Euclides da Cunha - BA tem potencial para aumentar os recursos do MAC, 
principalmente através da captação de incentivos adicionais. Isso é crucial para 
expandir e melhorar os serviços de saúde oferecidos à população.
""")

# Fonte dos dados
st.markdown("Fonte: Sismac/MS")
