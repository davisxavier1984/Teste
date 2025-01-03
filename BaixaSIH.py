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

# Configuração básica do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sih.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Sih:
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

    def capture_table_data(self, table_xpath):
        # Esperar a tabela carregar explicitamente usando Selenium
        logger.info("Esperando pela tabela na nova guia...")
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.XPATH, table_xpath))
        )

        logger.info("Capturando dados da tabela com Selenium...")

        # Encontrar a tabela usando o XPATH
        table = self.driver.find_element(By.XPATH, table_xpath)

        # Extrair cabeçalhos
        headers = []
        header_row = table.find_element(By.XPATH, "./thead/tr[2]")  # Seleciona a segunda linha do thead
        header_cells = header_row.find_elements(By.XPATH, "./th")
        for cell in header_cells:
            headers.append(cell.text.strip())
        logger.info(f"Headers: {headers}")

        # Extrair dados do corpo da tabela
        table_data = []

        # Iterar pelas linhas da tabela, incluindo tbody e tfoot
        for row in table.find_elements(By.XPATH, "./tbody/tr | ./tfoot/tr"):
            logger.debug(f"--- Processando linha: {row.get_attribute('outerHTML')}")

            cells = row.find_elements(By.XPATH, "./td")
            logger.debug(f"  Celulas encontradas: {len(cells)}")

            row_data = {}

            # Verificar se a linha é a linha TOTAL (contém "TOTAL" na primeira célula)
            if cells and "TOTAL" in cells[0].text.upper():
                logger.debug("  Processando linha TOTAL. Esta linha será ignorada.")
                continue  # Pula para a próxima iteração do loop, ignorando a linha TOTAL

            # Ignorar linhas 'separador' e 'rodape'
            elif 'separador' in row.get_attribute('class') or 'rodape' in row.get_attribute('class'):
                logger.debug("  Linha 'separador' ou 'rodape' encontrada. Ignorando.")
                continue

            elif len(cells) == len(headers):
                logger.debug("  Processando linha de dados normal.")
                # Primeira célula: Grupo procedimento
                row_data[headers[0]] = cells[0].text.strip()
                logger.debug(f"    Grupo procedimento: {row_data[headers[0]]}")

                # Iterar pelas outras células, começando da segunda (índice 1)
                for i, cell in enumerate(cells[1:]):
                    # Verificar se o índice é válido
                    if i + 1 < len(headers):
                        # Extrair valor numérico
                        valor = self.parse_value(cell.text.strip())
                        row_data[headers[i + 1]] = valor
                        logger.debug(f"    Valor {headers[i + 1]}: {valor}")

            # Adicionar a linha aos dados da tabela apenas se row_data não estiver vazio
            if row_data:
                logger.debug(f"  Dados da linha: {row_data}")
                table_data.append(row_data)

        logger.info("Dados da tabela capturados.")
        return table_data

    def parse_value(self, value):
        value = re.sub(r'[^\d,.-]', '', value)  # Remove caracteres não numéricos
        value = value.replace('.', '')  # Remove pontos
        value = value.replace(',', '.')  # Substitui vírgulas por pontos
        try:
            return float(value)
        except ValueError:
            return value

    def get_url_by_uf(self, uf):
        base_url = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/"
        uf_map = {
            "12": "qiac.def",  # Acre
            "27": "qial.def",  # Alagoas
            "16": "qiap.def",  # Amapá
            "13": "qiam.def",  # Amazonas
            "29": "qiba.def",  # Bahia
            "23": "qice.def",  # Ceará
            "53": "qidf.def",  # Distrito Federal
            "32": "qies.def",  # Espírito Santo
            "52": "qigo.def",  # Goiás
            "21": "qima.def",  # Maranhão
            "51": "qimt.def",  # Mato Grosso
            "50": "qims.def",  # Mato Grosso do Sul
            "31": "qimg.def",  # Minas Gerais
            "15": "qipa.def",  # Pará
            "25": "qipb.def",  # Paraíba
            "41": "qipr.def",  # Paraná
            "26": "qipe.def",  # Pernambuco
            "22": "qipi.def",  # Piauí
            "33": "qirj.def",  # Rio de Janeiro
            "24": "qirn.def",  # Rio Grande do Norte
            "43": "qirs.def",  # Rio Grande do Sul
            "11": "qiro.def",  # Rondônia
            "14": "qirr.def",  # Roraima
            "42": "qisc.def",  # Santa Catarina
            "35": "qisp.def",  # São Paulo
            "28": "qise.def",  # Sergipe
            "17": "qito.def"   # Tocantins
        }
        return base_url + uf_map.get(uf, "qipe.def")

    def run(self):
        url = self.get_url_by_uf(self.uf)
        prefix = url.split('/')[-1].split('.')[0]
        logger.info(f"Baixando SIH da UF {self.uf}...")
        self.driver.get(url)
        self.driver.set_window_size(1366, 736)

        logger.info("Selecionando 'Grupo procedimento'...")
        dropdown_L = self.driver.find_element(By.ID, "L")
        Select(dropdown_L).select_by_visible_text("Grupo procedimento")

        logger.info("Selecionando 'Ano processamento'...")
        dropdown_C = self.driver.find_element(By.ID, "C")
        Select(dropdown_C).select_by_visible_text("Ano processamento")

        logger.info("Selecionando múltiplos itens no dropdown 'Arquivos'...")
        select_element = self.driver.find_element(By.ID, "A")
        select = Select(select_element)

        # Desselecionar todas as opções antes de selecionar as desejadas
        select.deselect_all()

        for year in range(self.start_year, self.end_year + 1):
            start_month = self.start_month if year == self.start_year else 1
            end_month = self.end_month if year == self.end_year else 12
            year_suffix = str(year)[-2:] # Pega os dois últimos dígitos do ano
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
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.XPATH, f"//option[contains(text(), '{self.municipio_ibge}')]"))
        )

        logger.info("Contando a posição do município...")
        municipio_options = dropdown_S1.find_elements(By.TAG_NAME, "option")
        municipio_position = None
        for index, option in enumerate(municipio_options):
            logger.debug(f"Opção {index}: {option.text}")
            if f'{self.municipio_ibge}' in option.text:
                municipio_position = index
                break

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
        WebDriverWait(self.driver, 10).until(EC.number_of_windows_to_be(2))

        # Alterna para a nova guia
        self.driver.switch_to.window(self.driver.window_handles[-1])

        table_xpath = "//table[@class='tabdados']"
        table_data = self.capture_table_data(table_xpath)
        logger.info("Dados da tabela capturados:")
        logger.info(table_data)

        logger.info("Salvando os dados em arquivo JSON...")
        with open('SIH.json', 'w') as json_file:
            json.dump(table_data, json_file, ensure_ascii=False, indent=4)

        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])

        logger.info("Fechando todas as janelas restantes...")
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            self.driver.close()

        logger.info("Processo concluído.")

# Instanciar e executar a classe com intervalo
if __name__ == "__main__":
    start_year = int(sys.argv[1])
    start_month = int(sys.argv[2])
    end_year = int(sys.argv[3])
    end_month = int(sys.argv[4])
    municipio_ibge = sys.argv[5]
    if len(municipio_ibge) == 7: municipio_ibge = municipio_ibge[:-1]
    script = Sih(start_year, start_month, end_year, end_month, municipio_ibge)
    script.run()