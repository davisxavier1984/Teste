import glob
import os
import shutil

def combine_csv_files(folder_path, output_file):
    """
    Lê todos os arquivos CSV em uma pasta e os junta em um único arquivo CSV de saída,
    exatamente como estão.

    Args:
        folder_path: O caminho para a pasta que contém os arquivos CSV.
        output_file: O caminho para o arquivo CSV de saída.
    """

    all_files = sorted(glob.glob(os.path.join(folder_path, "*.csv")))

    with open(output_file, 'wb') as outfile:  # Abre o arquivo de saída em modo binário
        for i, filename in enumerate(all_files):
            try:
                with open(filename, 'rb') as infile:  # Abre o arquivo de entrada em modo binário
                    if i > 0:
                        # Tenta pular a primeira linha (cabeçalho) nos arquivos subsequentes
                        try:
                            next(infile)
                        except StopIteration:
                            print(f"Aviso: Arquivo vazio: {filename}")
                            continue
                    shutil.copyfileobj(infile, outfile)  # Copia o conteúdo do arquivo de entrada para o de saída

            except Exception as e:
                print(f"Erro ao processar o arquivo: {filename}")
                print(f"Erro específico: {e}")

    print(f"Arquivos CSV combinados com sucesso em '{output_file}'")

# Exemplo de uso
folder_path = "/home/davi/Python-Projetos/MAC/Rel Saude/SB/csv_procedimentos"
output_file = "arquivo_combinado_bruto.csv"

combine_csv_files(folder_path, output_file)