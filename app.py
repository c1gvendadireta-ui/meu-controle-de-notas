import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# Configuração da API Google lendo chaves individuais do Streamlit Secrets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = {
    "type": st.secrets["type"],
    "project_id": st.secrets["project_id"],
    "private_key_id": st.secrets["private_key_id"],
    "private_key": st.secrets["private_key"].replace("\\n", "\n"),
    "client_email": st.secrets["client_email"],
    "client_id": st.secrets["client_id"],
    "auth_uri": st.secrets["auth_uri"],
    "token_uri": st.secrets["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["client_x509_cert_url"]
}
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
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
        # 1. Definir o nome do arquivo
        nome_arquivo = f"{data}_{valor}_{estabelecimento}.jpg".replace(" ", "_")
        
        # 2. Salvar foto no Google Drive com MediaIoBaseUpload
        file_metadata = {'name': nome_arquivo}
        media = MediaIoBaseUpload(io.BytesIO(foto.getvalue()), mimetype='image/jpeg', resumable=True)
        drive_file = drive_service.files().create(body=file_metadata, media_body=media).execute()
        
        # 3. Adicionar linha na planilha "Controle de Notas"
        sheet = gc.open("Controle de Notas").sheet1
        sheet.append_row([id_despesa, str(data), valor, estabelecimento, categoria, drive_file['id']])
        
        st.success(f"Nota {id_despesa} enviada com sucesso!")
    else:
        st.error("Por favor, preencha todos os campos e tire a foto.")