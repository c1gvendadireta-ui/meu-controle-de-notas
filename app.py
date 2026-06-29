import streamlit as st
import gspread
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# URL exata cadastrada no Console
REDIRECT_URL = "https://meu-controle-de-notas-reyhlqux3cv4vlwz5qpxjx.streamlit.app"

st.title("Controle de Notas")

# Gerenciamento da Sessão
if "creds" not in st.session_state:
    query_params = st.query_params
    
    # 1. Se retornou o código do Google
    if "code" in query_params:
        code = query_params["code"]
        
        # Faz o POST manual para trocar o código pelo token (evita o erro de PKCE)
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": st.secrets["GOOGLE"]["client_id"],
            "client_secret": st.secrets["GOOGLE"]["client_secret"],
            "redirect_uri": REDIRECT_URL,
            "grant_type": "authorization_code"
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            st.session_state.creds = response.json()
            st.query_params.clear()
            st.rerun()
        else:
            st.error(f"Erro ao obter token: {response.text}")
            if st.button("Tentar Novamente"):
                st.query_params.clear()
                st.rerun()
    
    # 2. Link de Login
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={st.secrets['GOOGLE']['client_id']}&"
        f"redirect_uri={REDIRECT_URL}&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/spreadsheets&"
        f"access_type=offline&prompt=consent"
    )
    st.markdown(f"### [CLIQUE AQUI PARA FAZER LOGIN NO GOOGLE]({auth_url})")

else:
    # 3. Área Logada
    # Criamos as credenciais a partir do token salvo
    from google.oauth2.credentials import Credentials
    creds = Credentials(token=st.session_state.creds["access_token"])
    
    drive_service = build('drive', 'v3', credentials=creds)
    gc = gspread.authorize(creds)

    st.success("Autenticado!")
    
    id_despesa = st.text_input("ID da Despesa")
    valor = st.number_input("Valor", min_value=0.0, format="%.2f")
    data = st.date_input("Data")
    estabelecimento = st.text_input("Estabelecimento")
    foto = st.camera_input("Tirar Foto")

    if st.button("Enviar Nota"):
        if foto and id_despesa:
            file_metadata = {'name': f"{id_despesa}.jpg"}
            media = MediaIoBaseUpload(io.BytesIO(foto.getvalue()), mimetype='image/jpeg')
            file = drive_service.files().create(body=file_metadata, media_body=media).execute()
            
            sheet = gc.open("Controle de notas APP").sheet1
            sheet.append_row([id_despesa, str(data), valor, estabelecimento, file.get('id')])
            st.success("Nota salva!")
            
    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()