import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Função para carregar um arquivo CSV com múltiplas codificações
def carregar_csv(arquivo):
    codificacoes = ["utf-8", "iso-8859-1", "windows-1252", "latin1", "cp1252"]
    for codificacao in codificacoes:
        try:
            df = pd.read_csv(arquivo, encoding=codificacao, on_bad_lines='skip')
            return df
        except Exception as e:
            continue
    raise ValueError(f"Não foi possível decodificar o arquivo {arquivo} com as codificações testadas.")

# Função para corrigir nomes de colunas com caracteres corrompidos
def corrigir_nomes_colunas(df):
    codificacoes = ["utf-8", "iso-8859-1", "windows-1252", "latin1", "cp1252"]
    for codificacao in codificacoes:
        try:
            return df.rename(columns=lambda x: x.encode(codificacao).decode("utf-8") if isinstance(x, str) else x)
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    st.write("Erro: Não foi possível corrigir os nomes das colunas com as codificações testadas.")
    return df


# Função para carregar os dados
@st.cache_data
def load_data():
    arquivos = ["grupo.csv", "subgrupo.csv", "forma_organizacao.csv", "procedimento.csv"]
    dados = []
    for arquivo in arquivos:
        try:
            df = carregar_csv(arquivo)
            df = corrigir_nomes_colunas(df)
            if df.empty:
                st.warning(f"O arquivo {arquivo} está vazio.")
            else:
                dados.append(df)
        except Exception as e:
            st.error(f"Erro ao carregar o arquivo {arquivo}: {e}")
            return None
    return dados

# Função para transformar os dados no formato longo
def transformar_dados_longos(df):
    anos = [col for col in df.columns if col.isdigit()]
    df_long = df.melt(id_vars=["Procedimento"], value_vars=anos, var_name="Ano", value_name="Quantidade")
    return df_long

# Carregar os dados
with st.spinner("Carregando dados..."):
    dados = load_data()

if dados:
    st.success("Dados carregados com sucesso!")
    grupo, subgrupo, forma_organizacao, procedimento = dados

    # Verificar colunas esperadas
    colunas_esperadas = {
        "grupo.csv": ["Grupo procedimento"],
        "subgrupo.csv": ["Subgrupo proced."],
        "forma_organizacao.csv": ["Forma organização"],
        "procedimento.csv": ["Procedimento"]
    }

    for arquivo, colunas in colunas_esperadas.items():
        df = next((df for df in dados if arquivo in df.columns), None)
        if df is not None:
            for coluna in colunas:
                if coluna not in df.columns:
                    st.error(f"A coluna '{coluna}' não foi encontrada no arquivo '{arquivo}'. Verifique o arquivo.")

    # Título da aplicação
    st.title("Explorador de Procedimentos do Hospital de Ribeirão - PE")

    # Selecionar Grupo
    grupo_selecionado = st.selectbox("Selecione o Grupo", grupo["Grupo procedimento"])

    # Filtrar Subgrupos
    if "Subgrupo proced." in subgrupo.columns:
        codigo_grupo = grupo_selecionado.split()[0]
        subgrupos_filtrados = subgrupo[subgrupo["Subgrupo proced."].str.startswith(codigo_grupo, na=False)]
        if not subgrupos_filtrados.empty:
            subgrupo_selecionado = st.selectbox("Selecione o Subgrupo", subgrupos_filtrados["Subgrupo proced."])
        else:
            st.warning("Nenhum subgrupo encontrado para o grupo selecionado.")
            subgrupo_selecionado = None
    else:
        st.error("A coluna 'Subgrupo proced.' não foi encontrada no arquivo 'subgrupo.csv'.")
        subgrupo_selecionado = None

    # Filtrar Formas de Organização
    forma_selecionada = None
    if subgrupo_selecionado is not None and "Forma organização" in forma_organizacao.columns:
        codigo_subgrupo = subgrupo_selecionado.split()[0]
        formas_filtradas = forma_organizacao[forma_organizacao["Forma organização"].str.startswith(codigo_subgrupo, na=False)]
        if not formas_filtradas.empty:
            forma_selecionada = st.selectbox("Selecione a Forma de Organização", formas_filtradas["Forma organização"])
        else:
            st.warning("Nenhuma forma de organização encontrada para o subgrupo selecionado.")
    else:
        st.error("A coluna 'Forma organização' não foi encontrada no arquivo 'forma_organizacao.csv'.")

    # Extrair o código da forma de organização selecionada
    if forma_selecionada is not None and isinstance(forma_selecionada, str):
        codigo_forma = forma_selecionada.split()[0]
    else:
        st.error("Erro ao processar a forma de organização selecionada.")
        codigo_forma = ""

    # Filtrar Procedimentos
    if codigo_forma and "Procedimento" in procedimento.columns:
        procedimentos_filtrados = procedimento[procedimento["Procedimento"].str.startswith(codigo_forma, na=False)]
        if not procedimentos_filtrados.empty:
            st.write("Procedimentos Relacionados:")
            st.dataframe(procedimentos_filtrados)

            # Transformar os dados de procedimentos para o formato longo
            procedimento_long = transformar_dados_longos(procedimentos_filtrados)

            # Criar gráfico de colunas com Plotly
            fig = px.bar(procedimento_long, x="Ano", y="Quantidade", color="Procedimento",
                         labels={'Ano': 'Ano', 'Quantidade': 'Quantidade'},
                         title='Distribuição dos Procedimentos por Ano')
            st.plotly_chart(fig)
        else:
            st.warning("Nenhum procedimento encontrado para a forma de organização selecionada.")
    else:
        st.error("Não foi possível filtrar os procedimentos. Verifique a forma de organização selecionada.")
else:
    st.error("Não foi possível carregar os dados. Verifique os arquivos CSV.")
