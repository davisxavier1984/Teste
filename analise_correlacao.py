import json
import logging
import matplotlib.pyplot as plt
import os
import google.generativeai as genai
import time
from dotenv import load_dotenv
from google.api_core.exceptions import GoogleAPIError
import requests
import pandas as pd
import numpy as np

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analise_correlacao.log'),
        logging.StreamHandler()
    ]
)

# Configure a chave de API do Gemini usando a variável de ambiente
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_inflation_data(start_year, end_year):
    """
    Obtém dados de inflação (IPCA) do Banco Central do Brasil.

    Args:
        start_year: Ano inicial da série.
        end_year: Ano final da série.

    Returns:
        Um DataFrame do pandas com os dados de inflação acumulada anual.
        Retorna None em caso de erro.
    """
    try:
        url = f"http://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial=01/01/{start_year}&dataFinal=31/12/{end_year}"
        response = requests.get(url)
        response.raise_for_status()  # Lança exceção para erros HTTP
        data = response.json()
        df = pd.DataFrame(data)
        df['data'] = pd.to_datetime(df['data'], dayfirst=True)
        df['valor'] = pd.to_numeric(df['valor'])
        df.set_index('data', inplace=True)

        # Acumula a inflação anual
        df_annual = df.resample('YE').sum()
        df_annual['valor_acumulado'] = (1 + df_annual['valor'] / 100).cumprod()

        # Converte o índice para anos (strings)
        df_annual.index = df_annual.index.year.astype(str)

        return df_annual
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao obter dados de inflação: {e}")
        return None
    except (KeyError, ValueError) as e:
        logging.error(f"Erro ao processar dados de inflação: {e}")
        return None

