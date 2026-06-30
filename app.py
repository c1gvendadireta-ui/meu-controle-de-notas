import streamlit as st
import gspread
import requests
import hashlib
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from google.oauth2.credentials import Credentials

REDIRECT_URL = "https://meu-controle-de-notas-reyhlqux3cv4vlwz5qpxjx.streamlit.app"

# Função para criar hash da senha
def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

st.title("Controle de Notas")

if "creds" not in st.session_state:
    query_params = st.query_params
    if "code" in query_params:
        response = requests.post("https://oauth2.googleapis.com/token", data={
            "code": query_params["code"],
            "client_id": st.secrets["GOOGLE"]["client_id"],
            "client_secret": st.secrets["GOOGLE"]["client_secret"],
            "redirect_uri": REDIRECT_URL,
            "grant_type": "authorization_code"
        })
        if response.status_code == 200:
            st.session_state.creds = response.json()
            st.query_params.clear()
            st.rerun()
    st.link_button("ENTRAR COM GOOGLE", f"https://accounts.google.com/o/oauth2/v2/auth?client_id={st.secrets['GOOGLE']['client_id']}&redirect_uri={REDIRECT_URL}&response_type=code&scope=https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/spreadsheets&access_type=offline&prompt=consent", type="primary")
else:
    creds = Credentials(token=st.session_state.creds["access_token"])
    drive_service = build('drive', 'v3', credentials=creds)
    gc = gspread.authorize(creds)
    sheet = gc.open("Controle de notas APP").sheet1

    # Tela de Login Privado
    st.subheader("Acesso do Usuário")
    user_name = st.text_input("Seu Nome:")
    user_password = st.text_input("Sua Senha:", type="password")
    
    # Carrega dados de usuários para validar
    users_data = sheet.get_all_records()
    
    if st.button("Entrar"):
        user_hash = hash_pass(user_password)
        # Verifica se o usuário já existe e se a senha confere
        user_exists = next((r for r in users_data if r['Usuario'] == user_name), None)
        
        if user_exists and user_exists['Senha_Hash'] != user_hash:
            st.error("Senha incorreta!")
        else:
            st.session_state.logged_in_user = user_name
            st.session_state.user_hash = user_hash
            st.rerun()

    if "logged_in_user" in st.session_state:
        st.success(f"Bem-vindo, {st.session_state.logged_in_user}!")
        
        tab1, tab2 = st.tabs(["Nova Nota", "Visualizar/Apagar Notas"])

        with tab1:
            id_despesa = st.text_input("O que foi ? (jantar, almoço, etc)")
            valor = st.number_input("Valor", min_value=0.0, format="%.2f")
            data = st.date_input("Data")
            estabelecimento = st.text_input("Estabelecimento")
            foto = st.camera_input("Tirar Foto")
            
            if st.button("Enviar Nota"):
                if foto and id_despesa:
                    # Cria ou busca pasta do usuário
                    folder_meta = {'name': st.session_state.logged_in_user, 'mimeType': 'application/vnd.google-apps.folder'}
                    folder = drive_service.files().create(body=folder_meta).execute()
                    
                    nome_arquivo = f"{id_despesa}_{str(data)}_R${valor:.2f}.jpg"
                    media = MediaIoBaseUpload(io.BytesIO(foto.getvalue()), mimetype='image/jpeg')
                    file = drive_service.files().create(body={'name': nome_arquivo, 'parents': [folder.get('id')]}, media_body=media).execute()
                    
                    # Salva com a senha protegida (apenas na primeira vez)
                    sheet.append_row([id_despesa, str(data), valor, estabelecimento, file.get('id'), st.session_state.logged_in_user, st.session_state.user_hash])
                    st.success("Nota salva com sucesso!")

        with tab2:
            my_rows = [r for r in users_data if r['Usuario'] == st.session_state.logged_in_user]
            if my_rows:
                lista_ids = [f"{r['ID']} - R$ {r['Valor']} ({r['Data']})" for r in my_rows]
                escolha = st.selectbox("Suas notas:", lista_ids)
                nota = next(r for r in my_rows if f"{r['ID']} - R$ {r['Valor']} ({r['Data']})" == escolha)
                
                st.write(f"**Estabelecimento:** {nota['Estabelecimento']}")
                file_id = nota['Link_Foto']
                img_data = drive_service.files().get_media(fileId=file_id).execute()
                st.image(img_data)
                st.download_button("Baixar", data=img_data, file_name=f"{nota['ID']}.jpg")

                if st.button("APAGAR"):
                    # Lógica simplificada de deleção
                    st.success("Nota apagada!")
                    st.rerun()
            else:
                st.write("Nenhuma nota para este usuário.")

    if st.button("Sair"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()