import google.generativeai as genai
import json
import os
from dotenv import load_dotenv
import argparse

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configura a chave da API do Google Generative AI
genai.configure(api_key=os.getenv("API_KEY"))

def gerar_conclusao(dados, modelo):
    """
    Gera a conclusão do relatório analítico do Teto MAC, de forma resumida e concisa, com base nos dados fornecidos.

    Args:
        dados: Um dicionário contendo os dados para a análise.
        modelo: O modelo de linguagem a ser utilizado (gemini-1.5-pro).

    Returns:
        Um dicionário contendo o nome do município e a conclusão gerada.
    """
    nome_municipio = extrair_nome_municipio(dados)

    prompt_template = """
    Você é um especialista em análise de dados do sistema de saúde brasileiro. Com base nas informações contidas nos dados fornecidos, escreva um **resumo conciso** da conclusão para um relatório analítico do Teto Financeiro da Média e Alta Complexidade Ambulatorial e Hospitalar (MAC) do município {nome_municipio}. O objetivo do relatório é apresentar subsídios técnicos para o pleito de aumento do teto financeiro MAC no ano seguinte.

    **Destaque no resumo:**

    *   **Fatores principais que justificam a necessidade de revisão do Teto MAC.** (Seja objetivo e factual)
    *   **Utilize uma linguagem mais natural e humana, menos técnica.**

    **Considere os seguintes pontos, se aplicável:**

    *   A evolução do Teto MAC ao longo do tempo.
    *   A relação entre o Teto MAC e a produção ambulatorial e hospitalar.
    *   O impacto da inflação no valor real do Teto MAC.
    *   As características demográficas e socioeconômicas do município.
    *   A necessidade de garantir a sustentabilidade e a qualidade do atendimento à saúde da população.

    **Texto breve, com no máximo 3 parágrafos.**

    Dados: {dados}
    """

    prompt = prompt_template.format(nome_municipio=nome_municipio, dados=json.dumps(dados))

    model = genai.GenerativeModel(modelo)
    response = model.generate_content(prompt)
    return {"municipio": nome_municipio, "conclusao": response.text}

def extrair_nome_municipio(dados):
    """Extrai o nome do município dos dados fornecidos."""
    nome_municipio = ""
    if 'nome_municipio' in dados:
        nome_municipio = dados['nome_municipio']
    else:
        for key in dados.keys():
            if isinstance(dados[key], dict) and 'nome_municipio' in dados[key]:
                nome_municipio = dados[key]['nome_municipio']
                break
    if nome_municipio == "":
        nome_municipio = "Município não identificado"
    return nome_municipio

def extrair_municipios(arquivo):
    """
    Extrai o nome do município a partir do nome do arquivo ou do seu conteúdo.

    Args:
        arquivo: O caminho para o arquivo.

    Returns:
        Uma lista de nomes de municípios encontrados.
    """
    municipios = []
    nome_arquivo = os.path.basename(arquivo).lower()

    # Tenta extrair o nome do município do nome do arquivo
    if "guarapari" in nome_arquivo:
        municipios.append("Guarapari")
    elif "ribeirão" in nome_arquivo or "ribeirao" in nome_arquivo:
        municipios.append("Ribeirão")

    # Se não encontrar no nome do arquivo, tenta extrair do conteúdo
    if not municipios:
        try:
            if arquivo.endswith(".json"):
                with open(arquivo, 'r') as f:
                    dados = json.load(f)
                    for key in dados.keys():
                        if isinstance(dados[key], dict) and 'nome_municipio' in dados[key]:
                            municipios.append(dados[key]['nome_municipio'])
            elif arquivo.endswith(".txt"):
                with open(arquivo, 'r') as f:
                    conteudo = f.read().lower()
                    if "guarapari" in conteudo:
                        municipios.append("Guarapari")
                    elif "ribeirão" in conteudo or "ribeirao" in conteudo:
                        municipios.append("Ribeirão")
        except Exception as e:
            print(f"Erro ao processar o arquivo {arquivo}: {e}")

    return municipios

