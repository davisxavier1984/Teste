import pandas as pd

# Lê o arquivo CSV com encoding='latin-1'
df = pd.read_csv("arquivo_combinado_bruto.csv", encoding='latin-1')

# Guarda a primeira coluna
procedimentos = df["Procedimento sb"]

# Seleciona as colunas de meses e inverte a ordem
meses = df.columns[1:]
meses_invertidos = meses[::-1]

# Cria um novo DataFrame com as colunas na ordem desejada
df_reordenado = df[meses_invertidos]

# Adiciona a coluna de procedimentos de volta
df_reordenado.insert(0, "Procedimento sb", procedimentos)

# Salva o novo DataFrame em um novo arquivo CSV
df_reordenado.to_csv("arquivo_combinado_reordenado.csv", index=False)

print("Colunas reordenadas e salvas em 'arquivo_combinado_reordenado.csv'")