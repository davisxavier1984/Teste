import requests
import sys
import time
import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from datetime import datetime

# Configuração básica do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('evolucao_mac.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Mapeamento de categorias
category_mapping = {
    "Sem Incentivos": "Sem Incentivos",
    "Incentivos": "Incentivos",
    "Teto MAC": "Teto Financeiro MAC"
}

def obter_nome_municipio(codigo_ibge):
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{codigo_ibge}"
    response = requests.get(url)
        
    if response.status_code == 200:
        dados = response.json()
        nome_municipio = dados['nome']
        uf = dados['microrregiao']['mesorregiao']['UF']['sigla']
        return f"{nome_municipio}/{uf}"
    else:
        logger.error("Código IBGE não encontrado.")
        return "Código IBGE não encontrado"

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in headless mode (no browser window)
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1366, 736)
    return driver

def main(municipio):
    driver = setup_driver()
    wait = WebDriverWait(driver, 30)
    try:
        driver.get("https://sismac.saude.gov.br/teto_financeiro_detalhado")
        logger.info('Baixando Evolução do Teto MAC...')

        # Esperar até que o link "Município" esteja clicável
        logger.info("Waiting for 'Município' link...")
        municipio_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Município")))
        municipio_link.click()
        logger.info("'Município' link clicked!")

        # Re-locate the element after each interaction
        for _ in range(4):
            filtro_input = wait.until(EC.element_to_be_clickable((By.ID, "filtroPesquisaMunicipio_input")))
            if _ == 0:
                filtro_input.click()
                filtro_input.send_keys(municipio)  # Usando o município informado
            time.sleep(1)
            filtro_input.send_keys(Keys.ENTER)
            time.sleep(1)

        # Wait for the table to be fully loaded AFTER dropdown interaction
        logger.info("Waiting for table to load...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table[role='grid']")))
        logger.info("Table loaded!")

        time.sleep(1)  # Wait for 1 second after table loading

        # Extrair dados da tabela
        data = {}
        try:
            # Localizar a tabela
            table = driver.find_element(By.CSS_SELECTOR, "table[role='grid']")
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")

            if not rows:
                logger.warning("No rows found in the table.")
                return
            else:
                logger.info(f"Found {len(rows)} rows.")

            # Extrair os dados de cada linha
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) == 2:  # Verificar se a linha tem duas colunas
                    categoria_raw = cols[0].text.strip()  # Categoria (Sem Incentivos, Incentivos, Teto MAC)
                    valor_texto = cols[1].text.strip().replace(".", "").replace(",", ".")  # Valor
                    if valor_texto:  # Ignorar valores vazios
                        try:
                            valor = float(valor_texto)
                            # Mapear a categoria caso necessário
                            categoria = category_mapping.get(categoria_raw, categoria_raw)
                            data[categoria] = valor
                        except ValueError:
                            logger.warning(f"Valor inválido para {categoria_raw}: '{valor_texto}'")
            logger.info("Table data extracted.")
        except Exception as e:
            logger.error(f"Erro ao extrair dados da tabela: {e}")
            return

        # Carregar o JSON existente
        try:
            with open('evolucao_mac.json', 'r', encoding='utf-8') as file:
                json_data = json.load(file)
        except FileNotFoundError:
            logger.error("Arquivo evolucao_mac.json não encontrado.")
            return

        # Obter o ano atual
        ano_atual = str(datetime.now().year)

        # Atualizar o JSON com os novos dados
        for categoria_json in json_data:
            chave_categoria = list(categoria_json.keys())[0]  # Extrair a chave da categoria
            if chave_categoria in data:
                categoria_json[chave_categoria][ano_atual] = str(data[chave_categoria])
                logger.info(f"Adicionado {ano_atual} para {chave_categoria}: {data[chave_categoria]}")
            else:
                logger.warning(f"Categoria '{chave_categoria}' não encontrada nos dados extraídos.")

        # Salvar o JSON atualizado
        with open('evolucao_mac.json', 'w', encoding='utf-8') as file:
            json.dump(json_data, file, ensure_ascii=False, indent=4)
        logger.info("JSON atualizado e salvo com sucesso.")

    except (TimeoutException, StaleElementReferenceException) as e:
        logger.error(f"An error occurred: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("Uso: python script.py <código_IBGE>")
        sys.exit(1)

    municipio_ibge = sys.argv[1]
    municipio = obter_nome_municipio(municipio_ibge)
    if municipio != "Código IBGE não encontrado":
        main(municipio)
    else:
        logger.error("Código IBGE não encontrado.")