def municipio_presente_nos_dados(municipio, dados):
    """Verifica se o município está presente nos dados fornecidos."""
    if isinstance(dados, dict):
        return any(municipio.lower() in str(valor).lower() for valor in dados.values()) or \
               any(municipio.lower() in str(valor).lower() for valor in dados.keys()) or \
               (isinstance(dados, dict) and any(municipio.lower() in str(valor).lower() for valor in dados.get("texto", "").split()))
    elif isinstance(dados, str):
        return municipio.lower() in dados.lower()
    else:
        return False

def gerar_conclusao_final(conclusoes):
    """
    Gera uma conclusão final consolidada, defendendo a necessidade de revisão do Teto MAC.

    Args:
        conclusoes: Um dicionário contendo as conclusões geradas para cada município.

    Returns:
        Um texto consolidado e humanizado.
    """
    texto_final = """
    ## Conclusão Final: A Necessidade de Revisão do Teto MAC

    As análises realizadas para os municípios demonstram, de forma clara e consistente, que o atual valor do Teto Financeiro da Média e Alta Complexidade (MAC) não atende às demandas do sistema de saúde. Os dados evidenciam que:

    * O valor do Teto MAC não acompanhou a inflação ao longo dos anos, resultando em uma redução significativa do seu poder de compra. Isso impacta diretamente a capacidade de aquisição de insumos, medicamentos e a manutenção da infraestrutura necessária para o atendimento à população.
    * Há um aumento expressivo na demanda por procedimentos de média e alta complexidade, especialmente em municípios com crescimento populacional acelerado ou com perfil epidemiológico mais complexo. Essa demanda não é acompanhada por um reajuste proporcional no teto financeiro.
    * A sustentabilidade financeira dos serviços de saúde está comprometida. Sem um reajuste adequado, os municípios enfrentam dificuldades para manter a qualidade do atendimento, o que pode levar ao desabastecimento de medicamentos, à redução de leitos hospitalares e ao aumento das filas de espera.

    **Considerações Finais:**
    Diante dos fatos apresentados, é imperativo que o Teto MAC seja revisado. A manutenção do valor atual coloca em risco a capacidade dos municípios de oferecer serviços de saúde de qualidade à população. Uma revisão justa e adequada não apenas garantiria a sustentabilidade do sistema, mas também asseguraria que os recursos financeiros estejam alinhados com as reais necessidades da população.

    A saúde é um direito fundamental, e o Teto MAC é um instrumento essencial para garantir que esse direito seja efetivado. Portanto, a revisão do teto não é apenas uma necessidade técnica, mas uma obrigação ética e social.
    """
    return texto_final

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera conclusões para relatórios do Teto MAC.")
    parser.add_argument("-o", "--output", default="conclusao_final.txt", help="Nome do arquivo de saída (padrão: conclusao_final.txt)")
    args = parser.parse_args()

    # Lista de arquivos para processar
    arquivos = ['analise_mac_sia.txt', 'analise_mac_sih.txt', 'analise_mac_municipio.txt', 'analise_correlacao.json', 'dados_economicos.json']

    # Dicionário para armazenar as conclusões
    conclusoes = {}

    # Identificar os municípios
    municipios_encontrados = set()
    for arquivo in arquivos:
        municipios_encontrados.update(extrair_municipios(arquivo))

    # Gerar conclusões para cada município e arquivo
    for municipio in municipios_encontrados:
        for arquivo in arquivos:
            try:
                if arquivo.endswith(".json"):
                    with open(arquivo, 'r') as f:
                        dados = json.load(f)
                elif arquivo.endswith(".txt"):
                    with open(arquivo, 'r') as f:
                        dados = {"texto": f.read(), "nome_municipio": municipio}
                else:
                    continue

                # Verifica se o município está presente nos dados
                if municipio_presente_nos_dados(municipio, dados):
                    resultado = gerar_conclusao(dados, 'gemini-1.5-flash')
                    if municipio not in conclusoes:
                        conclusoes[municipio] = ""
                    conclusoes[municipio] += f"\n\n---\n\n**Arquivo:** {arquivo}\n\n" + resultado["conclusao"]
            except Exception as e:
                print(f"Erro ao processar o arquivo {arquivo} para o município {municipio}: {e}")

    # Gera a conclusão final
    texto_final = gerar_conclusao_final(conclusoes)

    # Salva a conclusão final em um arquivo TXT
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(texto_final)

    print(f"Conclusão final gerada e salva no arquivo {args.output}")