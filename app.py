import streamlit as st
import gspread
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from google.oauth2.credentials import Credentials

# URL exata cadastrada no Console
REDIRECT_URL = "https://meu-controle-de-notas-reyhlqux3cv4vlwz5qpxjx.streamlit.app"

st.title("Controle de Notas")

if "creds" not in st.session_state:
    query_params = st.query_params
    if "code" in query_params:
        code = query_params["code"]
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
    creds = Credentials(token=st.session_state.creds["access_token"])
    drive_service = build('drive', 'v3', credentials=creds)
    gc = gspread.authorize(creds)

    id_despesa = st.text_input("ID da Despesa")
    valor = st.number_input("Valor", min_value=0.0, format="%.2f")
    data = st.date_input("Data")
    estabelecimento = st.text_input("Estabelecimento")
    categoria = st.text_input("Categoria (Refeição/Lanche/Outros)")
    foto = st.camera_input("Tirar Foto")

    if st.button("Enviar Nota"):
        if foto and id_despesa:
            # 1. Upload da foto
            file_metadata = {'name': f"{id_despesa}.jpg"}
            media = MediaIoBaseUpload(io.BytesIO(foto.getvalue()), mimetype='image/jpeg')
            file = drive_service.files().create(body=file_metadata, media_body=media).execute()
            file_id = file.get('id')
            
            # 2. Salva na planilha (A=ID, B=Data, C=Valor, D=Estabelecimento, E=Categoria, F=Link_Foto)
            sheet = gc.open("Controle de notas APP").sheet1
            sheet.append_row([id_despesa, str(data), valor, estabelecimento, categoria, file_id])
            
            st.success(f"Nota salva com sucesso! ID da foto: {file_id}")
            
    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()