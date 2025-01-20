import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from pyUFbr.baseuf import ufbr

# Configurações da página
st.set_page_config(page_title="Sistema de Financiamento de Saúde", layout="wide")

# Funções auxiliares
def formatar_moeda(valor):
    """Formata valores monetários com símbolo R$ e separadores"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor else "R$ 0,00"

def obter_codigo_ibge(municipio, uf):
    """Obtém o código IBGE do município"""
    try:
        return ufbr.get_cidade(municipio).codigo[:6]
    except Exception as e:
        st.error(f"Erro ao obter código IBGE: {e}")
        return None

def consultar_api(codigo_ibge, competencia_inicial, competencia_final):
    """Consulta a API de financiamento"""
    url = "https://relatorioaps-prd.saude.gov.br/financiamento/pagamento"
    params = {
        "unidadeGeografica": "MUNICIPIO",
        "coUf": "26",
        "coMunicipio": codigo_ibge,
        "nuParcelaInicio": competencia_inicial,
        "nuParcelaFim": competencia_final,
        "tipoRelatorio": "COMPLETO"
    }
    
    try:
        response = requests.get(url, params=params, headers={"Accept": "application/json"})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Erro na consulta à API: {e}")
        return None

def criar_grafico_barras(df):
    """Cria gráfico de barras vertical com os valores de repasse"""
    fig = px.bar(
        df,
        x='dsPlanoOrcamentario',
        y='vlEfetivoRepasse',
        text='vlEfetivoRepasse',
        labels={'dsPlanoOrcamentario': 'Programa', 'vlEfetivoRepasse': 'Valor Repassado'},
        color='dsPlanoOrcamentario',
        height=500
    )
    fig.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Valor Repassado (R$)",
        hovermode="x unified"
    )
    fig.update_traces(
        texttemplate='%{text:,.2f}',
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>%{y:,.2f}'
    )
    return fig

def exibir_metricas_chave(pagamentos):
    """Exibe os principais indicadores em formato de métricas"""
    if not pagamentos:
        return
    
    dados = pagamentos[0]
    cols = st.columns(4)
    
    with cols[0]:
        st.metric("População Total", f"{dados.get('qtPopulacao', 0):,}".replace(",", "."))
    
    with cols[1]:
        st.metric("ACS Ativos", dados.get('qtAcsDiretoPgto', 0))
    
    with cols[2]:
        st.metric("Equipes de Saúde", dados.get('qtEsfTotalPgto', 0))
    
    with cols[3]:
        total = sum(item['vlEfetivoRepasse'] for item in st.session_state.dados['resumosPlanosOrcamentarios'])
        st.metric("Investimento Total", formatar_moeda(total))

# Barra lateral para entrada de parâmetros
with st.sidebar:
    st.header("Parâmetros da Consulta")
    
    uf = st.selectbox("UF:", ufbr.list_uf)
    municipio = st.selectbox("Município:", ufbr.list_cidades(uf))
    competencia_inicial = st.text_input("Competência Inicial (AAAAMM):", "202401")
    competencia_final = st.text_input("Competência Final (AAAAMM):", "202412")
    
    if st.button("Consultar", type="primary"):
        # Validação das competências
        if len(competencia_inicial) != 6 or len(competencia_final) != 6:
            st.error("Formato de competência inválido! Use o formato AAAAMM")
        else:
            with st.spinner("Consultando base de dados..."):
                codigo_ibge = obter_codigo_ibge(municipio, uf)
                if codigo_ibge:
                    dados = consultar_api(codigo_ibge, competencia_inicial, competencia_final)
                    if dados:
                        st.session_state.dados = dados
                        st.success("Dados carregados com sucesso!")
                    else:
                        st.error("Nenhum dado encontrado para os parâmetros selecionados")

# Conteúdo principal
st.title("🏥 Análise de Financiamento Municipal")

if 'dados' in st.session_state:
    dados = st.session_state.dados
    resumos = dados['resumosPlanosOrcamentarios']
    pagamentos = dados['pagamentos']
    
    # Cabeçalho informativo
    st.subheader(f"{dados['resumosPlanosOrcamentarios'][0]['noMunicipio']} - {uf}")
    st.caption(f"Última atualização: {dados['data']} | Competência: {competencia_inicial} a {competencia_final}")
    
    # Seção de métricas
    st.markdown("---")
    exibir_metricas_chave(pagamentos)
    
    # Seção de visualização de dados
    st.markdown("---")
    st.header("Distribuição dos Recursos por Programa")
    
    # Processamento dos dados
    df = pd.DataFrame(resumos).sort_values('vlEfetivoRepasse', ascending=False)
    df_filtrado = df[df['vlEfetivoRepasse'] > 0]
    
    # Layout principal
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Gráfico de barras
        fig = criar_grafico_barras(df_filtrado)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Gráfico de pizza
        st.subheader("Proporção por Programa")
        fig_pie = px.pie(
            df_filtrado,
            names='dsPlanoOrcamentario',
            values='vlEfetivoRepasse',
            hole=0.4,
            labels={'vlEfetivoRepasse': 'Valor Repassado'}
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Tabela detalhada
    st.markdown("---")
    st.header("Detalhamento dos Repasses")
    
    df_tabela = df_filtrado[['dsPlanoOrcamentario', 'vlEfetivoRepasse']].rename(columns={
        'dsPlanoOrcamentario': 'Programa',
        'vlEfetivoRepasse': 'Valor Repassado'
    })
    
    st.dataframe(
        df_tabela.style.format({'Valor Repassado': lambda x: formatar_moeda(x)}),
        height=400,
        use_container_width=True
    )
    
    # Seção técnica
    with st.expander("Detalhes Técnicos"):
        st.json(dados, expanded=False)

else:
    st.info("ℹ️ Selecione os parâmetros na barra lateral e clique em 'Consultar' para iniciar a análise")