def load_sia_data(file_path):
    logging.info(f"Carregando dados do SIA do arquivo: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        logging.error(f"Arquivo não encontrado: {file_path}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Erro ao decodificar JSON do arquivo: {file_path}")
        return None

    anos_disponiveis = set()
    media_complexidade = {}
    alta_complexidade = {}
    total_ambulatorial = {}

    # Verifica se a lista 'procedimentos' está presente e se não está vazia
    if not data or not isinstance(data, list):
        logging.warning(f"Dados do SIA ausentes ou em formato inválido no arquivo: {file_path}")
        return None

    for entrada in data:
        if not isinstance(entrada, dict):
            logging.warning("Entrada de dados do SIA em formato inválido. Ignorando.")
            continue

        complexidade = entrada.get("Complexidade", "")

        if not complexidade:
            logging.warning("Entrada de dados do SIA sem 'Complexidade' definida. Ignorando.")
            continue

        for chave in entrada:
            if chave.isdigit():
                ano = chave
                anos_disponiveis.add(ano)
                valor_str = entrada[chave]
                try:
                    valor = int(float(valor_str.replace('.', ''))) if valor_str != '-' else 0
                except ValueError:
                    logging.warning(f"Valor inválido encontrado para {chave} em {complexidade}: {valor_str}. Tratando como 0.")
                    valor = 0

                if complexidade == "Média complexidade":
                    media_complexidade[ano] = media_complexidade.get(ano, 0) + valor
                elif complexidade == "Alta complexidade":
                    alta_complexidade[ano] = alta_complexidade.get(ano, 0) + valor
                total_ambulatorial[ano] = total_ambulatorial.get(ano, 0) + valor

    logging.info(f"Dados do SIA carregados com sucesso. Anos disponíveis: {sorted(anos_disponiveis, key=int)}")
    return {
        'anos': sorted(anos_disponiveis, key=int),
        'media_complexidade': media_complexidade,
        'alta_complexidade': alta_complexidade,
        'total_ambulatorial': total_ambulatorial
    }

def load_sih_data(file_path):
    logging.info(f"Carregando dados do SIH do arquivo: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        logging.error(f"Arquivo não encontrado: {file_path}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Erro ao decodificar JSON do arquivo: {file_path}")
        return None

    grupos = {}

    # Verifica se a lista 'procedimentos' está presente e se não está vazia
    if not data or not isinstance(data, list):
        logging.warning(f"Dados do SIH ausentes ou em formato inválido no arquivo: {file_path}")
        return None

    for entrada in data:
        if not isinstance(entrada, dict):
            logging.warning("Entrada de dados do SIH em formato inválido. Ignorando.")
            continue

        grupo = entrada.get("Grupo procedimento", "Outros")
        if not grupo:
            logging.warning("Entrada de dados do SIH sem 'Grupo procedimento' definido. Ignorando.")
            continue

        if grupo not in grupos:
            grupos[grupo] = {}

        for chave in entrada:
            if chave.isdigit():
                ano = chave
                valor_str = entrada[chave]
                try:
                    valor = float(valor_str) if valor_str != '-' else 0.0
                except ValueError:
                    logging.warning(f"Valor inválido encontrado para {chave} em {grupo}: {valor_str}. Tratando como 0.")
                    valor = 0.0
                grupos[grupo][ano] = grupos[grupo].get(ano, 0) + valor

    logging.info(f"Dados do SIH carregados com sucesso. Grupos disponíveis: {list(grupos.keys())}")
    return grupos

def load_mac_data(file_path):
    logging.info(f"Carregando dados do MAC do arquivo: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        logging.error(f"Arquivo não encontrado: {file_path}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Erro ao decodificar JSON do arquivo: {file_path}")
        return None

    sem_incentivos = {}
    incentivos = {}
    teto_financeiro_mac = {}

    # Verifica se a lista 'evolução' está presente e se não está vazia
    if not data or not isinstance(data, list):
        logging.warning(f"Dados do MAC ausentes ou em formato inválido no arquivo: {file_path}")
        return None

    for entrada in data:
        if not isinstance(entrada, dict):
            logging.warning("Entrada de dados do MAC em formato inválido. Ignorando.")
            continue

        for chave, valores in entrada.items():
            if not chave:
                logging.warning("Entrada de dados do MAC sem chave definida. Ignorando.")
                continue

            for ano, valor_str in valores.items():
                try:
                    valor = float(valor_str) if valor_str != '-' else 0.0
                except ValueError:
                    logging.warning(f"Valor inválido encontrado para {ano} em {chave}: {valor_str}. Tratando como 0.")
                    valor = 0.0

                if chave == "Sem Incentivos":
                    sem_incentivos[ano] = valor
                elif chave == "Incentivos":
                    incentivos[ano] = valor
                elif chave == "Teto Financeiro MAC":
                    teto_financeiro_mac[ano] = valor

    # Repetir o último ano para cada chave, se necessário
    def repetir_ultimo_ano(dados, chave):
        if dados:
            ultimo_ano = max(dados.keys(), key=int)
            ultimo_valor = dados[ultimo_ano]
            proximo_ano = str(int(ultimo_ano) + 1)
            if proximo_ano not in dados:
                dados[proximo_ano] = ultimo_valor
                logging.info(f"Último ano repetido para {chave}: {ultimo_ano} -> {proximo_ano}")
        return dados

    sem_incentivos = repetir_ultimo_ano(sem_incentivos, "Sem Incentivos")
    incentivos = repetir_ultimo_ano(incentivos, "Incentivos")
    teto_financeiro_mac = repetir_ultimo_ano(teto_financeiro_mac, "Teto Financeiro MAC")

    logging.info(f"Dados do MAC carregados com sucesso.")
    return {
        'sem_incentivos': sem_incentivos,
        'incentivos': incentivos,
        'teto_financeiro_mac': teto_financeiro_mac
    }

def find_common_years(sia_data, sih_data, mac_data):
    anos_sia = set(sia_data['anos']) if sia_data else set()
    logging.info(f"Anos no SIA: {anos_sia}")

    anos_sih = set()
    if sih_data:
        for grupo in sih_data:
            anos_sih.update(sih_data[grupo].keys())
    logging.info(f"Anos no SIH: {anos_sih}")

    anos_mac = set()
    if mac_data:
        anos_mac = set(mac_data['sem_incentivos'].keys()).intersection(
            set(mac_data['incentivos'].keys()),
            set(mac_data['teto_financeiro_mac'].keys())
        )
    logging.info(f"Anos no MAC: {anos_mac}")

    # Verifica se há anos comuns, senão retorna uma lista vazia
    common_years = anos_sia.intersection(anos_sih, anos_mac)
    if not common_years:
        logging.warning("Não foram encontrados anos comuns entre os conjuntos de dados.")
        return []

    logging.info(f"Anos comuns: {common_years}")
    return sorted(common_years, key=int)

def pearson_correlation(x, y):
    if len(x) != len(y) or len(x) < 2:
        logging.warning("Não foi possível calcular a correlação: tamanhos diferentes ou dados insuficientes.")
        return None
    return x.corr(y)

def calculate_correlations(teto_total, sia_data, sih_data, common_years):
    correlations = {}

    # Converte teto_total para Series com índice explícito e tipo numérico
    teto_total_series = pd.Series(teto_total, index=common_years).astype(float)

    if sia_data:
        # Verifica se ambos os componentes (Média e Alta Complexidade) estão presentes
        media_presente = any(sia_data['media_complexidade'].get(str(ano), 0) != 0 for ano in common_years)
        alta_presente = any(sia_data['alta_complexidade'].get(str(ano), 0) != 0 for ano in common_years)

        # Calcula correlação para Média Complexidade
        if media_presente:
            data_list = [sia_data['media_complexidade'].get(str(ano), 0) for ano in common_years]
            data_series = pd.Series(data_list, index=common_years).astype(float)
            if data_series.nunique() > 1 and teto_total_series.nunique() > 1:
                correlations["Média Complexidade"] = pearson_correlation(teto_total_series, data_series)
            else:
                logging.warning(f"Dados constantes ou insuficientes para Média Complexidade. Correlação não será calculada.")
                correlations["Média Complexidade"] = None

        # Calcula correlação para Alta Complexidade
        if alta_presente:
            data_list = [sia_data['alta_complexidade'].get(str(ano), 0) for ano in common_years]
            data_series = pd.Series(data_list, index=common_years).astype(float)
            if data_series.nunique() > 1 and teto_total_series.nunique() > 1:
                correlations["Alta Complexidade"] = pearson_correlation(teto_total_series, data_series)
            else:
                logging.warning(f"Dados constantes ou insuficientes para Alta Complexidade. Correlação não será calculada.")
                correlations["Alta Complexidade"] = None

        # Calcula correlação para Total Ambulatorial apenas se ambos os componentes estiverem presentes
        if media_presente and alta_presente:
            data_list = [sia_data['total_ambulatorial'].get(str(ano), 0) for ano in common_years]
            data_series = pd.Series(data_list, index=common_years).astype(float)
            if data_series.nunique() > 1 and teto_total_series.nunique() > 1:
                correlations["Total Ambulatorial"] = pearson_correlation(teto_total_series, data_series)
            else:
                logging.warning(f"Dados constantes ou insuficientes para Total Ambulatorial. Correlação não será calculada.")
                correlations["Total Ambulatorial"] = None
        else:
            logging.warning(f"Total Ambulatorial não será calculado, pois apenas um dos componentes (Média ou Alta Complexidade) está presente.")
            correlations["Total Ambulatorial"] = None

    if sih_data:
        for grupo in sih_data:
            data_list = [sih_data[grupo].get(ano, 0) for ano in common_years]
            # Converte para Series com índice explícito e tipo numérico
            data_series = pd.Series(data_list, index=common_years).astype(float)

            # Verifica se os dados são nulos ou constantes
            if data_series.eq(0).all() or teto_total_series.eq(0).all():
                logging.warning(f"Dados nulos para {grupo} ou Teto MAC. Correlação não será calculada.")
                correlations[grupo] = None
            elif data_series.nunique() == 1 or teto_total_series.nunique() == 1:
                logging.warning(f"Dados constantes para {grupo} ou Teto MAC. Correlação não será calculada.")
                correlations[grupo] = None
            else:
                # Usa o método do pandas para calcular a correlação
                correlations[grupo] = pearson_correlation(teto_total_series, data_series)

    return correlations

def generate_correlation_graph(teto_total_real, data, variable, common_years, output_dir="graphs"):
    """
    Gera um gráfico de dispersão com linha de tendência usando matplotlib.

    Args:
        teto_total_real (list): Valores reais do Teto Financeiro MAC.
        data (dict): Dados da variável específica.
        variable (str): Nome da variável.
        common_years (list): Lista de anos comuns.
        output_dir (str): Diretório para salvar o gráfico.

    Returns:
        str: Caminho do arquivo do gráfico salvo.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Extrai os valores da variável para os anos comuns
    valores_variavel = [data.get(str(ano), 0) for ano in common_years]

    # Converte os dados para arrays numpy 1D
    teto_total_real = np.array(teto_total_real, dtype=float)
    valores_variavel = np.array(valores_variavel, dtype=float)

    # Verifica se os dados são válidos
    if len(teto_total_real) == 0 or len(valores_variavel) == 0:
        logging.warning(f"Dados insuficientes para gerar o gráfico de {variable}.")
        return None

    # Cria o gráfico de dispersão
    plt.figure(figsize=(12, 6))
    plt.scatter(teto_total_real, valores_variavel, label=variable, color='blue', alpha=0.6)

    # Adiciona uma linha de tendência
    try:
        z = np.polyfit(teto_total_real, valores_variavel, 1)  # Ajuste linear
        p = np.poly1d(z)
        plt.plot(teto_total_real, p(teto_total_real), "r--", label="Linha de Tendência")
    except Exception as e:
        logging.error(f"Erro ao calcular a linha de tendência para {variable}: {e}")

    # Configurações do gráfico
    plt.xlabel("Teto Financeiro MAC (Valores Nominais)")
    plt.ylabel(variable)
    plt.title(f"Correlação entre Teto Financeiro MAC e {variable}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Salva o gráfico
    graph_path = os.path.join(output_dir, f"{variable}_correlation.png")
    plt.savefig(graph_path)
    plt.close()

    return graph_path

def generate_analysis_with_gemini_vision(corr_values, graph_paths, inflation_data):
    analysis = {}
    model = genai.GenerativeModel('gemini-1.5-flash')

    for var, corr in corr_values.items():
        logging.info(f"Correlação para {var}: {corr}")

        if corr is None:
            logging.warning(f"Correlação não calculada para {var}. Análise não será gerada.")
            analysis[var] = "Não foi possível calcular a correlação devido a dados insuficientes ou constantes."
            continue

        if var not in graph_paths:
            logging.warning(f"Gráfico não encontrado para {var}. Análise não será gerada.")
            analysis[var] = f"Não foi possível gerar a análise com o Gemini devido à falta do gráfico correspondente."
            continue

        # --- Prepara a parte do prompt sobre inflação ---
        inflation_context = "Considerando a inflação acumulada (IPCA) no período analisado, "
        inflation_context += "é importante destacar que os valores nominais do Teto Financeiro MAC e dos gastos em saúde "
        inflation_context += "não foram ajustados pela inflação. Isso significa que o aumento real dos recursos pode ter sido "
        inflation_context += "menor do que o observado nominalmente, impactando a capacidade de financiamento do SUS."

        prompt = f"""
        Você é um especialista em análise de dados do sistema de saúde brasileiro.
        Analise a seguinte correlação e o gráfico correspondente, considerando o contexto do SUS (Sistema Único de Saúde) e a **inflação (IPCA) acumulada no período**:
        **Use destaques de forma elegante**
        Variável: {var}
        Correlação com o Teto Financeiro MAC (valores nominais): {corr:.4f}

        {inflation_context}

        1. **Interprete o valor da correlação** (forte, moderada, fraca, positiva, negativa, ou **inexistente/espúria se a correlação for nula devido a dados constantes ou ausentes**).
        2. **Descreva brevemente a tendência geral** observada no gráfico para ambas as variáveis, **mencionando se há dados ausentes, zerados ou constantes que invalidem a análise de correlação**.
        3. **Em não mais que 3 linhas**, foque em **como a baixa correlação ou a ausência de correlação, considerando a inflação, pode indicar subfinanciamento ou ineficiência na alocação de recursos para {var}**, considerando o contexto do SUS.
        4. **Em não mais que 3 linhas**, indique **implicações práticas** para o planejamento e gestão do SUS, **sugerindo ações para melhorar o acesso e a qualidade dos serviços relacionados a {var}**.

        **Faça texto corrido. Seja objetivo e conciso, adote o formato de análise crítica, e foque em insights acionáveis que evidenciem a necessidade de atenção para a variável {var} no contexto do financiamento do SUS, considerando a defasagem causada pela inflação.**
        """
        try:
            # Carrega a imagem do gráfico
            image_path = graph_paths.get(var)
            if image_path:
                image_parts = {
                    "mime_type": "image/png",
                    "data": open(image_path, "rb").read()
                }
                contents = [prompt, image_parts]

                # Tenta fazer a chamada à API
                try:
                    response = model.generate_content(contents=contents)
                    analysis[var] = response.text
                except GoogleAPIError as e:
                    logging.error(f"Erro de API ao chamar o Gemini para {var}: {e}")
                    analysis[var] = f"Erro de API ao chamar o Gemini: {e}"
                except Exception as e:
                    logging.error(f"Erro desconhecido ao chamar o Gemini para {var}: {e}")
                    analysis[var] = f"Erro desconhecido ao chamar o Gemini: {e}"

                time.sleep(1)  # Adiciona um atraso de 1 segundo para evitar atingir o limite de taxa
            else:
                logging.warning(f"Gráfico não encontrado para {var}. A análise será feita sem a imagem.")
                analysis[var] = f"Não foi possível gerar a análise com o Gemini devido à falta do gráfico correspondente. A correlação foi calculada como: {corr}"
        except Exception as e:
            logging.error(f"Erro ao chamar a API do Gemini para {var}: {e}")
            analysis[var] = "Não foi possível gerar a análise com o Gemini devido a um erro."

    return analysis

def main():
    logging.info("Iniciando análise de correlação.")
    sia_data = load_sia_data('SIA.json')
    sih_data = load_sih_data('SIH.json')
    mac_data = load_mac_data('evolucao_mac.json')

    # Verifica se os dados foram carregados corretamente
    if not sia_data:
        logging.error("Não foi possível carregar os dados do SIA. Análise abortada.")
        return
    if not sih_data:
        logging.error("Não foi possível carregar os dados do SIH. Análise abortada.")
        return
    if not mac_data:
        logging.error("Não foi possível carregar os dados do MAC. Análise abortada.")
        return

    common_years = find_common_years(sia_data, sih_data, mac_data)
    if not common_years:
        logging.error("Nenhum ano comum encontrado entre os conjuntos de dados. Análise abortada.")
        return

    # --- Obtém dados de inflação ---
    start_year = int(min(common_years))
    end_year = int(max(common_years))
    inflation_data = get_inflation_data(start_year, end_year)

    if inflation_data is None:
        logging.error("Não foi possível obter dados de inflação. Análise abortada.")
        return

    # --- Usa valores nominais do Teto MAC ---
    teto_total_nominal = [mac_data['teto_financeiro_mac'][ano] for ano in common_years]

    # --- Calcula correlações ---
    correlations = calculate_correlations(teto_total_nominal, sia_data, sih_data, common_years)

    # --- Geração dos Gráficos ---
    graph_paths = {}
    if sia_data:
        graph_paths["Média Complexidade"] = generate_correlation_graph(teto_total_nominal, sia_data['media_complexidade'], "Média Complexidade", common_years)
        graph_paths["Alta Complexidade"] = generate_correlation_graph(teto_total_nominal, sia_data['alta_complexidade'], "Alta Complexidade", common_years)
        graph_paths["Total Ambulatorial"] = generate_correlation_graph(teto_total_nominal, sia_data['total_ambulatorial'], "Total Ambulatorial", common_years)
    if sih_data:
        for grupo in sih_data:
            graph_paths[grupo] = generate_correlation_graph(teto_total_nominal, sih_data[grupo], grupo, common_years)

    # --- Análise com Gemini ---
    analysis = generate_analysis_with_gemini_vision(correlations, graph_paths, inflation_data)

    with open('analise_correlacao.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=4)
    logging.info("Análise salva em 'analise_correlacao.json'.")

if __name__ == "__main__":
    main()  