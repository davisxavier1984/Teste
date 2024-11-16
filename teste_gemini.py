import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os

st.title('Análise de Documentos')

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Acessar a chave da API
api_key = os.getenv("API_KEY")

# Configurar a chave da API
genai.configure(api_key=api_key)

# Inicializar o modelo
model = genai.GenerativeModel("gemini-1.5-flash")

# Fazer upload do(s) documento(s)
documentos = st.file_uploader('Selecione o(s) documento(s) a analisar', accept_multiple_files=True)

# Lista para armazenar os PDFs carregados
uploaded_pdfs = []

if documentos:
    for docs in documentos:
        # Especificar o tipo MIME para PDF
        sample_pdf = genai.upload_file(docs, mime_type='application/pdf')
        uploaded_pdfs.append(sample_pdf)

    # Pergunta
    userquestion = st.text_input('Digite o que deseja saber:')

    if userquestion and uploaded_pdfs:
        # Gerar o conteúdo a partir do PDF
        response = model.generate_content([userquestion] + uploaded_pdfs)
        
        # Exibir a resposta
        st.write('Resposta:')
        st.write(response.text)
