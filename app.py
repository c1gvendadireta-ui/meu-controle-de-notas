import streamlit as st
import gspread
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# URL exata cadastrada no Google Cloud Console
REDIRECT_URL = "https://meu-controle-de-notas-reyhlqux3cv4vlwz5qpxjx.streamlit.app"

def get_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": st.secrets["GOOGLE"]["client_id"],
                "client_secret": st.secrets["GOOGLE"]["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URL],
            }
        },
        scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets'],
        redirect_uri=REDIRECT_URL
    )

st.title("Controle de Notas")

# Gerenciamento da Sessão e Login
if "creds" not in st.session_state:
    query_params = st.query_params
    
    # Se o Google retornou o código de autorização
    if "code" in query_params:
        flow = get_flow()
        flow.fetch_token(code=query_params["code"])
        st.session_state.creds = flow.credentials
        
        # Remove o código da URL para evitar InvalidGrantError
        st.query_params.clear()
        st.rerun()
        
    else:
        # Exibe o botão de login se não estiver autenticado
        flow = get_flow()
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        st.markdown(f"[**Clique aqui para fazer login no Google e autorizar o app**]({auth_url})")
else:
    # App autenticado: processa uploads e planilhas
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
            # Upload da foto para o Drive
            file_metadata = {'name': f"{id_despesa}.jpg"}
            media = MediaIoBaseUpload(io.BytesIO(foto.getvalue()), mimetype='image/jpeg')
            file = drive_service.files().create(body=file_metadata, media_body=media).execute()
            
            # Adiciona dados na planilha
            sheet = gc.open("Controle de notas APP").sheet1
            sheet.append_row([id_despesa, str(data), valor, estabelecimento, file.get('id')])
            
            st.success("Nota salva no Drive com sucesso!")