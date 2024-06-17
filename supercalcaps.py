from selenium import webdriver
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service

service = Service()

options = webdriver.ChromeOptions()

driver = webdriver.Chrome(service=service, options=options)

driver.get("https://egestorab.saude.gov.br/gestaoaps/relFinanciamentoParcela.xhtml")

# Define a dictionary to store element IDs and data
campos = {
    "j_idt58:uf": "PE",
    "j_idt58:municipio": "RIBEIRÃO",
    "j_idt58:ano": "2024",
    "j_idt58:compInicio": "ABR/2024",
    "j_idt58:compFim": "ABR/2024",
}

# Loop through the dictionary to find and fill elements
for element_id, value in campos.items():
    element = driver.find_element(By.ID, element_id)
    element.send_keys(value)
    time.sleep(1)

element = driver.find_element(By.ID, "j_idt58:verResultado")
element.click()
