import streamlit as st
import pandas as pd

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Filtros DC | ERP", page_icon="💧", layout="wide")

# Estilização CSS personalizada para dar um ar mais moderno
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #004a99; color: white; }
    .stTextInput>div>div>input { border-radius: 5px; }
    .login-card { background-color: white; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# 2. DADOS DA CONEXÃO
ID_PLANILHA = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
GID_USUARIOS = "50561049"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv&gid={GID_USUARIOS}"

def verificar_login(usuario, senha):
    try:
        df_user = pd.read_csv(URL_CSV)
        df_user.columns = [c.strip().upper() for c in df_user.columns]
        df_user = df_user.astype(str)
        
        user_match = df_user[
            (df_user['USUARIO'].str.strip().str.upper() == str(usuario).strip().upper()) & 
            (df_user['SENHA'].str.strip() == str(senha).strip())
        ]
        
        if not user_match.empty:
            return True, user_match.iloc[0]['PERFIL']
    except Exception as e:
        st.error(f"Erro ao ler banco de dados: {e}")
    return False, None

# --- LÓGICA DE NAVEGAÇÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    # Centralização do Form de Login
    _, col_central, _ = st.columns([1, 1.2, 1])
    
    with col_central:
        st.image("LOGO Horizontal.jpg", use_container_width=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.subheader("🔐 Acesso ao Sistema")
        
        with st.form("login_form"):
            user_input = st.text_input("Usuário")
            pass_input = st.text_input("Senha", type="password")
            btn_login = st.form_submit_button("ENTRAR NO SISTEMA")
            
            if btn_login:
                sucesso, perfil = verificar_login(user_input, pass_input)
                if sucesso:
                    st.session_state.logado = True
                    st.session_state.perfil = perfil
                    st.session_state.usuario_atual = user_input.upper()
                    st.rerun()
                else:
                    st.error("⚠️ Usuário ou senha inválidos.")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # --- PÁGINA LOGADA ---
    # Barra Lateral com Logo e Info
    st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)
    st.sidebar.divider()
    st.sidebar.success(f"👤 **{st.session_state.usuario_atual}**")
    st.sidebar.info(f"Nível: {st.session_state.perfil}")
    
    if st.sidebar.button("🚪 Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()
    
    # Dashboard de Boas-vindas
    st.title(f"👋 Bem-vindo, {st.session_state.usuario_atual}!")
    st.markdown("---")
    
    # Cartões de Resumo (Exemplo Estético)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Status da Conexão", "Online", delta="Google Sheets")
    with c2:
        st.metric("Base de Dados", "ERP Nuvem", delta="Sincronizado")
    with c3:
        st.metric("Último Login", "Hoje", delta="Seguro")

    st.info("Utilize o menu lateral para navegar entre Clientes, Produtos e Vendas.")