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
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# Configuração básica do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analise_teto_mac.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')  # Emulate device metrics
    options.add_argument('--remote-debugging-port=9222')  # Enable DevTools
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1366, 736)
    return driver

def extract_table_data(driver, wait, headers):
    wait.until(EC.presence_of_all_elements_located((By.XPATH, "//tbody[@id='tabelaAnaliseTetoFinanceiroDetalhadoMunicipio_data']/tr[@data-ri]")))
    rows = driver.find_elements(By.XPATH, "//tbody[@id='tabelaAnaliseTetoFinanceiroDetalhadoMunicipio_data']/tr[@data-ri]")
    data = []
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) == len(headers):
            data.append([col.text for col in cols])
    return data

def save_to_json(data, headers):
    df = pd.DataFrame(data, columns=headers)
    reformatted_data = []
    for _, row in df.iterrows():
        reformatted_data.append({
            "Portaria": row['Portaria'],
            "Data": row['Data'],
            "Tipo": row['Tipo'],
            "Incentivo": row['Incentivo'],
            "Área": row['Área'],
            "Competência": row['Competência'],
            "Valor": row['Valor'].replace(".", "").replace(",", ".")
        })
    with open('tabela_analise.json', 'w', encoding='utf-8') as file:
        json.dump(reformatted_data, file, ensure_ascii=False, indent=4)
    logger.info("Data saved to tabela_analise.json")

def retry_find_element(by, value, driver, wait, retries=3):
    for i in range(retries):
        try:
            return wait.until(EC.presence_of_element_located((by, value)))
        except StaleElementReferenceException:
            if i < retries - 1:
                time.sleep(1)
                continue
            else:
                raise

def retry_find_elements(by, value, driver, wait, retries=3):
    for i in range(retries):
        try:
            return wait.until(EC.presence_of_all_elements_located((by, value)))
        except StaleElementReferenceException:
            if i < retries - 1:
                time.sleep(1)
                continue
            else:
                raise

def main(municipio):
    logger.info(f'Baixando análise do Teto MAC de {municipio}...')
    driver = setup_driver()
    wait = WebDriverWait(driver, 30)

    try:
        driver.get("https://sismac.saude.gov.br/analise_teto_financeiro")
        logger.info("Acessando SISMAC...")
        logger.info(f'Baixando Portarias de {municipio}...')

        retry_find_element(By.ID, "analise_teto_financeiro", driver, wait).click()
        retry_find_element(By.LINK_TEXT, "Município", driver, wait).click()

        filtro_input = retry_find_element(By.ID, "filtroPesquisaMunicipio_input", driver, wait)
        time.sleep(1)
        filtro_input.send_keys(municipio, Keys.ENTER)
        time.sleep(1)
        filtro_input.send_keys(Keys.ENTER)
        time.sleep(2)
        filtro_input.send_keys(Keys.ENTER)
        logger.info(f"Município {municipio} selecionado.")

        rows = retry_find_elements(By.XPATH, "//tbody[@id='tabelaAnaliseTetoFinanceiroDetalhadoMunicipio_data']/tr", driver, wait)
        if rows:
            logger.info(f"{len(rows)} linhas encontradas na tabela.")
        else:
            logger.warning("Nenhuma linha encontrada. Verifique se a navegação e os filtros estão corretos.")

        try:
            dropdown = Select(retry_find_element(By.XPATH, "//select[contains(@id, 'rppDD')]", driver, wait))
            dropdown.select_by_visible_text("100")
            logger.info("Opção '100' selecionada no dropdown.")
        except TimeoutException:
            logger.warning("Dropdown não encontrado. Verifique a estrutura da tabela.")

        logger.info("Aguardando carregamento das linhas da tabela...")
        retry_find_elements(By.XPATH, "//tbody[@id='tabelaAnaliseTetoFinanceiroDetalhadoMunicipio_data']/tr[@data-ri]", driver, wait)
        logger.info("Linhas da tabela carregadas!")
        time.sleep(5)

        rows = retry_find_elements(By.XPATH, "//tbody[@id='tabelaAnaliseTetoFinanceiroDetalhadoMunicipio_data']/tr[@data-ri]", driver, wait)
        if not rows:
            logger.warning("Nenhuma linha encontrada na tabela.")
            return
        else:
            logger.info(f"{len(rows)} linhas encontradas.")

        headers = [
            'Portaria', 
            'Data', 
            'Tipo', 
            'Incentivo', 
            'Área', 
            'Competência', 
            'Valor'
        ]
        logger.debug("Cabeçalhos ajustados: %s", headers)

        data = []
        try:
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                row_data = [
                    cols[0].text,
                    cols[1].text,
                    cols[2].text,
                    cols[3].text,
                    cols[4].text,
                    cols[5].text,
                    cols[6].text
                ]
                data.append(row_data)
            logger.info("Dados da tabela extraídos.")
        except Exception as e:
            logger.error(f"Erro ao extrair dados da tabela: {e}")
            return

        logger.debug("Dados das linhas: %s", data)

        if headers and data:
            df = pd.DataFrame(data, columns=headers)
            logger.info("DataFrame criado:")
            logger.info(df)

            reformatted_data = []
            for index, row in df.iterrows():
                reformatted_data.append({
                    "Portaria": row['Portaria'],
                    "Data": row['Data'],
                    "Tipo": row['Tipo'],
                    "Incentivo": row['Incentivo'],
                    "Área": row['Área'],
                    "Competência": row['Competência'],
                    "Valor": row['Valor'].replace(".", "").replace(",", ".")
                })

            with open('tabela_analise.json', 'w', encoding='utf-8') as file:
                json.dump(reformatted_data, file, ensure_ascii=False, indent=4)
            logger.info("Dados salvos em tabela_analise.json")
        else:
            logger.warning("Nenhum dado extraído para criar o DataFrame.")

    except Exception as e:
        logger.error(f"Um erro ocorreu: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    municipio_ibge = sys.argv[1]
    if len(municipio_ibge) == 7: municipio_ibge = municipio_ibge[:-1]
    main(municipio_ibge)