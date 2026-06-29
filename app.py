import streamlit as st
import gspread
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# Configuração do OAuth Flow
def get_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": st.secrets["GOOGLE"]["client_id"],
                "client_secret": st.secrets["GOOGLE"]["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [st.secrets["GOOGLE"]["redirect_uri"]],
            }
        },
        scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
    )

st.title("Controle de Notas (Web-Auth)")

# 1. Fluxo de Login
if "creds" not in st.session_state:
    flow = get_flow()
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    st.markdown(f"[**Clique aqui para fazer login no Google e autorizar o app**]({auth_url})")

    # Captura o código da URL
    query_params = st.query_params
    if "code" in query_params:
        flow.fetch_token(code=query_params["code"])
        st.session_state.creds = flow.credentials
        st.rerun()
else:
    # 2. App Logado
    creds = st.session_state.creds
    drive_service = build('drive', 'v3', credentials=creds)
    gc = gspread.authorize(creds)

    id_despesa = st.text_input("ID da Despesa")
    valor = st.number_input("Valor", min_value=0.0, format="%.2f")
    data = st.date_input("Data")
    estabelecimento = st.text_input("Estabelecimento")
    foto = st.camera_input("Tirar Foto")

    if st.button("Enviar Nota"):
        if foto and id_despesa:
            # Upload para o seu Drive pessoal
            file_metadata = {'name': f"{id_despesa}.jpg"}
            media = MediaIoBaseUpload(io.BytesIO(foto.getvalue()), mimetype='image/jpeg')
            
            # Salva na raiz do seu Drive (ou troque o ID da pasta se preferir)
            file = drive_service.files().create(body=file_metadata, media_body=media).execute()
            
            # Salva na planilha
            sheet = gc.open("Controle de notas APP").sheet1
            sheet.append_row([id_despesa, str(data), valor, estabelecimento, file.get('id')])
            
            st.success("Nota salva com sucesso no seu Drive!")