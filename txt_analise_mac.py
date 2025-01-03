import os
import json
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
import logging
import sys

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Função para ler arquivo JSON
def ler_dados_json(caminho):
    """Lê dados de um arquivo JSON com codificação UTF-8 e retorna uma lista de dicionários."""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Erro: Arquivo não encontrado em '{caminho}'")
        return None
    except json.JSONDecodeError:
        logging.error(f"Erro: Formato JSON inválido em '{caminho}'")
        return None

# Lê os arquivos JSON (certifique-se de que os nomes dos arquivos estão corretos)
evolucao_mac = ler_dados_json('evolucao_mac.json')
pt_mac_res = ler_dados_json('pt_mac_res.json')

# Verifica se os dados foram carregados corretamente
if evolucao_mac is None or pt_mac_res is None:
    logging.error("Erro ao carregar os arquivos JSON. Encerrando a execução.")
    exit()

# --- Configuração do Modelo Gemini ---
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

generation_config = {
  "temperature": 0.2,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
)

# --- Função para formatar data ---
def formatar_data(data_str):
    """Formata a data de AAAA-MM-DD para DD/MM/AAAA."""
    ano, mes, dia = data_str.split('-')
    return f"{dia}/{mes}/{ano}"

# --- Função para formatar valor ---
def formatar_valor(valor):
    """Formata o valor para o padrão brasileiro."""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- Função para gerar a tabela Markdown das portarias ---
def gerar_tabela_markdown(portarias):
    """Gera uma tabela Markdown a partir dos dados das portarias ordenados por data."""
    # Ordena as portarias por data (da mais recente para a mais antiga)
    portarias_ordenadas = sorted(portarias, key=lambda x: datetime.strptime(x['Data'], '%Y-%m-%d %H:%M:%S'), reverse=True)

    tabela_markdown = """
| Portaria | Data | Tipo | Incentivo | Valor (R$) | Competência |
|---|---|---|---|---|---|
"""
    for portaria in portarias_ordenadas:
        data_formatada = formatar_data(portaria['Data'][:10])
        valor_formatado = formatar_valor(portaria['Valor'])
        tabela_markdown += f"| {portaria['Portaria']} | {data_formatada} | {portaria['Tipo']} | {portaria['Incentivo']} | {valor_formatado} | {portaria['Competência']} |\n"

    return tabela_markdown

# --- Função para gerar o Markdown completo da análise ---
def gerar_markdown_analise(municipio, tabela_markdown, analise_tendencia, conclusao):
    """Gera o Markdown completo da análise."""
    markdown_completo = f"""
# Análise da Evolução do Teto Financeiro MAC - {municipio}

## Análise da Tendência
{analise_tendencia}

## Influência das Portarias
As portarias listadas abaixo tiveram impacto significativo na evolução do Teto Financeiro MAC. A análise detalhada da influência de cada portaria foge ao escopo deste documento, mas é possível afirmar que os acréscimos e remanejamentos descritos contribuíram diretamente para o aumento do teto ao longo dos anos.

### Tabela 1: Portarias com Maior Impacto na Evolução do Teto MAC
{tabela_markdown}

{conclusao}
"""
    return markdown_completo

