import streamlit as st
import gspread
import hashlib
import requests
import json
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÃO ---
IMGBB_API_KEY = "a35f9a3caa695c965c49b45522ce521d"
SPREADSHEET_ID = "1uKam-HuCEDBsF_8pNM1ICaPEX38Oz57rRZL8_O4ycaQ"

creds_dict = json.loads(st.secrets["SERVICE_ACCOUNT_JSON"])
creds = Credentials.from_service_account_info(creds_dict, scopes=[
    'https://www.googleapis.com/auth/spreadsheets'
])

gc = gspread.authorize(creds)
sh = gc.open_by_key(SPREADSHEET_ID)
sheet_usuarios = sh.worksheet("Usuarios")
sheet_notas = sh.worksheet("Notas")

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

def formatar_valor(v):
    try:
        return f"{float(v):.2f}"
    except:
        return str(v)

st.title("Controle de Notas")

st.markdown("""
    <style>
    [data-testid="stCameraInput"] {
        width: 100% !important;
    }
    </style>
""", unsafe_allow_html=True)

if "logged_in_user" not in st.session_state:
    st.subheader("Acesso ao Sistema")
    modo = st.radio("O que deseja fazer?", ["Entrar com minha conta", "Criar novo cadastro"])
    user_name = st.text_input("Nome:")
    user_password = st.text_input("Senha:", type="password")
    
    if modo == "Entrar com minha conta":
        if st.button("Entrar"):
            users_data = sheet_usuarios.get_all_records()
            user_hash = hash_pass(user_password)
            user_exists = next((r for r in users_data if r['Usuario'] == user_name), None)
            if user_exists and user_exists['Senha_Hash'] == user_hash:
                st.session_state.logged_in_user = user_name
                st.rerun()
            else: st.error("Nome ou senha incorretos!")
    else:
        if st.button("Finalizar Cadastro"):
            users_data = sheet_usuarios.get_all_records()
            user_exists = next((r for r in users_data if r['Usuario'] == user_name), None)
            if user_exists: st.error("Este nome já está cadastrado! Selecione 'Entrar' acima.")
            elif not user_password: st.warning("Digite uma senha.")
            else:
                sheet_usuarios.append_row([user_name, hash_pass(user_password)])
                st.session_state.logged_in_user = user_name
                st.success("Cadastro realizado!")
                st.rerun()
else:
    st.sidebar.markdown("### Sobre o App")
    st.sidebar.markdown("Desenvolvido por: [Raphael Dionisio](mailto:raphael.dionisio@technipfmc.com)")
    st.sidebar.markdown("---")
    st.sidebar.warning("""
    **Avisos Importantes:**
    * Este aplicativo é público, use-o com responsabilidade.
    * Não carregue informações confidenciais da empresa.
    * O desenvolvedor não se responsabiliza por perda de dados, uso indevido ou eventuais falhas do serviço.
    * Esse aplicativo deve ser usado como uma ferramenta de backup auxiliar para notas de despesas de viagem.
    """)
    
    st.success(f"Bem-vindo, {st.session_state.logged_in_user}!")
    tab1, tab2, tab3 = st.tabs(["Nova Nota", "Visualizar", "Lixeira"])
    
    with tab1:
        tipo_despesa = st.selectbox("Tipo de Despesa", ["Café", "Almoço", "Jantar", "Lanche", "Transporte", "Outros"])
        id_despesa = tipo_despesa if tipo_despesa != "Outros" else st.text_input("Especifique:")
        valor = st.number_input("Valor", min_value=0.0, format="%.2f")
        data = st.date_input("Data")
        estabelecimento = st.text_input("Estabelecimento")
        foto = st.camera_input("Tirar Foto da Nota")
        
        if st.button("Enviar Nota"):
            if foto and id_despesa:
                try:
                    valor_str = formatar_valor(valor)
                    # Nome formatado: DD-MM-YYYY_Valor_Tipo
                    nome_personalizado = f"{data.strftime('%d-%m-%Y')}_{valor_str}_{id_despesa}"
                    
                    response = requests.post(
                        "https://api.imgbb.com/1/upload",
                        params={"key": IMGBB_API_KEY, "name": nome_personalizado},
                        files={"image": foto.getvalue()}
                    )
                    url_foto = response.json()['data']['url']
                    
                    # Salva sem o apóstrofo
                    sheet_notas.append_row([id_despesa, data.strftime('%d/%m/%Y'), valor_str, estabelecimento, url_foto, st.session_state.logged_in_user, "Ativo"])
                    st.success("Nota salva!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
    
    with tab2:
        all_notes = sheet_notas.get_all_records()
        user_rows = [r for r in all_notes if r.get('Usuario') == st.session_state.logged_in_user and r.get('Status') == "Ativo"]
        if user_rows:
            # Exibe: Data - R$ Valor - ID
            escolha = st.selectbox("Selecione sua nota:", [f"{r['Data']} - R$ {r['Valor']} - {r['ID']}" for r in user_rows])
            nota = next(r for r in user_rows if f"{r['Data']} - R$ {r['Valor']} - {r['ID']}" == escolha)
            st.image(nota['Link_Foto'])
            
            img_data = requests.get(nota['Link_Foto']).content
            st.download_button("Baixar Foto", data=img_data, file_name=f"{nota['Data'].replace('/', '-')}_R${nota['Valor']}.jpg", mime="image/jpeg")
            
            if st.button("Mover para Lixeira"):
                sheet_notas.update_cell(all_notes.index(nota) + 2, 7, "Lixeira")
                st.rerun()
    
    with tab3:
        all_notes = sheet_notas.get_all_records()
        trash_rows = [r for r in all_notes if r.get('Usuario') == st.session_state.logged_in_user and r.get('Status') == "Lixeira"]
        if trash_rows:
            escolha_trash = st.selectbox("Notas na Lixeira:", [f"{r['Data']} - R$ {r['Valor']} - {r['ID']}" for r in trash_rows])
            nota_trash = next(r for r in trash_rows if f"{r['Data']} - R$ {r['Valor']} - {r['ID']}" == escolha_trash)
            st.image(nota_trash['Link_Foto'])
            
            if st.button("Restaurar"):
                sheet_notas.update_cell(all_notes.index(nota_trash) + 2, 7, "Ativo")
                st.rerun()
            if st.button("Excluir Definitivamente"):
                sheet_notas.delete_rows(all_notes.index(nota_trash) + 2)
                st.rerun()
                
    if st.button("Sair"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()