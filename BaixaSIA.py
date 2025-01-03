import sys
import time
import json
import re
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configuração básica do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sia.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SIA:
    def __init__(self, start_year, start_month, end_year, end_month, municipio_ibge):
        self.start_year = start_year
        self.start_month = start_month
        self.end_year = end_year
        self.end_month = end_month
        self.municipio_ibge = municipio_ibge
        self.uf = municipio_ibge[:2]  # Código UF a partir do código IBGE

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.vars = {}

    def wait_for_window(self, timeout=2):
        time.sleep(timeout)
        wh_now = self.driver.window_handles
        wh_then = self.vars["window_handles"]
        if len(wh_now) > len(wh_then):
            return list(set(wh_now) - set(wh_then)).pop()

    def capture_table_data(self, table_xpath):
        logger.info("Esperando pela tabela...")
        try:
            WebDriverWait(self.driver, 120).until(
                EC.presence_of_element_located((By.XPATH, table_xpath))
            )
        except TimeoutException:
            logger.error("Tempo limite excedido para encontrar a tabela.")
            return []

        logger.info("Capturando dados da tabela...")
        table_body = self.driver.find_element(By.XPATH, table_xpath + "/tbody")
        headers = self.driver.find_elements(By.XPATH, table_xpath + "/thead/tr/th")
        rows = table_body.find_elements(By.TAG_NAME, "tr")

        logger.debug(f"Headers: {[header.text for header in headers]}")
        logger.debug(f"Número de linhas encontradas: {len(rows)}")

        headers_text = [header.text.strip() for header in headers]
        all_cells_data = []
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            cells_text = [cell.text.strip() if cell.text.strip() else '' for cell in cells]
            row_data = dict(zip(headers_text, cells_text))

            # FILTRAGEM PARA "Média complexidade" e "Alta complexidade" (Exatamente como escrito)
            complexidade = row_data.get("Complexidade", "").strip()  # Pega o valor, sem modificar
            if complexidade == "Média complexidade" or complexidade == "Alta complexidade":
                all_cells_data.append(row_data)
                logger.debug(f"Dados da linha (Média/Alta Complexidade): {row_data}")
            else:
                logger.debug(f"Dados da linha (Ignorada): {row_data}")

        logger.info("Dados da tabela capturados.")
        return all_cells_data

    def parse_value(self, value):
        value = re.sub(r'[^\d,.-]', '', value)
        value = value.replace('.', '')
        value = value.replace(',', '.')
        try:
            return float(value)
        except ValueError:
            return value

    def get_url_by_uf(self, uf):
        base_url = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sia/cnv/"
        uf_map = {
            "12": "qaac.def",  # Acre
            "27": "qaal.def",  # Alagoas
            "16": "qaap.def",  # Amapá
            "13": "qaam.def",  # Amazonas
            "29": "qaba.def",  # Bahia
            "23": "qace.def",  # Ceará
            "53": "qadf.def",  # Distrito Federal
            "32": "qaes.def",  # Espírito Santo
            "52": "qago.def",  # Goiás
            "21": "qama.def",  # Maranhão
            "51": "qamt.def",  # Mato Grosso
            "50": "qams.def",  # Mato Grosso do Sul
            "31": "qamg.def",  # Minas Gerais
            "15": "qapa.def",  # Pará
            "25": "qapb.def",  # Paraíba
            "41": "qapr.def",  # Paraná
            "26": "qape.def",  # Pernambuco
            "22": "qapi.def",  # Piauí
            "33": "qarj.def",  # Rio de Janeiro
            "24": "qarn.def",  # Rio Grande do Norte
            "43": "qars.def",  # Rio Grande do Sul
            "11": "qaro.def",  # Rondônia
            "14": "qarr.def",  # Roraima
            "42": "qasc.def",  # Santa Catarina
            "35": "qasp.def",  # São Paulo
            "28": "qase.def",  # Sergipe
            "17": "qato.def"   # Tocantins
        }
        # Agora todos os estados usam arquivos que começam com 'qa'
        return base_url + uf_map.get(uf, "qape.def")  # Mantém qape.def como padrão

    def run(self):
        url = self.get_url_by_uf(self.uf)
        logger.info(f"Baixando SIA da UF {self.uf}...")
        self.driver.get(url)
        self.driver.set_window_size(1366, 736)

        # Espera explícita para a página carregar e a div principal ficar visível
        try:
            WebDriverWait(self.driver, 30).until(
                EC.visibility_of_element_located((By.XPATH, "//div[@class='borda']"))
            )
        except TimeoutException:
            logger.error(f"Tempo limite excedido para carregar a página {url}.")
            self.driver.quit()
            return

        logger.info("Selecionando 'Complexidade'...")
        try:
            dropdown_L = self.driver.find_element(By.ID, "L")
            Select(dropdown_L).select_by_visible_text("Complexidade")
        except NoSuchElementException:
            logger.error("Elemento 'Complexidade' não encontrado.")
            self.driver.quit()
            return

        logger.info("Selecionando 'Ano processamento'...")
        try:
            dropdown_C = self.driver.find_element(By.ID, "C")
            Select(dropdown_C).select_by_visible_text("Ano processamento")
        except NoSuchElementException:
            logger.error("Elemento 'Ano processamento' não encontrado.")
            self.driver.quit()
            return

        logger.info("Selecionando múltiplos itens no dropdown 'Arquivos'...")
        select_element = self.driver.find_element(By.ID, "A")
        select = Select(select_element)

        # Desselecionar todas as opções antes de selecionar as desejadas
        select.deselect_all()

        for year in range(self.start_year, self.end_year + 1):
            start_month = self.start_month if year == self.start_year else 1
            end_month = self.end_month if year == self.end_year else 12
            year_suffix = str(year)[-2:]  # Pega os dois últimos dígitos do ano
            available_options = [option.get_attribute("value") for option in select.options if str(year)[-2:] in option.get_attribute("value")]
            prefixes_for_year = set([option[:4] for option in available_options])

            for prefix in prefixes_for_year:
                for month in range(start_month, end_month + 1):
                    value = f'{prefix}{year_suffix}{month:02d}.dbf'
                    if value in available_options:
                        try:
                            select.select_by_value(value)
                            logger.info(f'Selecionado: {value}')
                        except Exception as e:
                            logger.error(f'Não foi possível selecionar {value}: {e}')

        logger.info("Interagindo com outros elementos da página...")
        self.driver.find_element(By.ID, "fig1").click()
        dropdown_S1 = self.driver.find_element(By.ID, "S1")

        logger.info("Esperando opções do dropdown de município serem carregadas...")
        try:
            WebDriverWait(self.driver, 30).until(
                lambda driver: len(driver.find_elements(By.XPATH, f"//select[@id='S1']/option")) > 1 and
                               EC.visibility_of_all_elements_located((By.XPATH, f"//select[@id='S1']/option"))
            )
        except TimeoutException:
            logger.error(f"Tempo limite excedido para carregar as opções do município.")
            self.driver.quit()
            return

        logger.info("Contando a posição do município...")
        municipio_options = dropdown_S1.find_elements(By.TAG_NAME, "option")
        municipio_position = None
        for index, option in enumerate(municipio_options):
            logger.debug(f"Opção {index}: {option.text}")
            if f'{self.municipio_ibge}' in option.text:
                municipio_position = index
                break

        # Corrigindo a verificação para aceitar a posição 0
        if municipio_position is not None:
            logger.info(f"Selecionando o município na posição {municipio_position} usando JavaScript...")
            try:
                self.driver.execute_script(
                    "arguments[0].selectedIndex = arguments[1]; arguments[0].dispatchEvent(new Event('change'));",
                    dropdown_S1, municipio_position
                )
                logger.info("Município selecionado.")
            except Exception as e:
                logger.error(f"Erro ao selecionar o município: {e}")
        else:
            logger.error(f"Município com IBGE {self.municipio_ibge} não encontrado.")
            return

        logger.info("Iniciando extração de dados...")
        self.driver.find_element(By.NAME, "mostre").click()

        # Aguarda a nova guia ser aberta
        WebDriverWait(self.driver, 30).until(EC.number_of_windows_to_be(2))

        # Alterna para a nova guia
        self.driver.switch_to.window(self.driver.window_handles[-1])

        table_xpath = "//table[@class='tabdados']"
        table_data = self.capture_table_data(table_xpath)
        if table_data:
            logger.info("Dados da tabela capturados (apenas Média e Alta Complexidade):")
            logger.info(table_data)

            logger.info("Salvando os dados em arquivo JSON...")
            with open('SIA.json', 'w') as json_file:  # Corrigido para SIA.json
                json.dump(table_data, json_file, ensure_ascii=False, indent=4)

        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])

        logger.info("Fechando todas as janelas restantes...")
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            self.driver.close()

        logger.info("Processo concluído.")

if __name__ == "__main__":
    start_year = int(sys.argv[1])
    start_month = int(sys.argv[2])
    end_year = int(sys.argv[3])
    end_month = int(sys.argv[4])
    municipio_ibge = sys.argv[5]
    if len(municipio_ibge) == 7: municipio_ibge = municipio_ibge[:-1]
    script = SIA(start_year, start_month, end_year, end_month, municipio_ibge)
    script.run()