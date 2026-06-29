import streamlit as st
import gspread
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from google.oauth2.credentials import Credentials

REDIRECT_URL = "https://meu-controle-de-notas-reyhlqux3cv4vlwz5qpxjx.streamlit.app"

# Função para encontrar ou criar pasta do usuário no Drive
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

# [MANTENDO SUA AUTENTICAÇÃO ATUAL]
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

    # SELEÇÃO DO USUÁRIO
    user_name = st.text_input("Seu Nome (para organizar suas pastas):")
    
    if user_name:
        tab1, tab2 = st.tabs(["Nova Nota", "Visualizar/Apagar Notas"])

        with tab1:
            id_despesa = st.text_input("ID da Despesa (ex: jantar, almoço...)")
            valor = st.number_input("Valor", min_value=0.0, format="%.2f")
            data = st.date_input("Data")
            estabelecimento = st.text_input("Estabelecimento")
            foto = st.camera_input("Tirar Foto")
            
            if st.button("Enviar Nota"):
                if foto and id_despesa:
                    folder_id = get_or_create_user_folder(drive_service, user_name)
                    nome_arquivo = f"{id_despesa}_{str(data)}_R${valor:.2f}.jpg"
                    media = MediaIoBaseUpload(io.BytesIO(foto.getvalue()), mimetype='image/jpeg')
                    
                    # Salva dentro da pasta do usuário
                    file = drive_service.files().create(
                        body={'name': nome_arquivo, 'parents': [folder_id]}, 
                        media_body=media
                    ).execute()
                    
                    sheet.append_row([id_despesa, str(data), valor, estabelecimento, file.get('id'), user_name])
                    st.success(f"Nota salva na sua pasta!")

        with tab2:
            rows = sheet.get_all_records()
            # Filtra apenas o que pertence ao usuário logado
            user_rows = [r for r in rows if r.get('Usuario') == user_name]
            
            if user_rows:
                lista_ids = [f"{r['ID']} - R$ {r['Valor']} ({r['Data']})" for r in user_rows]
                escolha = st.selectbox("Selecione sua nota:", lista_ids)
                idx = [i for i, r in enumerate(rows) if f"{r['ID']} - R$ {r['Valor']} ({r['Data']})" == escolha][0]
                nota = rows[idx]

                st.write(f"**Estabelecimento:** {nota['Estabelecimento']}")
                file_id = nota['Link_Foto']
                try:
                    img_data = drive_service.files().get_media(fileId=file_id).execute()
                    st.image(img_data, caption="Nota Fiscal")
                    st.download_button("Baixar Foto", data=img_data, file_name=f"{nota['ID']}.jpg", mime="image/jpeg")
                except Exception:
                    st.error("Não foi possível carregar a imagem.")

                if st.button("APAGAR ESTA NOTA"):
                    sheet.delete_rows(idx + 2)
                    drive_service.files().delete(fileId=file_id).execute()
                    st.success("Nota apagada!")
                    st.rerun()
            else:
                st.write("Nenhuma nota encontrada para este usuário.")

    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()