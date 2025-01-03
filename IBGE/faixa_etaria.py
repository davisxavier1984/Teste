import sidrapy
import pandas as pd
import json
import sys

class Faixa:
    def __init__(self, municipio_ibge):
        self.MUNICIPIO = municipio_ibge  # Código IBGE do município como atributo da classe
        self.dados_municipio = {
            self.MUNICIPIO: {}
        }

    # Lista de faixas etárias e códigos correspondentes
    faixas_etarias = [
        "Menos de 1 ano", "0 a 4 anos", "5 a 9 anos", "10 a 14 anos",
        "15 a 19 anos", "20 a 24 anos", "25 a 29 anos", "30 a 34 anos",
        "35 a 39 anos", "40 a 44 anos", "45 a 49 anos", "50 a 54 anos",
        "55 a 59 anos", "60 a 64 anos", "65 a 69 anos", "70 a 74 anos",
        "75 a 79 anos", "80 a 84 anos", "85 a 89 anos", "90 a 94 anos",
        "95 a 99 anos", "100 anos ou mais"
    ]

    codigos_faixas_etarias = {
        "Menos de 1 ano": "6557",
        "0 a 4 anos": "93070",
        "5 a 9 anos": "93084",
        "10 a 14 anos": "93085",
        "15 a 19 anos": "93086",
        "20 a 24 anos": "93087",
        "25 a 29 anos": "93088",
        "30 a 34 anos": "93089",
        "35 a 39 anos": "93090",
        "40 a 44 anos": "93091",
        "45 a 49 anos": "93092",
        "50 a 54 anos": "93093",
        "55 a 59 anos": "93094",
        "60 a 64 anos": "93095",
        "65 a 69 anos": "93096",
        "70 a 74 anos": "93097",
        "75 a 79 anos": "93098",
        "80 a 84 anos": "49108",
        "85 a 89 anos": "49109",
        "90 a 94 anos": "60040",
        "95 a 99 anos": "60041",
        "100 anos ou mais": "6653"
    }

    # DataFrame vazio para armazenar os resultados
    tabela_completa = pd.DataFrame()

    def run(self):
        # Fazer a requisição para cada faixa etária
        for faixa_etaria in self.faixas_etarias:
            codigo = self.codigos_faixas_etarias[faixa_etaria]
            print(f"Requisitando dados para: {faixa_etaria} (código {codigo})...")

            try:
                data = sidrapy.get_table(
                    table_code="9514",
                    territorial_level="6",
                    ibge_territorial_code=self.MUNICIPIO,  # Código do município
                    period="2022",
                    variable="93",
                    classifications={
                        "2": "4,5",  # Homens e Mulheres
                        "287": codigo,  # Código da faixa etária
                    },
                )

                # Remover a primeira linha (cabeçalho)
                data = data.drop(0)

                # Converter a coluna 'V' para numérico
                data["V"] = pd.to_numeric(data["V"], errors="coerce")

                # Verificar os dados extraídos
                print(data.head())

                # Criar uma tabela pivô para reorganizar os dados
                tabela_pivot = data.pivot_table(
                    values="V", index="D3N", columns="D4N", aggfunc="sum"
                )

                # Preencher NaN com 0 e lidar com o FutureWarning
                tabela_pivot = tabela_pivot.fillna(0).infer_objects(copy=False)

                # Converter valores para inteiros
                tabela_pivot = tabela_pivot.astype("Int64")

                # Adicionar uma coluna de total
                tabela_pivot["Total"] = tabela_pivot.sum(axis=1)

                # Adicionar a coluna 'Faixa Etária'
                tabela_pivot['Faixa Etária'] = faixa_etaria

                # Concatenar a tabela da faixa etária atual com a tabela completa
                self.tabela_completa = pd.concat([self.tabela_completa, tabela_pivot])

                print(f"Dados para {faixa_etaria} adicionados à tabela completa.")

            except Exception as e:
                print(f"Erro ao requisitar dados para {faixa_etaria}: {e}")

        # Redefinir o índice da tabela completa
        self.tabela_completa = self.tabela_completa.reset_index(drop=True)

        # Definir a coluna 'Faixa Etária' como o novo índice
        self.tabela_completa = self.tabela_completa.set_index('Faixa Etária')

        # Reordenar as linhas para a ordem correta das faixas etárias
        self.tabela_completa = self.tabela_completa.reindex(self.faixas_etarias)

        # Salvar a tabela completa em formato JSON
        self.tabela_completa.to_json("tabela_populacao_completa.json", orient="index", indent=4)

        print("Tabela completa salva em tabela_populacao_completa.json")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        municipio_ibge = sys.argv[1]
        script = Faixa(municipio_ibge)
        script.run()
    else:
        print("Uso: python faixa_etaria.py <codigo_ibge_municipio>")
