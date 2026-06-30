import streamlit as st
import gspread
import requests
import hashlib
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from google.oauth2.credentials import Credentials

# URL exata cadastrada no Console
REDIRECT_URL = "https://meu-controle-de-notas-reyhlqux3cv4vlwz5qpxjx.streamlit.app"

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_or_create_user_folder(drive_service, user_name):
    query = f"name = '{user_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = drive_service.files().list(q=query).execute().get('files', [])
    if results:
        return results[0]['id']
    else:
        folder_metadata = {'name': user_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = drive_service.files().create(body=folder_metadata).execute()
        return folder.get('id')

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

    if "logged_in_user" not in st.session_state:
        st.subheader("Acesso do Usuário")
        user_name = st.text_input("Seu Nome:")
        user_password = st.text_input("Sua Senha:", type="password")
        if st.button("Entrar"):
            users_data = sheet.get_all_records()
            user_hash = hash_pass(user_password)
            user_exists = next((r for r in users_data if r['Usuario'] == user_name), None)
            if user_exists:
                if user_exists['Senha_Hash'] == user_hash:
                    st.session_state.logged_in_user = user_name
                    st.rerun()
                else:
                    st.error("Senha incorreta!")
            else:
                sheet.append_row(["CADASTRO", "", 0, "", "", user_name, user_hash])
                st.session_state.logged_in_user = user_name
                st.success("Usuário cadastrado!")
                st.rerun()
    else:
        st.success(f"Bem-vindo, {st.session_state.logged_in_user}!")
        tab1, tab2 = st.tabs(["Nova Nota", "Visualizar/Apagar Notas"])
        with tab1:
            id_despesa = st.text_input("ID da Despesa (jantar, almoço, etc)")
            valor = st.number_input("Valor", min_value=0.0, format="%.2f")
            data = st.date_input("Data")
            estabelecimento = st.text_input("Estabelecimento")
            foto = st.camera_input("Tirar Foto")
            if st.button("Enviar Nota"):
                if foto and id_despesa:
                    folder_id = get_or_create_user_folder(drive_service, st.session_state.logged_in_user)
                    nome_arquivo = f"{id_despesa}_{str(data)}_R${valor:.2f}.jpg"
                    media = MediaIoBaseUpload(io.BytesIO(foto.getvalue()), mimetype='image/jpeg')
                    file = drive_service.files().create(body={'name': nome_arquivo, 'parents': [folder_id]}, media_body=media).execute()
                    sheet.append_row([id_despesa, str(data), valor, estabelecimento, file.get('id'), st.session_state.logged_in_user, ""])
                    st.success(f"Nota salva como: {nome_arquivo}")
        with tab2:
            rows = sheet.get_all_records()
            user_rows = [r for r in rows if r.get('Usuario') == st.session_state.logged_in_user]
            if user_rows:
                lista_ids = [f"{r['ID']} - R$ {r['Valor']} ({r['Data']})" for r in user_rows]
                escolha = st.selectbox("Selecione sua nota:", lista_ids)
                nota = next(r for r in user_rows if f"{r['ID']} - R$ {r['Valor']} ({r['Data']})" == escolha)
                st.write(f"**Estabelecimento:** {nota['Estabelecimento']}")
                file_id = nota['Link_Foto']
                try:
                    img_data = drive_service.files().get_media(fileId=file_id).execute()
                    st.image(img_data, caption="Nota Fiscal")
                    st.download_button("Baixar", data=img_data, file_name=f"{nota['ID']}_{nota['Data']}_R${nota['Valor']}.jpg", mime="image/jpeg")
                    if st.button("APAGAR ESTA NOTA"):
                        row_idx = rows.index(nota) + 2
                        sheet.delete_rows(row_idx)
                        drive_service.files().delete(fileId=file_id).execute()
                        st.success("Nota apagada!")
                        st.rerun()
                except Exception: st.error("Erro ao carregar imagem.")
            else: st.write("Nenhuma nota encontrada.")
        if st.button("Sair"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()