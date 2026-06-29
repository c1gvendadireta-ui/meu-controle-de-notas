import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# Configuração da API Google
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

# Inicialização
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

st.title("Controle de Notas")

id_despesa = st.text_input("ID da Despesa")
valor = st.number_input("Valor", min_value=0.0, format="%.2f")
data = st.date_input("Data")
estabelecimento = st.text_input("Estabelecimento")
categoria = st.selectbox("Categoria", ["Refeição", "Lanche", "Outros"])
foto = st.camera_input("Tirar Foto da Nota")

if st.button("Enviar Nota"):
    if foto and id_despesa and estabelecimento:
        try:
            FOLDER_ID = "1hjgjPItmUnuWyP4htMEk91tJS2XICSGj"
            nome_arquivo = f"{data}_{valor}_{estabelecimento}.jpg".replace(" ", "_")
            
            # Upload para o Drive
            file_metadata = {'name': nome_arquivo, 'parents': [FOLDER_ID]}
            media = MediaIoBaseUpload(io.BytesIO(foto.getvalue()), mimetype='image/jpeg', resumable=True)
            drive_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            
            # Adicionar à planilha
            sheet = gc.open("Controle de notas APP").sheet1
            sheet.append_row([id_despesa, str(data), valor, estabelecimento, categoria, drive_file.get('id')])
            
            st.success(f"Nota {id_despesa} enviada com sucesso!")
        except Exception as e:
            st.error(f"Erro ao conectar com o Google: {e}")
    else:
        st.error("Preencha todos os campos e tire a foto.")