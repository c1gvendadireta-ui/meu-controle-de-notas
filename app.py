import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import io

# Configuração da API Google usando os segredos configurados no Streamlit
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
gc = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

st.title("Controle de Notas")

# Campos do formulário
id_despesa = st.text_input("ID da Despesa (ex: Café, Almoço)")
valor = st.number_input("Valor", min_value=0.0, format="%.2f")
data = st.date_input("Data")
estabelecimento = st.text_input("Estabelecimento")
categoria = st.selectbox("Categoria", ["Refeição", "Lanche", "Outros"])
foto = st.camera_input("Tirar Foto da Nota")

if st.button("Enviar Nota"):
    if foto and id_despesa and estabelecimento:
        # 1. Definir o nome do arquivo conforme sua regra
        nome_arquivo = f"{data}_{valor}_{estabelecimento}.jpg".replace(" ", "_")
        
        # 2. Salvar a foto no Drive (na raiz ou ID de pasta específico)
        file_metadata = {'name': nome_arquivo}
        media = io.BytesIO(foto.getvalue())
        drive_file = drive_service.files().create(body=file_metadata, media_body=media).execute()
        
        # 3. Adicionar linha na planilha "Controle de Notas"
        sheet = gc.open("Controle de Notas").sheet1
        sheet.append_row([id_despesa, str(data), valor, estabelecimento, categoria, drive_file['id']])
        
        st.success(f"Nota {id_despesa} enviada com sucesso!")
    else:
        st.error("Por favor, preencha todos os campos e tire a foto.")