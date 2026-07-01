import streamlit as st
import gspread
import hashlib
import requests
import json
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
        id_despesa = tipo_despesa
        if tipo_despesa == "Outros":
            id_despesa = st.text_input("Especifique a despesa:")
            
        valor = st.number_input("Valor", min_value=0.0, format="%.2f")
        data = st.date_input("Data")
        estabelecimento = st.text_input("Estabelecimento")
        foto = st.camera_input("Tirar Foto da Nota")
        
        if st.button("Enviar Nota"):
            if foto and id_despesa:
                try:
                    # Garantir salvamento como texto exato
                    valor_str = f"{valor:.2f}"
                    nome_personalizado = f"{valor_str}_{data}_{id_despesa}"
                    response = requests.post(
                        "https://api.imgbb.com/1/upload",
                        params={"key": IMGBB_API_KEY, "name": nome_personalizado},
                        files={"image": foto.getvalue()}
                    )
                    data_json = response.json()
                    url_foto = data_json['data']['url']
                    
                    # Salvar valor como string na planilha
                    sheet_notas.append_row([id_despesa, str(data), valor_str, estabelecimento, url_foto, st.session_state.logged_in_user, "Ativo"])
                    st.success("Nota salva!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Preencha o ID/Tipo e tire a foto.")
    
    with tab2:
        all_notes = sheet_notas.get_all_records()
        user_rows = [r for r in all_notes if r.get('Usuario') == st.session_state.logged_in_user and r.get('Status') == "Ativo"]
        if user_rows:
            # Força a conversão para string com vírgula antes de exibir
            escolha = st.selectbox("Selecione sua nota:", [f"R$ {str(r['Valor']).replace('.', ',')} - {r['Data']} - {r['ID']}" for r in user_rows])
            nota = next(r for r in user_rows if f"R$ {str(r['Valor']).replace('.', ',')} - {r['Data']} - {r['ID']}" == escolha)
            st.image(nota['Link_Foto'])
            
            img_data = requests.get(nota['Link_Foto']).content
            st.download_button("Baixar Foto", data=img_data, file_name=f"R${str(nota['Valor']).replace('.', ',')}_{nota['Data']}_{nota['ID']}.jpg", mime="image/jpeg")
            
            if st.button("Mover para Lixeira"):
                row_idx = all_notes.index(nota) + 2
                sheet_notas.update_cell(row_idx, 7, "Lixeira")
                st.rerun()
        else: st.write("Nenhuma nota ativa.")
        
    with tab3:
        all_notes = sheet_notas.get_all_records()
        trash_rows = [r for r in all_notes if r.get('Usuario') == st.session_state.logged_in_user and r.get('Status') == "Lixeira"]
        if trash_rows:
            escolha_trash = st.selectbox("Notas na Lixeira:", [f"R$ {str(r['Valor']).replace('.', ',')} - {r['Data']} - {r['ID']}" for r in trash_rows])
            nota_trash = next(r for r in trash_rows if f"R$ {str(r['Valor']).replace('.', ',')} - {r['Data']} - {r['ID']}" == escolha_trash)
            st.image(nota_trash['Link_Foto'])
            
            img_data_trash = requests.get(nota_trash['Link_Foto']).content
            st.download_button("Baixar Foto da Lixeira", data=img_data_trash, file_name=f"R${str(nota_trash['Valor']).replace('.', ',')}_{nota_trash['Data']}_{nota_trash['ID']}.jpg", mime="image/jpeg")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Restaurar Nota"):
                    row_idx = all_notes.index(nota_trash) + 2
                    sheet_notas.update_cell(row_idx, 7, "Ativo")
                    st.rerun()
            with col2:
                if st.button("Excluir Definitivamente"):
                    row_idx = all_notes.index(nota_trash) + 2
                    sheet_notas.delete_rows(row_idx)
                    st.success("Nota excluída definitivamente")
                    st.rerun()
        else: st.write("Lixeira vazia.")
                
    if st.button("Sair"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()