import requests
import json
import sys
import google.generativeai as genai
import os
import pandas as pd
import logging
import time

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuração da API do Google Generative AI (Gemini)
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

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

def obter_uf_por_ibge(codigo_ibge):
    """Retorna a UF com base nos dois primeiros dígitos do código IBGE."""
    uf_codigo = str(codigo_ibge)[:2]
    uf_map = {
        "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
        "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
        "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
        "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
        "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
        "52": "GO", "53": "DF"
    }
    return uf_map.get(uf_codigo, "UF desconhecida")

def gerar_analise_demografica(df_populacao, dados_economicos, codigo_ibge, nome_municipio, uf):
    """
    Gera uma análise textual dos dados demográficos e econômicos usando o Gemini.
    Divide a análise em seções: introdução, análise da pirâmide etária,
    análise da população por faixa etária e conclusão.

    Evita redundâncias mantendo um controle das informações já mencionadas e
    removendo títulos repetidos.
    """
    logger.info(f"Iniciando geração de análise demográfica para {nome_municipio} ({codigo_ibge}, {uf})")
    dados_eco_municipio = dados_economicos.get(codigo_ibge)
    if not dados_eco_municipio:
        logger.error(f"Dados econômicos não encontrados para o código IBGE {codigo_ibge}.")
        return {"erro": "Dados econômicos não encontrados para o código IBGE fornecido."}

    info_mencionadas = set()  # Conjunto para armazenar informações já mencionadas

    def gerar_texto(secao, prompt, info_mencionadas):
        """Gera o texto para uma seção específica, evitando redundâncias e títulos repetidos."""
        tentativas = 0
        while tentativas < 3:
            try:
                logger.info(f"Gerando análise para a seção: {secao}")
                response = model.generate_content(prompt)
                texto_gerado = response.text

                # Remover informações já mencionadas e títulos repetidos
                texto_limpo = ""
                for frase in texto_gerado.split(". "):
                    frase_limpa = frase
                    for info in info_mencionadas:
                        frase_limpa = frase_limpa.replace(info, "")
                    
                    # Remover títulos repetidos (heurística simples)
                    if secao != "introducao" and frase_limpa.strip().startswith(f"{nome_municipio} (IBGE: {codigo_ibge}, {uf}):"):
                        frase_limpa = frase_limpa.replace(f"{nome_municipio} (IBGE: {codigo_ibge}, {uf}):", "").strip()
                    elif secao != "introducao" and frase_limpa.strip().startswith("##"):
                        frase_limpa = frase_limpa.replace("##", "").strip()
                    
                    if frase_limpa.strip() != "" and frase_limpa not in texto_limpo:
                        texto_limpo += frase_limpa + ". "
                
                if texto_limpo == "":
                    logger.warning(f"Texto gerado para a seção '{secao}' está vazio após a limpeza. Tentando novamente...")
                    tentativas += 1
                    time.sleep(5)
                    continue

                # Adicionar novas informações ao conjunto (exceto títulos)
                for frase in texto_limpo.split(". "):
                    if not frase.strip().startswith(f"{nome_municipio} (IBGE: {codigo_ibge}, {uf}):") and not frase.strip().startswith("##"):
                        info_mencionadas.add(frase)

                logger.info(f"Resposta do Gemini para a seção {secao}: {texto_limpo[:200]}...")
                return texto_limpo.strip()

            except Exception as e:
                if "429" in str(e):
                    logger.warning(f"Limite de taxa atingido para a seção '{secao}'. Tentando novamente em 60 segundos...")
                    time.sleep(60)
                    tentativas += 1
                else:
                    logger.error(f"Erro ao gerar análise (seção: {secao}): {e}")
                    return f"Não foi possível gerar a análise para esta seção ({secao})."
        return f"Não foi possível gerar a análise para esta seção ({secao}) após várias tentativas."

    # Verifica se o campo 'rendimento_medio_mensal_real' está disponível
    rendimento_medio = dados_eco_municipio.get("rendimento_medio", {}).get("rendimento_medio_mensal_real", "N/A")
    if rendimento_medio == "N/A":
        logger.warning(f"Dados de rendimento médio não encontrados para o município {nome_municipio} ({codigo_ibge}, {uf}).")

    prompt_base = f"""
    Analise os dados demográficos e econômicos do município de {nome_municipio} (código IBGE: {codigo_ibge}, UF: {uf}).
    Use destaques de forma elegante. Acrescente informações socioeconômicas que puder sobre a cidade (confirme com o código ibge e o nome).
    Mantenha os textos curtos e objetivos, e evite repetir informações.
    MAC significa Teto Municipal de Média e Alta Complexidade.

    Dados Demográficos (tabela_populacao_completa.json):
    {df_populacao.to_string()}

    Dados Econômicos (dados_economicos.json):
    População Residente: {dados_eco_municipio["populacao_area_densidade"]["populacao_residente"]}
    Taxa de Alfabetização (15 anos ou mais): {dados_eco_municipio["taxa_alfabetizacao"]["taxa_alfabetizacao_15_anos_ou_mais"]}%
    Rendimento Médio Mensal: R$ {rendimento_medio if rendimento_medio != "N/A" else "Dado não disponível"}
    Total de Domicílios: {dados_eco_municipio['domicilios_especie']['total']}
    Domicílios Ocupados: {dados_eco_municipio['domicilios_moradores']['domicilios_particulares_permanentes_ocupados']}
    Média de Moradores: {dados_eco_municipio['domicilios_moradores']['media_de_moradores_em_domicilios_particulares_permanentes_ocupados']:.1f}
    Área da Unidade Territorial: {dados_eco_municipio['populacao_area_densidade']['area_da_unidade_territorial']} km²
    Densidade Demográfica: {dados_eco_municipio['populacao_area_densidade']['densidade_demografica']} hab/km²

    ---
    """

    prompts = {
        "introducao": prompt_base + "Faça uma introdução geral sobre o município, destacando os principais indicadores demográficos e econômicos.",
        "analise_piramide_etaria": prompt_base + "Analise a estrutura etária da população com base nos dados da pirâmide etária (distribuição por gênero e faixa etária).",
        "analise_populacao_faixa_etaria": prompt_base + "Analise a distribuição da população por faixa etária, independentemente do gênero.",
        "conclusao": prompt_base + "Faça uma conclusão geral, relacionando os dados demográficos e econômicos e destacando possíveis tendências ou desafios para o município."
    }

    analise_completa = {}
    for secao, prompt in prompts.items():
        analise_completa[secao] = gerar_texto(secao, prompt, info_mencionadas)

    logger.info(f"Análise completa gerada: {analise_completa}")
    return analise_completa

