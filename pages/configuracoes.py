import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado!")
    st.stop()

if st.session_state.get('perfil') != "ADM":
    st.warning("⚠️ Acesso restrito ao Administrador.")
    st.stop()

st.set_page_config(page_title="Configurações | Filtros DC", layout="wide")

# Conexão para escrita (Cadastro) e Link para leitura (Visualização)
# No arquivo configuracoes.py, tente mudar para:
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

# Se o erro "Spreadsheet must be specified" persistir, force assim:
# conn.update(spreadsheet=URL_PLANILHA, worksheet="Usuarios", data=df_final)
conn = st.connection("gsheets", type=GSheetsConnection)
ID_PLANILHA = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_USUARIOS = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/gviz/tq?tqx=out:csv&sheet=Usuarios"

def carregar_usuarios():
    try:
        df = pd.read_csv(URL_USUARIOS)
        df.columns = [c.replace('"', '').strip() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

# --- INTERFACE ---
st.title("⚙️ Configurações do Sistema")

aba1, aba2 = st.tabs(["👤 Gestão de Usuários", "🔄 Manutenção"])

with aba1:
    col_lista, col_form = st.columns([1.5, 1])
    
    with col_lista:
        st.subheader("Usuários Atuais")
        df_u = carregar_usuarios()
        if not df_u.empty:
            st.dataframe(df_u[['USUARIO', 'PERFIL']], use_container_width=True, hide_index=True)

    with col_form:
        st.subheader("Cadastrar Novo")
        with st.form("form_novo_usuario", clear_on_submit=True):
            novo_nome = st.text_input("Nome do Usuário (Login)").upper()
            nova_senha = st.text_input("Senha", type="password")
            novo_perfil = st.selectbox("Nível de Acesso", ["OPER", "ADM"])
            
            if st.form_submit_button("✅ Salvar Usuário"):
                if novo_nome and nova_senha:
                    try:
                        # Lê a base atual via conector
                        df_atual = conn.read(worksheet="Usuarios", ttl=0)
                        # Prepara o novo usuário
                        novo_u = pd.DataFrame([{
                            "USUARIO": novo_nome.strip(), 
                            "SENHA": nova_senha.strip(), 
                            "PERFIL": novo_perfil
                        }])
                        # Une e salva
                        df_final = pd.concat([df_atual, novo_u], ignore_index=True)
                        conn.update(worksheet="Usuarios", data=df_final)
                        
                        st.success(f"Usuário {novo_nome} criado!")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
                else:
                    st.warning("Preencha todos os campos.")

with aba2:
    st.subheader("Controle de Cache")
    if st.button("🔄 Forçar Atualização de Dados"):
        st.cache_data.clear()
        st.success("Sistema sincronizado com a planilha!")

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)