def main(municipio):
    # --- Prompt para Análise Completa (MODIFICADO para Markdown) ---
    prompt_analise_completa = f"""
    # Análise da Evolução do Teto Financeiro MAC e Portarias para {municipio}

    Você é um assistente de análise de dados financeiros na área da saúde pública. Sua tarefa é analisar a evolução do "Teto Financeiro MAC" para o município de {municipio}, com base nos dados fornecidos e nas portarias que mais impactaram essa evolução.

    ## Objetivo:

    O objetivo deste documento é justificar um pleito para solicitação de ajuste do teto MAC para o ano seguinte (implícito, não deve ser mencionado).

    ## Instruções:

    - Gere a **análise da tendência** observada na evolução do Teto MAC, **e a conclusão**, em formato **Markdown**.
    - Busque focar, mas não exclusivamente, sua análise, no período das portarias listadas.
    - Divida a análise da tendência em parágrafos. Não numere os parágrafos.
    - Analise os dados de evolução do Teto MAC e descreva a tendência observada, seja ela de crescimento, decrescimento ou estabilidade.
    - Relacione a tendência observada com as portarias listadas, explicando como elas podem ter contribuído para o cenário atual.
    - Destaque os valores iniciais e finais do Teto MAC no período analisado e calcule a variação percentual, se aplicável.
    - Não cite os arquivos, mas use seus dados para a análise.
    - Considere que as portarias foram previamente selecionadas como as que mais impactaram as variações do gráfico.
    - O documento contará ainda com informações do município, dados de produção ambulatorial e hospitalar, e terá uma análise exclusiva das correlações entre a produção e esses valores. Esta parte não entra na sua análise.
    - Sua missão é gerar a **análise da tendência e a conclusão**, em Markdown, para serem inseridas posteriormente em um documento.
    - **A conclusão deve, obrigatoriamente, iniciar com '## Conclusão'**.
    - **Utilize formatação Markdown para melhorar a legibilidade do texto (negrito, itálico, etc.).**
    - **Quando for se referir a valores monetários, use sempre R\\$ e não R$ para evitar erros de formatação.**
    - **Use destaques e cores: Colored text and background colors for text, using the syntax :color[text to be colored] and :color-background[text to be colored], respectively. color must be replaced with any of the following supported colors: blue, green, orange, red, violet, gray/grey, rainbow, or primary. For example, you can use :orange[your text here] or :blue-background[your text here]. If you use "primary" for color, Streamlit will use the default primary accent color unless you set the theme.primaryColor configuration option.***

    ## Dados:

    **Evolução do Teto MAC:**
    ```json
    {json.dumps(evolucao_mac, ensure_ascii=False)}

    Gere a análise da tendência e a conclusão, em Markdown, com parágrafos numerados e justificada, conforme as instruções acima. Certifique-se de que a conclusão inicie com '## Conclusão'.
    """

    # --- Execução da Análise ---
    logging.info("Iniciando a análise com o Gemini 1.5 pro...")

    response = model.generate_content(prompt_analise_completa)

    logging.info("Análise concluída.")

    # --- Limpeza da Resposta ---
    analise_tendencia_conclusao = response.text

    # --- Dividir a resposta em análise da tendência e conclusão ---
    if "## Conclusão" in analise_tendencia_conclusao:
        partes = analise_tendencia_conclusao.split("## Conclusão")
        analise_tendencia_texto = partes[0].strip()
        conclusao = f"## Conclusão\n{partes[1].strip()}"
    else:
        analise_tendencia_texto = analise_tendencia_conclusao
        conclusao = ""
        logging.warning("Aviso: '## Conclusão' não encontrado na resposta do modelo.")

    # --- Dividir a análise da tendência em parágrafos e adicionar o estilo de justificar ---
    paragrafos = analise_tendencia_texto.split("\n")
    analise_tendencia = ""
    for paragrafo in paragrafos:
        if paragrafo.strip().startswith(tuple(f"{i}." for i in range(1, 10))):
            analise_tendencia += f"<p style='text-align: justify;'>{paragrafo.strip()}</p>"  # Adiciona o estilo aqui
        else:
            if analise_tendencia.endswith("</p>"):
                analise_tendencia = analise_tendencia[:-4] + " " + paragrafo.strip() + "</p>"
            else:
                analise_tendencia += f"<p style='text-align: justify;'>{paragrafo.strip()}</p>"  # Adiciona o estilo aqui

    # --- Gerar a tabela Markdown ---
    tabela_markdown = gerar_tabela_markdown(pt_mac_res)

    # --- Gerar o Markdown completo da análise ---
    markdown_completo = gerar_markdown_analise(municipio, tabela_markdown,  analise_tendencia_texto, conclusao)

    # --- Salvar o Resultado em um Arquivo TXT ---
    nome_arquivo_saida = 'analise_mac_municipio.txt'
    with open(nome_arquivo_saida, 'w', encoding='utf-8') as f:
        f.write(markdown_completo)

if __name__ == "__main__":
    municipio = sys.argv[1]
    main(municipio)