class Econo:
    def __init__(self, municipio_ibge, municipio_nome):
        self.MUNICIPIO = municipio_ibge
        self.NOME_MUNICIPIO = municipio_nome
        self.dados_municipio = {
            self.MUNICIPIO: {
                "nome_municipio": self.NOME_MUNICIPIO
            }
        }

    def obter_dados_sidra(self, url):
        """Obtém os dados da API do SIDRA usando requests."""
        logger.info(f"Obtendo dados da URL: {url}...")
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Dados brutos:\n{data}")

            if not data:
                logger.warning(f"Resposta vazia retornada para a URL.")
                return None

            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao obter dados da URL: {e}")
            return None

    def run(self):
        """Obtém os dados das tabelas, adiciona a análise do Gemini e salva em um arquivo JSON."""

        # Obter a UF do município
        uf = obter_uf_por_ibge(self.MUNICIPIO)

        # --- URLs da API do SIDRA ---
        url_4709 = f"https://apisidra.ibge.gov.br/values/t/4709/n6/{self.MUNICIPIO}/v/93,5936,10605/p/last%201?header=y"
        url_4714 = f"https://apisidra.ibge.gov.br/values/t/4714/n6/{self.MUNICIPIO}/v/93,6318,614/p/last%201?header=y"
        url_4711 = f"https://apisidra.ibge.gov.br/values/t/4711/n6/{self.MUNICIPIO}/v/617/p/last%201?header=y"
        url_4712 = f"https://apisidra.ibge.gov.br/values/t/4712/n6/{self.MUNICIPIO}/v/381,382,5930/p/last%201?header=y"
        url_9543 = f"https://apisidra.ibge.gov.br/values/t/9543/n6/{self.MUNICIPIO}/v/2513/p/last%201?header=y"
        url_4660 = f"https://apisidra.ibge.gov.br/values/t/4660/n6/{self.MUNICIPIO}/v/5933/p/last%201?header=y"

        # --- Obter Dados das Tabelas ---

        # Tabela 4709: População residente, Variação absoluta e Taxa de crescimento
        tabela_4709 = self.obter_dados_sidra(url_4709)
        if tabela_4709 is not None:
            self.dados_municipio[self.MUNICIPIO]["populacao_variacao"] = {}
            header = tabela_4709[0]
            variavel_index = list(header.keys()).index("D2N")
            valor_index = list(header.keys()).index("V")
            for row in tabela_4709[1:]:
                variavel = row[list(header.keys())[variavel_index]]
                valor = row[list(header.keys())[valor_index]]
                if valor and valor != "...":
                    if variavel == "População residente":
                        self.dados_municipio[self.MUNICIPIO]["populacao_variacao"]["populacao_residente"] = float(valor)
                    elif "Variação absoluta da população" in variavel:
                        self.dados_municipio[self.MUNICIPIO]["populacao_variacao"]["variacao_absoluta_da_populacao_residente_2010_2022"] = float(valor)
                    elif variavel == "Taxa de crescimento geométrico":
                        self.dados_municipio[self.MUNICIPIO]["populacao_variacao"]["taxa_de_crescimento_geometrico"] = float(valor)

        # Tabela 4714: População Residente, Área territorial e Densidade demográfica
        tabela_4714 = self.obter_dados_sidra(url_4714)
        if tabela_4714 is not None:
            self.dados_municipio[self.MUNICIPIO]["populacao_area_densidade"] = {}
            header = tabela_4714[0]
            variavel_index = list(header.keys()).index("D2N")
            valor_index = list(header.keys()).index("V")
            for row in tabela_4714[1:]:
                variavel = row[list(header.keys())[variavel_index]]
                valor = row[list(header.keys())[valor_index]]
                if valor and valor != "...":
                    if variavel == "População residente":
                        self.dados_municipio[self.MUNICIPIO]["populacao_area_densidade"]["populacao_residente"] = float(valor)
                    elif variavel == "Área da unidade territorial":
                        self.dados_municipio[self.MUNICIPIO]["populacao_area_densidade"]["area_da_unidade_territorial"] = float(valor)
                    elif variavel == "Densidade demográfica":
                        self.dados_municipio[self.MUNICIPIO]["populacao_area_densidade"]["densidade_demografica"] = float(valor)

        # Tabela 4711: Domicílios recenseados, por espécie
        tabela_4711 = self.obter_dados_sidra(url_4711)
        if tabela_4711 is not None:
            self.dados_municipio[self.MUNICIPIO]["domicilios_especie"] = {}
            header = tabela_4711[0]
            variavel_index = list(header.keys()).index("D4N")
            valor_index = list(header.keys()).index("V")
            for row in tabela_4711[1:]:
                variavel = row[list(header.keys())[variavel_index]]
                valor = row[list(header.keys())[valor_index]]
                if valor and valor != "...":
                    if variavel == "Total":
                        self.dados_municipio[self.MUNICIPIO]["domicilios_especie"]["total"] = float(valor)

        # Tabela 4712: Domicílios particulares permanentes ocupados, Moradores e Média de moradores
        tabela_4712 = self.obter_dados_sidra(url_4712)
        if tabela_4712 is not None:
            self.dados_municipio[self.MUNICIPIO]["domicilios_moradores"] = {}
            header = tabela_4712[0]
            variavel_index = list(header.keys()).index("D2N")
            valor_index = list(header.keys()).index("V")
            for row in tabela_4712[1:]:
                variavel = row[list(header.keys())[variavel_index]]
                valor = row[list(header.keys())[valor_index]]
                if valor and valor != "...":
                    if variavel == "Domicílios particulares permanentes ocupados":
                        self.dados_municipio[self.MUNICIPIO]["domicilios_moradores"]["domicilios_particulares_permanentes_ocupados"] = float(valor)
                    elif variavel == "Moradores em domicílios particulares permanentes ocupados":
                        self.dados_municipio[self.MUNICIPIO]["domicilios_moradores"]["moradores_em_domicilios_particulares_permanentes_ocupados"] = float(valor)
                    elif variavel == "Média de moradores em domicílios particulares permanentes ocupados":
                        self.dados_municipio[self.MUNICIPIO]["domicilios_moradores"]["media_de_moradores_em_domicilios_particulares_permanentes_ocupados"] = float(valor)

        # Tabela 9543: Taxa de alfabetização
        tabela_9543 = self.obter_dados_sidra(url_9543)
        if tabela_9543 is not None:
            self.dados_municipio[self.MUNICIPIO]["taxa_alfabetizacao"] = {}
            header = tabela_9543[0]
            valor_index = list(header.keys()).index("V")
            for row in tabela_9543[1:]:
                valor = row[list(header.keys())[valor_index]]
                if valor and valor != "...":
                    self.dados_municipio[self.MUNICIPIO]["taxa_alfabetizacao"]["taxa_alfabetizacao_15_anos_ou_mais"] = float(valor)

        # Tabela 4660: Rendimento médio mensal
        tabela_4660 = self.obter_dados_sidra(url_4660)
        if tabela_4660 is not None:
            self.dados_municipio[self.MUNICIPIO]["rendimento_medio"] = {}
            header = tabela_4660[0]
            valor_index = list(header.keys()).index("V")
            for row in tabela_4660[1:]:
                valor = row[list(header.keys())[valor_index]]
                if valor and valor != "...":
                    self.dados_municipio[self.MUNICIPIO]["rendimento_medio"]["rendimento_medio_mensal_real"] = float(valor)

        # --- Gerar Análise com Gemini e Adicionar aos Dados ---
        # Carregar dados populacionais do arquivo local
        try:
            with open('tabela_populacao_completa.json', 'r', encoding='utf-8') as f:
                dados_populacao_completa = json.load(f)
        except FileNotFoundError:
            logger.error("Arquivo tabela_populacao_completa.json não encontrado.")
            sys.exit(1)

        # Criar DataFrame de população para o Gemini
        df_populacao = pd.DataFrame.from_dict(dados_populacao_completa, orient='index')
        df_populacao.index.name = 'Faixa Etária'

        # Gerar análise dividida em seções
        logger.info(f"Gerando análise com Gemini para {self.NOME_MUNICIPIO} ({self.MUNICIPIO}, {uf})")
        analise_gemini = gerar_analise_demografica(df_populacao, self.dados_municipio, self.MUNICIPIO, self.NOME_MUNICIPIO, uf)
        logger.info(f"Análise do Gemini gerada: {analise_gemini}")

        # Adicionar a análise do Gemini aos dados do município
        self.dados_municipio[self.MUNICIPIO]["analise_gemini"] = analise_gemini
        logger.info(f"Dados do município antes de salvar: {self.dados_municipio}")

        # --- Salvar os Dados em um Único JSON ---
        # Remover a chave 'rendimento_medio' se estiver vazia
        if self.MUNICIPIO in self.dados_municipio and "rendimento_medio" in self.dados_municipio[self.MUNICIPIO] and not self.dados_municipio[self.MUNICIPIO]["rendimento_medio"]:
            del self.dados_municipio[self.MUNICIPIO]["rendimento_medio"]

        with open(f"dados_economicos.json", "w", encoding='utf-8') as f:
            json.dump(self.dados_municipio, f, indent=4, ensure_ascii=False)

        logger.info(f"Dados salvos em dados_economicos.json")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        municipio_ibge = sys.argv[1]
        municipio_nome = sys.argv[2]
        script = Econo(municipio_ibge, municipio_nome)
        script.run()
    else:
        print("Uso: python teste.py <codigo_ibge_municipio> <nome_municipio>")