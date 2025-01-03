import pandas as pd
import glob
import os

# Defina o caminho onde seus arquivos CSV estão armazenados
caminho_dos_arquivos = '/home/davi/Python-Projetos/MAC/Rel Saude/SB/csv_procedimentos/*.csv'

# Lista todos os arquivos na pasta
arquivos = glob.glob(caminho_dos_arquivos)

# Crie uma lista para armazenar os DataFrames
dataframes = []

# Função para tentar ler o CSV com diferentes encodings
def ler_csv_com_multiplos_encodings(caminho):
    try:
        return pd.read_csv(caminho, encoding='utf-8', skiprows=6, skipfooter=2, engine='python')
    except UnicodeDecodeError:
        try:
            return pd.read_csv(caminho, encoding='latin-1', skiprows=6, skipfooter=2, engine='python')
        except UnicodeDecodeError:
            print(f"Erro ao ler o arquivo: {os.path.basename(caminho)}")
            return None

# Função para filtrar as linhas que contêm números e pontos e vírgulas
def filtrar_linhas(df):
    return df[df.apply(lambda x: x.str.contains(r'\d+;\d+;\d+').any(), axis=1)]

# Itere sobre a lista de arquivos e leia cada um como um DataFrame
for arquivo in arquivos:
    df = ler_csv_com_multiplos_encodings(arquivo)
    if df is not None:
        df_filtered = filtrar_linhas(df)
        dataframes.append(df_filtered)

# Exemplo: concatenar todos os DataFrames em um único DataFrame
df_final = pd.concat(dataframes, ignore_index=True)

# Salvar o DataFrame final em um arquivo CSV
df_final.to_csv('/home/davi/Python-Projetos/MAC/Rel Saude/SB/dataframe_final.csv', index=False)

print("DataFrame final salvo em: /home/davi/Python-Projetos/MAC/Rel Saude/SB/dataframe_final.csv")
