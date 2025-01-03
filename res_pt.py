import pandas as pd
import json
import logging

# Configuração básica do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('filtrar_portarias.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def ler_dados_json(caminho):
    """Lê dados de um arquivo JSON com codificação UTF-8 e retorna uma lista de dicionários."""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Erro: Arquivo não encontrado em '{caminho}'")
        return None
    except json.JSONDecodeError:
        logger.error(f"Erro: Formato JSON inválido em '{caminho}'")
        return None

def criar_dataframe_mac_incentivos(data_mac):
    """Cria um DataFrame para o Teto MAC e Incentivos a partir dos dados lidos."""
    df_mac_incentivos = pd.DataFrame()
    for item in data_mac:
        for key, values in item.items():
            temp_df = pd.DataFrame.from_dict(values, orient='index').reset_index()
            temp_df.columns = ['Ano', 'Valor']
            temp_df['Categoria'] = key
            df_mac_incentivos = pd.concat([df_mac_incentivos, temp_df], ignore_index=True)

    df_mac_incentivos['Ano'] = pd.to_numeric(df_mac_incentivos['Ano'])
    df_mac_incentivos['Valor'] = pd.to_numeric(df_mac_incentivos['Valor'].astype(str).str.replace('.', '').str.replace(',', '.'))
    return df_mac_incentivos

def preprocessar_dados_mac(data_mac):
    """Preprocessa dados do Teto MAC e Incentivos."""
    df_mac_incentivos = criar_dataframe_mac_incentivos(data_mac)
    df_mac = df_mac_incentivos[df_mac_incentivos['Categoria'] == 'Teto Financeiro MAC'].copy()
    df_incentivos = df_mac_incentivos[df_mac_incentivos['Categoria'] == 'Incentivos'].copy()
    df_mac['Mês'] = 1
    df_incentivos['Mês'] = 1
    return df_mac, df_incentivos

def calcular_variacoes_anuais(df, col_valor='Valor'):
    """Calcula variações percentuais anuais."""
    df['Var_Perc'] = df[col_valor].pct_change() * 100
    return df

def obter_maiores_variacoes(df, top_n=3):
    """Obtém os anos com as maiores variações (positivas e negativas)."""
    df_sorted = df.reindex(df.Var_Perc.abs().sort_values(ascending=False).index)
    anos_maiores_variacoes = df_sorted['Ano'].drop_duplicates().head(top_n).tolist()
    return anos_maiores_variacoes

def preprocessar_dados_portarias(caminho_portarias):
    """Lê e preprocessa os dados das portarias."""
    df_portarias = pd.read_json(caminho_portarias)
    df_portarias['Valor'] = pd.to_numeric(df_portarias['Valor'].astype(str).str.replace('.', '').str.replace(',', '.'))
    df_portarias['Data'] = pd.to_datetime(df_portarias['Data'], format='%d/%m/%Y')
    df_portarias['Ano'] = df_portarias['Data'].dt.year
    df_portarias['Competência_Num'] = df_portarias['Competência'].str.extract('(\d+)')[0].astype(int)
    return df_portarias

def filtrar_portarias_por_ano_e_valor(df_portarias, anos_variacoes, max_portarias_por_ano=10):
    """Filtra as portarias com base nos anos relevantes e no valor da portaria."""
    df_filtrado = pd.DataFrame()
    for ano in anos_variacoes:
        df_ano = df_portarias[df_portarias['Ano'] == ano]
        df_filtrado = pd.concat([df_filtrado, df_ano.nlargest(max_portarias_por_ano, 'Valor')])
    return df_filtrado

def filtrar_portarias_por_variacoes(caminho_mac, caminho_portarias, top_n=3, max_portarias_por_ano=10, output_json='output.json'):
    """
    Filtra as portarias com base nas maiores variações do Teto Financeiro MAC e dos Incentivos,
    limitando o número de portarias por ano.

    Args:
        caminho_mac: Caminho para o arquivo JSON com os dados do Teto MAC e Incentivos.
        caminho_portarias: Caminho para o arquivo JSON com os dados das portarias.
        top_n: Número de maiores variações a serem consideradas.
        max_portarias_por_ano: Número máximo de portarias por ano a serem incluídas no JSON de saída.
        output_json: Caminho para o arquivo JSON de saída.

    Returns:
        None
    """

    # Ler e preprocessar os dados do Teto MAC e Incentivos
    data_mac = ler_dados_json(caminho_mac)
    if data_mac is None:
        return
    df_mac, df_incentivos = preprocessar_dados_mac(data_mac)

    # Ler e preprocessar os dados das portarias
    df_portarias = preprocessar_dados_portarias(caminho_portarias)

    # Definir o intervalo de anos com base nos dados das portarias
    ano_inicial_portarias = df_portarias['Ano'].min()
    ano_final_portarias = df_portarias['Ano'].max()

    logger.info(f"Analisando dados para o período de {ano_inicial_portarias} a {ano_final_portarias}")

    # Filtrar os DataFrames do Teto MAC e Incentivos para o intervalo de anos das portarias
    df_mac = df_mac[(df_mac['Ano'] >= ano_inicial_portarias) & (df_mac['Ano'] <= ano_final_portarias)]
    df_incentivos = df_incentivos[(df_incentivos['Ano'] >= ano_inicial_portarias) & (df_incentivos['Ano'] <= ano_final_portarias)]

    # Calcular variações anuais
    df_mac = calcular_variacoes_anuais(df_mac)
    df_incentivos = calcular_variacoes_anuais(df_incentivos)

    # Combinar as variações em um único DataFrame
    df_variacoes = pd.concat([
        df_mac[['Ano', 'Var_Perc']],
        df_incentivos[['Ano', 'Var_Perc']]
    ])

    # Remover NaNs
    df_variacoes.dropna(subset=['Var_Perc'], inplace=True)

    logger.debug("DataFrame de Variações (df_variacoes):\n%s", df_variacoes)

    # Obter os anos com as maiores variações (positivas e negativas)
    anos_variacoes = obter_maiores_variacoes(df_variacoes, top_n=top_n)

    logger.info("Anos com Maiores Variações (Positivas e Negativas): %s", anos_variacoes)

    # Filtrar portarias por ano e valor
    df_portarias_filtrado = filtrar_portarias_por_ano_e_valor(df_portarias, anos_variacoes, max_portarias_por_ano)

    # Converter o DataFrame filtrado em JSON
    json_filtrado = df_portarias_filtrado.to_dict(orient='records')

    # Salvar o JSON em um arquivo com indentação para melhor legibilidade
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(json_filtrado, f, ensure_ascii=False, indent=4, default=str)

    logger.info(f"JSON salvo em {output_json}")

# Exemplo de Uso
caminho_mac = 'evolucao_mac.json'
caminho_portarias = 'tabela_analise.json'
output_json = 'pt_mac_res.json'

filtrar_portarias_por_variacoes(caminho_mac, caminho_portarias, top_n=10, max_portarias_por_ano=2, output_json=output_json)