import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
import time

st.title('Análise de Documentos 📄🤖')

TIPOS_MIME_SUPORTADOS = {
    'application/pdf': 'PDF',
    'application/x-javascript': 'JavaScript',
    'text/javascript': 'JavaScript',
    'application/x-python': 'Python',
    'text/x-python': 'Python',
    'text/plain': 'TXT',
    'text/html': 'HTML',
    'text/css': 'CSS',
    'text/md': 'Markdown',
    'text/csv': 'CSV',
    'text/xml': 'XML',
    'text/rtf': 'RTF'
}

def init_session_state():
    """Inicializa os estados da sessão."""
    if 'historico_perguntas' not in st.session_state:
        st.session_state.historico_perguntas = []
    if 'pdfs_carregados' not in st.session_state:
        st.session_state.pdfs_carregados = []
    if 'documentos_carregados' not in st.session_state:
        st.session_state.documentos_carregados = False
    if 'perguntas_habilitadas' not in st.session_state:
        st.session_state.perguntas_habilitadas = False
    if 'nova_pergunta' not in st.session_state:
        st.session_state.nova_pergunta = ""

def reset_session():
    """Redefine o estado da sessão."""
    st.session_state.historico_perguntas = []
    st.session_state.pdfs_carregados = []
    st.session_state.documentos_carregados = False
    st.session_state.perguntas_habilitadas = False
    st.session_state.nova_pergunta = ""
    st.experimental_rerun()  # Recarrega a aplicação

def upload_documents(docs):
    """Realiza o upload de documentos válidos."""
    if not st.session_state.documentos_carregados:  # Apenas carregar se ainda não foram carregados
        progresso = st.progress(0)
        total_docs = len(docs)
        with st.spinner('Carregando documentos...'):
            for i, doc in enumerate(docs):
                if doc.type not in TIPOS_MIME_SUPORTADOS:
                    st.error(f"{doc.name} não é um tipo de arquivo suportado.")
                    continue  # Continue para o próximo documento
                try:
                    documento_carregado = genai.upload_file(doc, mime_type=doc.type)
                    st.session_state.pdfs_carregados.append(documento_carregado)
                    st.toast(f"Documento {doc.name} ({TIPOS_MIME_SUPORTADOS[doc.type]}) carregado com sucesso.", icon="✅")
                except Exception as e:
                    st.error(f"Erro ao carregar {doc.name}: {e}")
                progresso.progress((i + 1) / total_docs)
        progresso.empty()
        if st.session_state.pdfs_carregados:
            st.session_state.documentos_carregados = True
            st.session_state.perguntas_habilitadas = True

def delete_documents():
    """Exclui os documentos carregados usando a lista de arquivos."""
    try:
        arquivos = genai.list_files()
        if arquivos:
            with st.spinner('Excluindo documentos...'):
                for f in arquivos:
                    try:
                        genai.delete_file(f.name)
                    except Exception as e:
                        st.error(f"Erro ao excluir {f.name}: {e}")
                st.session_state.pdfs_carregados = []  # Limpar a lista de documentos carregados
                st.session_state.documentos_carregados = False
                st.session_state.perguntas_habilitadas = False
                st.toast('Documentos excluídos com sucesso!', icon="🗑️")
                time.sleep(2)
                
        else:
            st.warning('Nenhum documento para excluir.')
    except Exception as e:
        st.error(f"Erro ao listar documentos: {e}")

# Inicializar o estado da sessão
init_session_state()

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Acessar a chave da API
api_key = os.getenv("API_KEY")

# Configurar a chave da API
genai.configure(api_key=api_key)

# Inicializar o modelo
model = genai.GenerativeModel("gemini-1.5-flash")

# Botão para excluir os documentos carregados
if st.button('📝 Excluir Documentos'):
    delete_documents()

# Fazer upload do(s) documento(s)
documentos = st.file_uploader('Selecione o(s) documento(s) a analisar', accept_multiple_files=True)

if documentos and not st.session_state.documentos_carregados:
    upload_documents(documentos)

# Exibir histórico de perguntas e o campo de perguntas se os documentos foram carregados
if st.session_state.perguntas_habilitadas:
    # Frame para as respostas
    resposta_container = st.container()
    with resposta_container:
        for i, chat in enumerate(st.session_state.historico_perguntas):
            st.markdown(f"**Pergunta {i + 1}:** {chat['pergunta']}", unsafe_allow_html=True)
            st.markdown(f"**Resposta {i + 1}:** {chat['resposta']}", unsafe_allow_html=True)

    # Campo de perguntas multilinhas abaixo das respostas
    userquestion = st.text_area('Digite sua pergunta aqui:', value=st.session_state.nova_pergunta, height=100, key='nova_pergunta_usuario')

    if st.button('Enviar'):
        if userquestion and st.session_state.pdfs_carregados:
            with st.spinner('Gerando resposta...'):
                try:
                    # Gerar o conteúdo a partir dos PDFs e do histórico de perguntas
                    prompt = f"Responda a seguinte pergunta no idioma dos documentos enviados: {userquestion}"
                    
                    # Incluir histórico de perguntas e respostas
                    historico_prompt = "\n".join([f"Pergunta: {item['pergunta']}\nResposta: {item['resposta']}" for item in st.session_state.historico_perguntas])
                    completo_prompt = f"{historico_prompt}\n{prompt}" if historico_prompt else prompt
                    
                    response = model.generate_content([completo_prompt] + st.session_state.pdfs_carregados)
                    answer = response.text
                    
                    # Adicionar ao histórico
                    st.session_state.historico_perguntas.append({"pergunta": userquestion, "resposta": answer})
                    
                    # Exibir a resposta dentro do container
                    with resposta_container:
                        st.write_stream(f"### Resposta {len(st.session_state.historico_perguntas)}:")
                        st.markdown(answer, unsafe_allow_html=True)

                    # Limpar o campo de pergunta
                    st.session_state.nova_pergunta = ""

                except Exception as e:
                    st.error(f"Ocorreu um erro ao gerar a resposta: {e}")
