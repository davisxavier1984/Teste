import sys
import time
import pandas as pd
import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# Configuração básica do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mac_uf.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')  # Use the newer headless argument
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')  # Emulate device metrics
    options.add_argument('--remote-debugging-port=9222')  # Enable DevTools
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1366, 736)
    logger.info("Driver configurado.")
    return driver

def extract_table_data(driver, wait, headers):
    logger.info("Aguardando carregamento das linhas da tabela...")
    try:
        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//tbody[@id='tetoFinanceiroBrasil_data']/tr")))
    except TimeoutException:
        logger.warning("Timeout ao esperar pelas linhas da tabela. Tentando novamente com maior tempo de espera...")
        time.sleep(5)  # Espera adicional antes de tentar novamente
        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//tbody[@id='tetoFinanceiroBrasil_data']/tr")))
    
    rows = driver.find_elements(By.XPATH, "//tbody[@id='tetoFinanceiroBrasil_data']/tr")
    logger.info(f"{len(rows)} linhas encontradas na tabela.")
    data = []
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) == len(headers):  # Match header length
            data.append([col.text for col in cols])
    logger.info("Dados da tabela extraídos.")
    return data

def save_to_json(data, headers):
    df = pd.DataFrame(data, columns=headers)
    reformatted_data = []
    for _, row in df.iterrows():
        reformatted_data.append({
            "Região": row['Região'],
            "Sigla UF": row['Sigla UF'],
            "Código IBGE": row['Código IBGE'],
            "Estado / Município": row['Estado / Município'],
            "Código Gestão": row['Código Gestão'],
            "Descrição Gestão": row['Descrição Gestão'],
            "Teto Financeiro MAC - Valores Anuais (R$)": row['Teto Financeiro MAC - Valores Anuais (R$)'].replace(".", "").replace(",", ".")
        })
    with open('MAC_UF.json', 'w', encoding='utf-8') as file:
        json.dump(reformatted_data, file, ensure_ascii=False, indent=4)
    logger.info("Dados salvos no arquivo MAC_UF.json.")

# Dicionário para mapear os códigos dos estados brasileiros
uf_mapping = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
    "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
    "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
    "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
    "52": "GO", "53": "DF"
}

def get_uf_from_ibge(municipio_ibge):
    state_code = municipio_ibge[:2]
    return uf_mapping.get(state_code, "Código IBGE não encontrado")

def main(municipio_ibge):
    uf = get_uf_from_ibge(municipio_ibge)
    logger.info(f"Iniciando o processo para a UF: {uf}")
    
    driver = setup_driver()
    wait = WebDriverWait(driver, 30)

    try:
        # Navigate to the URL
        logger.info(f"Baixando Teto MAC do {uf}...")
        driver.get("https://sismac.saude.gov.br/teto_financeiro_brasil_por_estado_municipio")
        driver.set_window_size(1366, 736)
        
        # Explicit wait for the element to be present
        logger.info("Aguardando o campo de filtro de UF estar presente...")
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "tetoFinanceiroBrasil:siglaUF:filter"))
        )
        element.click()
        element.send_keys(uf)
        logger.info(f"UF {uf} inserida no campo de filtro.")
        
        # Espera para garantir que o campo seja atualizado
        time.sleep(3)
        
        # Wait for the dropdown and select the largest option
        logger.info("Aguardando o dropdown de seleção de quantidade de registros...")
        dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "tetoFinanceiroBrasil_rppDD"))
        )
        select = Select(dropdown)
        select.select_by_visible_text("6000")
        logger.info("Maior opção do dropdown selecionada.")
        
        # Espera para garantir que a tabela seja atualizada após selecionar o dropdown
        time.sleep(5)
        
        # Wait for the table to be present
        logger.info("Aguardando a tabela estar presente...")
        table = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//tbody[@id='tetoFinanceiroBrasil_data']"))
        )
        logger.info("Tabela encontrada.")

        # Verify if rows are present in the table
        rows = driver.find_elements(By.XPATH, "//tbody[@id='tetoFinanceiroBrasil_data']/tr")
        if not rows:
            logger.warning("Nenhuma linha encontrada na tabela.")
        else:
            logger.info(f"{len(rows)} linhas encontradas na tabela.")

        # Adjust headers to match desired data
        headers = [
            'Região', 
            'Sigla UF', 
            'Código IBGE', 
            'Estado / Município', 
            'Código Gestão', 
            'Descrição Gestão', 
            'Teto Financeiro MAC - Valores Anuais (R$)'
        ]
        logger.info("Cabeçalhos ajustados para corresponder aos dados desejados.")
        
        # Extract table data
        logger.info("Extraindo dados da tabela...")
        data = extract_table_data(driver, wait, headers)
        
        # Save to JSON
        logger.info("Salvando dados no arquivo JSON...")
        save_to_json(data, headers)
        
    except TimeoutException as e:
        logger.error(f"Timeout ocorreu: {e}")
    except NoSuchElementException as e:
        logger.error(f"Elemento não encontrado: {e}")
    except WebDriverException as e:
        logger.error(f"Erro no WebDriver: {e}")
    except Exception as e:
        logger.error(f"Ocorreu um erro: {e}")
    finally:
        driver.quit()
        logger.info("Driver encerrado.")

if __name__ == "__main__":
    municipio_ibge = sys.argv[1]
    main(municipio_ibge)