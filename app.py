import streamlit as st
import gspread
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from google.oauth2.credentials import Credentials

REDIRECT_URL = "https://meu-controle-de-notas-reyhlqux3cv4vlwz5qpxjx.streamlit.app"

def get_flow_auth_url():
    return (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={st.secrets['GOOGLE']['client_id']}&"
        f"redirect_uri={REDIRECT_URL}&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/spreadsheets&"
        f"access_type=offline&prompt=consent"
    )

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
    st.markdown(f"### [CLIQUE AQUI PARA FAZER LOGIN]({get_flow_auth_url()})")
else:
    creds = Credentials(token=st.session_state.creds["access_token"])
    drive_service = build('drive', 'v3', credentials=creds)
    gc = gspread.authorize(creds)
    sheet = gc.open("Controle de notas APP").sheet1

    tab1, tab2 = st.tabs(["Nova Nota", "Visualizar/Apagar Notas"])

    with tab1:
        # Campo renomeado e com dica para o usuário
        id_despesa = st.text_input("ID da Despesa (jantar, almoço, café, refeição, etc)")
        valor = st.number_input("Valor", min_value=0.0, format="%.2f")
        data = st.date_input("Data")
        estabelecimento = st.text_input("Estabelecimento")
        
        foto = st.camera_input("Tirar Foto")
        if st.button("Enviar Nota"):
            if foto and id_despesa:
                nome_arquivo = f"{id_despesa}_{str(data)}_R${valor:.2f}.jpg"
                
                media = MediaIoBaseUpload(io.BytesIO(foto.getvalue()), mimetype='image/jpeg')
                file = drive_service.files().create(body={'name': nome_arquivo}, media_body=media).execute()
                
                # Planilha agora grava apenas 5 colunas (sem Categoria)
                sheet.append_row([id_despesa, str(data), valor, estabelecimento, file.get('id')])
                st.success(f"Nota salva como: {nome_arquivo}")

    with tab2:
        rows = sheet.get_all_records()
        if rows:
            lista_ids = [f"{r['ID']} - R$ {r['Valor']} ({r['Data']})" for r in rows]
            escolha = st.selectbox("Selecione a nota para visualizar:", lista_ids)
            idx = lista_ids.index(escolha)
            nota = rows[idx]

            st.write(f"**Estabelecimento:** {nota['Estabelecimento']}")
            
            file_id = nota['Link_Foto']
            try:
                img_data = drive_service.files().get_media(fileId=file_id).execute()
                st.image(img_data, caption="Nota Fiscal")
                st.download_button("Baixar Foto", data=img_data, file_name=f"{nota['ID']}_{nota['Data']}_R${nota['Valor']}.jpg", mime="image/jpeg")
            except Exception:
                st.error("Não foi possível carregar a imagem.")

            if st.button("APAGAR ESTA NOTA"):
                sheet.delete_rows(idx + 2)
                drive_service.files().delete(fileId=file_id).execute()
                st.success("Nota apagada!")
                st.rerun()
        else:
            st.write("Nenhuma nota encontrada.")

    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()