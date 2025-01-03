import requests
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import json
import logging

# Configuração básica do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('executa_scripts.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def obter_municipios_por_uf(uf):
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
    response = requests.get(url)

    if response.status_code == 200:
        dados = response.json()
        municipios = [municipio['nome'] for municipio in dados]
        return municipios
    else:
        logger.error(f"Erro ao obter municípios para a UF {uf}. Código de status: {response.status_code}")
        return []

def obter_codigo_ibge(nome_municipio, uf):
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
    response = requests.get(url)

    if response.status_code == 200:
        dados = response.json()
        for municipio in dados:
            if municipio['nome'].lower() == nome_municipio.lower():
                return municipio['id']
        logger.warning(f"Município {nome_municipio} não encontrado na UF {uf}.")
        return None
    else:
        logger.error(f"Erro ao obter código IBGE para o município {nome_municipio}. Código de status: {response.status_code}")
        return None

def atualizar_municipios(event):
    uf = combo_uf.get()
    logger.info(f"Atualizando municípios para a UF {uf}...")
    municipios = obter_municipios_por_uf(uf)
    combo_municipio['values'] = municipios
    combo_municipio.set('')  # Limpar o campo de municípios
    logger.debug(f"Municípios atualizados: {municipios}")

def run_script(script_name, *params):
    script_mapping = {
        "analise_teto_mac": "analise_teto_mac.py",
        "BaixaSIA": "BaixaSIA.py",
        "BaixaSIH": "BaixaSIH.py",
        "evolucao_mac": "evolucao_mac.py",
        "MacUF": "MacUF.py",
        "Econo": "/home/davi/Python-Projetos/MAC/IBGE/economia.py",
        "Faixa": "/home/davi/Python-Projetos/MAC/IBGE/faixa_etaria.py",
        "Resumo_PT": "/home/davi/Python-Projetos/MAC/res_pt.py",
        "Analise MAC": "/home/davi/Python-Projetos/MAC/txt_analise_mac.py",
        "Analise MAC_SIH": "/home/davi/Python-Projetos/MAC/txt_analise_mac_sih.py",
        "Analise MAC_SIA": "/home/davi/Python-Projetos/MAC/txt_analise_mac_sia.py",
    }
    script_path = script_mapping.get(script_name)

    if script_path:
        try:
            # Convert params to strings
            params = [str(param) for param in params]
            logger.info(f"Executando script {script_name} com parâmetros: {params}")
            # Executa o script e direciona a saída para o terminal
            subprocess.run(["python", script_path, *params], check=True)
            logger.info(f"Script {script_name} executado com sucesso!")

        except subprocess.CalledProcessError as e:
            logger.error(f"Erro ao executar o script {script_name}.")
            logger.error(f"Código de retorno: {e.returncode}")
            if e.output:
                logger.error(f"Saída:\n{e.output.decode()}")
            if e.stderr:
                logger.error(f"Erro padrão:\n{e.stderr.decode()}")

    else:
        logger.error(f"Script {script_name} não encontrado.")

def executar_scripts():
    nome_municipio = combo_municipio.get()
    uf = combo_uf.get()
    logger.info(f"Iniciando execução de scripts para o município {nome_municipio}/{uf}...")
    codigo_ibge = obter_codigo_ibge(nome_municipio, uf)

    if not codigo_ibge:
        logger.error(f"Não foi possível encontrar o município {nome_municipio}/{uf}.")
        messagebox.showerror("Erro", f"Não foi possível encontrar o município {nome_municipio}/{uf}.")
        return

    # Obtendo range de anos da evolução do MAC
    with open('evolucao_mac.json', 'r', encoding='utf-8') as file:
        evolucao_mac_json = json.load(file)

    # Função para obter os parâmetros
    def obter_params(json_data):
        anos = set()
        for item in json_data:
            for key, value in item.items():
                anos.update(value.keys())

        start_year = min(anos)
        end_year = str(int(max(anos)) + 1)
        start_month = 1  # Janeiro
        end_month = 12   # Dezembro

        return [start_year, start_month, end_year, str(end_month)]

    # Executa todos os scripts
    run_script("evolucao_mac", str(codigo_ibge))
    # Obtendo os parâmetros do JSON
    params = [*obter_params(evolucao_mac_json), str(codigo_ibge)]
    logger.debug(f"Parâmetros obtidos: {params}")
    run_script("MacUF", str(codigo_ibge))
    run_script("analise_teto_mac", str(codigo_ibge))
    run_script("BaixaSIA", *params)
    run_script("BaixaSIH", *params)
    run_script("Faixa", str(codigo_ibge))
    run_script("Econo", str(codigo_ibge), nome_municipio)
    run_script("Resumo_PT")
    run_script("Analise MAC", nome_municipio)
    run_script("Analise MAC_SIH", nome_municipio)
    run_script("Analise MAC_SIA", nome_municipio)
    logger.info("Todos os scripts foram executados com sucesso!")
    messagebox.showinfo("Sucesso", "Todos os scripts foram executados com sucesso!")

# Lista de UFs
ufs = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]

# Criar a janela principal
root = tk.Tk()
root.title("Executa Scripts do Teto MAC")

# Label e combobox para a UF
label_uf = tk.Label(root, text="UF:")
label_uf.grid(row=0, column=0, padx=10, pady=10)
combo_uf = ttk.Combobox(root, values=ufs)
combo_uf.grid(row=0, column=1, padx=10, pady=10)
combo_uf.bind("<<ComboboxSelected>>", atualizar_municipios)
combo_uf.current(0)  # Selecionar o primeiro estado por padrão

# Label e combobox para o município
label_municipio = tk.Label(root, text="Nome do Município:")
label_municipio.grid(row=1, column=0, padx=10, pady=10)
combo_municipio = ttk.Combobox(root)
combo_municipio.grid(row=1, column=1, padx=10, pady=10)

# Botão para executar scripts
botao_executar = tk.Button(root, text="Executar Scripts", command=executar_scripts)
botao_executar.grid(row=6, column=0, columnspan=2, pady=20)

# Iniciar o loop da interface gráfica
root.mainloop()