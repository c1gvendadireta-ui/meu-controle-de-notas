import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import base64
import io

# Configuração da API
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

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

st.title("Controle de Notas")

# Campos do formulário
id_despesa = st.text_input("ID da Despesa")
valor = st.number_input("Valor", min_value=0.0, format="%.2f")
data = st.date_input("Data")
estabelecimento = st.text_input("Estabelecimento")
categoria = st.selectbox("Categoria", ["Refeição", "Lanche", "Outros"])
foto = st.camera_input("Tirar Foto da Nota")

# Lógica de Envio
if st.button("Enviar Nota"):
    if foto and id_despesa and estabelecimento:
        try:
            # Converte a imagem em texto (Base64) para salvar na célula
            foto_bytes = foto.getvalue()
            foto_base64 = base64.b64encode(foto_bytes).decode('utf-8')
            
            # Abre a planilha pelo nome
            sheet = gc.open("Controle de notas APP").sheet1
            
            # Salva os dados na planilha
            sheet.append_row([
                id_despesa, 
                str(data), 
                valor, 
                estabelecimento, 
                categoria, 
                foto_base64
            ])
            
            st.success("Nota enviada com sucesso! Foto salva na planilha.")
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
    else:
        st.error("Preencha todos os campos e tire a foto.")

# Lógica de Download
st.divider()
if st.checkbox("Ver notas salvas para download"):
    try:
        sheet = gc.open("Controle de notas APP").sheet1
        data_rows = sheet.get_all_values()[1:]  # Pula o cabeçalho
        
        for row in data_rows:
            if len(row) >= 6:
                id_nota, data, valor, estab, cat, b64_foto = row
                st.write(f"Nota: {id_nota} - {estab} (R$ {valor})")
                
                # Decodifica e cria botão de download
                img_bytes = base64.b64decode(b64_foto)
                st.download_button(
                    label=f"Baixar {id_nota}_{data}.jpg",
                    data=img_bytes,
                    file_name=f"{id_nota}_{data}.jpg",
                    mime="image/jpeg"
                )
    except Exception as e:
        st.error(f"Erro ao carregar notas: {e}")